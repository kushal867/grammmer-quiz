# utils/ollama_helper.py   ← create this file anywhere in your project
import requests
import json

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

PROMPT_MAP = {
    "grammar": "Correct all grammar, spelling, and punctuation errors. Return only the fixed text, no explanations:\n\n",
    "rewrite": "Rewrite the text to be clearer, more natural and fluent. Return only the new text:\n\n",
    "formal":  "Rewrite the text in professional, formal English. Return only the new version:\n\n",
    "casual":  "Rewrite the text in friendly, casual English. Return only the new version:\n\n",
    "summary": "Summarize the following text in 3–4 concise sentences:\n\n",
}

def improve_text(text: str, task: str = "grammar") -> str:
    if not text or not text.strip():
        return "No text provided."

    system_prompt = PROMPT_MAP.get(task, "")
    full_prompt = system_prompt + text.strip()

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
        result = response.json()
        return result["response"].strip()
    except requests.exceptions.ConnectionError:
        return "Error: Ollama is not running. Run 'ollama serve' in terminal."
    except Exception as e:
        return f"Ollama error: {str(e)}"