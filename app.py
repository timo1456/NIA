from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import inspect, text

from extensions import db
from models.user import (
    User,
    Student,
    Subject,
    TeacherAssignment,
    Score,
    AcademicPeriod,
    BehavioralRating,
    ResultToken,
    ClassTeacherAssignment,
    ResultComment,
    SchoolSignature
)

import os


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "dev-only-secret-key-change-me"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
    "SESSION_COOKIE_SECURE",
    "0"
) == "1"


basedir = os.path.abspath(
    os.path.dirname(__file__)
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///"
    + os.path.join(basedir, "school.db")
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

SIGNATURE_FOLDER = os.path.join(
    basedir,
    "static",
    "uploads",
    "signatures"
)
os.makedirs(SIGNATURE_FOLDER, exist_ok=True)

db.init_app(app)

# Public landing page and student result access routes.
from public_routes import public_bp, build_result_context
app.register_blueprint(public_bp)


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

BEHAVIOR_TRAITS = [
    "Punctuality",
    "Attendance In Class",
    "Reliability",
    "Neatness",
    "Politeness",
    "Honesty",
    "Relationship with Staff",
    "Relationship with Students",
    "Self Control",
    "Spirit of Cooperation",
    "Sense of Responsibility",
    "Attentiveness",
    "Initiative",
    "Organisational Ability",
    "Perseverance",
    "Fluency"
]

REMOVED_BEHAVIOR_TRAITS = [
    "Games",
    "Sports",
    "Drawing and Painting",
    "Musical Skills",
    "Handing of Tools"
]


with app.app_context():

    db.create_all()

    # Add newly introduced AcademicPeriod columns to existing SQLite databases.
    inspector = inspect(db.engine)
    academic_period_columns = {
        column["name"]
        for column in inspector.get_columns("academic_period")
    }

    if "next_term_begins" not in academic_period_columns:
        db.session.execute(
            text(
                "ALTER TABLE academic_period "
                "ADD COLUMN next_term_begins DATE"
            )
        )
        db.session.commit()

    # Add the student date of birth column to existing SQLite databases.
    inspector = inspect(db.engine)
    student_columns = {
        column["name"]
        for column in inspector.get_columns("student")
    }

    if "date_of_birth" not in student_columns:
        db.session.execute(
            text(
                "ALTER TABLE student "
                "ADD COLUMN date_of_birth DATE"
            )
        )
        db.session.commit()

    # Add the user-entered Student ID to existing SQLite databases.
    inspector = inspect(db.engine)
    student_columns = {
        column["name"]
        for column in inspector.get_columns("student")
    }

    if "student_id" not in student_columns:
        db.session.execute(
            text(
                "ALTER TABLE student "
                "ADD COLUMN student_id VARCHAR(50)"
            )
        )
        db.session.execute(
            text(
                "UPDATE student "
                "SET student_id = CAST(id AS TEXT) "
                "WHERE student_id IS NULL OR student_id = ''"
            )
        )
        db.session.commit()

    # Add teacher portal/signature fields to existing databases.
    inspector = inspect(db.engine)
    user_columns = {
        column["name"]
        for column in inspector.get_columns("user")
    }

    if "portal_access" not in user_columns:
        db.session.execute(
            text(
                "ALTER TABLE user "
                "ADD COLUMN portal_access BOOLEAN NOT NULL DEFAULT 1"
            )
        )

    if "signature_filename" not in user_columns:
        db.session.execute(
            text(
                "ALTER TABLE user "
                "ADD COLUMN signature_filename VARCHAR(255)"
            )
        )

    db.session.commit()

    admin = User.query.filter_by(
        username="Admin"
    ).first()

    # Remove behavioral traits that are no longer part of the system.
    BehavioralRating.query.filter(
        BehavioralRating.trait.in_(REMOVED_BEHAVIOR_TRAITS)
    ).delete(synchronize_session=False)

    db.session.commit()

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


def calculate_grade(total, class_name=None):

    if class_name and class_name.startswith("SSS"):
        if total >= 75:
            return "A1"
        elif total >= 70:
            return "B2"
        elif total >= 65:
            return "B3"
        elif total >= 60:
            return "C4"
        elif total >= 55:
            return "C5"
        elif total >= 50:
            return "C6"
        elif total >= 45:
            return "D7"
        elif total >= 40:
            return "E8"
        return "F9"

    if total >= 70:
        return "A"
    elif total >= 60:
        return "B"
    elif total >= 50:
        return "C"
    elif total >= 40:
        return "D"

    return "E"


def get_school_section(class_name):
    if class_name and class_name.startswith("JSS"):
        return "JUNIOR SECONDARY SCHOOL"
    return "SENIOR SECONDARY SCHOOL"
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


def current_teacher():
    if session.get("role") != "teacher":
        return None
    return User.query.filter_by(
        id=session.get("user_id"),
        role="teacher"
    ).first()


@app.before_request
def enforce_teacher_portal_access():
    if session.get("role") != "teacher":
        return None

    teacher = current_teacher()

    if not teacher or not teacher.portal_access:
        session.clear()
        return redirect("/login?revoked=1")

    return None


def allowed_signature_file(filename):
    if not filename or "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in {
        "png", "jpg", "jpeg", "webp"
    }


def save_signature(upload, prefix):
    if not upload or not upload.filename:
        return None

    if not allowed_signature_file(upload.filename):
        return None

    extension = upload.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(
        f"{prefix}_{os.urandom(8).hex()}.{extension}"
    )
    upload.save(os.path.join(SIGNATURE_FOLDER, filename))
    return filename


def remove_signature_file(filename):
    if not filename:
        return
    path = os.path.join(SIGNATURE_FOLDER, filename)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


@app.route("/")
def home():
    return render_template("landing.html")


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

        if user and user.role == "teacher" and not user.portal_access:
            return render_template(
                "login.html",
                invalid="Your teacher portal access has been revoked. Contact the administrator."
            )

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

    return redirect("/check-result")


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

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        date_of_birth = request.form.get(
            "date_of_birth",
            ""
        ).strip()

        if not name:

            return render_template(
                "create_student.html",
                classes=CLASSES,
                gen_der=GENDER,
                error="Student name cannot be empty."
            )

        if not date_of_birth:
            return render_template(
                "create_student.html",
                classes=CLASSES,
                gen_der=GENDER,
                error="Date of birth is required."
            )

        from datetime import date
        try:
            date_of_birth = date.fromisoformat(date_of_birth)
        except ValueError:
            return render_template(
                "create_student.html",
                classes=CLASSES,
                gen_der=GENDER,
                error="Please enter a valid date of birth."
            )

        if not student_id:
            return render_template(
                "create_student.html",
                classes=CLASSES,
                gen_der=GENDER,
                error="Student ID cannot be empty."
            )

        if Student.query.filter_by(student_id=student_id).first():
            return render_template(
                "create_student.html",
                classes=CLASSES,
                gen_der=GENDER,
                error="That Student ID is already in use."
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
            student_id=student_id,
            name=name,
            class_name=class_name,
            gender=gender,
            date_of_birth=date_of_birth
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

        BehavioralRating.query.filter_by(
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


@app.route("/change-teacher-password/<int:user_id>", methods=["GET", "POST"])
def change_teacher_password(user_id):

    if session.get("role") != "admin":
        return "Unauthorized", 403

    teacher = User.query.filter_by(
        id=user_id,
        role="teacher"
    ).first()

    if not teacher:
        return "Teacher not found", 404

    if request.method == "POST":

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not new_password or not confirm_password:
            return render_template(
                "change_teacher_password.html",
                teacher=teacher,
                error="Both password fields are required."
            )

        if new_password != confirm_password:
            return render_template(
                "change_teacher_password.html",
                teacher=teacher,
                error="Passwords do not match."
            )

        if len(new_password) < 8:
            return render_template(
                "change_teacher_password.html",
                teacher=teacher,
                error="Password must be at least 8 characters long."
            )

        teacher.password = generate_password_hash(new_password)
        db.session.commit()

        return redirect(f"/teacher/{teacher.id}")

    return render_template(
        "change_teacher_password.html",
        teacher=teacher
    )


@app.route("/edit-teacher-assignments/<int:user_id>", methods=["GET", "POST"])
def edit_teacher_assignments(user_id):
    if session.get("role") != "admin":
        return "Unauthorized", 403

    teacher = User.query.filter_by(
        id=user_id,
        role="teacher"
    ).first_or_404()

    subjects = Subject.query.order_by(Subject.name).all()

    if request.method == "POST":
        classes = request.form.getlist("assignment_class")
        subject_ids = request.form.getlist("assignment_subject")

        if len(classes) != len(subject_ids):
            return render_template(
                "edit_teacher_assignments.html",
                teacher=teacher,
                subjects=subjects,
                classes=CLASSES,
                assignments=teacher.assignments,
                error="Invalid assignment data."
            )

        validated = []
        seen = set()

        for class_name, raw_subject_id in zip(classes, subject_ids):
            if class_name not in CLASSES:
                continue
            try:
                subject_id = int(raw_subject_id)
            except (TypeError, ValueError):
                continue

            subject = db.session.get(Subject, subject_id)
            if not subject:
                continue

            key = (class_name, subject.id)
            if key not in seen:
                seen.add(key)
                validated.append(key)

        TeacherAssignment.query.filter_by(
            teacher_id=teacher.id
        ).delete(synchronize_session=False)

        for class_name, subject_id in validated:
            db.session.add(
                TeacherAssignment(
                    teacher_id=teacher.id,
                    subject_id=subject_id,
                    class_name=class_name
                )
            )

        db.session.commit()
        return redirect(f"/teacher/{teacher.id}")

    assignments = TeacherAssignment.query.filter_by(
        teacher_id=teacher.id
    ).join(Subject).order_by(
        TeacherAssignment.class_name,
        Subject.name
    ).all()

    return render_template(
        "edit_teacher_assignments.html",
        teacher=teacher,
        subjects=subjects,
        classes=CLASSES,
        assignments=assignments
    )


@app.route("/toggle-teacher-access/<int:user_id>", methods=["POST"])
def toggle_teacher_access(user_id):
    if session.get("role") != "admin":
        return "Unauthorized", 403

    teacher = User.query.filter_by(
        id=user_id,
        role="teacher"
    ).first_or_404()

    teacher.portal_access = not teacher.portal_access
    db.session.commit()

    return redirect("/teachers")


@app.route("/class-teachers", methods=["GET", "POST"])
def class_teachers():
    if session.get("role") != "admin":
        return "Unauthorized", 403

    active_period = get_active_period()
    if not active_period:
        return "No active academic period has been set.", 400

    teachers_list = User.query.filter_by(
        role="teacher"
    ).order_by(User.name).all()

    if request.method == "POST":
        class_name = request.form.get("class_name", "").strip()
        teacher_id = request.form.get("teacher_id", "").strip()

        if class_name not in CLASSES or not teacher_id.isdigit():
            return "Invalid class teacher assignment.", 400

        teacher = User.query.filter_by(
            id=int(teacher_id),
            role="teacher"
        ).first()

        if not teacher:
            return "Teacher not found.", 404

        assignment = ClassTeacherAssignment.query.filter_by(
            class_name=class_name,
            academic_session=active_period.academic_session
        ).first()

        if assignment:
            assignment.teacher_id = teacher.id
        else:
            db.session.add(
                ClassTeacherAssignment(
                    teacher_id=teacher.id,
                    class_name=class_name,
                    academic_session=active_period.academic_session
                )
            )

        db.session.commit()
        return redirect("/class-teachers")

    assignments = ClassTeacherAssignment.query.filter_by(
        academic_session=active_period.academic_session
    ).join(User).order_by(
        ClassTeacherAssignment.class_name
    ).all()

    assigned_by_class = {
        assignment.class_name: assignment
        for assignment in assignments
    }

    return render_template(
        "class_teachers.html",
        active_period=active_period,
        classes=CLASSES,
        teachers=teachers_list,
        assignments=assigned_by_class
    )


@app.route("/remove-class-teacher/<int:assignment_id>", methods=["POST"])
def remove_class_teacher(assignment_id):
    if session.get("role") != "admin":
        return "Unauthorized", 403

    assignment = db.session.get(ClassTeacherAssignment, assignment_id)
    if assignment:
        db.session.delete(assignment)
        db.session.commit()

    return redirect("/class-teachers")


@app.route("/signatures", methods=["GET", "POST"])
def signatures():
    if session.get("role") != "admin":
        return "Unauthorized", 403

    roles = {
        "principal": "Principal",
        "guidance_counselor": "Guidance Counsellor"
    }

    if request.method == "POST":
        role = request.form.get("role", "").strip()

        if role not in roles:
            return "Invalid signature role.", 400

        upload = request.files.get("signature")
        if not upload or not upload.filename:
            return render_template(
                "signatures.html",
                roles=roles,
                signatures={
                    item.role: item
                    for item in SchoolSignature.query.all()
                },
                error="Please choose a signature image."
            )

        filename = save_signature(
            upload,
            role
        )

        if not filename:
            return render_template(
                "signatures.html",
                roles=roles,
                signatures={
                    item.role: item
                    for item in SchoolSignature.query.all()
                },
                error="Use a PNG, JPG, JPEG or WEBP image."
            )

        setting = SchoolSignature.query.filter_by(role=role).first()
        if not setting:
            setting = SchoolSignature(role=role)
            db.session.add(setting)

        remove_signature_file(setting.filename)
        setting.filename = filename
        db.session.commit()

        return redirect("/signatures")

    return render_template(
        "signatures.html",
        roles=roles,
        signatures={
            item.role: item
            for item in SchoolSignature.query.all()
        }
    )


@app.route("/class-teacher-comment", methods=["GET", "POST"])
def class_teacher_comment():
    if session.get("role") != "teacher":
        return "Unauthorized", 403

    teacher = current_teacher()
    active_period = get_active_period()

    if not teacher or not active_period:
        return "Unauthorized", 403

    class_assignments = ClassTeacherAssignment.query.filter_by(
        teacher_id=teacher.id,
        academic_session=active_period.academic_session
    ).all()

    assigned_classes = [item.class_name for item in class_assignments]
    selected_class = request.values.get("class_name", "").strip()
    selected_student_id = request.values.get("student_id", "").strip()

    if selected_class not in assigned_classes:
        selected_class = ""

    students = []
    student = None

    if selected_class:
        students = Student.query.filter_by(
            class_name=selected_class
        ).order_by(Student.name).all()

    if selected_student_id.isdigit():
        student = Student.query.filter_by(
            id=int(selected_student_id),
            class_name=selected_class
        ).first()

    comment = None
    if student:
        comment = ResultComment.query.filter_by(
            student_id=student.id,
            academic_period_id=active_period.id
        ).first()

    if request.method == "POST":
        if not student:
            return "Invalid student selection.", 400

        if selected_class not in assigned_classes:
            return "Unauthorized", 403

        if not comment:
            comment = ResultComment(
                student_id=student.id,
                academic_period_id=active_period.id,
                class_teacher_id=teacher.id
            )
            db.session.add(comment)

        comment.class_teacher_id = teacher.id
        comment.class_teacher_remark = request.form.get(
            "class_teacher_remark",
            ""
        ).strip()

        upload = request.files.get("signature")
        if upload and upload.filename:
            filename = save_signature(upload, f"teacher_{teacher.id}")
            if not filename:
                return "Use a PNG, JPG, JPEG or WEBP signature image.", 400

            remove_signature_file(teacher.signature_filename)
            teacher.signature_filename = filename

        db.session.commit()

        return redirect(
            f"/class-teacher-comment?class_name={selected_class}"
            f"&student_id={student.id}"
        )

    return render_template(
        "class_teacher_comment.html",
        active_period=active_period,
        classes=assigned_classes,
        students=students,
        selected_class=selected_class,
        student=student,
        comment=comment,
        teacher=teacher
    )


@app.route("/result-comments", methods=["GET", "POST"])
def result_comments():
    if session.get("role") != "admin":
        return "Unauthorized", 403

    active_period = get_active_period()
    if not active_period:
        return "No active academic period has been set.", 400

    selected_class = request.values.get("class_name", "").strip()
    selected_student_id = request.values.get("student_id", "").strip()

    if selected_class not in CLASSES:
        selected_class = ""

    students = []
    student = None
    comment = None

    if selected_class:
        students = Student.query.filter_by(
            class_name=selected_class
        ).order_by(Student.name).all()

    if selected_student_id.isdigit():
        student = Student.query.filter_by(
            id=int(selected_student_id),
            class_name=selected_class
        ).first()

    if student:
        comment = ResultComment.query.filter_by(
            student_id=student.id,
            academic_period_id=active_period.id
        ).first()

    if request.method == "POST":
        if not student:
            return "Invalid student selection.", 400

        if not comment:
            comment = ResultComment(
                student_id=student.id,
                academic_period_id=active_period.id
            )
            db.session.add(comment)

        comment.principal_remark = request.form.get(
            "principal_remark",
            ""
        ).strip()
        comment.counselor_remark = request.form.get(
            "counselor_remark",
            ""
        ).strip()

        db.session.commit()

        return redirect(
            f"/result-comments?class_name={selected_class}"
            f"&student_id={student.id}"
        )

    return render_template(
        "result_comments.html",
        active_period=active_period,
        classes=CLASSES,
        students=students,
        selected_class=selected_class,
        student=student,
        comment=comment
    )


@app.route("/broad-sheet", methods=["GET"])
def broad_sheet():
    if session.get("role") != "admin":
        return "Unauthorized", 403

    active_period = get_active_period()
    if not active_period:
        return "No active academic period has been set.", 400

    selected_class = request.args.get("class_name", "").strip()
    if selected_class not in CLASSES:
        selected_class = ""

    students = []
    subjects = []
    rows = []

    if selected_class:
        students = Student.query.filter_by(
            class_name=selected_class
        ).order_by(Student.name).all()

        subject_ids = {
            assignment.subject_id
            for assignment in TeacherAssignment.query.filter_by(
                class_name=selected_class
            ).all()
        }

        session_periods = AcademicPeriod.query.filter_by(
            academic_session=active_period.academic_session
        ).all()

        session_period_ids = [period.id for period in session_periods]

        if session_period_ids:
            subject_ids.update(
                score.subject_id
                for score in Score.query.join(Student).filter(
                    Student.class_name == selected_class,
                    Score.academic_period_id.in_(session_period_ids)
                ).all()
            )

        if subject_ids:
            subjects = Subject.query.filter(
                Subject.id.in_(subject_ids)
            ).order_by(Subject.name).all()

        for student in students:
            cumulative = {}

            for subject in subjects:
                result = calculate_cumulative(
                    student.id,
                    subject.id,
                    active_period
                )

                has_any_score = Score.query.filter(
                    Score.student_id == student.id,
                    Score.subject_id == subject.id,
                    Score.academic_period_id.in_(session_period_ids)
                ).first()

                cumulative[subject.id] = (
                    result["cumulative_average"]
                    if has_any_score
                    else None
                )

            rows.append({
                "student": student,
                "cumulative": cumulative
            })

    return render_template(
        "broad_sheet.html",
        active_period=active_period,
        classes=CLASSES,
        selected_class=selected_class,
        subjects=subjects,
        rows=rows
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


@app.route("/result-sheet", methods=["GET"])
def result_sheet():

    if session.get("role") not in ["admin", "teacher"]:
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

        subject_classes = {
            assignment.class_name
            for assignment in TeacherAssignment.query.filter_by(
                teacher_id=teacher.id
            ).all()
        }
        class_teacher_classes = {
            assignment.class_name
            for assignment in ClassTeacherAssignment.query.filter_by(
                teacher_id=teacher.id,
                academic_session=active_period.academic_session
            ).all()
        }
        assigned_classes = sorted(
            subject_classes | class_teacher_classes
        )

        if not assigned_classes:
            return render_template(
                "result_sheet.html",
                available_students=[],
                available_classes=[],
                selected_class="",
                active_period=active_period
            )

        students_query = students_query.filter(
            Student.class_name.in_(assigned_classes)
        )

    else:
        assigned_classes = CLASSES

    selected_class = request.args.get("class_name", "").strip()

    if selected_class not in assigned_classes:
        selected_class = ""

    available_students = []

    if selected_class:
        available_students = students_query.filter(
            Student.class_name == selected_class
        ).all()

    return render_template(
        "result_sheet.html",
        available_students=available_students,
        available_classes=assigned_classes,
        selected_class=selected_class,
        active_period=active_period
    )


@app.route("/behavior-rating", methods=["GET", "POST"])
def behavior_rating():
    if session.get("role") != "teacher":
        return "Unauthorized", 403

    teacher = current_teacher()
    active_period = get_active_period()

    if not teacher or not active_period:
        return "Unauthorized", 403

    class_assignments = ClassTeacherAssignment.query.filter_by(
        teacher_id=teacher.id,
        academic_session=active_period.academic_session
    ).all()

    assigned_classes = sorted({
        assignment.class_name
        for assignment in class_assignments
    })

    selected_class = request.values.get("class_name", "").strip()
    selected_student_id = request.values.get("student_id", "").strip()

    if selected_class not in assigned_classes:
        selected_class = ""

    students = []
    student = None
    ratings = {}

    if selected_class:
        students = Student.query.filter_by(
            class_name=selected_class
        ).order_by(Student.name).all()

    if selected_student_id.isdigit():
        student = Student.query.filter_by(
            id=int(selected_student_id),
            class_name=selected_class
        ).first()

    if student:
        existing_ratings = BehavioralRating.query.filter_by(
            student_id=student.id,
            academic_period_id=active_period.id
        ).all()

        ratings = {
            rating.trait: rating.rating
            for rating in existing_ratings
        }

    traits = BEHAVIOR_TRAITS

    if request.method == "POST":
        if not student or selected_class not in assigned_classes:
            return "Invalid student selection", 400

        for trait in traits:
            raw_rating = request.form.get(
                "rating_" + trait,
                ""
            ).strip()

            existing = BehavioralRating.query.filter_by(
                student_id=student.id,
                academic_period_id=active_period.id,
                trait=trait
            ).first()

            if raw_rating == "":
                if existing:
                    db.session.delete(existing)
                continue

            if raw_rating not in {"1", "2", "3", "4", "5"}:
                return f"Invalid rating for {trait}.", 400

            rating_value = int(raw_rating)

            if existing:
                existing.rating = rating_value
            else:
                db.session.add(
                    BehavioralRating(
                        student_id=student.id,
                        academic_period_id=active_period.id,
                        trait=trait,
                        rating=rating_value
                    )
                )

        db.session.commit()

        return redirect(
            f"/behavior-rating?class_name={selected_class}"
            f"&student_id={student.id}"
        )

    return render_template(
        "behavior_rating.html",
        active_period=active_period,
        classes=assigned_classes,
        students=students,
        selected_class=selected_class,
        selected_student_id=student.id if student else "",
        student=student,
        traits=traits,
        ratings=ratings
    )


@app.route("/result/<int:student_id>")
def result_display(student_id):

    if session.get("role") not in ["admin", "teacher"]:
        return "Unauthorized", 403

    active_period = get_active_period()

    if not active_period:
        return (
            "No active academic period has been set. "
            "Ask the administrator to set one."
        )

    student = db.session.get(Student, student_id)

    if not student:
        return "Student not found", 404

    if session.get("role") == "teacher":
        subject_access = TeacherAssignment.query.filter_by(
            teacher_id=session.get("user_id"),
            class_name=student.class_name
        ).first()

        class_teacher_access = ClassTeacherAssignment.query.filter_by(
            teacher_id=session.get("user_id"),
            class_name=student.class_name,
            academic_session=active_period.academic_session
        ).first()

        if not subject_access and not class_teacher_access:
            return "Unauthorized", 403

    return render_template(
        "result_display.html",
        **build_result_context(student, active_period)
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

        next_term_begins = request.form.get(
            "next_term_begins",
            ""
        ).strip()

        valid_terms = {
            "First Term",
            "Second Term",
            "Third Term"
        }

        if not academic_session or term not in valid_terms:
            return "Invalid academic period", 400

        if next_term_begins:
            from datetime import date
            try:
                next_term_begins = date.fromisoformat(
                    next_term_begins
                )
            except ValueError:
                return "Invalid next term begins date", 400
        else:
            next_term_begins = None

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
            period.next_term_begins = next_term_begins

        else:

            period = AcademicPeriod(
                academic_session=academic_session,
                term=term,
                is_active=True,
                next_term_begins=next_term_begins
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
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")