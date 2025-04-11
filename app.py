# redirect user to the correct page when logged in 
# based on authority of user 
# teacher page: display a table of the classes the teacher teaches 
# with the columns: course name, teacher, time, students enrolled
# if the teacher clicks on a course name, they get redirected 
# to a table of students in that class with their name and grades
# in two separate columns
# handle sign out

import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

# create a new sql database uri 
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.secret_key = os.urandom(24)

# initialize database
db = SQLAlchemy(app)

# define user model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uni_id = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "student", "teacher", "admin"

    student_classes = db.relationship('Enrollment', backref='student', lazy=True)
    teacher_classes = db.relationship('TeacherClass', backref='teacher', lazy=True)

    def __repr__(self):
        return f'<User {self.uni_id}>'

# define class model
class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    students = db.relationship('Enrollment', backref='class_', lazy=True)
    teachers = db.relationship('TeacherClass', backref='class_', lazy=True)

    def __repr__(self):
        return f'<Class {self.name}>'

# enrollment association table
class Enrollment(db.Model):
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), primary_key=True)
    grade = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<Enrollment Student:{self.student_id} Class:{self.class_id}>'

# teacher-class association table
class TeacherClass(db.Model):
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), primary_key=True)

    def __repr__(self):
        return f'<TeacherClass Teacher:{self.teacher_id} Class:{self.class_id}>'

# Flask-Admin setup
admin = Admin(app, name='School Admin', template_mode='bootstrap3')
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Class, db.session))
admin.add_view(ModelView(Enrollment, db.session))
admin.add_view(ModelView(TeacherClass, db.session))

# routes

@app.route('/')
def home():
    return render_template('Home.html')

@app.route('/student-registration', methods=['GET', 'POST'])
def student_registration():
    if request.method == 'POST':
        uni_id = request.form.get("uni_id")
        password = request.form.get("password")

        existing_user = User.query.filter_by(uni_id=uni_id).first()
        if existing_user:
            return render_template('Student_Registration_Page.html', message="User already exists!", uni_id=uni_id)

        new_student = User(uni_id=uni_id, password=password, role='student')
        db.session.add(new_student)
        db.session.commit()
        return redirect(url_for('student_login'))

    return render_template('Student_Registration_Page.html')

@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        uni_id = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(uni_id=uni_id).first()

        if not user:
            error = "University ID not found."
        elif user.password != password:
            error = "Incorrect password."
        else:
            session['uni_id'] = uni_id
            return redirect(url_for('student_view_courses'))

        return render_template('Student_Login_Page.html', error=error)

    return render_template('Student_Login_Page.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    message = ""
    if request.method == 'POST':
        uni_id = request.form.get('uni_id')
        user = User.query.filter_by(uni_id=uni_id).first()

        if user:
            message = f"Your password is: {user.password}"
        else:
            message = "No account found with that University ID."

    return render_template('Forgot_Password_Page.html', message=message)

@app.route('/student-view-courses')
def student_view_courses():
    uni_id = session.get('uni_id')
    if not uni_id:
        return redirect(url_for('student_login'))

    student = User.query.filter_by(uni_id=uni_id, role='student').first()
    if not student:
        return redirect(url_for('student_login'))

    enrolled_classes = Class.query\
        .join(Enrollment, Class.id == Enrollment.class_id)\
        .filter(Enrollment.student_id == student.id)\
        .all()

    courses = []
    for class_ in enrolled_classes:
        teacher_name = "TBA"
        if class_.teachers:
            teacher = class_.teachers[0].teacher
            teacher_name = teacher.uni_id

        courses.append({
            "name": class_.name,
            "teacher_name": teacher_name,
            "time": "TBD",
            "student_count": len(class_.students)
        })

    return render_template('Student_View_Courses.html', student_name=student.uni_id, courses=courses)

@app.route('/student-add-courses')
def student_add_courses():
    uni_id = session.get('uni_id')
    if not uni_id:
        return redirect(url_for('student_login'))

    student = User.query.filter_by(uni_id=uni_id, role='student').first()
    if not student:
        return redirect(url_for('student_login'))

    enrolled_ids = [en.class_id for en in student.student_classes]
    available_classes = Class.query.filter(~Class.id.in_(enrolled_ids)).all()

    courses = []
    for class_ in available_classes:
        teacher_name = "TBA"
        if class_.teachers:
            teacher = class_.teachers[0].teacher
            teacher_name = teacher.uni_id

        courses.append({
            "id": class_.id,
            "name": class_.name,
            "teacher_name": teacher_name,
            "time": "TBD",
            "student_count": len(class_.students)
        })

    return render_template("Student_Add_Courses.html", student_name=student.uni_id, courses=courses)

@app.route('/enroll/<int:course_id>')
def enroll(course_id):
    if 'uni_id' not in session:
        return redirect(url_for('student_login'))

    student = User.query.filter_by(uni_id=session['uni_id']).first()

    existing = Enrollment.query.filter_by(student_id=student.id, class_id=course_id).first()
    if existing:
        return redirect(url_for('student_add_courses'))

    new_enrollment = Enrollment(student_id=student.id, class_id=course_id)
    db.session.add(new_enrollment)
    db.session.commit()

    return redirect(url_for('student_view_courses'))

@app.route('/users')
def show_users():
    users = User.query.all()
    return render_template('Users.html', users=users)

# For Teacher Registration
@app.route('/teacher-registration', methods=['GET', 'POST'])
def teacher_registration():
    if request.method == 'POST':
        uni_id = request.form.get("uni_id")  
        password = request.form.get("password")
        
        # Check if user exists
        existing_user = User.query.filter_by(uni_id=uni_id).first()
        if existing_user:
            return render_template('Teacher_Registration_Page.html', message="User ID already exists!", uni_id=uni_id)  # Pass back the entered ID
        
        # Create new user
        new_teacher = User(uni_id=uni_id, password=password, role='teacher')
        db.session.add(new_teacher)
        db.session.commit()
        return redirect(url_for('teacher_login'))  # Redirect to login after success
    
    return render_template('Teacher_Registration_Page.html')

# To make the teacher login run
@app.route('/teacher-login', methods = ['GET', 'POST'])
def teacher_login():
    error = None

    #iterate through the table
    if request.method == 'POST':
        uni_id = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(uni_id=uni_id).first()

        if not user: 
            error = "University ID not found."
        elif user.password != password: 
            error = "Incorrect password." 
        elif user.role != 'teacher': 
            error = "You are not authorized to access this page."
        else: 
            session['uni_id'] = uni_id
            return redirect(url_for('teacher_dashboard'))

    return render_template('Teacher_Login_Page.html', error=error)

@app.route('/teacher-view-course')
def teacher_view_course():
    return render_template('Teacher_View_Course.html')

@app.route('/teacher-dashboard', methods=['GET', 'POST'])
def teacher_dashboard():
    uni_id = session.get('uni_id')

    if not uni_id:
        return redirect(url_for('teacher_login'))

    teacher = User.query.filter_by(uni_id=uni_id, role='teacher').first()
    if not teacher:
        return redirect(url_for('teacher_login')) 

    enrolled_classes = Class.query \
        .join(TeacherClass, Class.id == TeacherClass.class_id) \
        .filter(TeacherClass.teacher_id == teacher.id) \
        .all()
    
    courses = []
    for class_ in enrolled_classes:
        teacher_name = "TBA"
        if class_.teachers:
            assigned_teacher = class_.teachers[0].teacher
            teacher_name = assigned_teacher.uni_id

        courses.append({
            "name": class_.name,
            "teacher_name": teacher_name,
            "time": "TBD",
            "student_count": len(class_.students)
        })

    return render_template('Teacher_Dashboard.html', teacher_name=teacher.uni_id, courses=courses)


@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    return render_template('Admin_Login_Page.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    return render_template('Admin_Dashboard.html')

# optional utility
@app.route('/student-check-data')
def student_check_data():
    students = User.query.filter_by(role='student').all()
    courses = Class.query.all()
    enrollments = Enrollment.query.all()
    return f"Students: {[s.uni_id for s in students]}<br>Courses: {[c.name for c in courses]}<br>Enrollments: {[(e.student_id, e.class_id) for e in enrollments]}"

@app.route('/student-create-test-data')
def student_create_test_data():
    student = User.query.filter_by(uni_id='teststudent').first()
    if not student:
        student = User(uni_id='teststudent', password='123', role='student')
        db.session.add(student)
    else:
        student.password = '123'
    db.session.commit()
    return "Test data ready"


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)