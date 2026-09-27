import hashlib
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for

from extensions import db
from models.user import (
    Student,
    Subject,
    Score,
    AcademicPeriod,
    BehavioralRating,
    ResultToken,
)

public_bp = Blueprint("public", __name__)

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
    "Fluency",
]


def _active_period():
    return AcademicPeriod.query.filter_by(is_active=True).first()


def _total(score):
    if not score:
        return 0
    return (score.ca1 or 0) + (score.ca2 or 0) + (score.ca3 or 0) + (score.exam or 0)


def _grade(total, class_name):
    if class_name.startswith("SSS"):
        if total >= 75: return "A1"
        if total >= 70: return "B2"
        if total >= 65: return "B3"
        if total >= 60: return "C4"
        if total >= 55: return "C5"
        if total >= 50: return "C6"
        if total >= 45: return "D7"
        if total >= 40: return "E8"
        return "F9"
    if total >= 70: return "A"
    if total >= 60: return "B"
    if total >= 50: return "C"
    if total >= 40: return "D"
    return "E"


def _remark(total):
    if total >= 70: return "Excellent"
    if total >= 60: return "Very Good"
    if total >= 50: return "Good"
    if total >= 45: return "Fair"
    if total >= 40: return "Pass"
    return "Fail"


def _section(class_name):
    return (
        "JUNIOR SECONDARY SCHOOL"
        if class_name.startswith("JSS")
        else "SENIOR SECONDARY SCHOOL"
    )


def _period_score(student_id, subject_id, session_name, term):
    period = AcademicPeriod.query.filter_by(
        academic_session=session_name,
        term=term
    ).first()
    if not period:
        return None
    return Score.query.filter_by(
        student_id=student_id,
        subject_id=subject_id,
        academic_period_id=period.id
    ).first()


def _cumulative(student_id, subject_id, period):
    current = Score.query.filter_by(
        student_id=student_id,
        subject_id=subject_id,
        academic_period_id=period.id
    ).first()
    current_total = _total(current)

    if period.term == "First Term":
        return {"last_term_cumulative": None, "cumulative_average": current_total}

    first = _total(_period_score(
        student_id, subject_id, period.academic_session, "First Term"
    ))

    if period.term == "Second Term":
        return {
            "last_term_cumulative": first,
            "cumulative_average": (first + current_total) / 2,
        }

    second = _total(_period_score(
        student_id, subject_id, period.academic_session, "Second Term"
    ))
    second_cumulative = (first + second) / 2

    return {
        "last_term_cumulative": second_cumulative,
        "cumulative_average": (second_cumulative + current_total) / 2,
    }


def _comment(average):
    if average >= 70:
        return "Excellent performance. Keep up the outstanding work."
    if average >= 60:
        return "Very good performance. Continue working consistently."
    if average >= 50:
        return "Good performance. More consistent effort will bring further improvement."
    if average >= 40:
        return "A fair performance. Focused effort is needed for stronger results."
    return "More effort and regular study are needed to improve performance."


def build_result_context(student, active_period):
    score_list = Score.query.filter_by(
        student_id=student.id,
        academic_period_id=active_period.id
    ).all()

    scores = {score.subject_id: score for score in score_list}
    scored_subject_ids = set(scores)

    subjects = (
        Subject.query.filter(Subject.id.in_(scored_subject_ids))
        .order_by(Subject.name).all()
        if scored_subject_ids else []
    )

    cumulative_results = {
        subject.id: _cumulative(student.id, subject.id, active_period)
        for subject in subjects
    }

    class_averages = {}
    for subject in subjects:
        subject_scores = Score.query.filter_by(
            subject_id=subject.id,
            academic_period_id=active_period.id
        ).join(Student).filter(
            Student.class_name == student.class_name
        ).all()
        totals = [_total(score) for score in subject_scores]
        class_averages[subject.id] = sum(totals) / len(totals) if totals else 0

    overall_total = sum(_total(score) for score in scores.values())
    subject_count = len(scores)
    overall_average = overall_total / subject_count if subject_count else 0

    # Position is shown only for Third Term. Students are ranked by the
    # average of the subjects for which they have recorded scores.
    position = None
    total_students = 0
    if active_period.term == "Third Term" and subject_count:
        class_students = Student.query.filter_by(
            class_name=student.class_name
        ).all()
        averages = []
        for candidate in class_students:
            candidate_scores = Score.query.filter_by(
                student_id=candidate.id,
                academic_period_id=active_period.id
            ).all()
            if candidate_scores:
                candidate_average = (
                    sum(_total(s) for s in candidate_scores)
                    / len(candidate_scores)
                )
                averages.append((candidate.id, candidate_average))
        total_students = len(averages)
        position = 1 + sum(
            1 for candidate_id, average in averages
            if average > overall_average and candidate_id != student.id
        )

    behavior_rows = BehavioralRating.query.filter_by(
        student_id=student.id,
        academic_period_id=active_period.id
    ).all()
    behavior_ratings = {row.trait: row.rating for row in behavior_rows}

    return {
        "student": student,
        "subjects": subjects,
        "scores": scores,
        "cumulative_results": cumulative_results,
        "class_averages": class_averages,
        "active_period": active_period,
        "overall_total": overall_total,
        "overall_average": overall_average,
        "calculate_total": _total,
        "calculate_grade": _grade,
        "calculate_remark": _remark,
        "school_section": _section(student.class_name),
        "behavior_ratings": behavior_ratings,
        "behavior_traits": BEHAVIOR_TRAITS,
        "position": position,
        "total_students": total_students,
        "principal_comment": _comment(overall_average),
        "teacher_comment": _comment(overall_average),
        "counsellor_comment": (
            "Continue to develop good study habits, discipline and positive relationships."
        ),
    }


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@public_bp.route("/check-result", methods=["GET", "POST"])
def check_result():
    active_period = _active_period()
    error = None

    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        token = request.form.get("token", "").strip()

        if not student_id.isdigit() or not token:
            error = "Enter your Student ID and result token."
        elif not active_period:
            error = "Results are not currently available. Please contact the school."
        else:
            student = Student.query.filter_by(id=int(student_id)).first()
            token_record = ResultToken.query.filter_by(
                token_hash=_hash_token(token),
                student_id=int(student_id),
                academic_period_id=active_period.id,
                revoked=False,
            ).first()

            if not student or not token_record:
                error = "Invalid Student ID or result token."
            elif token_record.expires_at and token_record.expires_at < datetime.utcnow():
                error = "This result token has expired. Please request a new token."
            else:
                context = build_result_context(student, active_period)
                if not context["subjects"]:
                    error = "Your result has not been published yet. Please contact the school."
                else:
                    token_record.last_used_at = datetime.utcnow()
                    db.session.commit()
                    return render_template("public_result.html", **context)

    return render_template(
        "check_result.html",
        active_period=active_period,
        error=error,
    )


@public_bp.route("/admin/result-tokens", methods=["GET", "POST"])
def result_tokens():
    from flask import session

    if session.get("role") != "admin":
        return "Unauthorized", 403

    active_period = _active_period()
    students = Student.query.order_by(Student.class_name, Student.name).all()

    if not active_period:
        return render_template(
            "result_tokens.html",
            active_period=None,
            students=students,
            active_tokens=[],
            new_token=None,
            error="Set an active academic period before generating result tokens.",
        )

    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()

        if not student_id.isdigit():
            return render_template(
                "result_tokens.html",
                active_period=active_period,
                students=students,
                active_tokens=[],
                new_token=None,
                error="Invalid student.",
            )

        student = Student.query.filter_by(id=int(student_id)).first()
        if not student:
            return "Student not found", 404

        ResultToken.query.filter_by(
            student_id=student.id,
            academic_period_id=active_period.id,
            revoked=False,
        ).update({"revoked": True}, synchronize_session=False)

        raw_token = secrets.token_urlsafe(24)
        token = ResultToken(
            student_id=student.id,
            academic_period_id=active_period.id,
            token_hash=_hash_token(raw_token),
            token_prefix=raw_token[:10],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90),
        )
        db.session.add(token)
        db.session.commit()

        active_tokens = (
            ResultToken.query.filter_by(
                academic_period_id=active_period.id,
                revoked=False
            )
            .order_by(ResultToken.created_at.desc())
            .all()
        )

        return render_template(
            "result_tokens.html",
            active_period=active_period,
            students=students,
            active_tokens=active_tokens,
            new_token=raw_token,
            generated_for=student,
            error=None,
        )

    active_tokens = (
        ResultToken.query.filter_by(
            academic_period_id=active_period.id,
            revoked=False
        )
        .order_by(ResultToken.created_at.desc())
        .all()
    )

    return render_template(
        "result_tokens.html",
        active_period=active_period,
        students=students,
        active_tokens=active_tokens,
        new_token=None,
        error=None,
    )


@public_bp.route("/admin/result-tokens/revoke/<int:token_id>", methods=["POST"])
def revoke_result_token(token_id):
    from flask import session

    if session.get("role") != "admin":
        return "Unauthorized", 403

    token = db.session.get(ResultToken, token_id)
    if token:
        token.revoked = True
        db.session.commit()

    return redirect(url_for("public.result_tokens"))
