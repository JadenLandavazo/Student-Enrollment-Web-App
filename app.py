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
from flask_admin import Admin, expose, AdminIndexView
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

    student_classes = db.relationship('Enrollment', backref='student', lazy=True, passive_deletes=True)
    teacher_classes = db.relationship('TeacherClass', backref='teacher', lazy=True, passive_deletes=True)

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
    day = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    max_seats = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<TeacherClass Teacher:{self.teacher_id} Class:{self.class_id}>'

# Flask-Admin setup
class SecureModelView(ModelView):
    def is_accessible(self):
        print("Role in session:", session.get('role'))  # Debugging print
        return session.get('role') == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        print("Inaccessible callback triggered")  # Debugging print
        return redirect(url_for('admin_login'))

class TeacherClassModelView(SecureModelView):
    form_columns = ['teacher_id', 'class_id', 'day', 'time', 'max_seats']
class GradeModelView(SecureModelView):
    form_columns = ['student_id', 'class_id', 'grade']
class UserModelView(SecureModelView):
    form_columns = ['id', 'uni_id','password','role']
    
class SecureAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if session.get('role') != 'admin':
            return redirect(url_for('admin_login'))
        return super().index()

# Flask-Admin setup
admin = Admin(app, name='School Admin', template_mode='bootstrap3',
              index_view=SecureAdminIndexView(url='/admin/'))
admin.add_view(UserModelView(User, db.session))
admin.add_view(SecureModelView(Class, db.session))
admin.add_view(GradeModelView(Enrollment, db.session))
admin.add_view(TeacherClassModelView(TeacherClass, db.session))

# Routes
@app.route('/')
def home():
    return render_template('Home.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == '1':
            session['role'] = 'admin'
            return redirect(url_for('admin.index'))
        return render_template('Admin_Login_Page.html', error='Invalid credentials')
    return render_template('Admin_Login_Page.html')

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

@app.route('/forgot-password/<role>', methods=['GET', 'POST'])
def forgot_password(role):
    message = ""
    if request.method == 'POST':
        uni_id = request.form.get('uni_id')
        user = User.query.filter_by(uni_id=uni_id, role=role).first()

        if user:
            message = f"Your password is: {user.password}"
        else:
            message = "No account found with that University ID."

    return render_template('Forgot_Password_Page.html', message=message, role=role)


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
        teacher_info = class_.teachers[0] if class_.teachers else None

        teacher_name = teacher_info.teacher.uni_id if teacher_info else "TBA"
        class_time = f"{teacher_info.time}" if teacher_info else "TBD"

        max_seats = teacher_info.max_seats if teacher_info else 30  # Default fallback value

        student_count = len(class_.students)

        courses.append({
            "name": class_.name,
            "teacher_name": teacher_name,
            "time": class_time,
            "student_count": student_count,
            "max_seats": max_seats  # Ensure this is included in the dictionary
        })

    return render_template('student_view_courses.html', student_name=student.uni_id, courses=courses)


@app.route('/student-add-courses')
def student_add_courses():
    uni_id = session.get('uni_id')
    if not uni_id:
        return redirect(url_for('student_login'))

    student = User.query.filter_by(uni_id=uni_id, role='student').first()
    if not student:
        return redirect(url_for('student_login')) 

    enrolled_class_ids = [enrollment.class_id for enrollment in student.student_classes]

    all_classes = Class.query.all()
    courses = []

    for class_ in all_classes:
        teacher_info = class_.teachers[0] if class_.teachers else None

        # Dynamically fetch the teacher's information
        teacher_name = teacher_info.teacher.uni_id if teacher_info else "TBA"
        class_time = f"{teacher_info.time}" if teacher_info else "TBD"

        # Dynamically fetch max_seats from TeacherClass (if a teacher exists for the class)
        max_seats = teacher_info.max_seats if teacher_info else 30  # Default to 30 if no teacher

        student_count = len(class_.students)
        is_enrolled = class_.id in enrolled_class_ids
        is_full = student_count >= max_seats

        courses.append({
            "id": class_.id,
            "name": class_.name,
            "teacher_name": teacher_name,
            "time": class_time,
            "student_count": student_count,
            "is_enrolled": is_enrolled,
            "is_full": is_full,
            "max_seats": max_seats  # Dynamically include max_seats from TeacherClass
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

    new_enrollment = Enrollment(student_id=student.id, class_id=course_id, grade=0.00)
    db.session.add(new_enrollment)
    db.session.commit()

    return redirect(url_for('student_add_courses'))

@app.route('/unenroll/<int:course_id>')
def unenroll(course_id):
    if 'uni_id' not in session:
        return redirect(url_for('student_login'))

    student = User.query.filter_by(uni_id=session['uni_id']).first()

    enrollment = Enrollment.query.filter_by(student_id=student.id, class_id=course_id).first()
    if enrollment:
        db.session.delete(enrollment)
        db.session.commit()

    return redirect(url_for('student_add_courses'))

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

    return render_template('Teacher_Login_Page.html')


@app.route('/teacher-view-course/<int:class_id>')
def teacher_view_course(class_id):

    class_ = Class.query.get_or_404(class_id)

    teacher_class = class_.teachers[0]
    teacher = User.query.get(teacher_class.teacher_id)

    # Get enrolled students and their grades
    enrollments = Enrollment.query.filter_by(class_id=class_id).all()
    students = []
    for enrollment in enrollments:
        student = User.query.get(enrollment.student_id)
        students.append({
            "student_id": student.id,
            "name": student.uni_id,
            "grade": enrollment.grade
        })

    return render_template('Teacher_View_Course.html', class_ = class_, students=students, teacher_name= teacher.uni_id)
@app.route('/update-grade/<int:student_id>/<int:class_id>', methods=['POST'])
def update_grade(student_id, class_id):
    new_grade = request.form.get('grade')
    
    # Find the enrollment and update the grade
    enrollment = Enrollment.query.filter_by(student_id=student_id, class_id=class_id).first()
    if enrollment:
        enrollment.grade = new_grade
        db.session.commit()
    
    # Redirect back (or adjust based on where you're coming from)
    return redirect(request.referrer)

@app.route('/teacher-dashboard', methods=['GET', 'POST'])
def teacher_dashboard():
    uni_id = session.get('uni_id')

    if not uni_id:
        return redirect(url_for('teacher_login'))

    teacher = User.query.filter_by(uni_id=uni_id, role='teacher').first()
    if not teacher:
        return redirect(url_for('teacher_login')) 

    teacher_classes = TeacherClass.query.filter_by(teacher_id=teacher.id).all()

    courses = []
    for entry in teacher_classes:
        class_ = Class.query.get(entry.class_id)
       

        courses.append({
            "id": class_.id,
            "name": class_.name,
            "teacher_name": teacher.uni_id,
            "time": entry.time,
            "day": entry.day,
            "student_count": len(class_.students),
            "max_count": entry.max_seats,
        })

    return render_template('teacher_dashboard.html', teacher_name=teacher.uni_id, teacher_courses=courses)


@app.route('/student-test-data')
def student_test_data():
    db.drop_all()
    db.create_all()

    student = User(uni_id='teststudent', password='123', role='student')
    math = Class(id=1, name='Math 101')
    cs = Class(id=2, name='CS 106')
    physics = Class(id=3, name='Physics 121')

    db.session.add_all([student, math, cs, physics])
    db.session.commit()

    return "Test student and course data created."


@app.route('/sample-data')
def init_sample_data():
    db.drop_all()
    db.create_all()
    # Create users
    students = [
        User(uni_id='Jaden Landavazo', password='pass1', role='student'),
        User(uni_id='Adrian Botello', password='pass2', role='student'),
        User(uni_id='Toshinori Oizumi', password='pass3', role='student'),
        User(uni_id='Reykjavik Salvador', password='pass4', role='student'),
        User(uni_id='John Doe', password='pass5', role='student')
    ]

    teacher = User(uni_id='John Pork', password='teachpass', role='teacher')
    admin = User(uni_id='admin1', password='adminpass', role='admin')

    db.session.add_all(students + [teacher, admin])
    db.session.commit()

    # Create classes
    class1 = Class(name='Math 101', description='Intro to Math')
    class2 = Class(name='History 201', description='World History Overview')
    db.session.add_all([class1, class2])
    db.session.commit()

    # Assign teacher to classes
    teacher_class1 = TeacherClass(teacher_id=teacher.id, class_id=class1.id, day='MW', time='MW 10:00-11:15 AM', max_seats=30)
    teacher_class2 = TeacherClass(teacher_id=teacher.id, class_id=class2.id, day='TT', time='TT 1:00-2:15 PM', max_seats=30)
    db.session.add_all([teacher_class1, teacher_class2])
    db.session.commit()

    # Enroll students in classes
    enrollments = [
        Enrollment(student_id=students[0].id, class_id=class1.id, grade=85.0),
        Enrollment(student_id=students[1].id, class_id=class1.id, grade=90.5),
        Enrollment(student_id=students[2].id, class_id=class2.id, grade=78.0),
        Enrollment(student_id=students[3].id, class_id=class2.id, grade=88.5),
        Enrollment(student_id=students[4].id, class_id=class1.id, grade=55.8)
    ]
    db.session.add_all(enrollments)
    db.session.commit()

    return "✅ Sample data initialized!"




if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)