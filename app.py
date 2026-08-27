from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models.user import User, Student, Score
import os

app = Flask(__name__)
app.secret_key = "secret_key_change_later"

# DB
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "school.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ======================
# CREATE DB + ADMIN
# ======================
with app.app_context():
    db.create_all()

    admin = User.query.filter_by(username="Admin").first()
    if not admin:
        admin = User(
            username="Admin",
            password=generate_password_hash("administrator"),
            role="admin",
            name="System Admin"
        )
        db.session.add(admin)
        db.session.commit()


# ======================
# HOME
# ======================
@app.route("/")
def home():
    return redirect("/login")


# ======================
# REGISTER (STUDENTS ONLY)
# ======================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        exists = User.query.filter_by(username=username).first()
        if exists:
            user_exist = "User exists"
            return render_template("register.html", user_exist=user_exist)

        user = User(username=username, password=password, role="student")
        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")


# ======================
# LOGIN (ADMIN / TEACHER ONLY)
# ======================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["user"] = user.username
            session["role"] = user.role
            return redirect("/dashboard")

        invalid = "Invalid Login Credentials"
        return render_template("login.html", invalid=invalid)

    return render_template("login.html")

# ======================
# DASHBOARD ROUTER
# ======================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    role = session["role"]

    if role == "admin":
        return render_template("admin_dashboard.html", user=session["user"])

    elif role == "teacher":
        return render_template("teacher_dashboard.html", user=session["user"])

    return "Student dashboard not implemented yet"


# ======================
# CREATE STUDENT
# ======================
@app.route("/create-student", methods=["GET", "POST"])
def create_student():
    if session.get("role") != "admin":
        return "Unauthorized"

    if request.method == "POST":
        name = request.form["name"]
        class_name = request.form["class_name"]

        student = Student(name=name, class_name=class_name)
        db.session.add(student)
        db.session.commit()

        return redirect("/dashboard")

    return render_template("create_student.html")


# ======================
# CREATE TEACHER
# ======================
@app.route("/create-teacher", methods=["GET", "POST"])
def create_teacher():
    if session.get("role") != "admin":
        return "Unauthorized"

    if request.method == "POST":
        user = User(
            username=request.form["username"],
            name=request.form["name"],
            password=generate_password_hash(request.form["password"]),
            role="teacher",
            allowed_subjects=request.form["subjects"],
            allowed_class=request.form["classs"]
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/dashboard")

    return render_template("create_teacher.html")


# ======================
# ADD SCORE (STEP 1)
# ======================
@app.route("/add-score", methods=["GET", "POST"])
def add_score():
    if session.get("role") != "teacher":
        return "Unauthorized"

    teacher = User.query.filter_by(username=session["user"]).first()
    subjects = teacher.allowed_subjects.split(",")
    classs = teacher.allowed_class.split(",")

    if request.method == "POST":
        class_name = request.form["class_name"]
        subject = request.form["subject"]

        students = Student.query.filter_by(class_name=class_name).all()

        return render_template(
            "enter_scores.html",
            students=students,
            subject=subject
        )

    return render_template("add_score_select.html", subjects=subjects)


# ======================
# SAVE SCORES
# ======================
@app.route("/save-scores", methods=["POST"])
def save_scores():
    if session.get("role") != "teacher":
        return "Unauthorized", 403

    subject = request.form.get("subject")

    processed_students = set()

    for key in request.form:
        if key.startswith("ca1_"):
            student_id = key.split("_")[1]

            # prevent duplicate processing
            if student_id in processed_students:
                continue

            processed_students.add(student_id)

            ca1 = request.form.get(f"ca1_{student_id}")
            ca2 = request.form.get(f"ca2_{student_id}")
            exam = request.form.get(f"exam_{student_id}")

            # check if score already exists (optional but recommended)
            existing = Score.query.filter_by(
                student_id=student_id,
                subject=subject
            ).first()

            if existing:
                # update instead of duplicate insert
                existing.ca1 = ca1
                existing.ca2 = ca2
                existing.exam = exam
            else:
                new_score = Score(
                    student_id=student_id,
                    subject=subject,
                    ca1=ca1,
                    ca2=ca2,
                    exam=exam
                )
                db.session.add(new_score)

    db.session.commit()
    return render_template("enter_scores.html")

@app.route("/students")
def students():
    if session.get("role") not in ["teacher", "admin"]:
        return "Unauthorized"

    all_students = Student.query.all()
    return render_template("students.html", students=all_students)

@app.route("/delete-student/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    if session.get("role") not in ["teacher", "admin"]:
        return "Unauthorized"

    student = Student.query.get(student_id)
    if student:
        db.session.delete(student)
        db.session.commit()

    return redirect("/students")

@app.route("/student/<int:student_id>")
def student_profile(student_id):
    if session.get("role") not in ["teacher", "admin"]:
        return "Unauthorized"

    student = Student.query.get_or_404(student_id)
    scores = Score.query.filter_by(student_id=student_id).all()

    return render_template("student_profile.html", student=student, scores=scores)

#---------------------------

@app.route("/teachers")
def teachers():
    if session.get("role") not in ["teacher", "admin"]:
        return "Unauthorized"

    all_teachers = User.query.filter(User.role != "admin").all()
    return render_template("teachers.html", teachers=all_teachers)


@app.route("/delete-teacher/<int:user_id>", methods=["POST"])
def delete_teacher(user_id):
    if session.get("role") not in ["teacher", "admin"]:
        return "Unauthorized"

    teacher = User.query.get(user_id)
    if teacher:
        db.session.delete(teacher)
        db.session.commit()

    return redirect("/teachers")

@app.route("/teacher/<int:user_id>")
def teacher_profile(user_id):
    if session.get("role") not in ["teacher", "admin"]:
        return "Unauthorized"

    teacher = User.query.get_or_404(user_id)

    return render_template("teacher_profile.html", teacher=teacher)
# ======================
# LOGOUT
# ======================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
    
# Create Student list and Teacher list page
# Create student and teacher profile page
# add removal of student and teachers