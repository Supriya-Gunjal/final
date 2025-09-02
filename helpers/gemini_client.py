import os
import json
import re
from typing import Dict
from PIL import Image
import google.generativeai as genai

def _get_model():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("No API key. Set GOOGLE_API_KEY (preferred) or GEMINI_API_KEY in environment or .env")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    return genai.GenerativeModel(model_name)

def _extract_json_block(text: str) -> dict:
    """Try to extract a JSON object from the model text response."""
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
    Return {1:'A'|'B'|'C'|'D'|'NA', ...} for questions 1..num_questions.
    - Uses Gemini multimodal model to read the image.
    - Interprets "half" / multiple marks → "NA".
    """
    model = _get_model()

    prompt = f"""You are an OMR sheet bubble reader.
TASK:
- For each visible question, detect which options [A, B, C, D] are marked.
- Distinguish between:
  - Fully filled bubble -> ["A"]
  - Multiple fully filled bubbles -> ["A","C"]
  - No bubble filled -> []
  - Half-filled, faint, partially shaded, dotted, or incomplete bubble -> ["half"]

STRICT RULE:
- If you are unsure whether a bubble is completely filled, classify it as ["half"].
- Do NOT guess: only return ["A"], ["B"], etc. when the bubble is completely filled.

RULES:
- Output only valid JSON, no extra commentary.
- Schema:
  {{
    "answers": {{
      "1": ["A"],
      "2": ["B","C"],
      "3": [],
      "4": ["half"]
    }}
  }}
- If more than {num_questions} questions visible, include only the first {num_questions}.
"""

    img = Image.open(image_path)

    response = model.generate_content([prompt, img])

    try:
        text = response.text
    except Exception:
        parts = []
        for cand in getattr(response, 'candidates', []) or []:
            for p in getattr(cand.content, 'parts', []) or []:
                if getattr(p, 'text', None):
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
            raw_list = [raw_val]
        elif isinstance(raw_val, list):
            raw_list = raw_val
        else:
            raw_list = []

        cleaned = []
        for opt in raw_list:
            if opt in {"A", "B", "C", "D"}:
                cleaned.append(opt)
            elif str(opt).lower() == "half":
                cleaned.append("NA")

        if len(cleaned) == 1 and cleaned[0] in {"A", "B", "C", "D"}:
            normalized[i] = cleaned[0]
        else:
            normalized[i] = "NA"

    return normalized




















