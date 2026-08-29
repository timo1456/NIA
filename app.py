from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db

from models.user import (
    User,
    Student,
    Subject,
    TeacherAssignment,
    Score
)

import os


# ==================================================
# APP
# ==================================================

app = Flask(__name__)

app.secret_key = "secret_key_change_later"


# ==================================================
# DATABASE
# ==================================================

basedir = os.path.abspath(
    os.path.dirname(__file__)
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///"
    + os.path.join(basedir, "school.db")
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ==================================================
# CLASSES
# ==================================================

CLASSES = [
    "JSS 1",
    "JSS 2",
    "JSS 3",
    "SSS 1",
    "SSS 2",
    "SSS 3"
]



# ==================================================
# DATABASE INITIALIZATION
# ==================================================

with app.app_context():

    db.create_all()

    admin = User.query.filter_by(
        username="Admin"
    ).first()

    if not admin:

        admin = User(
            username="Admin",
            password=generate_password_hash(
                "administrator"
            ),
            role="admin",
            name="System Admin"
        )

        db.session.add(admin)
        db.session.commit()



@app.route("/")
def home():

    return redirect("/login")




@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()

        password = generate_password_hash(
            request.form["password"]
        )

        existing = User.query.filter_by(
            username=username
        ).first()

        if existing:

            return render_template(
                "register.html",
                user_exist="User exists"
            )

        user = User(
            username=username,
            password=password,
            role="student"
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template(
        "register.html"
    )



@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            session["user"] = user.username
            session["role"] = user.role
            session["user_id"] = user.id

            return redirect("/dashboard")

        return render_template(
            "login.html",
            invalid="Invalid Login Credentials"
        )

    return render_template(
        "login.html"
    )


# ==================================================
# DASHBOARD
# ==================================================

@app.route("/dashboard")
def dashboard():

    if "user" not in session:

        return redirect("/login")

    if session["role"] == "admin":

        return render_template(
            "admin_dashboard.html",
            user=session["user"]
        )

    if session["role"] == "teacher":

        return render_template(
            "teacher_dashboard.html",
            user=session["user"]
        )

    return "Student dashboard not implemented yet"


# ==================================================
# SUBJECT MANAGEMENT
# ==================================================

@app.route(
    "/add-subject",
    methods=["GET", "POST"]
)
def add_subject():

    if session.get("role") != "admin":

        return "Unauthorized", 403

    if request.method == "POST":

        name = request.form["name"].strip()

        if not name:

            return render_template(
                "add_subject.html",
                error="Subject name cannot be empty."
            )

        existing = Subject.query.filter_by(
            name=name
        ).first()

        if existing:

            return render_template(
                "add_subject.html",
                error="Subject already exists."
            )

        subject = Subject(
            name=name
        )

        db.session.add(subject)
        db.session.commit()

        return redirect("/subjects")

    return render_template(
        "add_subject.html"
    )


# ==================================================
# SUBJECT LIST
# ==================================================

@app.route("/subjects")
def subjects():

    if session.get("role") != "admin":

        return "Unauthorized", 403

    all_subjects = Subject.query.order_by(
        Subject.name
    ).all()

    return render_template(
        "subjects.html",
        subjects=all_subjects
    )


# ==================================================
# DELETE SUBJECT
# ==================================================

@app.route(
    "/delete-subject/<int:subject_id>",
    methods=["POST"]
)
def delete_subject(subject_id):

    if session.get("role") != "admin":

        return "Unauthorized", 403

    subject = Subject.query.get(
        subject_id
    )

    if subject:

        TeacherAssignment.query.filter_by(
            subject_id=subject.id
        ).delete()

        Score.query.filter_by(
            subject_id=subject.id
        ).delete()

        db.session.delete(subject)

        db.session.commit()

    return redirect("/subjects")


# ==================================================
# STUDENT MANAGEMENT
# ==================================================
GENDER = [
    "Male",
    "Female"
]
@app.route(
    "/create-student",
    methods=["GET", "POST"]
)
def create_student():

    if session.get("role") != "admin":

        return "Unauthorized", 403

    if request.method == "POST":

        name = request.form["name"].strip()

        class_name = request.form[
            "class_name"
        ]
        gender = request.form["gender"]

        student = Student(
            name=name,
            class_name=class_name,
            gender=gender
        )

        db.session.add(student)
        db.session.commit()

        return redirect("/students")

    return render_template(
        "create_student.html",
        classes=CLASSES,
        gen_der=GENDER
    )


# ==================================================
# STUDENT LIST
# ==================================================

@app.route("/students")
def students():

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:

        return "Unauthorized", 403

    all_students = Student.query.order_by(
        Student.class_name,
        Student.name
    ).all()

    return render_template(
        "students.html",
        students=all_students
    )


# ==================================================
# DELETE STUDENT
# ==================================================

@app.route(
    "/delete-student/<int:student_id>",
    methods=["POST"]
)
def delete_student(student_id):

    if session.get("role") != "admin":

        return "Unauthorized", 403

    student = Student.query.get(
        student_id
    )

    if student:

        Score.query.filter_by(
            student_id=student.id
        ).delete()

        db.session.delete(student)

        db.session.commit()

    return redirect("/students")


# ==================================================
# STUDENT PROFILE
# ==================================================

@app.route(
    "/student/<int:student_id>"
)
def student_profile(student_id):

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:

        return "Unauthorized", 403

    student = Student.query.get_or_404(
        student_id
    )

    scores = Score.query.filter_by(
        student_id=student.id
    ).all()

    return render_template(
        "student_profile.html",
        student=student,
        scores=scores
    )


# ==================================================
# CREATE TEACHER
# ==================================================

@app.route(
    "/create-teacher",
    methods=["GET", "POST"]
)
def create_teacher():

    if session.get("role") != "admin":

        return "Unauthorized", 403

    subjects = Subject.query.order_by(
        Subject.name
    ).all()

    if request.method == "POST":

        name = request.form["name"].strip()

        username = request.form[
            "username"
        ].strip()

        password = request.form[
            "password"
        ]

        existing = User.query.filter_by(
            username=username
        ).first()

        if existing:

            return render_template(
                "create_teacher.html",
                subjects=subjects,
                classes=CLASSES,
                error="Username already exists."
            )

        # ------------------------------------------
        # GET ASSIGNMENTS
        # ------------------------------------------

        assignment_classes = request.form.getlist(
            "assignment_class"
        )

        assignment_subjects = request.form.getlist(
            "assignment_subject"
        )

        # ------------------------------------------
        # CREATE TEACHER
        # ------------------------------------------

        teacher = User(
            name=name,
            username=username,
            password=generate_password_hash(
                password
            ),
            role="teacher"
        )

        db.session.add(teacher)

        # Flush gives teacher an ID
        db.session.flush()

        # ------------------------------------------
        # CREATE ASSIGNMENTS
        # ------------------------------------------

        for i in range(
            len(assignment_classes)
        ):

            class_name = assignment_classes[i]

            subject_id = int(
                assignment_subjects[i]
            )

            # Validate class
            if class_name not in CLASSES:

                continue

            subject = Subject.query.get(
                subject_id
            )

            if not subject:

                continue

            assignment = TeacherAssignment(
                teacher_id=teacher.id,
                subject_id=subject.id,
                class_name=class_name
            )

            db.session.add(
                assignment
            )

        db.session.commit()

        return redirect("/teachers")

    return render_template(
        "create_teacher.html",
        subjects=subjects,
        classes=CLASSES
    )


# ==================================================
# TEACHER LIST
# ==================================================

@app.route("/teachers")
def teachers():

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:

        return "Unauthorized", 403

    all_teachers = User.query.filter_by(
        role="teacher"
    ).order_by(
        User.name
    ).all()

    return render_template(
        "teachers.html",
        teachers=all_teachers
    )


# ==================================================
# DELETE TEACHER
# ==================================================

@app.route(
    "/delete-teacher/<int:user_id>",
    methods=["POST"]
)
def delete_teacher(user_id):

    if session.get("role") != "admin":

        return "Unauthorized", 403

    teacher = User.query.filter_by(
        id=user_id,
        role="teacher"
    ).first()

    if teacher:

        TeacherAssignment.query.filter_by(
            teacher_id=teacher.id
        ).delete()

        db.session.delete(
            teacher
        )

        db.session.commit()

    return redirect("/teachers")


# ==================================================
# TEACHER PROFILE
# ==================================================

@app.route(
    "/teacher/<int:user_id>"
)
def teacher_profile(user_id):

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:

        return "Unauthorized", 403

    teacher = User.query.filter_by(
        id=user_id,
        role="teacher"
    ).first_or_404()

    assignments = TeacherAssignment.query.filter_by(
        teacher_id=teacher.id
    ).join(
        Subject
    ).order_by(
        TeacherAssignment.class_name,
        Subject.name
    ).all()

    return render_template(
        "teacher_profile.html",
        teacher=teacher,
        assignments=assignments
    )


# ==================================================
# ADD SCORE
# ==================================================

@app.route(
    "/add-score",
    methods=["GET", "POST"]
)
def add_score():

    if session.get("role") != "teacher":

        return "Unauthorized", 403

    teacher = User.query.filter_by(
        id=session["user_id"],
        role="teacher"
    ).first()

    assignments = TeacherAssignment.query.filter_by(
        teacher_id=teacher.id
    ).join(
        Subject
    ).order_by(
        TeacherAssignment.class_name,
        Subject.name
    ).all()

    if request.method == "POST":

        assignment_id = request.form.get(
            "assignment_id"
        )

        assignment = TeacherAssignment.query.filter_by(
            id=assignment_id,
            teacher_id=teacher.id
        ).first()

        if not assignment:

            return "Unauthorized", 403

        students = Student.query.filter_by(
            class_name=assignment.class_name
        ).order_by(
            Student.name
        ).all()

        return render_template(
            "enter_scores.html",
            students=students,
            subject=assignment.subject,
            assignment=assignment
        )

    return render_template(
        "add_score_select.html",
        assignments=assignments
    )


# ==================================================
# SAVE SCORES
# ==================================================

@app.route(
    "/save-scores",
    methods=["POST"]
)
def save_scores():

    if session.get("role") != "teacher":

        return "Unauthorized", 403

    teacher = User.query.filter_by(
        id=session["user_id"],
        role="teacher"
    ).first()

    assignment_id = request.form.get(
        "assignment_id"
    )

    assignment = TeacherAssignment.query.filter_by(
        id=assignment_id,
        teacher_id=teacher.id
    ).first()

    if not assignment:

        return "Unauthorized", 403

    processed_students = set()

    for key in request.form:

        if not key.startswith("ca1_"):

            continue

        student_id = key.split("_")[1]

        if student_id in processed_students:

            continue

        processed_students.add(
            student_id
        )

        student = Student.query.filter_by(
            id=student_id,
            class_name=assignment.class_name
        ).first()

        if not student:

            continue

        ca1 = int(request.form.get(
            f"ca1_{student_id}"
        ) or 0)

        ca2 = int(request.form.get(
            f"ca2_{student_id}"
        ) or 0)
        ca3 = int(request.form.get(
            f"ca3_{student_id}"
        ) or 0)

        exam = int(request.form.get(
            f"exam_{student_id}"
        ) or 0)

        total = ca1 + ca2 + ca3 + exam

        

        existing = Score.query.filter_by(
            student_id=student.id,
            subject_id=assignment.subject_id
        ).first()

        if existing:

            existing.ca1 = ca1 or 0
            existing.ca2 = ca2 or 0
            existing.ca3 = ca3 or 0
            existing.exam = exam or 0
            existing.total = total or 0

        else:

            new_score = Score(
                student_id=student.id,
                subject_id=assignment.subject_id,
                ca1=ca1 or 0,
                ca2=ca2 or 0,
                ca3=ca3 or 0,
                exam=exam or 0,
                total=total or 0
            )

            db.session.add(
                new_score
            )

    db.session.commit()

    return redirect("/add-score")

def result_sheet():

    # get class/subject
    ...

    scores = Score.query.filter_by(
        subject_id=subject_id
    ).join(
        Student
    ).filter(
        Student.class_name == class_name
    ).all()

    student_count = len(scores)

    if student_count > 0:
        class_average = sum(
            score.total for score in scores
        ) / student_count
    else:
        class_average = 0

    # render result sheet
    return render_template(
        "result_sheet.html",
        scores=scores,
        class_average=class_average
    )

# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )