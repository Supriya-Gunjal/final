import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# Import your helpers
from helpers.gemini_client import extract_answers_from_omr
from utils.omr_scoring import parse_answer_key, compute_score

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def create_app():
    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

    # -------------------------------
    # Upload form (UI)
    # -------------------------------
    @app.route("/api/omr", methods=["GET"])
    def index():
        return render_template("index.html")

    # -------------------------------
    # API: Always return JSON
    # -------------------------------
    @app.route("/api/omr/score", methods=["POST"])
    def api_score():
        if "omr_image" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400

        file = request.files["omr_image"]

        if file.filename == "":
            return jsonify({"status": "error", "message": "Empty filename"}), 400

        if not allowed_file(file.filename):
            return jsonify({
                "status": "error",
                "message": "Invalid file type. Allowed: PNG, JPG, JPEG, WEBP"
            }), 400

        # Number of questions
        try:
            num_questions = int(request.form.get("num_questions", "100"))
            if num_questions < 1 or num_questions > 300:
                raise ValueError
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid number of questions"}), 400

        # Save uploaded file
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)

        # ✅ Extract answers using Gemini
        try:
            student_answers = extract_answers_from_omr(save_path, num_questions=num_questions)
        except Exception as e:
            return jsonify({"status": "error", "message": f"Gemini extraction failed: {e}"}), 500

        # ✅ Answer key is OPTIONAL
        answer_key_text = request.form.get("answer_key", "").strip()
        if answer_key_text:
            key_answers = parse_answer_key(answer_key_text, num_questions=num_questions)
            summary, breakdown = compute_score(student_answers, key_answers, num_questions)

            return jsonify({
                "status": "success",
                "mode": "scored",
                "summary": summary,
                "breakdown": breakdown,
                "student_answers": student_answers,
                "correct_answers": key_answers,
            })
        else:
            # No key provided → just return detected answers
            return jsonify({
                "status": "success",
                "mode": "detection_only",
                "student_answers": student_answers,
                "num_questions": num_questions
            })

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
