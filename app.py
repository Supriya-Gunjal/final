import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

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

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            if "omr_image" not in request.files:
                flash(("error", "No image part in the request."))
                return redirect(url_for("index"))

            file = request.files["omr_image"]
            if file.filename == "":
                flash(("error", "No selected file."))
                return redirect(url_for("index"))

            if not allowed_file(file.filename):
                flash(("error", "Invalid file type. Please upload PNG/JPG/WebP."))
                return redirect(url_for("index"))

            try:
                num_questions = int(request.form.get("num_questions", "100"))
                if num_questions < 1 or num_questions > 300:
                    raise ValueError
            except ValueError:
                flash(("error", "Invalid number of questions."))
                return redirect(url_for("index"))

            answer_key_text = request.form.get("answer_key", "").strip()

            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)

            
            try:
                student_answers = extract_answers_from_omr(save_path, num_questions=num_questions)
            except Exception as e:
                flash(("error", f"Gemini extraction failed: {e}"))
                return redirect(url_for("index"))

            
            key_answers = parse_answer_key(answer_key_text, num_questions=num_questions)

            
            summary, breakdown = compute_score(student_answers, key_answers, num_questions)

            return render_template("result.html", summary=summary, breakdown=breakdown)

        return render_template("index.html")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
