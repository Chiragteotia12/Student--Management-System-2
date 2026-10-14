"""Detailed analytics helpers for class dashboards and export workflows."""
from collections import Counter
from statistics import mean, pstdev
from typing import Iterable
from .academic_service import calculate_average, calculate_grade
from .config import PASS_MARK, SUBJECTS


def subject_summary(students: Iterable) -> dict:
    """Describe each subject with average, median-like middle, min/max, and pass rate."""
    records = list(students)
    summary = {}
    for subject in SUBJECTS:
        values = sorted(student.marks[subject] for student in records)
        if not values:
            summary[subject] = {"count": 0, "average": 0.0, "median": 0.0,
                                "minimum": 0, "maximum": 0, "pass_rate": 0.0}
            continue
        middle = len(values) // 2
        median_value = values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2
        summary[subject] = {
            "count": len(values),
            "average": round(mean(values), 2),
            "median": round(median_value, 2),
            "minimum": values[0],
            "maximum": values[-1],
            "pass_rate": round(sum(value >= PASS_MARK for value in values) * 100 / len(values), 2),
        }
    return summary


def score_bands(students: Iterable) -> dict:
    """Group student averages into readable score ranges."""
    bands = {"0–39": 0, "40–49": 0, "50–59": 0, "60–74": 0, "75–89": 0, "90–100": 0}
    for student in students:
        score = calculate_average(student.marks)
        if score < 40:
            key = "0–39"
        elif score < 50:
            key = "40–49"
        elif score < 60:
            key = "50–59"
        elif score < 75:
            key = "60–74"
        elif score < 90:
            key = "75–89"
        else:
            key = "90–100"
        bands[key] += 1
    return bands


def identify_at_risk(students: Iterable, average_threshold: float = 50.0) -> list[dict]:
    """Identify records needing support based on average or failed subjects."""
    results = []
    for student in students:
        average = calculate_average(student.marks)
        failed = [subject for subject, mark in student.marks.items() if mark < PASS_MARK]
        if average < average_threshold or failed:
            results.append({"roll_no": student.roll_no, "name": student.name,
                            "average": average, "failed_subjects": failed,
                            "reason": "Below average threshold" if average < average_threshold else "Failed subject(s)"})
    return sorted(results, key=lambda item: (item["average"], item["name"].casefold()))


def compare_courses(students: Iterable) -> dict:
    """Compare average marks and student counts for each course."""
    grouped = {}
    for student in students:
        grouped.setdefault(student.course, []).append(calculate_average(student.marks))
    return {course: {"student_count": len(scores), "average": round(mean(scores), 2),
                     "spread": round(pstdev(scores), 2) if len(scores) > 1 else 0.0,
                     "highest": max(scores), "lowest": min(scores)}
            for course, scores in sorted(grouped.items(), key=lambda item: item[0].casefold())}


def build_dashboard_payload(students: Iterable) -> dict:
    """Build one JSON-friendly object for future dashboard visualizations."""
    records = list(students)
    averages = [calculate_average(student.marks) for student in records]
    grade_counts = Counter(calculate_grade(score) for score in averages)
    subjects = subject_summary(records)
    best = max(subjects, key=lambda subject: subjects[subject]["average"]) if records else None
    weakest = min(subjects, key=lambda subject: subjects[subject]["average"]) if records else None
    return {
        "student_count": len(records),
        "average_score": round(mean(averages), 2) if averages else 0.0,
        "score_bands": score_bands(records),
        "grade_distribution": dict(grade_counts),
        "subject_summary": subjects,
        "best_subject": best,
        "subject_to_review": weakest,
        "at_risk_students": identify_at_risk(records),
        "course_comparison": compare_courses(records),
    }
