"""SQLite persistence and repository operations."""
import csv
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional
from .config import BACKUP_DIR, DATABASE_PATH, SUBJECTS, ensure_directories
from .models import Student
from .auth import hash_password, verify_password, validate_username
from .logger import get_logger

LOGGER = get_logger(__name__)


class StudentRepository:
    """Own all database reads/writes and keep SQL out of the UI layer."""
    def __init__(self, database_path: Path | str = DATABASE_PATH):
        ensure_directories()
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self):
        """Yield a connection with foreign keys enabled and safe transaction handling."""
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create tables and add newly introduced columns where possible."""
        subject_columns = ",\n".join(f'"{subject}" INTEGER NOT NULL DEFAULT 0 CHECK("{subject}" BETWEEN 0 AND 100)' for subject in SUBJECTS)
        with self.connection() as conn:
            conn.execute(f"""CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT NOT NULL UNIQUE COLLATE NOCASE,
                name TEXT NOT NULL,
                age INTEGER NOT NULL CHECK(age BETWEEN 10 AND 100),
                course TEXT NOT NULL,
                {subject_columns},
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                created_at TEXT NOT NULL
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_students_name ON students(name COLLATE NOCASE)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_students_course ON students(course COLLATE NOCASE)")

    @staticmethod
    def _student_from_row(row: sqlite3.Row) -> Student:
        """Convert a database row into a domain model."""
        return Student(
            student_id=row["id"], roll_no=row["roll_no"], name=row["name"],
            age=row["age"], course=row["course"],
            marks={subject: row[subject] for subject in SUBJECTS},
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    def add_student(self, student: Student) -> Student:
        """Insert a student and return it with the assigned database ID."""
        now = datetime.now().isoformat(timespec="seconds")
        columns = ["roll_no", "name", "age", "course", *SUBJECTS, "created_at", "updated_at"]
        values = [student.roll_no, student.name, student.age, student.course,
                  *[student.marks[subject] for subject in SUBJECTS], now, now]
        placeholders = ", ".join("?" for _ in columns)
        quoted_columns = ", ".join(f'"{column}"' for column in columns)
        try:
            with self.connection() as conn:
                cursor = conn.execute(f"INSERT INTO students ({quoted_columns}) VALUES ({placeholders})", values)
                student.student_id = cursor.lastrowid
                student.created_at = now
                student.updated_at = now
        except sqlite3.IntegrityError as exc:
            LOGGER.info("Student insert rejected: %s", exc)
            if "roll_no" in str(exc).lower():
                raise ValueError(f"Roll number '{student.roll_no}' already exists.") from exc
            raise ValueError(f"Could not add student: {exc}") from exc
        LOGGER.info("Added student roll=%s", student.roll_no)
        return student

    def update_student(self, student: Student) -> Student:
        """Update a student's profile and marks by roll number."""
        now = datetime.now().isoformat(timespec="seconds")
        assignments = ["name = ?", "age = ?", "course = ?"]
        values = [student.name, student.age, student.course]
        for subject in SUBJECTS:
            assignments.append(f'"{subject}" = ?')
            values.append(student.marks[subject])
        assignments.append("updated_at = ?")
        values.extend([now, student.roll_no])
        try:
            with self.connection() as conn:
                cursor = conn.execute(f"UPDATE students SET {', '.join(assignments)} WHERE roll_no = ?", values)
                if cursor.rowcount == 0:
                    raise ValueError(f"Student '{student.roll_no}' was not found.")
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Could not update student: {exc}") from exc
        student.updated_at = now
        LOGGER.info("Updated student roll=%s", student.roll_no)
        return student

    def delete_student(self, roll_no: str) -> bool:
        """Delete a student by roll number; return whether a row was deleted."""
        with self.connection() as conn:
            cursor = conn.execute("DELETE FROM students WHERE roll_no = ?", (roll_no,))
        if cursor.rowcount:
            LOGGER.info("Deleted student roll=%s", roll_no)
        return bool(cursor.rowcount)

    def clear_students(self) -> int:
        """Delete all student rows and return the number removed."""
        with self.connection() as conn:
            cursor = conn.execute("DELETE FROM students")
        LOGGER.warning("Cleared %s student records", cursor.rowcount)
        return cursor.rowcount

    def get_student(self, roll_no: str) -> Optional[Student]:
        """Retrieve one student by roll number."""
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM students WHERE roll_no = ?", (roll_no,)).fetchone()
        return self._student_from_row(row) if row else None

    def list_students(self, search: str = "", course: str = "") -> list[Student]:
        """List students sorted numerically where possible, then alphabetically."""
        conditions, parameters = [], []
        if search.strip():
            token = f"%{search.strip()}%"
            conditions.append("(roll_no LIKE ? OR name LIKE ? OR course LIKE ?)")
            parameters.extend([token, token, token])
        if course.strip() and course != "All courses":
            conditions.append("course = ?")
            parameters.append(course)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT * FROM students{where} ORDER BY name COLLATE NOCASE, roll_no COLLATE NOCASE"
        with self.connection() as conn:
            rows = conn.execute(query, parameters).fetchall()
        return [self._student_from_row(row) for row in rows]

    def count_students(self) -> int:
        """Return total number of stored student records."""
        with self.connection() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM students").fetchone()[0])

    def courses(self) -> list[str]:
        """Return distinct courses for filters."""
        with self.connection() as conn:
            rows = conn.execute("SELECT DISTINCT course FROM students ORDER BY course COLLATE NOCASE").fetchall()
        return [row[0] for row in rows]

    def create_user(self, username: str, password: str, role: str = "admin") -> None:
        """Create a local account with a salted password hash."""
        username = validate_username(username)
        salt, digest = hash_password(password)
        with self.connection() as conn:
            conn.execute("INSERT INTO users(username, salt, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                         (username, salt, digest, role, datetime.now().isoformat(timespec="seconds")))
        LOGGER.info("Created user username=%s role=%s", username, role)

    def ensure_default_user(self, username: str, password: str) -> None:
        """Create the initial local admin only when no accounts exist."""
        with self.connection() as conn:
            exists = conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
        if not exists:
            self.create_user(username, password)
            LOGGER.warning("Initial default administrator created; change its password for shared use")

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Return user metadata on success; return None on invalid credentials."""
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
        if row and verify_password(password, row["salt"], row["password_hash"]):
            return {"id": row["id"], "username": row["username"], "role": row["role"]}
        LOGGER.info("Rejected login attempt username=%s", username.strip())
        return None

    def change_password(self, username: str, old_password: str, new_password: str) -> None:
        """Change an account password after verifying the current password."""
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
            if not row or not verify_password(old_password, row["salt"], row["password_hash"]):
                raise ValueError("Current password is incorrect.")
            salt, digest = hash_password(new_password)
            conn.execute("UPDATE users SET salt = ?, password_hash = ? WHERE id = ?", (salt, digest, row["id"]))
        LOGGER.info("Password changed for username=%s", username.strip())

    def export_csv(self, destination: Path | str, students: Optional[Iterable[Student]] = None) -> int:
        """Export student profiles and marks to UTF-8 CSV."""
        records = list(students if students is not None else self.list_students())
        columns = ["roll_no", "name", "age", "course", *SUBJECTS, "average", "grade", "created_at", "updated_at"]
        with open(destination, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for student in records:
                row = {"roll_no": student.roll_no, "name": student.name, "age": student.age,
                       "course": student.course, **student.marks, "average": student.average,
                       "grade": student.grade, "created_at": student.created_at, "updated_at": student.updated_at}
                writer.writerow(row)
        LOGGER.info("Exported %s student rows to %s", len(records), destination)
        return len(records)

    def import_csv(self, source: Path | str, replace_existing: bool = False) -> dict:
        """Import CSV rows; report successes and row-level failures."""
        from .validators import validate_student_fields
        imported, skipped, errors = 0, 0, []
        with open(source, "r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            required = {"roll_no", "name", "age", "course", *SUBJECTS}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise ValueError("CSV headers must include roll_no, name, age, course, and every subject name.")
            for line_number, row in enumerate(reader, start=2):
                try:
                    student = validate_student_fields(row["roll_no"], row["name"], row["age"], row["course"],
                                                       {subject: row[subject] for subject in SUBJECTS})
                    existing = self.get_student(student.roll_no)
                    if existing:
                        if replace_existing:
                            self.update_student(student)
                            imported += 1
                        else:
                            skipped += 1
                    else:
                        self.add_student(student)
                        imported += 1
                except Exception as exc:
                    errors.append(f"Line {line_number}: {exc}")
        LOGGER.info("CSV import completed imported=%s skipped=%s errors=%s", imported, skipped, len(errors))
        return {"imported": imported, "skipped": skipped, "errors": errors}

    def backup(self, destination: Optional[Path | str] = None) -> Path:
        """Create a consistent SQLite backup using SQLite's backup API."""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        target = Path(destination) if destination else BACKUP_DIR / f"students-{datetime.now():%Y%m%d-%H%M%S}.db"
        target.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as source, sqlite3.connect(target) as backup:
            source.backup(backup)
        LOGGER.info("Database backup created at %s", target)
        return target

    def restore_backup(self, source_path: Path | str) -> None:
        """Restore from a backup after verifying it can be opened as SQLite."""
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        with sqlite3.connect(source_path) as source:
            result = source.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise ValueError("The selected backup failed the SQLite integrity check.")
        shutil.copy2(source_path, self.database_path)
        self.initialize()
        LOGGER.warning("Database restored from %s", source_path)
