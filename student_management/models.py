"""Domain models used by the UI, services, and persistence layer."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from .config import SUBJECTS


@dataclass
class Student:
    """A student's profile and marks for the configured subjects."""
    roll_no: str
    name: str
    age: int
    course: str
    marks: Dict[str, int] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    student_id: Optional[int] = None

    def __post_init__(self) -> None:
        """Fill omitted subject marks and timestamps with safe defaults."""
        self.marks = {subject: int(self.marks.get(subject, 0)) for subject in SUBJECTS}
        now = datetime.now().isoformat(timespec="seconds")
        self.created_at = self.created_at or now
        self.updated_at = self.updated_at or now

    @property
    def average(self) -> float:
        """Return the arithmetic mean of all subject marks."""
        if not self.marks:
            return 0.0
        return round(sum(self.marks.values()) / len(self.marks), 2)

    @property
    def grade(self) -> str:
        """Return a grade derived from the average score."""
        from .academic_service import calculate_grade
        return calculate_grade(self.average)

    @property
    def passed(self) -> bool:
        """A student passes when every subject reaches the pass mark."""
        from .config import PASS_MARK
        return all(mark >= PASS_MARK for mark in self.marks.values())

    def to_dict(self) -> dict:
        """Convert the model into a serializable dictionary."""
        result = {
            "student_id": self.student_id,
            "roll_no": self.roll_no,
            "name": self.name,
            "age": self.age,
            "course": self.course,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "average": self.average,
            "grade": self.grade,
            "passed": self.passed,
        }
        result.update(self.marks)
        return result
