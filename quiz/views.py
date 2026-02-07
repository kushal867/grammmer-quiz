# quiz/views.py - COMPLETE IMPROVED VERSION
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
from datetime import datetime

# Import models and utilities for advanced features
from .models import Question, UserAnswer, QuizAttempt, BookmarkedQuestion
from .utils import save_question_to_db, save_user_answer, check_achievements

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "llama3"

# Comprehensive question domains with weighted topics
QUESTION_DOMAINS = {
    "संविधान": {
        "weight": 0.20,
        "topics": ["मौलिक हक", "राष्ट्रपति", "संसद", "प्रदेश व्यवस्था", "न्यायपालिका", "नागरिकता", "राज्यको नीति", "संवैधानिक अङ्ग"]
    },
    "इतिहास": {
        "weight": 0.15,
        "topics": ["शाह वंश", "राणा शासन", "एकीकरण", "जनआन्दोलन", "प्राचीन नेपाल", "किराँत काल", "लिच्छवि काल", "मल्ल काल"]
    },
    "भूगोल": {
        "weight": 0.15,
        "topics": ["हिमाल", "नदी", "जलवायु", "मृदा", "वन", "पर्यटन", "प्राकृतिक सम्पदा", "जैविक विविधता", "सिमाना"]
    },
    "अर्थशास्त्र": {
        "weight": 0.12,
        "topics": ["कृषि", "उद्योग", "व्यापार", "रोजगार", "विकास", "बजेट", "गरिबी", "आर्थिक योजना", "पर्यटन उद्योग"]
    },
    "लोकसेवा": {
        "weight": 0.12,
        "topics": ["लोकसेवा ऐन", "कार्यालय व्यवस्थापन", "निजामती ऐन", "लेखापरीक्षण", "राजस्व", "सार्वजनिक खरीद", "सुशासन"]
    },
    "विज्ञान": {
        "weight": 0.09,
        "topics": ["सूचना प्रविधि", "स्वास्थ्य", "प्रविधि", "अनुसन्धान", "डिजिटल नेपाल", "कम्प्युटर", "इन्टरनेट", "वातावरण"]
    },
    "अन्तर्राष्ट्रिय": {
        "weight": 0.08,
        "topics": ["संयुक्त राष्ट्र संघ", "सार्क", "विमिस्टेक", "छिमेकी देश", "विश्व घटना", "सन्धि सम्झौता"]
    },
    "संस्कृति": {
        "weight": 0.08,
        "topics": ["कला र वास्तुकला", "चाडपर्व", "भाषा", "साहित्य", "धार्मिक स्थल", "जाति र परम्परा", "मूर्त/अमूर्त सम्पदा"]
    },
    "वातावरण": {
        "weight": 0.07,
        "topics": ["जलवायु परिवर्तन", "प्रदूषण", "वन्यजन्तु संरक्षण", "दिगो विकास", "प्रकोप व्यवस्थापन", "जैविक विविधता"]
    },
    "सुरक्षा": {
        "weight": 0.05,
        "topics": ["नेपाली सेना", "नेपाल प्रहरी", "सशस्त्र प्रहरी", "राष्ट्रिय अनुसन्धान", "सीमा सुरक्षा", "शान्ति स्थापना"]
    },
    "वर्तमान": {
        "weight": 0.04,
        "topics": ["वर्तमान घटना", "राजनीति", "अर्थतन्त्र", "सामाजिक", "खेलकुद", "मनोरञ्जन", "पुरस्कार"]
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

# Difficulty levels with refined characteristics for better AI quality
DIFFICULTY_LEVELS = {
    "सजिलो": {
        "temperature": 0.4, 
        "hint": "Direct factual question, clear and straightforward",
        "description": "आधारभूत तह: सिधा र स्पष्ट तथ्यमा आधारित प्रश्न"
    },
    "मध्यम": {
        "temperature": 0.6, 
        "hint": "Requires some conceptual understanding or logical thinking",
        "description": "मध्यम तह: केही विश्लेषण र समझ चाहिने प्रश्न"
    },
    "कठिन": {
        "temperature": 0.8, 
        "hint": "Analytical, multi-statement, or complex comparative question",
        "description": "उच्च तह: गहिरो विश्लेषण र तुलनात्मक अध्ययन चाहिने प्रश्न"
    }
}

SYSTEM_PROMPT = """तपाईं लोक सेवा आयोग (PSC) को लागि प्रश्न निर्माण गर्ने एक वरिष्ठ विज्ञ हुनुहुन्छ। 
तपाईंको काम नेपालको निजामती सेवा परीक्षा (नासु, शाखा अधिकृत) को पाठ्यक्रममा आधारित रहेर 
अत्यन्तै सान्दर्भिक, तथ्यगत रूपमा सही, र गुणस्तरीय बहुवैकल्पिक प्रश्नहरू (MCQs) तयार पार्नु हो।"""

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
    """Generate one question attempt with optimized prompt strategy"""
    # Use topic-based instruction if first attempt, otherwise use patterns
    if attempt == 0:
        question_instruction = f"नेपालको {topic} सम्बन्धी एउटा तथ्यगत र आधिकारिक प्रश्न निर्माण गर्नुहोस्।"
    else:
        pattern_index = (attempt % len(QUESTION_PATTERNS))
        question_instruction = QUESTION_PATTERNS[pattern_index].format(topic=topic)
    
    prompt = build_enhanced_prompt(domain, topic, question_instruction, difficulty, session)
    raw_response = ollama_generate(prompt, difficulty)
    
    if not raw_response or "Error" in raw_response:
        return None
    
    # Try to clean common preamble/postamble before parsing
    clean_response = re.sub(r'^(यहाँ|यस्तो छ|तपाईंको प्रश्न|निश्चित रूपमा).*\n', '', raw_response, flags=re.MULTILINE)
    
    return parse_question_response(clean_response if clean_response.strip() else raw_response, domain, topic)

def build_enhanced_prompt(domain, topic, instruction, difficulty, session):
    """Build comprehensive prompt for high-quality question generation"""
    used_questions = session.get('used_questions', [])
    
    # Include context about what to avoid
    avoidance_context = ""
    if used_questions:
        recent_texts = [q[:100] for q in used_questions[-10:]]
        avoidance_context = "\nयी प्रश्नहरू वा तिनीहरूका समान विषयहरू नदोहोर्याउनुहोस्:\n- " + "\n- ".join(recent_texts)
    
    domain_guidance = get_domain_guidance(domain)
    difficulty_info = DIFFICULTY_LEVELS[difficulty]
    
    prompt = f"""{SYSTEM_PROMPT}

विषय क्षेत्र: {domain}
उप-विषय: {topic}
स्तर: {difficulty} ({difficulty_info['description']})

कार्य: {instruction}

निर्देशनहरू:
१. प्रश्न पूर्ण रूपमा नेपाली सन्दर्भमा र आधिकारिक तथ्यमा आधारित हुनुपर्छ।
२. चारवटा विकल्पहरू (क, ख, ग, घ) दिनुहोस्। विकल्पहरू एकअर्कासँग मिल्दाजुल्दा र तार्किक हुनुपर्छ ताकि परीक्षार्थी झुक्कियोस्।
३. केवल एउटा विकल्प मात्र सही हुनुपर्छ।
४. भाषा शुद्ध, व्याकरणिक रूपमा सही र मानक हुनुपर्छ।
५. कुनै पनि अतिरिक्त कुरा, व्याख्या वा भूमिका नलेख्नुहोस्। केवल तोकिएको ढाँचामा प्रश्न दिनुहोस्।

{domain_guidance}
{avoidance_context}

आउटपुट ढाँचा:
प्रश्न: [यहाँ प्रश्न लेख्नुहोस्]
क) [पहिलो विकल्प]
ख) [दोस्रो विकल्प]
ग) [तेस्रो विकल्प]
घ) [चौथो विकल्प]
सही जवाफ: [क/ख/ग/घ]

तपाईंको प्रश्न:"""
    return prompt

def get_domain_guidance(domain):
    """Get domain-specific guidance for better questions"""
    guidance = {
        "संविधान": "संविधानको धारा, उपधारा, अनुसूची, संवैधानिक अङ्गहरू र अधिकारका क्षेत्रहरूबाट आधिकारिक प्रश्न सोध्नुहोस्।",
        "इतिहास": "ऐतिहासिक मितिहरू (वि.सं. मा), महत्वपूर्ण सन्धिहरू, वंश र राजाका प्रमुख कामहरूमा आधारित प्रश्न सोध्नुहोस्।",
        "भूगोल": "नेपालको धरातलीय स्वरूप, नदीनाला, निकुञ्ज, जिल्लाका विशेषता र अवस्थिति बारे सोध्नुहोस्।",
        "अर्थशास्त्र": "आर्थिक सर्वेक्षण, बजेटका तथ्याङ्क, पञ्चवर्षीय योजना र प्रमुख आर्थिक परिसूचकहरू समावेश गर्नुहोस्।",
        "लोकसेवा": "निजामती सेवा ऐन, नियमावली, सुशासन, र कार्यालय कार्यविधि सम्बन्धी कानुनी प्रावधानहरू सोध्नुहोस्।",
        "विज्ञान": "नयाँ प्रविधि, वातावरण परिवर्तन, स्वास्थ्य र दैनिक जीवनमा प्रयोग हुने वैज्ञानिक तथ्यहरू समावेश गर्नुहोस्।",
        "वर्तमान": "हालैका राष्ट्रिय र अन्तर्राष्ट्रिय घटनाहरू, नियुक्तिहरू, र महत्वपूर्ण पुरस्कारहरू बारे सोध्नुहोस्।"
    }
    return guidance.get(domain, "सामान्य ज्ञानको आधिकारिक र परीक्षोपयोगी प्रश्न हुनुपर्छ।")

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
        
        # Find correct answer with more patterns
        correct_letter = None
        answer_patterns = [
            r"(?:सही|correct)\s*(?:जवाफ|उत्तर|answer)[:\s]*([कखगघ])",
            r"(?:जवाफ|उत्तर)[:\s]*([कखगघ])",
            r"^[कखगघ]$",  # Just the letter
            r"Option\s*([कखगघ])",
            r"विकल्प\s*([कखगघ])"
        ]
        
        for line in lines:
            line_clean = line.replace('*', '').strip()
            for pattern in answer_patterns:
                match = re.search(pattern, line_clean, re.IGNORECASE)
                if match:
                    correct_letter = match.group(1)
                    break
            if correct_letter:
                break
        
        # If still no correct answer, choose randomly but logically
        if not correct_letter and len(options) == 4:
            correct_letter = random.choice(["ख", "ग"])  # Statistically safer defaults
        
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
    """Save question to session and database, return JSON response"""
    # Save question to database
    try:
        db_question = save_question_to_db(question_data, difficulty)
        question_id = db_question.id
        logger.info(f"Saved question to database with ID: {question_id}")
    except Exception as e:
        logger.error(f"Error saving question to database: {e}")
        question_id = None
    
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
    if 'domain_stats' not in context:
        context['domain_stats'] = {}
    context['domain_stats'][domain] = context['domain_stats'].get(domain, 0) + 1
    
    # Track consecutive same domain
    if context.get('last_domain') == domain:
        context['consecutive_same'] = context.get('consecutive_same', 0) + 1
    else:
        context['consecutive_same'] = 1
    
    request.session['question_context'] = context
    request.session['current_question'] = question_data
    request.session['current_question_id'] = question_id  # Store DB ID
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
        "question_id": question_id,  # Include DB ID in response
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
            user_data = json.loads(request.body)
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
    
    # Generate explanation for all answers to enhance learning
    explanation = generate_question_explanation(current_data)
    
    # Update session statistics if needed
    context = request.session.get('question_context', {})
    if is_correct:
        context['correct_answers'] = context.get('correct_answers', 0) + 1
    context['total_answered'] = context.get('total_answered', 0) + 1
    request.session['question_context'] = context
    
    # Check if this specific question is bookmarked by the user
    is_bookmarked = False
    if request.user.is_authenticated:
        current_question_id = request.session.get('current_question_id')
        if current_question_id:
            is_bookmarked = BookmarkedQuestion.objects.filter(
                user=request.user, 
                question_id=current_question_id
            ).exists()

    return JsonResponse({
        "correct": is_correct,
        "your_choice": user_choice,
        "correct_answer": correct_letter,
        "correct_text": current_data['options'].get(correct_letter, ""),
        "explanation": explanation,
        "question": user_question,
        "domain": current_data.get('domain', ''),
        "topic": current_data.get('topic', ''),
        "is_bookmarked": is_bookmarked,
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