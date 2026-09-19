from extensions import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100))


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(20), nullable=False)


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class TeacherAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

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

    class_name = db.Column(db.String(50), nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            "teacher_id",
            "subject_id",
            "class_name",
            name="uq_teacher_subject_class"
        ),
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


class AcademicPeriod(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    academic_session = db.Column(
        db.String(20),
        nullable=False
    )

    term = db.Column(
        db.String(20),
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    next_term_begins = db.Column(
        db.Date,
        nullable=True
    )

    __table_args__ = (
        db.UniqueConstraint(
            "academic_session",
            "term",
            name="uq_academic_session_term"
        ),
    )


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.id", ondelete="CASCADE"),
        nullable=False
    )

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subject.id", ondelete="CASCADE"),
        nullable=False
    )

    academic_period_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_period.id", ondelete="CASCADE"),
        nullable=False
    )

    ca1 = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    ca2 = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    ca3 = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    exam = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "subject_id",
            "academic_period_id",
            name="uq_student_subject_period"
        ),
    )

    student = db.relationship(
        "Student",
        backref=db.backref(
            "scores",
            cascade="all, delete-orphan"
        )
    )

    subject = db.relationship("Subject")
    academic_period = db.relationship("AcademicPeriod")



class BehavioralRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.id", ondelete="CASCADE"),
        nullable=False
    )

    academic_period_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_period.id", ondelete="CASCADE"),
        nullable=False
    )

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False
    )

    trait = db.Column(
        db.String(100),
        nullable=False
    )

    rating = db.Column(
        db.Integer,
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "academic_period_id",
            "trait",
            name="uq_behavioral_rating"
        ),
    )

    student = db.relationship("Student")
    academic_period = db.relationship("AcademicPeriod")
    teacher = db.relationship("User")
