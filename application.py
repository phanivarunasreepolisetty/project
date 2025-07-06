from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)


# Secret key for session management
app.secret_key = 'your_secret_key'

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# In-memory storage (note: this won't persist if you restart the app)
evaluation_data = {}

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))
    roll_number = db.Column(db.String(20), unique=True, nullable=False)

# Evaluation model
class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_roll = db.Column(db.String(20))
    session_type = db.Column(db.String(50))
    session_number = db.Column(db.Integer)
    section = db.Column(db.String(100))
    score = db.Column(db.Integer)
    remarks = db.Column(db.String(500))
    teacher_id = db.Column(db.Integer)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        roll_number = request.form['roll_number']

        if User.query.filter_by(roll_number=roll_number).first():
            flash('Roll number already exists!')
            return redirect('/signup')

        new_user = User(name=name, password=password, role=role, roll_number=roll_number)
        db.session.add(new_user)
        db.session.commit()
        flash('Signup successful! Please login.')
        return redirect('/login')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        roll_number = request.form['roll_number']
        password = request.form['password']

        user = User.query.filter_by(roll_number=roll_number).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful.')
            if user.role == 'teacher':
                return redirect('/teacher_dashboard')
            else:
                return redirect('/student_dashboard')
        else:
            flash('Invalid roll number or password')
            return redirect('/login')

    return render_template('login.html')

@app.route('/teacher_dashboard', methods=['GET', 'POST'])
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        return redirect('/logout')

    # Load all students and extract names for dropdown
    students = User.query.filter_by(role='student').all()
    student_usernames = [student.name for student in students]

    roll_number = None
    session_counts = None
    selected_type = None
    session_list = []

    if request.method == 'POST':
        roll_number = request.form.get('roll_number') or session.get('last_roll')
        session['last_roll'] = roll_number

        session_counts = {
            'mock': 0,
            'gd': 0,
            'jam': 0
        }

        for (r, s_type, _), data in evaluation_data.items():
            if r == roll_number and s_type in session_counts:
                session_counts[s_type] += 1

        if 'view_type' in request.form:
            selected_type = request.form['view_type']
            session_list = []

            for (r, s_type, n), data in evaluation_data.items():
                if r == roll_number and s_type == selected_type:
                    session_key = f"{s_type.capitalize()} Session {n}"
                    evaluations = data['evaluations']

                    session_list.append({
                        'title': session_key,
                        'details': [
                            {'section': section, 'score': score}
                            for section, (score, _) in evaluations.items()
                        ]
                    })

    return render_template('teacher_dashboard.html',
                           student_usernames=student_usernames,
                           roll_number=roll_number,
                           session_counts=session_counts,
                           selected_type=selected_type,
                           session_list=session_list)


@app.route('/search_student', methods=['POST'])
@login_required
def search_student():
    roll_number = request.form['roll_number']
    session_type = request.form['session_type']
    return redirect(url_for('evaluate', roll_number=roll_number, session_type=session_type))

@app.route('/evaluate/<roll_number>/<session_type>', methods=['GET', 'POST'])
@login_required
def evaluate(roll_number, session_type):
    sections = (
        ['Resume Building', 'LinkedIn Profile', 'Behaviour', 'Body Language', 'Communication Skills']
        if session_type == 'mock' else
        ['Behaviour', 'Body Language', 'Communication Skills', 'Eye Contact']
    )

    session_number = request.args.get('edit', type=int)
    existing_sessions = (
        db.session.query(Evaluation.session_number)
        .filter_by(student_roll=roll_number, session_type=session_type)
        .distinct()
        .all()
    )

    if not session_number:
        existing = [sn for (r, s, sn) in evaluation_data.keys() if r == roll_number and s == session_type]
        session_number = max(existing, default=0) + 1

    if request.method == 'POST':
        evaluations = {}
        for section in sections:
            score = int(request.form[f'score_{section}'])
            evaluations[section] = (score, "")

        evaluation_data[(roll_number, session_type, session_number)] = {
            'evaluations': evaluations,
            'teacher': current_user.name
        }

        flash(f"{session_type.capitalize()} Session {session_number} saved!", "success")
        return redirect(url_for('teacher_dashboard'))

    return render_template(
        'evaluate.html',
        roll_number=roll_number,
        session_type=session_type,
        sections=sections,
        session_number=session_number,
        existing_sessions=existing_sessions,
        evaluation_data=evaluation_data
    )

@app.route('/student_dashboard', methods=['GET', 'POST'])
@login_required
def student_dashboard():
    session_data = {}
    session_selected = False
    session_type = None

    session_counts = {
        'mock': 0,
        'gd': 0,
        'jam': 0
    }

    for (r, s_type, _), data in evaluation_data.items():
        if r == current_user.roll_number:
            if s_type in session_counts:
                session_counts[s_type] += 1

    if request.method == 'POST':
        session_type = request.form['session_type'].lower()
        session_selected = True

        for (r, s_type, session_number), data in evaluation_data.items():
            if r == current_user.roll_number and s_type == session_type:
                key = f"{session_type.capitalize()} {session_number}"
                session_data[key] = [
                    {
                        'section': section,
                        'score': score
                    }
                    for section, (score, _) in data['evaluations'].items()
                ]

    return render_template('student_dashboard.html',
                           session_data=session_data,
                           session_selected=session_selected,
                           session_counts=session_counts)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
