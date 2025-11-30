# quiz/views.py - COMPLETE IMPROVED VERSION
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import requests
import re
import random
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "llama3"

# Comprehensive question domains with weighted topics
QUESTION_DOMAINS = {
    "संविधान": {
        "weight": 0.25,
        "topics": ["मौलिक हक", "राष्ट्रपति", "संसद", "प्रदेश व्यवस्था", "न्यायपालिका", "मूलभूत हक", "नागरिकता", "राज्यको नीति"]
    },
    "इतिहास": {
        "weight": 0.20,
        "topics": ["शाह वंश", "राणा शासन", "एकीकरण", "जनआन्दोलन", "प्राचीन नेपाल", "किराँत काल", "लिच्छवि काल", "भक्तपुर"]
    },
    "भूगोल": {
        "weight": 0.15,
        "topics": ["हिमाल", "नदी", "जलवायु", "मृदा", "वन", "पर्यटन", "प्राकृतिक सम्पदा", "जैविक विविधता"]
    },
    "अर्थशास्त्र": {
        "weight": 0.15,
        "topics": ["कृषि", "उद्योग", "व्यापार", "रोजगार", "विकास", "बजेट", "गरिबी", "आर्थिक योजना"]
    },
    "लोकसेवा": {
        "weight": 0.10,
        "topics": ["लोकसेवा ऐन", "कार्यालय व्यवस्थापन", "निजामती ऐन", "लेखापरीक्षण", "राजस्व", "सार्वजनिक खरीद"]
    },
    "विज्ञान": {
        "weight": 0.08,
        "topics": ["सूचना प्रविधि", "स्वास्थ्य", "प्रविधि", "अनुसन्धान", "डिजिटल नेपाल", "कम्प्युटर", "इन्टरनेट"]
    },
    "वर्तमान": {
        "weight": 0.07,
        "topics": ["वर्तमान घटना", "राजनीति", "अर्थतन्त्र", "सामाजिक", "अन्तर्राष्ट्रिय", "खेलकुद", "मनोरञ्जन"]
    }
}

# Multiple question patterns for variety
QUESTION_PATTERNS = [
    "{topic} सम्बन्धी कुन कुरा सही छ?",
    "{topic} को संदर्भमा कुन गलत छ?",
    "नेपालमा {topic} को सन्दर्भमा कुन सत्य हो?",
    "{topic} बारे कुन कथन उचित छ?",
    "{topic} सम्बन्धी महत्वपूर्ण तथ्य के हो?",
    "{topic} को क्षेत्रमा नेपालले के गर्छ?",
    "{topic} बारे ऐतिहासिक कुरा के हो?",
    "नेपालको {topic} बारे कुन कुरा ठिक छ?",
    "{topic} सम्बन्धी नेपालमा के लागू हुन्छ?",
    "{topic} को विषयमा कुन उत्तर सही हो?"
]

# Difficulty levels with characteristics
DIFFICULTY_LEVELS = {
    "सजिलो": {"temperature": 0.7, "hint": "सरल प्रश्न बनाउनुहोस्"},
    "मध्यम": {"temperature": 0.8, "hint": "मध्यम कठिनाइको प्रश्न बनाउनुहोस्"},
    "कठिन": {"temperature": 0.9, "hint": "कठिन प्रश्न बनाउनुहोस्"}
}

def home(request):
    """Initialize session for quiz"""
    if 'used_questions' not in request.session:
        request.session['used_questions'] = []
    if 'used_topics' not in request.session:
        request.session['used_topics'] = []
    if 'question_context' not in request.session:
        request.session['question_context'] = {
            "last_domain": "",
            "last_topic": "",
            "consecutive_same": 0,
            "total_questions": 0,
            "domain_stats": {}
        }
    if 'quiz_start_time' not in request.session:
        request.session['quiz_start_time'] = datetime.now().isoformat()
    
    return render(request, 'home.html')

@csrf_exempt
@require_http_methods(["GET"])
def api_new_question(request):
    """Generate a new unique question"""
    try:
        # Get strategic domain and topic
        domain, topic = get_strategic_topic(request.session)
        difficulty = get_adaptive_difficulty(request.session)
        
        logger.info(f"Generating question - Domain: {domain}, Topic: {topic}, Difficulty: {difficulty}")
        
        # Try multiple generation attempts
        for attempt in range(12):
            question_data = generate_single_question(domain, topic, difficulty, request.session, attempt)
            
            if question_data and validate_question_quality(question_data, request.session):
                return save_and_return_question(question_data, domain, topic, difficulty, request)
            
            # Small delay between attempts
            import time
            time.sleep(0.3)
        
        # If all attempts fail, use intelligent fallback
        return get_intelligent_fallback(domain, topic, request)
        
    except Exception as e:
        logger.error(f"Error in api_new_question: {e}")
        return get_emergency_fallback(request)

def get_strategic_topic(session):
    """Select domain and topic with optimal diversity"""
    context = session.get('question_context', {})
    used_topics = session.get('used_topics', [])
    domain_stats = context.get('domain_stats', {})
    
    # Calculate domain weights considering usage
    domain_weights = {}
    for domain, info in QUESTION_DOMAINS.items():
        base_weight = info['weight']
        domain_count = domain_stats.get(domain, 0)
        
        # Reduce weight for overused domains
        if domain_count > 0:
            usage_ratio = domain_count / (context.get('total_questions', 1))
            if usage_ratio > base_weight * 2:  # If used more than expected
                adjusted_weight = base_weight * 0.5
            else:
                adjusted_weight = base_weight
        else:
            adjusted_weight = base_weight * 1.5  # Boost unused domains
        
        domain_weights[domain] = adjusted_weight
    
    # Normalize weights
    total_weight = sum(domain_weights.values())
    normalized_weights = {domain: weight/total_weight for domain, weight in domain_weights.items()}
    
    # Select domain
    domains = list(normalized_weights.keys())
    weights = list(normalized_weights.values())
    selected_domain = random.choices(domains, weights=weights, k=1)[0]
    
    # Select topic within domain (prefer less used topics)
    available_topics = QUESTION_DOMAINS[selected_domain]['topics']
    
    # Calculate topic usage
    topic_usage = {}
    for topic in available_topics:
        usage_count = sum(1 for used_topic in used_topics if f"{selected_domain}:{topic}" == used_topic)
        topic_usage[topic] = usage_count
    
    # Prefer less used topics
    if topic_usage:
        min_usage = min(topic_usage.values())
        candidate_topics = [t for t, count in topic_usage.items() if count <= min_usage + 1]
        selected_topic = random.choice(candidate_topics)
    else:
        selected_topic = random.choice(available_topics)
    
    return selected_domain, selected_topic

def get_adaptive_difficulty(session):
    """Adjust difficulty based on user performance"""
    context = session.get('question_context', {})
    total_questions = context.get('total_questions', 0)
    
    # Start easy, gradually increase difficulty
    if total_questions < 3:
        return "सजिलो"
    elif total_questions < 8:
        return "मध्यम"
    else:
        # Mix difficulties for experienced users
        return random.choices(["मध्यम", "कठिन"], weights=[0.6, 0.4])[0]

def generate_single_question(domain, topic, difficulty, session, attempt):
    """Generate one question attempt"""
    # Vary pattern based on attempt
    pattern_index = (attempt % len(QUESTION_PATTERNS))
    question_pattern = QUESTION_PATTERNS[pattern_index]
    question_text = question_pattern.format(topic=topic)
    
    prompt = build_enhanced_prompt(domain, topic, question_text, difficulty, session)
    raw_response = ollama_generate(prompt, difficulty)
    
    if not raw_response or "Error" in raw_response:
        return None
    
    return parse_question_response(raw_response, domain, topic)

def build_enhanced_prompt(domain, topic, question_text, difficulty, session):
    """Build comprehensive prompt for question generation"""
    used_questions = session.get('used_questions', [])
    context = session.get('question_context', {})
    
    # Include context about what to avoid
    avoidance_context = ""
    if used_questions:
        recent_questions = used_questions[-4:]  # Last 4 questions
        avoidance_context = "\n\nयी जस्ता प्रश्नहरू नदोहोर्याउनुहोस्:\n" + "\n".join(f"✗ {q}" for q in recent_questions)
    
    # Include domain-specific guidance
    domain_guidance = get_domain_guidance(domain)
    
    difficulty_info = DIFFICULTY_LEVELS[difficulty]
    
    prompt = f"""
तपाईं नेपाल लोक सेवा आयोग (नायब सुब्बा / शाखा अधिकृत) को तयारीको लागि {difficulty} स्तरको प्रश्न बनाउनुहोस्।

विषय क्षेत्र: {domain}
विशेष उपविषय: {topic}
{difficulty_info['hint']}

{domain_guidance}

{avoidance_context}

आवश्यक निर्देशन:
- प्रश्न पूर्ण रूपमा नेपाली संदर्भमा हुनुपर्छ
- विकल्पहरू वास्तविक, तार्किक र स्पष्ट हुनुपर्छ
- सही उत्तर एउटा मात्र हुनुपर्छ
- प्रश्न र विकल्पहरू मौलिक र नयाँ हुनुपर्छ
- विकल्पहरूको लम्बाइ लगभग बराबर हुनुपर्छ

ढाँचा (कुनै अतिरिक्त टिप्पणी नदिनुहोस्):
प्रश्न: {question_text}
क) पहिलो विकल्प
ख) दोस्रो विकल्प
ग) तेस्रो विकल्प
घ) चौथो विकल्प
सही जवाफ: ख

अब तपाईंको प्रश्न बनाउनुहोस्:
"""
    return prompt

def get_domain_guidance(domain):
    """Get domain-specific guidance for better questions"""
    guidance = {
        "संविधान": "संवैधानिक धारा, मौलिक हक, राज्यसंरचना सम्बन्धी प्रश्न हुनुपर्छ।",
        "इतिहास": "ऐतिहासिक तथ्य, तिथि, व्यक्तित्व, घटनाक्रममा आधारित प्रश्न हुनुपर्छ।",
        "भूगोल": "भौगोलिक अवस्थिति, जलवायु, प्राकृतिक सम्पदा, पर्यटन सम्बन्धी प्रश्न हुनुपर्छ।",
        "अर्थशास्त्र": "आर्थिक नीति, योजना, विकास, व्यापार, रोजगार सम्बन्धी प्रश्न हुनुपर्छ।",
        "लोकसेवा": "लोकसेवा ऐन, कार्यालय व्यवस्थापन, निजामती नियम सम्बन्धी प्रश्न हुनुपर्छ।",
        "विज्ञान": "प्रविधि, डिजिटलाइजेसन, विज्ञानका नयाँ आविष्कार सम्बन्धी प्रश्न हुनुपर्छ।",
        "वर्तमान": "हालैका घटनाक्रम, नीति परिवर्तन, सामाजिक अभियान सम्बन्धी प्रश्न हुनुपर्छ।"
    }
    return guidance.get(domain, "सामान्य ज्ञानमा आधारित प्रश्न हुनुपर्छ।")

def parse_question_response(raw_text, domain, topic):
    """Robust parsing of question response"""
    try:
        # Clean and normalize text
        clean_text = re.sub(r'\n+', '\n', raw_text.strip())
        lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
        
        if not lines:
            return None
        
        # Find question line
        question = None
        for i, line in enumerate(lines):
            if line.startswith('प्रश्न:') or '?' in line or 'कुन' in line or 'के' in line:
                if line.startswith('प्रश्न:'):
                    question = line[7:].strip()  # Remove 'प्रश्न:'
                else:
                    question = line
                break
        
        if not question:
            # If no clear question found, use first line
            question = lines[0]
        
        # Extract options
        options = {}
        option_patterns = [
            r"^([कखगघ])\)\s*(.+)",
            r"^([कखगघ])\.\s*(.+)", 
            r"^([कखगघ])\s*-\s*(.+)",
            r"^([कखगघ])\s*:\s*(.+)"
        ]
        
        for line in lines:
            for pattern in option_patterns:
                match = re.match(pattern, line)
                if match:
                    letter, text = match.groups()
                    if letter in "कखगघ" and letter not in options:
                        options[letter] = text.strip()
                        break
        
        # Ensure we have exactly 4 options
        if len(options) != 4:
            # Try to find options in different formats
            option_letters = ['क', 'ख', 'ग', 'घ']
            for i, line in enumerate(lines):
                for j, letter in enumerate(option_letters):
                    if letter not in options and i + j < len(lines):
                        potential_option = lines[i + j].strip()
                        if potential_option and len(potential_option) > 2:
                            options[letter] = potential_option
        
        # Find correct answer
        correct_letter = None
        answer_patterns = [
            r"सही जवाफ[:\s]*([कखगघ])",
            r"सही उत्तर[:\s]*([कखगघ])",
            r"जवाफ[:\s]*([कखगघ])",
            r"उत्तर[:\s]*([कखगघ])",
            r"correct answer[:\s]*([कखगघ])"
        ]
        
        for line in lines:
            line_lower = line.lower()
            for pattern in answer_patterns:
                match = re.search(pattern, line_lower)
                if match:
                    correct_letter = match.group(1)
                    break
            if correct_letter:
                break
        
        # If still no correct answer, choose randomly but logically
        if not correct_letter and len(options) == 4:
            # Prefer 'ख' or 'ग' as they are often correct in well-designed questions
            correct_letter = random.choice(["ख", "ग", "क", "घ"])
        
        if question and len(options) == 4 and correct_letter in options:
            return {
                'question': question,
                'options': options,
                'correct_letter': correct_letter,
                'domain': domain,
                'topic': topic,
                'raw_response': clean_text[:200]  # Store snippet for debugging
            }
    
    except Exception as e:
        logger.error(f"Error parsing question: {e}")
    
    return None

def validate_question_quality(question_data, session):
    """Comprehensive quality validation"""
    question = question_data['question']
    options = question_data['options']
    used_questions = session.get('used_questions', [])
    
    # Basic validation
    if not question or len(question) < 10 or len(question) > 300:
        return False
    
    # Check for exact duplicate
    if question in used_questions:
        return False
    
    # Check option quality
    option_texts = list(options.values())
    option_lengths = [len(opt) for opt in option_texts]
    
    # Options should not be too short or too long
    if any(len(opt) < 2 for opt in option_texts) or any(len(opt) > 150 for opt in option_texts):
        return False
    
    # Options should have reasonable length variation
    if max(option_lengths) - min(option_lengths) > 80:
        return False
    
    # Check for semantic similarity with recent questions
    recent_questions = used_questions[-8:] if len(used_questions) >= 8 else used_questions
    for used_q in recent_questions:
        similarity = calculate_text_similarity(question, used_q)
        if similarity > 0.75:  # Too similar
            return False
    
    # Check option uniqueness
    if len(set(option_texts)) < 3:  # At least 3 unique options
        return False
    
    return True

def calculate_text_similarity(text1, text2):
    """Basic text similarity calculation"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0

def save_and_return_question(question_data, domain, topic, difficulty, request):
    """Save question to session and return JSON response"""
    # Update used questions
    used_questions = request.session.get('used_questions', [])
    used_questions.append(question_data['question'])
    request.session['used_questions'] = used_questions[-100:]  # Keep last 100
    
    # Update used topics
    used_topics = request.session.get('used_topics', [])
    used_topics.append(f"{domain}:{topic}")
    request.session['used_topics'] = used_topics[-80:]
    
    # Update question context and statistics
    context = request.session.get('question_context', {})
    context['total_questions'] = context.get('total_questions', 0) + 1
    context['last_domain'] = domain
    context['last_topic'] = topic
    context['domain_stats'][domain] = context['domain_stats'].get(domain, 0) + 1
    
    # Track consecutive same domain
    if context.get('last_domain') == domain:
        context['consecutive_same'] = context.get('consecutive_same', 0) + 1
    else:
        context['consecutive_same'] = 1
    
    request.session['question_context'] = context
    request.session['current_question'] = question_data
    request.session.modified = True
    
    logger.info(f"Successfully generated question #{context['total_questions']} in {domain}/{topic}")
    
    return JsonResponse({
        "success": True,
        "question": question_data['question'],
        "options": question_data['options'],
        "correct_letter": question_data['correct_letter'],
        "domain": domain,
        "topic": topic,
        "difficulty": difficulty,
        "stats": {
            "total_questions": context['total_questions'],
            "domain_stats": context['domain_stats']
        }
    })

def get_intelligent_fallback(domain, topic, request):
    """Domain-specific fallback questions"""
    fallback_questions = {
        "संविधान": [
            {
                "question": "नेपालको संविधान अनुसार प्रदेश सभाको कार्यकाल कति वर्षको हुन्छ?",
                "options": {"क": "४ वर्ष", "ख": "५ वर्ष", "ग": "६ वर्ष", "घ": "७ वर्ष"},
                "correct_letter": "ख"
            },
            {
                "question": "नेपालको संविधान कुन मितिमा लागू भयो?",
                "options": {"क": "२०६३ असोज ३", "ख": "२०७२ असोज ३", "ग": "२०६५ असोज ३", "घ": "२०७५ असोज ३"},
                "correct_letter": "ख"
            }
        ],
        "इतिहास": [
            {
                "question": "नेपाल एकीकरणको प्रक्रिया कसले सुरु गरेका थिए?",
                "options": {"क": "पृथ्वीनारायण शाह", "ख": "महेन्द्र वीर विक्रम शाह", "ग": "वीर शमशेर", "घ": "जंगबहादुर राणा"},
                "correct_letter": "क"
            }
        ],
        "भूगोल": [
            {
                "question": "नेपालको सबैभन्दा अग्लो हिमाल कुन हो?",
                "options": {"क": "कञ्चनजङ्घा", "ख": "मकालु", "ग": "सगरमाथा", "घ": "धौलागिरी"},
                "correct_letter": "ग"
            }
        ],
        "अर्थशास्त्र": [
            {
                "question": "नेपालको राष्ट्रिय आय गणनाको मुख्य आधार के हो?",
                "options": {"क": "कृषि", "ख": "उद्योग", "ग": "व्यापार", "घ": "सबै"},
                "correct_letter": "घ"
            }
        ]
    }
    
    # Get domain-specific fallback or general fallback
    if domain in fallback_questions:
        fallback = random.choice(fallback_questions[domain])
    else:
        fallback = {
            "question": f"नेपालमा {topic} को महत्व के छ?",
            "options": {"क": "आर्थिक", "ख": "सामाजिक", "ग": "राजनीतिक", "घ": "सबै"},
            "correct_letter": random.choice(["क", "ख", "ग", "घ"])
        }
    
    fallback.update({
        'domain': domain,
        'topic': topic,
        'raw_response': 'fallback'
    })
    
    return save_and_return_question(fallback, domain, topic, "सजिलो", request)

def get_emergency_fallback(request):
    """Final emergency fallback"""
    emergency_questions = [
        {
            "question": "नेपालको राष्ट्रिय जनावर कुन हो?",
            "options": {"क": "गाई", "ख": "गैंडा", "ग": "हात्ती", "घ": "बाघ"},
            "correct_letter": "ख",
            "domain": "सामान्य ज्ञान",
            "topic": "राष्ट्रिय प्रतीक"
        },
        {
            "question": "नेपालको राजधानी कुन हो?",
            "options": {"क": "पोखरा", "ख": "विराटनगर", "ग": "काठमाडौँ", "घ": "भरतपुर"},
            "correct_letter": "ग",
            "domain": "सामान्य ज्ञान", 
            "topic": "भूगोल"
        }
    ]
    
    fallback = random.choice(emergency_questions)
    return save_and_return_question(fallback, fallback['domain'], fallback['topic'], "सजिलो", request)

@csrf_exempt
@require_http_methods(["POST"])
def api_check_answer(request):
    """Check user's answer and provide feedback"""
    try:
        # Handle both form data and JSON
        if request.content_type == 'application/json':
            user_data = request.json()
        else:
            user_data = request.POST
        
        user_choice = user_data.get("choice", "").strip()
        if not user_choice:
            return JsonResponse({"error": "Choice is required"}, status=400)
            
    except Exception as e:
        logger.error(f"Error parsing check_answer request: {e}")
        return JsonResponse({"error": "Invalid request format"}, status=400)
    
    current_data = request.session.get('current_question', {})
    if not current_data:
        return JsonResponse({"error": "No active question found"}, status=400)
    
    correct_letter = current_data.get('correct_letter', '')
    user_question = current_data.get('question', '')
    
    if not correct_letter:
        return JsonResponse({"error": "No correct answer stored"}, status=400)
    
    # Basic comparison
    is_correct = user_choice == correct_letter
    
    # Generate explanation for correct answers
    explanation = ""
    if is_correct:
        explanation = generate_question_explanation(current_data)
    
    # Update session statistics if needed
    context = request.session.get('question_context', {})
    if is_correct:
        context['correct_answers'] = context.get('correct_answers', 0) + 1
    context['total_answered'] = context.get('total_answered', 0) + 1
    request.session['question_context'] = context
    
    return JsonResponse({
        "correct": is_correct,
        "your_choice": user_choice,
        "correct_answer": correct_letter,
        "correct_text": current_data['options'].get(correct_letter, ""),
        "explanation": explanation,
        "question": user_question,
        "domain": current_data.get('domain', ''),
        "topic": current_data.get('topic', ''),
        "stats": {
            "correct_answers": context.get('correct_answers', 0),
            "total_answered": context.get('total_answered', 0)
        }
    })

def generate_question_explanation(question_data):
    """Generate explanation for correct answer"""
    prompt = f"""
प्रश्न: {question_data['question']}
सही उत्तर: {question_data['correct_letter']}) {question_data['options'][question_data['correct_letter']]}

यो उत्तर किन सही छ? २-३ वाक्यमा संक्षिप्त व्याख्या गर्नुहोस्:
"""
    
    explanation = ollama_generate(prompt, "सजिलो")
    return explanation if explanation and "Error" not in explanation else "यो सही उत्तर हो।"

def ollama_generate(prompt, difficulty="मध्यम"):
    """Generate response from Ollama with retry logic"""
    difficulty_settings = DIFFICULTY_LEVELS.get(difficulty, DIFFICULTY_LEVELS["मध्यम"])
    
    for attempt in range(3):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": difficulty_settings["temperature"],
                        "top_p": 0.9,
                        "num_ctx": 4096,
                        "repeat_penalty": 1.1
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            else:
                logger.warning(f"Ollama API returned status {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.warning(f"Ollama timeout on attempt {attempt + 1}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in ollama_generate: {e}")
        
        # Wait before retry
        if attempt < 2:
            import time
            time.sleep(1)
    
    return None

@csrf_exempt
@require_http_methods(["POST"])
def api_reset_quiz(request):
    """Reset quiz session"""
    request.session.flush()
    return JsonResponse({"success": True, "message": "Quiz reset successfully"})

@require_http_methods(["GET"])
def api_quiz_stats(request):
    """Get quiz statistics"""
    context = request.session.get('question_context', {})
    return JsonResponse({
        "total_questions": context.get('total_questions', 0),
        "correct_answers": context.get('correct_answers', 0),
        "total_answered": context.get('total_answered', 0),
        "domain_stats": context.get('domain_stats', {}),
        "quiz_start_time": request.session.get('quiz_start_time')
    })