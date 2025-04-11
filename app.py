# redirect user to the correct page when logged in 
# based on authority of user 
# teacher page: display a table of the classes the teacher teaches 
# with the columns: course name, teacher, time, students enrolled
# if the teacher clicks on a course name, they get redirected 
# to a table of students in that class with their name and grades
# in two separate columns
# handle sign out
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import text

# create a new sql database uri 
# created an app object
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'

# created the student database
db = SQLAlchemy(app)
# these are the attributes of a user of the website
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uni_id = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "student", "teacher", "admin"

    # relationships of user
    student_classes = db.relationship('Enrollment', backref='student', lazy=True)
    teacher_classes = db.relationship('TeacherClass', backref='teacher', lazy=True)

    # makes the object easy to idenrify when debugging
    def __repr__(self):
        return f'<User {self.username}>'
    
# these are the attributes of a class that the user can pick 
# on the website    
class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Relationships of class
    students = db.relationship('Enrollment', backref='class_', lazy=True)
    teachers = db.relationship('TeacherClass', backref='class_', lazy=True)

    # makes the object easy to idenrify when debugging
    def __repr__(self):
        return f'<Class {self.name}>'

# these are the attributes of the enrollment class
# this represents the association between students and classes
class Enrollment(db.Model):
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), primary_key=True)
    grade = db.Column(db.Float, nullable=True)  # Nullable since grades may not be assigned initially

    def __repr__(self):
        return f'<Enrollment Student:{self.student_id} Class:{self.class_id}>'

# these are the attributes of the teacher class 
# this represents the association between teachers and the classes
# they teach
class TeacherClass(db.Model):
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), primary_key=True)

     # makes the object easy to idenrify when debugging
    def __repr__(self):
        return f'<TeacherClass Teacher:{self.teacher_id} Class:{self.class_id}>'

# Flask-Admin Integration
admin = Admin(app, name='School Admin', template_mode='bootstrap3')
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Class, db.session))
admin.add_view(ModelView(Enrollment, db.session))
admin.add_view(ModelView(TeacherClass, db.session))

#Registration logic

# temporary routing just to make the app run
@app.route('/')
def home():
    return render_template('Home.html')

# For Sudent Registration
@app.route('/student-registration', methods=['GET', 'POST'])
def student_registration():
    if request.method == 'POST':
        uni_id = request.form.get("uni_id")  
        password = request.form.get("password")
        
        # Check if user exists
        existing_user = User.query.filter_by(uni_id=uni_id).first()
        if existing_user:
            return render_template('Student_Registration_Page.html', message="User already exists!", uni_id=uni_id)  # Pass back the entered ID
        
        # Create new user
        new_student = User(uni_id=uni_id, password=password, role='student')
        db.session.add(new_student)
        db.session.commit()
        return redirect(url_for('student_login'))  # Redirect to login after success
    
    return render_template('Student_Registration_Page.html')

# To see the users 
@app.route('/users')
def show_users():
    users = User.query.all()
    return render_template('Users.html', users=users)


# To make the student login run
@app.route('/student-login', methods = ['GET', 'POST'])
def student_login():
    #iterate through the table
    if request.method == 'POST':
        uni_id = request.form.get("username")
        password = request.form.get("password")

        result = db.session.execute(text('SELECT * FROM user WHERE uni_id = :uni_id AND password = :password'), {'uni_id': uni_id, 'password': password})
        
        student = result.fetchone()

        if student:
            return redirect(url_for('student_view_courses'))
        else:
            return render_template('Student_Login_Page.html', error="Invalid username or password")

        
    return render_template('Student_Login_Page.html')

@app.route('/student-view-courses')
def student_view_courses():
    return render_template('Student_View_Courses.html')

# For Teacher Registration
@app.route('/teacher-registration', methods=['GET', 'POST'])
def teacher_registration():
    if request.method == 'POST':
        uni_id = request.form.get("uni_id")  
        password = request.form.get("password")
        
        # Check if user exists
        existing_user = User.query.filter_by(uni_id=uni_id).first()
        if existing_user:
            return render_template('Teacher_Registration_Page.html', message="User already exists!", uni_id=uni_id)  # Pass back the entered ID
        
        # Create new user
        new_teacher = User(uni_id=uni_id, password=password, role='teacher')
        db.session.add(new_teacher)
        db.session.commit()
        return redirect(url_for('teacher_login'))  # Redirect to login after success
    
    return render_template('Teacher_Registration_Page.html')

# To make the teacher login run
@app.route('/teacher-login', methods = ['GET', 'POST'])
def teacher_login():
    #iterate through the table
    if request.method == 'POST':
        uni_id = request.form.get("username")
        password = request.form.get("password")

        result = db.session.execute(text('SELECT * FROM user WHERE uni_id = :uni_id AND password = :password'), {'uni_id': uni_id, 'password': password})
        
        teacher = result.fetchone()

        if teacher:
            return redirect(url_for('Teacher_View_Courses'))
        else:
            return render_template('Teacher_Login_Page.html', error="Invalid username or password")
    return render_template('Teacher_Login_Page.html')

# To make the admin run
@app.route('/admin-login')
def admin_login():
    return render_template('Admin_Login_Page.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
