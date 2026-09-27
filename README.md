# New Innovation Academy (NIA)

NIA is a Flask-based school academic result management system for New Innovation Academy.

## Core capabilities

- Admin management of students, teachers, subjects and academic periods.
- Teacher-specific subject/class assignments.
- CA1, CA2, CA3 and examination score entry.
- Automatic totals, grades, remarks and cumulative calculations.
- Behavioural/observable-trait ratings.
- Fixed A4 terminal result sheets for printing.
- Secure student result access using a unique Student ID plus an admin-generated token.
- Token revocation and automatic 90-day token expiry.
- School landing page and staff portal.
- Wine, yellow and white visual design system.

## Student result access

Students do not need a staff account.

1. The administrator sets the active academic session and term.
2. The administrator generates a result token for the student.
3. The student receives their Student ID and token.
4. The student opens the public result portal.
5. The student enters both credentials to view the active term result.

Tokens are generated using cryptographically secure random values and only a SHA-256 hash is stored in the database.

## Local setup

Create a virtual environment, install dependencies and set a production SECRET_KEY.

```bash
pip install -r requirements.txt
python app.py
```

For production, set:

- SECRET_KEY
- SESSION_COOKIE_SECURE=1
- FLASK_DEBUG=0

SQLite is used by the current project. For a larger production deployment, move the database to a managed relational database and configure the SQLAlchemy URI through an environment variable.

## Important routes

- / — school landing page
- /check-result — public student result portal
- /login — staff login
- /dashboard — role-based staff dashboard
- /admin/result-tokens — admin result-token management
- /result-sheet — staff result selection
- /result/<student_id> — staff terminal result

## Default administrator

The application creates the initial administrator when no user named Admin exists.

Change the default password immediately in any real deployment.
