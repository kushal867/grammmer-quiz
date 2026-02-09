# quiz/views.py - CLEAN REFACTORED VERSION
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import requests
import re
import random
import json
import logging
import time
from datetime import datetime

# Import models
from .models import Question, UserAnswer, QuizAttempt, BookmarkedQuestion
# Import utilities and constants
from .utils import save_question_to_db, save_user_answer, check_achievements
from .constants import QUESTION_DOMAINS, DIFFICULTY_LEVELS
from .ai_engine import generate_single_question, validate_question_quality, generate_question_explanation

logger = logging.getLogger(__name__)

def home(request):
    """Initialize session for quiz"""
    session_defaults = {
        'used_questions': [],
        'used_topics': [],
        'question_context': {
            "last_domain": "",
            "last_topic": "",
            "consecutive_same": 0,
            "total_questions": 0,
            "domain_stats": {}
        },
        'quiz_start_time': datetime.now().isoformat()
    }
    
    for key, value in session_defaults.items():
        if key not in request.session:
            request.session[key] = value
            
    return render(request, 'home.html')

@csrf_exempt
@require_http_methods(["GET"])
def api_new_question(request):
    """Generate a new unique question"""
    try:
        # Get strategic domain and topic
        domain, topic = get_strategic_topic(request.session)
        difficulty = get_adaptive_difficulty(request.session)
        
        logger.info(f"Question request - Domain: {domain}, Topic: {topic}, Difficulty: {difficulty}")
        
        # Generation loop with limited attempts
        for attempt in range(8):
            question_data = generate_single_question(domain, topic, difficulty, request.session, attempt)
            
            if question_data and validate_question_quality(question_data, request.session):
                return save_and_return_question(question_data, domain, topic, difficulty, request)
            
            time.sleep(0.2) # Small backoff
        
        # Fallback if AI fails
        return get_intelligent_fallback(domain, topic, request)
        
    except Exception as e:
        logger.error(f"Failed to generate question: {e}", exc_info=True)
        return get_emergency_fallback(request)

def get_strategic_topic(session):
    """Select domain and topic with optimal diversity to prevent repetition"""
    context = session.get('question_context', {})
    used_topics = session.get('used_topics', [])
    domain_stats = context.get('domain_stats', {})
    total_q = context.get('total_questions', 0)
    
    # Calculate weighted domain selection
    weighted_domains = []
    for domain, info in QUESTION_DOMAINS.items():
        weight = info['weight']
        count = domain_stats.get(domain, 0)
        
        # Adjust weight based on usage
        if total_q > 0:
            usage_ratio = count / total_q
            if usage_ratio > weight * 1.5: weight *= 0.3 # Penalize overuse
            elif count == 0: weight *= 2.0 # Boost unused
            
        weighted_domains.append((domain, weight))
    
    domains, weights = zip(*weighted_domains)
    selected_domain = random.choices(domains, weights=weights, k=1)[0]
    
    # Select topic (favoring less used ones)
    topics = QUESTION_DOMAINS[selected_domain]['topics']
    topic_scores = []
    for t in topics:
        usage = sum(1 for ut in used_topics if f"{selected_domain}:{t}" == ut)
        topic_scores.append((t, 1 / (usage + 1)))
        
    topics_list, scores = zip(*topic_scores)
    selected_topic = random.choices(topics_list, weights=scores, k=1)[0]
    
    return selected_domain, selected_topic

def get_adaptive_difficulty(session):
    """Gradually increase difficulty based on session progression"""
    total = session.get('question_context', {}).get('total_questions', 0)
    if total < 3: return "सजिलो"
    if total < 7: return "मध्यम"
    return random.choices(["मध्यम", "कठिन"], weights=[0.6, 0.4])[0]

def save_and_return_question(question_data, domain, topic, difficulty, request):
    """Core logic to persist and transmit question data"""
    try:
        db_q = save_question_to_db(question_data, difficulty)
        qid = db_q.id
    except Exception as e:
        logger.error(f"DB save error: {e}")
        qid = None
    
    # Update Session
    session = request.session
    session['used_questions'] = (session.get('used_questions', []) + [question_data['question']])[-50:]
    session['used_topics'] = (session.get('used_topics', []) + [f"{domain}:{topic}"])[-40:]
    
    ctx = session.get('question_context', {})
    ctx['total_questions'] = ctx.get('total_questions', 0) + 1
    ctx['domain_stats'][domain] = ctx['domain_stats'].get(domain, 0) + 1
    ctx['consecutive_same'] = (ctx['consecutive_same'] + 1) if ctx.get('last_domain') == domain else 1
    ctx['last_domain'] = domain
    ctx['last_topic'] = topic
    
    session['question_context'] = ctx
    session['current_question'] = question_data
    session['current_question_id'] = qid
    session.modified = True
    
    return JsonResponse({
        "success": True,
        "question": question_data['question'],
        "options": question_data['options'],
        "correct_letter": question_data['correct_letter'],
        "domain": domain,
        "topic": topic,
        "difficulty": difficulty,
        "question_id": qid,
        "stats": {"total": ctx['total_questions'], "stats": ctx['domain_stats']}
    })

@csrf_exempt
@require_http_methods(["POST"])
def api_check_answer(request):
    """Verify user selection and provide rich feedback"""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        choice = data.get("choice", "").strip()
        if not choice: return JsonResponse({"error": "Missing choice"}, status=400)
            
        current = request.session.get('current_question', {})
        if not current: return JsonResponse({"error": "No active question"}, status=400)
        
        is_correct = choice == current.get('correct_letter')
        explanation = generate_question_explanation(current)
        
        # Update stats
        ctx = request.session.get('question_context', {})
        if is_correct: ctx['correct_answers'] = ctx.get('correct_answers', 0) + 1
        ctx['total_answered'] = ctx.get('total_answered', 0) + 1
        request.session['question_context'] = ctx
        
        # Bookmark status
        bookmarked = False
        if request.user.is_authenticated and request.session.get('current_question_id'):
            bookmarked = BookmarkedQuestion.objects.filter(
                user=request.user, question_id=request.session['current_question_id']
            ).exists()

        return JsonResponse({
            "correct": is_correct,
            "correct_answer": current.get('correct_letter'),
            "explanation": explanation,
            "is_bookmarked": bookmarked,
            "stats": {
                "correct": ctx.get('correct_answers', 0),
                "total": ctx.get('total_answered', 0)
            }
        })
    except Exception as e:
        logger.error(f"Check answer error: {e}")
        return JsonResponse({"error": "Processing error"}, status=500)

def get_intelligent_fallback(domain, topic, request):
    """High-reliability fallback questions for when AI is unavailable"""
    fallbacks = {
        "संविधान": {"question": "नेपालको संविधान २०७२ मा कतिवटा अनुसूचीहरू छन्?", "options": {"क": "७", "ख": "८", "ग": "९", "घ": "१०"}, "correct_letter": "ग"},
        "भूगोल": {"question": "नेपालको सबैभन्दा ठूलो जिल्ला (क्षेत्रफलको आधारमा) कुन हो?", "options": {"क": "मुगु", "ख": "डोल्पा", "ग": "हुम्ला", "घ": "ताप्लेजुङ्ग"}, "correct_letter": "ख"}
    }
    fb = fallbacks.get(domain, {"question": f"नेपालमा {topic} को मुख्य विशेषता के हो?", "options": {"क": "भौगोलिक", "ख": "सांस्कृतिक", "ग": "आर्थिक", "घ": "सबै"}, "correct_letter": "घ"})
    fb.update({'domain': domain, 'topic': topic})
    return save_and_return_question(fb, domain, topic, "सजिलो", request)

def get_emergency_fallback(request):
    """Last resort fallback for system critical failures"""
    fb = {"question": "नेपालको राष्ट्रिय झण्डाको आकार कस्तो छ?", "options": {"क": "आयताकार", "ख": "वर्गाकार", "ग": "दुई त्रिकोण मिलेको", "घ": "गोलाकार"}, "correct_letter": "ग", "domain": "सामान्य ज्ञान", "topic": "राष्ट्रिय प्रतीक"}
    return save_and_return_question(fb, fb['domain'], fb['topic'], "सजिलो", request)

@csrf_exempt
def api_reset_quiz(request):
    request.session.flush()
    return JsonResponse({"success": True})

def api_quiz_stats(request):
    ctx = request.session.get('question_context', {})
    return JsonResponse({
        "total": ctx.get('total_questions', 0),
        "correct": ctx.get('correct_answers', 0),
        "answered": ctx.get('total_answered', 0),
        "start_time": request.session.get('quiz_start_time')
    })