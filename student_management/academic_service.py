"""Academic calculations and class-level statistics."""
from collections import Counter
from statistics import mean, median
from typing import Iterable, Mapping
from .config import GRADE_THRESHOLDS, PASS_MARK, SUBJECTS


def calculate_grade(average: float) -> str:
    """Map an average mark to the configured letter grade."""
    for threshold, grade in GRADE_THRESHOLDS:
        if average >= threshold:
            return grade
    return "Fail"


def calculate_average(marks: Mapping[str, int]) -> float:
    """Calculate the mean of a non-empty marks mapping."""
    return round(mean(marks.values()), 2) if marks else 0.0


def weak_subjects(marks: Mapping[str, int], threshold: int = 60) -> list[str]:
    """Return every subject below a threshold, ordered by mark ascending."""
    return [name for name, score in sorted(marks.items(), key=lambda pair: pair[1]) if score < threshold]


def strongest_subjects(marks: Mapping[str, int]) -> list[str]:
    """Return all subjects tied for the highest score."""
    if not marks:
        return []
    top = max(marks.values())
    return [subject for subject, score in marks.items() if score == top]


def student_summary(student) -> dict:
    """Summarize one student with performance and pass information."""
    marks = student.marks
    average = calculate_average(marks)
    return {
        "roll_no": student.roll_no,
        "name": student.name,
        "average": average,
        "grade": calculate_grade(average),
        "weak_subjects": weak_subjects(marks),
        "strongest_subjects": strongest_subjects(marks),
        "failed_subjects": [subject for subject, mark in marks.items() if mark < PASS_MARK],
        "passed": all(mark >= PASS_MARK for mark in marks.values()),
    }


def class_statistics(students: Iterable) -> dict:
    """Calculate useful class-wide statistics without mutating student data."""
    records = list(students)
    if not records:
        return {
            "student_count": 0, "class_average": 0.0, "median_average": 0.0,
            "highest_average": 0.0, "lowest_average": 0.0, "pass_percentage": 0.0,
            "grade_distribution": {}, "subject_averages": {subject: 0.0 for subject in SUBJECTS},
        }
    averages = [calculate_average(student.marks) for student in records]
    distribution = Counter(calculate_grade(value) for value in averages)
    passed = sum(all(mark >= PASS_MARK for mark in student.marks.values()) for student in records)
    subject_averages = {
        subject: round(mean(student.marks[subject] for student in records), 2)
        for subject in SUBJECTS
    }
    return {
        "student_count": len(records),
        "class_average": round(mean(averages), 2),
        "median_average": round(median(averages), 2),
        "highest_average": max(averages),
        "lowest_average": min(averages),
        "pass_percentage": round(passed * 100 / len(records), 2),
        "grade_distribution": dict(distribution),
        "subject_averages": subject_averages,
    }


def rank_students(students: Iterable) -> list:
    """Return students sorted by average descending, then name."""
    return sorted(students, key=lambda item: (-calculate_average(item.marks), item.name.casefold()))


def improvement_delta(previous_marks: Mapping[str, int], current_marks: Mapping[str, int]) -> dict:
    """Compare marks for common subjects and report each delta."""
    subjects = set(previous_marks) & set(current_marks)
    deltas = {subject: current_marks[subject] - previous_marks[subject] for subject in subjects}
    return {"deltas": deltas, "improved": [s for s, d in deltas.items() if d > 0],
            "declined": [s for s, d in deltas.items() if d < 0],
            "unchanged": [s for s, d in deltas.items() if d == 0]}
