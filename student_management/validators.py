"""Input validation helpers with actionable error messages."""
import re
from typing import Dict
from .config import MAX_AGE, MAX_MARK, MIN_AGE, SUBJECTS
from .models import Student

ROLL_PATTERN = re.compile(r"^[A-Za-z0-9_-]{2,30}$")
NAME_PATTERN = re.compile(r"^[\w][\w .'-]{1,79}$", re.UNICODE)
COURSE_PATTERN = re.compile(r"^[\w][\w .&()/-]{1,79}$", re.UNICODE)


class ValidationError(ValueError):
    """Raised when a profile or mark is invalid."""


def validate_roll_no(value: str) -> str:
    """Validate and normalize a roll number."""
    value = value.strip()
    if not ROLL_PATTERN.fullmatch(value):
        raise ValidationError("Roll number must be 2–30 letters, numbers, '_' or '-'.")
    return value


def validate_name(value: str) -> str:
    """Validate a person's display name."""
    value = " ".join(value.strip().split())
    if not NAME_PATTERN.fullmatch(value):
        raise ValidationError("Enter a name between 2 and 80 characters.")
    if not any(character.isalpha() for character in value):
        raise ValidationError("Name must contain at least one letter.")
    return value


def validate_age(value) -> int:
    """Parse and validate an age."""
    try:
        age = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValidationError("Age must be a whole number.") from exc
    if not MIN_AGE <= age <= MAX_AGE:
        raise ValidationError(f"Age must be between {MIN_AGE} and {MAX_AGE}.")
    return age


def validate_course(value: str) -> str:
    """Validate a course/programme name."""
    value = " ".join(value.strip().split())
    if not COURSE_PATTERN.fullmatch(value):
        raise ValidationError("Enter a course name between 2 and 80 characters.")
    return value


def validate_mark(value, subject: str = "Mark") -> int:
    """Parse a mark and enforce the inclusive 0–100 range."""
    try:
        mark = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{subject}: enter a whole number from 0 to 100.") from exc
    if not 0 <= mark <= MAX_MARK:
        raise ValidationError(f"{subject}: mark must be between 0 and {MAX_MARK}.")
    return mark


def validate_marks(raw_marks: Dict[str, object]) -> Dict[str, int]:
    """Validate all configured subjects and return normalized integer marks."""
    missing = [subject for subject in SUBJECTS if subject not in raw_marks]
    if missing:
        raise ValidationError("Missing marks for: " + ", ".join(missing))
    return {subject: validate_mark(raw_marks[subject], subject) for subject in SUBJECTS}


def validate_student_fields(roll_no, name, age, course, marks) -> Student:
    """Build a Student only after every input has passed validation."""
    return Student(
        roll_no=validate_roll_no(roll_no),
        name=validate_name(name),
        age=validate_age(age),
        course=validate_course(course),
        marks=validate_marks(marks),
    )
