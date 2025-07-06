from application import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))  # 'teacher' or 'student'
    roll_number = db.Column(db.String(20), unique=True, nullable=True)

class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_roll = db.Column(db.String(20))
    session_type = db.Column(db.String(50))  # 'mock', 'gd', 'jam'
    session_number = db.Column(db.Integer)   # 1, 2, or 3
    section = db.Column(db.String(100))
    score = db.Column(db.Integer)
    remarks = db.Column(db.String(500))
    teacher_id = db.Column(db.Integer)
