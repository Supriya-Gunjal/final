import re
from typing import Dict, Tuple, List, Union

VALID = {"A", "B", "C", "D", "NA"}

def _norm_token(tok: str) -> str:
    t = tok.strip().upper()
    return t if t in VALID else "NA"

def parse_answer_key(text: str, num_questions: int) -> Dict[int, str]:
    """
    Flexible parser:
    - One per line: A\nB\nC...
    - Space/comma-separated: A, B, C...
    - Numbered: 1:A, 2=B, 3- C
    Returns map 1..num_questions -> 'A'|'B'|'C'|'D'|'NA'
    """
    key: Dict[int, str] = {}

    if not text or not text.strip():
        return {i: "NA" for i in range(1, num_questions + 1)}

    text = text.strip()

    numbered_pairs = re.findall(r"(\d+)\s*[:=\-]\s*([A-D]|NA)", text, flags=re.IGNORECASE)
    if numbered_pairs:
        for q_str, opt in numbered_pairs:
            q = int(q_str)
            if 1 <= q <= num_questions:
                key[q] = _norm_token(opt)
    else:
        blob = re.fullmatch(r"[A-DNAa-dna\s,]+", text)
        if blob and (len(text.replace(" ", "").replace(",", "")) == num_questions):
            seq = [c for c in text if c.upper() in {"A", "B", "C", "D", "N"}]
            cleaned = []
            for c in seq:
                cleaned.append("NA" if c.upper() == "N" else c.upper())
            for i in range(1, num_questions + 1):
                key[i] = _norm_token(cleaned[i-1])
        else:
            tokens = re.split(r"[\s,]+", text)
            idx = 1
            for tok in tokens:
                if idx > num_questions:
                    break
                if not tok:
                    continue
                key[idx] = _norm_token(tok)
                idx += 1

    for i in range(1, num_questions + 1):
        if i not in key:
            key[i] = "NA"
    return key

def compute_score(student: Dict[int, Union[str, List[str]]], key: Dict[int, str], num_questions: int):
    """
    student: {1: "A", 2: ["B","C"], 3: "NA" ...}
    key:     {1: "A", 2: "C", 3: "B" ...}
    Returns (summary, breakdown)
    """
    correct = incorrect = na = 0
    breakdown: List[dict] = []

    for i in range(1, num_questions + 1):
        s = student.get(i, "NA")
        k = key.get(i, "NA")

        if isinstance(s, list):
            if len(s) == 1 and s[0] in {"A", "B", "C", "D"}:
                s = s[0]
            else:
                s = "NA"

        if s == "NA":
            na += 1
            result = "NA"
        elif s == k and s in {"A", "B", "C", "D"}:
            correct += 1
            result = "Correct"
        else:
            incorrect += 1
            result = "Incorrect"

        breakdown.append({"q": i, "key": k, "student": s, "result": result})

    summary = {
        "total": num_questions,
        "correct": correct,
        "incorrect": incorrect,
        "na": na,
    }
    return summary, breakdown