# OMR Scoring (Flask + Gemini)

Upload a student's filled OMR sheet image, paste your answer key, and get the student's score.
Uses Google's Gemini multimodal model to detect filled bubbles (A/B/C/D).

## 1) Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY
```

### Environment variable (Windows PowerShell)
```powershell
setx GOOGLE_API_KEY "YOUR_KEY_HERE"
```
(Restart terminal after `setx` so it's available.)

## 2) Run

```bash
flask --app app run --debug
# or
python app.py
```

Then open http://127.0.0.1:5000

## 3) How to enter the answer key

- **One option per line** (simplest):
  ```
  A
  B
  C
  D
  ...
  ```

- **Comma/space separated**:
  ```
  A, B, C, D, ...
  # or
  A B C D ...
  ```

- **Numbered pairs** (in any order):
  ```
  1:A
  2=B
  3- C
  10: D
  ```

Rules:
- Valid options: A, B, C, D, NA (case-insensitive).
- If fewer answers than `Number of questions`, missing ones become `NA`.

## 4) Notes & Tips

- For best results: crop/scan the OMR sheet straight, high contrast, good lighting.
- If your sheet has more/less than A–D per question, adjust the prompt in `helpers/gemini_client.py`.
- This sample keeps things simple. Production apps should add auth, stronger validations, and retries.