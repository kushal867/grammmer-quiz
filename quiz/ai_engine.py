# quiz/ai_engine.py
import requests
import re
import random
import logging
from .constants import (
    QUESTION_DOMAINS, QUESTION_PATTERNS, DIFFICULTY_LEVELS, 
    SYSTEM_PROMPT, OLLAMA_URL, MODEL
)

logger = logging.getLogger(__name__)

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

def generate_question_explanation(question_data):
    """Generate explanation for correct answer"""
    prompt = f"""
प्रश्न: {question_data['question']}
सही उत्तर: {question_data['correct_letter']}) {question_data['options'][question_data['correct_letter']]}

यो उत्तर किन सही छ? २-३ वाक्यमा संक्षिप्त व्याख्या गर्नुहोस्:
"""
    
    explanation = ollama_generate(prompt, "सजिलो")
    return explanation if explanation and "Error" not in explanation else "यो सही उत्तर हो।"
