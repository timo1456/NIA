from extensions import db

# ======================
# USER (ADMIN + TEACHER)
# ======================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    role = db.Column(db.String(20), nullable=False)  # admin / teacher

    name = db.Column(db.String(100))
    allowed_subjects = db.Column(db.String(300))  # "Math,English
    allowed_class = db.Column(db.String(100))
# ======================
# STUDENT
# ======================
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)


# ======================
# SCORES
# ======================
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(db.Integer, db.ForeignKey("student.id"))
    subject = db.Column(db.String(100))

    ca1 = db.Column(db.Integer, default=0)
    ca2 = db.Column(db.Integer, default=0)
    exam = db.Column(db.Integer, default=0)