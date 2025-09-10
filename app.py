import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# Import your helpers
from helpers.gemini_client import extract_answers_from_omr
from utils.omr_scoring import compute_score

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def create_app():
    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

    # -------------------------------
    # Upload form (UI) for testing
    # -------------------------------
    @app.route("/api/omr", methods=["GET"])
    def index():
        return render_template("index.html")

    # -------------------------------
    # API: Always return JSON
    # -------------------------------
    @app.route("/api/omr/score", methods=["POST"])
    def api_score():
        # ✅ Student OMR is required
        student_file = request.files.get("omr_image")
        if not student_file or student_file.filename == "":
            return jsonify({"status": "error", "message": "Student OMR file is required"}), 400
        if not allowed_file(student_file.filename):
            return jsonify({"status": "error", "message": "Invalid student OMR file type"}), 400

        # ✅ Answer key OMR is optional
        key_file = request.files.get("answer_key_omr")
        if key_file and key_file.filename != "" and not allowed_file(key_file.filename):
            return jsonify({"status": "error", "message": "Invalid answer key file type"}), 400

        # ✅ Number of questions
        try:
            num_questions = int(request.form.get("num_questions", "100"))
            if num_questions < 1 or num_questions > 300:
                raise ValueError
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid number of questions"}), 400

        # ✅ Save uploaded files
        student_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(student_file.filename))
        student_file.save(student_path)

        key_path = None
        if key_file and key_file.filename != "":
            key_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(key_file.filename))
            key_file.save(key_path)

        try:
            # ✅ Extract student answers
            student_answers = extract_answers_from_omr(student_path, num_questions)

            if key_path:
                # ✅ Scoring mode
                key_answers = extract_answers_from_omr(key_path, num_questions)
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
                # ✅ Detection only mode
                return jsonify({
                    "status": "success",
                    "mode": "detection_only",
                    "student_answers": student_answers,
                    "num_questions": num_questions,
                })

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
