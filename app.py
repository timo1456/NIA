from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models.user import (
    User,
    Student,
    Subject,
    TeacherAssignment,
    Score,
    AcademicPeriod
)

import os


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "dev-only-secret-key-change-me"
)


basedir = os.path.abspath(
    os.path.dirname(__file__)
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///"
    + os.path.join(basedir, "school.db")
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


CLASSES = [
    "JSS 1",
    "JSS 2",
    "JSS 3",
    "SSS 1",
    "SSS 2",
    "SSS 3"
]

GENDER = [
    "Male",
    "Female"
]

SCORE_LIMITS = {
    "ca1": 10,
    "ca2": 20,
    "ca3": 20,
    "exam": 50
}


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


def get_active_period():

    return AcademicPeriod.query.filter_by(
        is_active=True
    ).first()


def get_valid_score(form, field, student_id):

    raw_value = form.get(
        f"{field}_{student_id}",
        "0"
    ).strip()

    if raw_value == "":
        raw_value = "0"

    try:
        value = int(raw_value)
    except ValueError:
        return None

    if value < 0 or value > SCORE_LIMITS[field]:
        return None

    return value


def calculate_total(score):

    if not score:
        return 0

    return (
        (score.ca1 or 0) +
        (score.ca2 or 0) +
        (score.ca3 or 0) +
        (score.exam or 0)
    )


def calculate_grade(total):

    if total >= 70:
        return "A"
    elif total >= 60:
        return "B"
    elif total >= 50:
        return "C"
    elif total >= 45:
        return "D"
    elif total >= 40:
        return "E"

    return "F"


def calculate_remark(total):

    if total >= 70:
        return "Excellent"
    elif total >= 60:
        return "Very Good"
    elif total >= 50:
        return "Good"
    elif total >= 45:
        return "Fair"
    elif total >= 40:
        return "Pass"

    return "Fail"


def get_term_score(student_id, subject_id, academic_session, term):
    period = AcademicPeriod.query.filter_by(
        academic_session=academic_session,
        term=term
    ).first()

    if not period:
        return None

    return Score.query.filter_by(
        student_id=student_id,
        subject_id=subject_id,
        academic_period_id=period.id
    ).first()


def calculate_cumulative(student_id, subject_id, active_period):
    current_score = Score.query.filter_by(
        student_id=student_id,
        subject_id=subject_id,
        academic_period_id=active_period.id
    ).first()

    current_total = calculate_total(current_score)

    if active_period.term == "First Term":
        return {
            "last_term_cumulative": None,
            "cumulative_average": current_total
        }

    first_score = get_term_score(
        student_id,
        subject_id,
        active_period.academic_session,
        "First Term"
    )

    first_total = calculate_total(first_score)

    if active_period.term == "Second Term":
        return {
            "last_term_cumulative": first_total,
            "cumulative_average": (first_total + current_total) / 2
        }

    second_score = get_term_score(
        student_id,
        subject_id,
        active_period.academic_session,
        "Second Term"
    )

    second_total = calculate_total(second_score)
    second_cumulative_average = (first_total + second_total) / 2

    return {
        "last_term_cumulative": second_cumulative_average,
        "cumulative_average": (
            second_cumulative_average + current_total
        ) / 2
    }


@app.route("/")
def home():
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not username or not password:

            return render_template(
                "register.html",
                user_exist="Username and password are required."
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
            password=generate_password_hash(password),
            role="student"
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            session.clear()
            session["user"] = user.username
            session["role"] = user.role
            session["user_id"] = user.id

            return redirect("/dashboard")

        return render_template(
            "login.html",
            invalid="Invalid Login Credentials"
        )

    return render_template("login.html")


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


@app.route("/add-subject", methods=["GET", "POST"])
def add_subject():

    if session.get("role") != "admin":
        return "Unauthorized", 403

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

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

        subject = Subject(name=name)

        db.session.add(subject)
        db.session.commit()

        return redirect("/subjects")

    return render_template("add_subject.html")


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


@app.route("/delete-subject/<int:subject_id>", methods=["POST"])
def delete_subject(subject_id):

    if session.get("role") != "admin":
        return "Unauthorized", 403

    subject = db.session.get(
        Subject,
        subject_id
    )

    if subject:

        TeacherAssignment.query.filter_by(
            subject_id=subject.id
        ).delete(synchronize_session=False)

        Score.query.filter_by(
            subject_id=subject.id
        ).delete(synchronize_session=False)

        db.session.delete(subject)
        db.session.commit()

    return redirect("/subjects")


@app.route("/create-student", methods=["GET", "POST"])
def create_student():

    if session.get("role") != "admin":
        return "Unauthorized", 403

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        class_name = request.form.get(
            "class_name",
            ""
        )

        gender = request.form.get(
            "gender",
            ""
        )

        if not name:

            return render_template(
                "create_student.html",
                classes=CLASSES,
                gen_der=GENDER,
                error="Student name cannot be empty."
            )

        if class_name not in CLASSES:

            return render_template(
                "create_student.html",
                classes=CLASSES,
                gen_der=GENDER,
                error="Please select a valid class."
            )

        if gender not in GENDER:

            return render_template(
                "create_student.html",
                classes=CLASSES,
                gen_der=GENDER,
                error="Please select a valid gender."
            )

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


@app.route("/delete-student/<int:student_id>", methods=["POST"])
def delete_student(student_id):

    if session.get("role") != "admin":
        return "Unauthorized", 403

    student = db.session.get(
        Student,
        student_id
    )

    if student:

        Score.query.filter_by(
            student_id=student.id
        ).delete(synchronize_session=False)

        db.session.delete(student)
        db.session.commit()

    return redirect("/students")


@app.route("/student/<int:student_id>")
def student_profile(student_id):

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:

        return "Unauthorized", 403

    student = db.session.get(
        Student,
        student_id
    )

    if not student:
        return "Student not found", 404

    active_period = get_active_period()

    scores = []

    if active_period:

        scores = Score.query.filter_by(
            student_id=student.id,
            academic_period_id=active_period.id
        ).join(
            Subject
        ).order_by(
            Subject.name
        ).all()

    return render_template(
        "student_profile.html",
        student=student,
        scores=scores,
        active_period=active_period
    )


@app.route("/create-teacher", methods=["GET", "POST"])
def create_teacher():

    if session.get("role") != "admin":
        return "Unauthorized", 403

    subjects = Subject.query.order_by(
        Subject.name
    ).all()

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not username or not password:

            return render_template(
                "create_teacher.html",
                subjects=subjects,
                classes=CLASSES,
                error="Name, username and password are required."
            )

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

        assignment_classes = request.form.getlist(
            "assignment_class"
        )

        assignment_subjects = request.form.getlist(
            "assignment_subject"
        )

        if not assignment_classes or not assignment_subjects:

            return render_template(
                "create_teacher.html",
                subjects=subjects,
                classes=CLASSES,
                error="At least one teaching assignment is required."
            )

        if len(assignment_classes) != len(assignment_subjects):

            return render_template(
                "create_teacher.html",
                subjects=subjects,
                classes=CLASSES,
                error="Invalid assignment data."
            )

        validated_assignments = []
        seen_assignments = set()

        for class_name, raw_subject_id in zip(
            assignment_classes,
            assignment_subjects
        ):

            if class_name not in CLASSES:
                continue

            try:
                subject_id = int(raw_subject_id)
            except (TypeError, ValueError):
                continue

            subject = db.session.get(
                Subject,
                subject_id
            )

            if not subject:
                continue

            key = (class_name, subject.id)

            if key in seen_assignments:
                continue

            seen_assignments.add(key)
            validated_assignments.append(
                (class_name, subject.id)
            )

        if not validated_assignments:

            return render_template(
                "create_teacher.html",
                subjects=subjects,
                classes=CLASSES,
                error="At least one valid teaching assignment is required."
            )

        teacher = User(
            name=name,
            username=username,
            password=generate_password_hash(password),
            role="teacher"
        )

        db.session.add(teacher)
        db.session.flush()

        for class_name, subject_id in validated_assignments:

            db.session.add(
                TeacherAssignment(
                    teacher_id=teacher.id,
                    subject_id=subject_id,
                    class_name=class_name
                )
            )

        db.session.commit()

        return redirect("/teachers")

    return render_template(
        "create_teacher.html",
        subjects=subjects,
        classes=CLASSES
    )


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


@app.route("/delete-teacher/<int:user_id>", methods=["POST"])
def delete_teacher(user_id):

    if session.get("role") != "admin":
        return "Unauthorized", 403

    teacher = User.query.filter_by(
        id=user_id,
        role="teacher"
    ).first()

    if teacher:

        db.session.delete(teacher)
        db.session.commit()

    return redirect("/teachers")


@app.route("/teacher/<int:user_id>")
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


@app.route("/add-score", methods=["GET", "POST"])
def add_score():

    if session.get("role") != "teacher":
        return "Unauthorized", 403

    teacher = User.query.filter_by(
        id=session.get("user_id"),
        role="teacher"
    ).first()

    if not teacher:
        return "Unauthorized", 403

    active_period = get_active_period()

    if not active_period:

        return (
            "No active academic period has been set. "
            "Ask the administrator to set one."
        )

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
            "assignment_id",
            ""
        )

        try:
            assignment_id = int(assignment_id)
        except (TypeError, ValueError):
            return "Invalid assignment", 400

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

        scores = {}

        for student in students:

            score = Score.query.filter_by(
                student_id=student.id,
                subject_id=assignment.subject_id,
                academic_period_id=active_period.id
            ).first()

            scores[student.id] = score

        return render_template(
            "enter_scores.html",
            students=students,
            subject=assignment.subject,
            assignment=assignment,
            active_period=active_period,
            scores=scores
        )

    return render_template(
        "add_score_select.html",
        assignments=assignments,
        active_period=active_period
    )


@app.route("/save-scores", methods=["POST"])
def save_scores():

    if session.get("role") != "teacher":
        return "Unauthorized", 403

    teacher = User.query.filter_by(
        id=session.get("user_id"),
        role="teacher"
    ).first()

    if not teacher:
        return "Unauthorized", 403

    active_period = get_active_period()

    if not active_period:

        return (
            "No active academic period has been set. "
            "Ask the administrator to set one."
        )

    assignment_id = request.form.get(
        "assignment_id",
        ""
    )

    try:
        assignment_id = int(assignment_id)
    except (TypeError, ValueError):
        return "Invalid assignment", 400

    assignment = TeacherAssignment.query.filter_by(
        id=assignment_id,
        teacher_id=teacher.id
    ).first()

    if not assignment:
        return "Unauthorized", 403

    student_ids = set()

    for key in request.form:

        if key.startswith("ca1_"):
            student_ids.add(key[4:])

    for student_id in student_ids:

        if not student_id.isdigit():
            continue

        student = Student.query.filter_by(
            id=int(student_id),
            class_name=assignment.class_name
        ).first()

        if not student:
            continue

        values = {}

        for field in SCORE_LIMITS:

            value = get_valid_score(
                request.form,
                field,
                student.id
            )

            if value is None:

                db.session.rollback()

                return (
                    f"Invalid {field.upper()} score "
                    f"for {student.name}. "
                    f"Allowed range: 0-{SCORE_LIMITS[field]}.",
                    400
                )

            values[field] = value

        existing = Score.query.filter_by(
            student_id=student.id,
            subject_id=assignment.subject_id,
            academic_period_id=active_period.id
        ).first()

        if existing:

            existing.ca1 = values["ca1"]
            existing.ca2 = values["ca2"]
            existing.ca3 = values["ca3"]
            existing.exam = values["exam"]

        else:

            db.session.add(
                Score(
                    student_id=student.id,
                    subject_id=assignment.subject_id,
                    academic_period_id=active_period.id,
                    ca1=values["ca1"],
                    ca2=values["ca2"],
                    ca3=values["ca3"],
                    exam=values["exam"]
                )
            )

    db.session.commit()

    return redirect("/add-score")


@app.route("/marks-sheet", methods=["GET", "POST"])
def marks_sheet():

    if session.get("role") not in ["admin", "teacher"]:
        return "Unauthorized", 403

    active_period = get_active_period()

    if not active_period:
        return (
            "No active academic period has been set. "
            "Ask the administrator to set one."
        )

    role = session.get("role")
    assignments_query = TeacherAssignment.query.join(
        Subject
    ).order_by(
        TeacherAssignment.class_name,
        Subject.name
    )

    if role == "teacher":
        assignments_query = assignments_query.filter_by(
            teacher_id=session.get("user_id")
        )

    assignments = assignments_query.all()

    assignment_id = request.values.get("assignment_id", "")
    assignment = None
    students = []
    scores = {}

    if assignment_id:
        try:
            assignment_id = int(assignment_id)
        except ValueError:
            assignment_id = None

    if assignment_id:
        assignment = db.session.get(
            TeacherAssignment,
            assignment_id
        )

        if not assignment:
            return "Assignment not found", 404

        if role == "teacher" and assignment.teacher_id != session.get("user_id"):
            return "Unauthorized", 403

        students = Student.query.filter_by(
            class_name=assignment.class_name
        ).order_by(
            Student.name
        ).all()

        score_list = Score.query.filter_by(
            subject_id=assignment.subject_id,
            academic_period_id=active_period.id
        ).join(
            Student
        ).filter(
            Student.class_name == assignment.class_name
        ).all()

        scores = {
            score.student_id: score
            for score in score_list
        }

    return render_template(
        "marks_sheet.html",
        assignments=assignments,
        assignment=assignment,
        students=students,
        scores=scores,
        active_period=active_period,
        calculate_total=calculate_total,
        calculate_grade=calculate_grade,
        calculate_remark=calculate_remark
    )


@app.route("/result-sheet", methods=["GET", "POST"])
def result_sheet():

    if session.get("role") not in [
        "admin",
        "teacher"
    ]:

        return "Unauthorized", 403

    active_period = get_active_period()

    if not active_period:
        return (
            "No active academic period has been set. "
            "Ask the administrator to set one."
        )

    role = session.get("role")

    students_query = Student.query.order_by(
        Student.class_name,
        Student.name
    )

    if role == "teacher":

        teacher = User.query.filter_by(
            id=session.get("user_id"),
            role="teacher"
        ).first()

        if not teacher:
            return "Unauthorized", 403

        assigned_classes = [
            assignment.class_name
            for assignment in TeacherAssignment.query.filter_by(
                teacher_id=teacher.id
            ).all()
        ]

        students_query = students_query.filter(
            Student.class_name.in_(assigned_classes)
        )

    available_students = students_query.all()

    student_id = request.values.get(
        "student_id",
        ""
    )

    selected_student_id = None

    if student_id:
        try:
            selected_student_id = int(student_id)
        except ValueError:
            selected_student_id = None

    student = None
    subjects = []
    scores = {}
    cumulative_results = {}
    class_averages = {}
    overall_total = 0
    overall_average = 0

    if selected_student_id:

        student = db.session.get(
            Student,
            selected_student_id
        )

        if not student:
            return "Student not found", 404

        if role == "teacher":

            allowed = TeacherAssignment.query.filter_by(
                teacher_id=session.get("user_id"),
                class_name=student.class_name
            ).first()

            if not allowed:
                return "Unauthorized", 403

        subjects = Subject.query.order_by(
            Subject.name
        ).all()

        score_list = Score.query.filter_by(
            student_id=student.id,
            academic_period_id=active_period.id
        ).all()

        scores = {
            score.subject_id: score
            for score in score_list
        }

        cumulative_results = {
            subject.id: calculate_cumulative(
                student.id,
                subject.id,
                active_period
            )
            for subject in subjects
        }

        class_students = Student.query.filter_by(
            class_name=student.class_name
        ).all()

        for subject in subjects:

            subject_scores = Score.query.filter_by(
                subject_id=subject.id,
                academic_period_id=active_period.id
            ).join(
                Student
            ).filter(
                Student.class_name == student.class_name
            ).all()

            totals = [
                calculate_total(score)
                for score in subject_scores
            ]

            class_averages[subject.id] = (
                sum(totals) / len(totals)
                if totals
                else 0
            )

        overall_total = sum(
            calculate_total(score)
            for score in scores.values()
        )

        subjects_with_scores = len(scores)

        overall_average = (
            overall_total / subjects_with_scores
            if subjects_with_scores
            else 0
        )

    return render_template(
        "result_sheet.html",
        available_students=available_students,
        selected_student_id=selected_student_id,
        student=student,
        subjects=subjects,
scores=scores,
        cumulative_results=cumulative_results,
        class_averages=class_averages,
        active_period=active_period,
        overall_total=overall_total,
        overall_average=overall_average,
        calculate_total=calculate_total,
        calculate_grade=calculate_grade,
        calculate_remark=calculate_remark
    )


@app.route("/academic-period", methods=["GET", "POST"])
def academic_period():

    if session.get("role") != "admin":
        return "Unauthorized", 403

    if request.method == "POST":

        academic_session = request.form.get(
            "academic_session",
            ""
        ).strip()

        term = request.form.get(
            "term",
            ""
        ).strip()

        valid_terms = {
            "First Term",
            "Second Term",
            "Third Term"
        }

        if not academic_session or term not in valid_terms:
            return "Invalid academic period", 400

        AcademicPeriod.query.update(
            {
                AcademicPeriod.is_active: False
            },
            synchronize_session=False
        )

        period = AcademicPeriod.query.filter_by(
            academic_session=academic_session,
            term=term
        ).first()

        if period:

            period.is_active = True

        else:

            period = AcademicPeriod(
                academic_session=academic_session,
                term=term,
                is_active=True
            )

            db.session.add(period)

        db.session.commit()

        return redirect("/academic-period")

    active_period = get_active_period()

    periods = AcademicPeriod.query.order_by(
        AcademicPeriod.id.desc()
    ).all()

    return render_template(
        "academic_period.html",
        active_period=active_period,
        periods=periods
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
