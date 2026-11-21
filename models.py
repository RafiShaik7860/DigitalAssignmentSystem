from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
db = SQLAlchemy()


class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")

class Assignment(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(150), nullable=False)

    description = db.Column(db.Text, nullable=False)

    subject = db.Column(db.String(100), nullable=False)

    deadline = db.Column(db.DateTime, nullable=False)

    max_marks = db.Column(db.Integer, nullable=False, default=100)

    faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )
class Submission(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey("assignment.id"),
        nullable=False
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    filename = db.Column(db.String(255), nullable=False)

    submitted_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Submitted"
    )

    # New evaluation fields
    marks = db.Column(db.Integer, nullable=True)

    feedback = db.Column(db.Text, nullable=True)

    # Relationships
    assignment = db.relationship("Assignment", backref="submissions")

    student = db.relationship("User", backref="submissions")