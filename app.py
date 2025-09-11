from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import qrcode
from io import BytesIO
import base64
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)
app.secret_key = "your-secret-key-change-in-production"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey('student.student_id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
# Initialize database
def create_tables():
    with app.app_context():
        db.create_all()
        # Add sample student if not exists
        if not Student.query.filter_by(student_id='STU123').first():
            hashed_pw = generate_password_hash("password123")
            s = Student(student_id='STU123', name='John Doe', password_hash=hashed_pw)
            db.session.add(s)
            db.session.commit()
# Home page with login options
@app.route('/')
def home():
    return "<h1>Welcome to Smart Attendance</h1><p><a href='/student/login'>Student Login</a> | <a href='/register'>Register</a> | <a href='/teacher/login'>Teacher Login</a></p>"
# Student Login
@app.route('/student/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        password = request.form.get('password')
        student = Student.query.filter_by(student_id=student_id).first()
        if student and password and check_password_hash(student.password_hash, password):
            session['student_id'] = student.student_id
            session['student_name'] = student.name
            return redirect(url_for('student_dashboard'))
        else:
            flash("Invalid student ID or password")
            return redirect(url_for('login'))
    return render_template('student_login.html')
# Student Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        password = request.form.get('password')
        if Student.query.filter_by(student_id=student_id).first():
            flash("Student ID already exists!")
            return redirect(url_for('register'))
        if not password:
            flash("Password is required!")
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password)
        new_student = Student(student_id=student_id, name=name, password_hash=hashed_pw)
        db.session.add(new_student)
        db.session.commit()
        flash("Registration successful! Please login.")
        return redirect(url_for('login'))
    return render_template('student_register.html')
# Student Dashboard
@app.route('/dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    student_id = session['student_id']
    name = session['student_name']
    img = qrcode.make(student_id)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_data = base64.b64encode(buffer.getvalue()).decode()
    return render_template('dashboard.html', name=name, student_id=student_id, qr_data=qr_data)
# Teacher Login
@app.route('/teacher/login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        teacher = Teacher.query.filter_by(username=username).first()
        if teacher and password and check_password_hash(teacher.password_hash, password):
            session['teacher_id'] = teacher.id
            return redirect(url_for('teacher_dashboard'))
        else:
            flash("Invalid teacher username or password")
            return redirect(url_for('teacher_login'))
    return render_template('teacher_login.html')
# Teacher Registration
@app.route('/teacher/register', methods=['GET', 'POST'])
def teacher_register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if Teacher.query.filter_by(username=username).first():
            flash("Teacher username already exists!")
            return redirect(url_for('teacher_register'))
        if not password:
            flash("Password is required!")
            return redirect(url_for('teacher_register'))
            
        hashed_pw = generate_password_hash(password)
        new_teacher = Teacher(username=username, password_hash=hashed_pw)
        db.session.add(new_teacher)
        db.session.commit()
        flash("Teacher registration successful!")
        return redirect(url_for('teacher_login'))
    return render_template('teacher_register.html')
# Teacher Dashboard
@app.route('/teacher/dashboard')
def teacher_dashboard():
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))
    return render_template('teacher_dashboard.html')
# Mark Attendance from QR Code
@app.route('/teacher/mark_attendance/<student_id>')
def mark_attendance(student_id):
    if 'teacher_id' not in session:
        return redirect(url_for('teacher_login'))
    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        return "Student not found", 404
    today = datetime.utcnow().date()
    existing = Attendance.query.filter(
        Attendance.student_id == student_id,
        db.func.date(Attendance.timestamp) == today
    ).first()
    if existing:
        return f"Attendance already marked for {student.name} today."
    attendance = Attendance(student_id=student_id)
    db.session.add(attendance)
    db.session.commit()
    return f"Attendance marked for {student.name}."
# View Attendance Records
@app.route('/attendance')
def attendance():
    records = Attendance.query.order_by(Attendance.timestamp.desc()).all()
    result = []
    for r in records:
        student = Student.query.filter_by(student_id=r.student_id).first()
        result.append({
            'student_id': r.student_id,
            'name': student.name if student else "Unknown",
            'timestamp': r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })
    return render_template('attendance.html', records=result)
# Student Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=5000, debug=True)
