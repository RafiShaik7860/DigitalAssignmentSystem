import os
import uuid

from werkzeug.utils import secure_filename
from datetime import datetime
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash,
    send_from_directory, abort
)

from models import db, User, Assignment, Submission


from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)


# 1. Flask application
app = Flask(__name__)


# 2. Application configuration
app.config["SECRET_KEY"] = "assigneval-development-key"
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///assigneval.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# 3. Database connection
db.init_app(app)


# 4. Flask-Login configuration
login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# 5. Homepage
@app.route("/")
def home():
    return render_template("index.html")


# 6. Student registration
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not username or not email or not password:
            flash("Please fill in all fields.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already registered.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            role="student"
        )

        db.session.add(new_user)

        db.session.commit()

        flash("Registration successful!")

        return redirect(url_for("register"))

    return render_template("register.html")


# 7. User login
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):

            login_user(user)

            flash("Login successful! Welcome " + user.username)

            return redirect(url_for("dashboard"))

        else:
            flash("Invalid email or password.")

            return redirect(url_for("login"))

    return render_template("login.html")


# 8. Protected dashboard

@app.route("/dashboard")
@login_required
def dashboard():

    if current_user.role == "student":

        assignments = Assignment.query.order_by(
            Assignment.deadline.asc()
        ).all()

        submissions = Submission.query.filter_by(
            student_id=current_user.id
        ).order_by(
            Submission.submitted_at.desc()
        ).all()

        return render_template(
            "dashboard.html",
            assignments=assignments,
            submissions=submissions
        )

    elif current_user.role == "faculty":

        return render_template("faculty_dashboard.html")

    elif current_user.role == "admin":

        return render_template("admin_dashboard.html")

    else:

        logout_user()
        return redirect(url_for("login"))



@app.route("/create-assignment", methods=["GET", "POST"])
@login_required
def create_assignment():

    if current_user.role != "faculty":
        flash("Access denied! Only faculty can create assignments.")
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        title = request.form.get("title")
        description = request.form.get("description")
        subject = request.form.get("subject")
        deadline = request.form.get("deadline")
        max_marks = request.form.get("max_marks")

        new_assignment = Assignment(
            title=title,
            description=description,
            subject=subject,
            deadline=datetime.strptime(
                deadline, "%Y-%m-%dT%H:%M"
            ),
            max_marks=int(max_marks),
            faculty_id=current_user.id
        )

        db.session.add(new_assignment)
        db.session.commit()

        flash("Assignment created successfully!")

        return redirect(url_for("dashboard"))

    return render_template("create_assignment.html")

@app.route("/submit-assignment", methods=["GET", "POST"])
@login_required
def submit_assignment():

    if current_user.role != "student":
        flash("Access denied! Only students can submit assignments.")
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        assignment_id = request.form.get("assignment_id")
        uploaded_file = request.files.get("file")

        if not assignment_id or not uploaded_file:
            flash("Please select an assignment and upload a PDF.")
            return redirect(url_for("submit_assignment"))

        assignment = db.session.get(Assignment, assignment_id)

        if not assignment:
            flash("Invalid assignment selected.")
            return redirect(url_for("submit_assignment"))

        if not uploaded_file.filename:
            flash("Please choose a file.")
            return redirect(url_for("submit_assignment"))

        clean_filename = secure_filename(uploaded_file.filename)

        if not clean_filename.lower().endswith(".pdf"):
            flash("Only PDF files are allowed.")
            return redirect(url_for("submit_assignment"))

        # Check the actual PDF file signature
        file_signature = uploaded_file.read(5)
        uploaded_file.seek(0)

        if file_signature != b"%PDF-":
            flash("Invalid PDF file.")
            return redirect(url_for("submit_assignment"))

        # Create the upload folder
        upload_folder = os.path.join(app.root_path, "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        # Generate a unique filename
        stored_filename = f"{uuid.uuid4().hex}_{clean_filename}"

        file_path = os.path.join(upload_folder, stored_filename)

        # Save the uploaded PDF
        uploaded_file.save(file_path)

        # Save submission details in the database
        new_submission = Submission(
            assignment_id=assignment.id,
            student_id=current_user.id,
            filename=stored_filename
        )

        db.session.add(new_submission)
        db.session.commit()

        flash("Assignment submitted successfully!")

        return redirect(url_for("dashboard"))

    assignments = Assignment.query.order_by(
        Assignment.deadline.asc()
    ).all()

    return render_template(
        "submit_assignment.html",
        assignments=assignments
    )
@app.route("/view-submissions")
@login_required
def view_submissions():

    if current_user.role != "faculty":
        flash("Access denied! Only faculty can view submissions.")
        return redirect(url_for("dashboard"))

    submissions = Submission.query.join(Assignment).filter(
        Assignment.faculty_id == current_user.id
    ).order_by(Submission.submitted_at.desc()).all()

    return render_template(
        "view_submissions.html",
        submissions=submissions
    )
@app.route("/evaluate-submission/<int:submission_id>", methods=["GET", "POST"])
@login_required
def evaluate_submission(submission_id):

    if current_user.role != "faculty":
        abort(403)

    submission = Submission.query.join(Assignment).filter(
        Submission.id == submission_id,
        Assignment.faculty_id == current_user.id
    ).first_or_404()

    if request.method == "POST":

        marks = request.form.get("marks", type=int)
        feedback = request.form.get("feedback", "").strip()

        max_marks = submission.assignment.max_marks

        if marks is None or marks < 0 or marks > max_marks:
            flash(f"Marks must be between 0 and {max_marks}.")
            return redirect(
                url_for("evaluate_submission",
                        submission_id=submission.id)
            )

        if not feedback:
            flash("Please enter feedback.")
            return redirect(
                url_for("evaluate_submission",
                        submission_id=submission.id)
            )

        submission.marks = marks
        submission.feedback = feedback
        submission.status = "Evaluated"

        db.session.commit()

        flash("Assignment evaluated successfully!")
        return redirect(url_for("view_submissions"))

    return render_template(
        "evaluate_submission.html",
        submission=submission
    )
@app.route("/download-submission/<int:submission_id>")
@login_required
def download_submission(submission_id):

    if current_user.role != "faculty":
        abort(403)

    submission = Submission.query.join(Assignment).filter(
        Submission.id == submission_id,
        Assignment.faculty_id == current_user.id
    ).first_or_404()

    upload_folder = os.path.join(app.root_path, "uploads")

    return send_from_directory(
        upload_folder,
        submission.filename,
        as_attachment=True
    )
# 9. Logout
@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash("You have been logged out.")

    return redirect(url_for("login"))


# 10. Run application
if __name__ == "__main__":

    with app.app_context():

        db.create_all()

    app.run(debug=True)
