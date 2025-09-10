import os, json, re
from typing import Dict
from PIL import Image
import google.generativeai as genai

def _get_model():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY.")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    return genai.GenerativeModel(model_name)

def _extract_json_block(text: str) -> dict:
    """Extract JSON safely from model text response."""
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*({[\s\S]*?})\s*```", text, re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m2 = re.search(r"({[\s\S]*})", text)
    if m2:
        try:
            return json.loads(m2.group(1))
        except Exception:
            pass
    raise ValueError("Could not parse JSON from model response.")

def extract_answers_from_omr(image_path: str, num_questions: int) -> Dict[int, str]:
    """
    Extract answers from OMR sheet image.
    Returns dict: {1:'A'|'B'|'C'|'D'|'NA', ...}
    """
    model = _get_model()

    prompt = f"""
    You are an OMR sheet bubble reader.

    TASK:
    - For each visible question, detect which options [A, B, C, D] are filled.
    - Always return answers as lists:
      - One bubble filled → ["A"]
      - Multiple bubbles filled → ["A","C"]
      - None filled → []

    RULES:
    - Output ONLY valid JSON.
    - Schema:
      {{
        "answers": {{
          "1": ["A"],
          "2": ["B","C"],
          "3": [],
          ...
        }}
      }}
    - Only include up to {num_questions} questions.
    """

    img = Image.open(image_path)
    response = model.generate_content([prompt, img])

    try:
        text = response.text
    except Exception:
        parts = []
        for cand in getattr(response, "candidates", []) or []:
            for p in getattr(cand.content, "parts", []) or []:
                if getattr(p, "text", None):
                    parts.append(p.text)
        text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("Empty response from Gemini.")

    data = _extract_json_block(text)
    answers = data.get("answers", {})

    normalized: Dict[int, str] = {}
    for i in range(1, num_questions + 1):
        raw_val = answers.get(str(i), answers.get(i, []))
        if isinstance(raw_val, str):
            raw_list = [raw_val] if raw_val in {"A", "B", "C", "D"} else []
        elif isinstance(raw_val, list):
            raw_list = [opt for opt in raw_val if opt in {"A", "B", "C", "D"}]
        else:
            raw_list = []

        if len(raw_list) == 1:
            normalized[i] = raw_list[0]
        else:
            normalized[i] = "NA"

    return normalized
