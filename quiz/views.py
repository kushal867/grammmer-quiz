# quiz/views.py  ← 100% OLLAMA + NEVER REPEATS (by Kushal Sapkota)
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import re
import random

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "llama3"

# Store used questions in session to prevent repeat
def home(request):
    if 'used_questions' not in request.session:
        request.session['used_questions'] = []
    return render(request, 'quiz/home.html')

@csrf_exempt
def api_new_question(request):
    used_questions = request.session.get('used_questions', [])
    
    # Try up to 10 times to get a NEW question
    for attempt in range(10):
        prompt = f"""
तपाईं नेपाल लोक सेवा आयोग (नायब सुब्बा / शाखा अधिकृत स्तर) को लागि एकदमै उच्च गुणस्तरको बहुवैकल्पिक प्रश्न बनाउनुहोस्।
विषय: नेपालको संविधान, इतिहास, भूगोल, अर्थशास्त्र, लोकसेवा ऐन, सामान्य ज्ञान, गणित, अंग्रेजी, वा वर्तमान घटना।
कठिनाई: मध्यम–कठिन।

अनिवार्य रूपमा यो ढाँचा प्रयोग गर्नुहोस् (कुनै अतिरिक्त शब्द नलेख्नुहोस्):

प्रश्न: नेपालको संविधान अनुसार प्रदेश सभाको कार्यकाल कति वर्षको हुन्छ?
क) ४ वर्ष
ख) ५ वर्ष
ग) ६ वर्ष
घ) ७ वर्ष

सही जवाफ: ख

अब तपाईंको पालो — नयाँ प्रश्न बनाउनुहोस् (पहिलेका प्रश्न दोहोरिनु हुँदैन):
"""

        raw = ollama_generate(prompt)
        
        # Extract question
        q_match = re.search(r"प्रश्न:\s*(.+?)(?=क\)|$)", raw, re.DOTALL)
        if not q_match:
            continue
        question = q_match.group(1).strip()
        
        # Extract options
        options = {}
        for letter in "कखगघ":
            m = re.search(f"{letter}\\)\s*(.+)", raw)
            if m:
                options[letter] = m.group(1).strip()
        
        # Extract correct answer
        corr_match = re.search(r"सही जवाफ[:\s]*([कखगघ])", raw, re.I)
        if not corr_match:
            continue
        correct = corr_match.group(1).strip()

        # Check if question already used
        if question not in used_questions and len(options) == 4:
            # Save as used
            used_questions.append(question)
            request.session['used_questions'] = used_questions[-50:]  # keep last 50
            
            # Save current correct answer
            request.session['correct_letter'] = correct
            request.session['current_question'] = question

            return JsonResponse({
                "question": question,
                "options": options,
                "correct_letter": correct  # remove later if you want secret
            })

    # Emergency fallback (if Ollama fails)
    return JsonResponse({
        "question": "नेपालको राष्ट्रिय जनावर कुन हो?",
        "options": {"क": "गाई", "ख": "गैंडा", "ग": "हात्ती", "घ": "बाघ"},
        "correct_letter": "ख"
    })

@csrf_exempt
def api_check_answer(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    
    try:
        user_choice = request.json.get("choice", "").strip()
    except:
        return JsonResponse({"error": "Send: {\"choice\": \"ख\"}"}, status=400)

    correct = request.session.get('correct_letter', 'क')
    question = request.session.get('current_question', 'प्रश्न')

    # Let Ollama double-check (optional, super accurate)
    judge_prompt = f"""
प्रश्न: {question}
सही जवाफ: {correct}
प्रयोगकर्ताको जवाफ: {user_choice}

के यो जवाफ सही हो? केवल "सही" वा "गलत" लेख्नुहोस्।
"""
    judgment = ollama_generate(judge_prompt)
    is_correct = "सही" in judgment

    return JsonResponse({
        "correct": is_correct,
        "your_choice": user_choice,
        "correct_answer": correct
    })

def ollama_generate(prompt):
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.8,
                "num_ctx": 4096,
                "top_p": 0.9
            }
        }, timeout=40)
        r.raise_for_status()
        return r.json()["response"]
    except:
        return "Error"