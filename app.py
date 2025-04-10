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

@app.route('/student-registration', methods = ['GET', 'POST'])
def student_registration():
    if request.method == 'POST':
        uni_id = request.form.get("username")
        password = request.form.get("password")
        result = db.session.execute(text('SELECT uni_id FROM user WHERE uni_id = :uni_id'), {'uni_id': uni_id})
        existing_user = result.fetchone()

        if existing_user:
            return render_template('Student_Registration_Page.html')
        new_student = User(uni_id=uni_id, password=password, role='student')
        db.session.add(new_student)
        db.session.commit()
        return render_template('Student_Registration_Page.html')
    return render_template('Student_Registration_Page.html')

# To make the student login run
@app.route('/student-login')
def student_login():
    return render_template('Student_Login_Page.html')

# To make the teacher login run
@app.route('/teacher-login')
def teacher_login():
    return render_template('Teacher_Login_Page.html')

# To make the admin run
@app.route('/admin-login')
def admin_login():
    return render_template('Admin_Login_Page.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
