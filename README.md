# AI Powered Student Management System

A Python desktop application for managing student profiles and academic marks. Version 2 adds SQLite persistence, validated CRUD workflows, password hashing, search, CSV import/export, backups, class statistics, student recommendations, and HTML/CSV reports.

> **About the “AI” label:** the included academic recommendation engine is an explainable rule-based system. It is not a trained machine-learning model or a generative AI service.

## Features

- Tkinter desktop UI with light/dark themes.
- SQLite persistence; student records survive application restarts.
- Add, update, search, and delete student records.
- Unique roll numbers and validation for names, ages, courses, and marks.
- Subject-wise marks, average, grade, pass/review status, and recommendations.
- Class average, median, high/low averages, pass percentage, grade distribution, and subject averages.
- CSV import/export with row-level error reporting and duplicate handling.
- HTML individual student report and CSV class report.
- SQLite backup and restore helpers.
- Salted PBKDF2 password hashes and password-change UI.
- Application log and automated tests.

## Requirements

- Python 3.10 or newer recommended.
- Tkinter (usually included with standard Python installers).
- No third-party runtime dependencies.

## Run

1. Extract the ZIP.
2. Open a terminal in the extracted `student_management_upgraded` folder.
3. Run:

   ```bash
   python main.py
   ```

4. On first launch, sign in with `admin` / `admin1234`.
5. Change the initial password before using real or sensitive records. The database and logs are created locally in `data/` and `logs/`.

If Tkinter is missing on Linux, install your distribution's `python3-tk` package.

## Run tests

From the project root:

```bash
python -m unittest discover -s tests -v
```

The test suite uses temporary databases and does not touch your real application database.

## Project structure

```text
main.py
student_management/
  app.py                 # startup and dependency wiring
  config.py              # configuration and paths
  models.py              # Student model
  validators.py          # input validation
  database.py            # SQLite repository, authentication storage, CSV, backups
  academic_service.py    # grades and class statistics
  analytics_service.py   # detailed subject, course, and at-risk analytics
  maintenance_service.py # database health, CSV preflight, backup retention
  recommendation_service.py
  report_service.py      # HTML student reports and CSV class reports
  auth.py                # password hashing and username validation
  logger.py
  utils.py
  ui/
    dashboard.py
    login_window.py
    theme.py
tests/
  test_academic_service.py
  test_database.py
  test_validators.py
```

## GitHub setup

If this project should replace the code in your existing repository, first make a local backup of the current repository. Then copy the contents of this folder into your cloned repository, review the diff, run the tests, and commit the changes.

```bash
git status
git add .
git commit -m "Upgrade student management system with SQLite and analytics"
git push origin main
```

Do not add database files, credentials, personal student data, or logs to Git. The `.gitignore` excludes common runtime artifacts.

## Data and security notes

- The initial admin password is for local setup only; change it before sharing the app.
- This is a local desktop app, not a hardened multi-user web service.
- Do not store real student data in a public repository.
- Backups contain the database and should be kept private.
- Rule-based recommendations are advisory; teachers should make final academic decisions.

## Detailed analytics module

`student_management/analytics_service.py` also exposes reusable functions for subject summaries, score bands, at-risk students, course comparisons, and a JSON-friendly dashboard payload. The UI uses the core class statistics in the current release; these additional helpers are covered by unit tests and can be used to add charts in a future iteration.
