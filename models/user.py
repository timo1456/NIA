from extensions import db


# ======================
# USER
# ADMIN + TEACHER
# ======================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False
    )

    name = db.Column(
        db.String(100)
    )


# ======================
# STUDENT
# ======================
class Student(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    class_name = db.Column(
        db.String(50),
        nullable=False
    )

    gender = db.Column(
            db.String(20),
            nullable=False
        )
    


# ======================
# SUBJECT
# ======================
class Subject(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )


# ======================
# TEACHER ASSIGNMENT
# ======================
class TeacherAssignment(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False
    )

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subject.id", ondelete="CASCADE"),
        nullable=False
    )

    class_name = db.Column(
        db.String(50),
        nullable=False
    )

    teacher = db.relationship(
        "User",
        backref=db.backref(
            "assignments",
            cascade="all, delete-orphan"
        )
    )

    subject = db.relationship(
        "Subject",
        backref=db.backref(
            "assignments",
            cascade="all, delete-orphan"
        )
    )


# ======================
# SCORES
# ======================
class Score(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "student.id",
            ondelete="CASCADE"
        )
    )

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "subject.id",
            ondelete="SET NULL"
        )
    )

    ca1 = db.Column(
        db.Integer,
        default=0
    )

    ca2 = db.Column(
        db.Integer,
        default=0
    )

    ca3 = db.Column(
        db.Integer,
        default=0
    )

    exam = db.Column(
        db.Integer,
        default=0
    )

    total = db.Column(
        db.Integer,
        default=0
    )

    student = db.relationship(
        "Student",
        backref=db.backref(
            "scores",
            cascade="all, delete-orphan"
        )
    )

    subject = db.relationship(
        "Subject"
    )