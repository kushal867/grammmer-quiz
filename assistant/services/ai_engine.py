# utils/ollama_helper.py  ← FINAL VERSION (copy-paste this)
import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

PROMPT_MAP = {
    "grammar": "Correct all grammar, spelling, and punctuation errors. Return only the corrected text, no explanation or extra words:\n\n",
    "rewrite": "Rewrite the following text to be clearer, more engaging, and natural. Return only the improved version:\n\n",
    "formal":  "Rewrite the text in perfect professional, formal English. Return only the formal version:\n\n",
    "casual":  "Rewrite the text in friendly, casual, modern English. Return only the casual version:\n\n",
    "summary": "Summarize the following text in 3–4 powerful, concise sentences. Return only the summary:\n\n",
}

def improve_text(text: str, task: str = "grammar") -> str:
    task = task.lower().strip()

    # If user sends empty text → we give a smart, dynamic, funny & useful response
    if not text or not text.strip():
        smart_empty_responses = {
            "grammar": "Your text is already perfect... or you forgot to write anything",
            "rewrite": "Give me some messy text and watch me turn it into gold",
            "formal": "Dear esteemed user, kindly provide text for formal enhancement. Thank you.",
            "casual": "Yo! Drop some text here and I'll make it chill AF",
            "summary": "Nothing to summarize yet... but I'm ready when you are!"
        }
        return smart_empty_responses.get(task, "Hey! I'm Kushal Writer — type something and I'll make it amazing")

    # Normal flow: user gave text → send to Ollama
    prompt_template = PROMPT_MAP.get(task, "Improve this text:\n\n")
    full_prompt = prompt_template + text.strip()

    payload = {
        "model": "llama3",
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1 if task == "grammar" else 0.7,
            "num_ctx": 8192,
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=90)
        response.raise_for_status()
        result = response.json()["response"].strip()
        return result
    except requests.exceptions.ConnectionError:
        return "Ollama is not running. Run: ollama serve"
    except Exception as e:
        return f"Error: {e}"