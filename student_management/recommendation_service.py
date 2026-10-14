"""Explainable study recommendations (rule-based, not trained machine learning)."""
from .config import PASS_MARK
from .academic_service import calculate_average, weak_subjects


def recommend_for_student(student) -> dict:
    """Create practical study actions from marks and identify their rationale."""
    average = calculate_average(student.marks)
    weak = weak_subjects(student.marks, threshold=65)
    failed = [subject for subject, mark in student.marks.items() if mark < PASS_MARK]
    strengths = [subject for subject, mark in student.marks.items() if mark >= 85]
    actions = []
    if failed:
        actions.append("Prioritize fundamentals and remedial practice in: " + ", ".join(failed) + ".")
    if weak:
        actions.append("Schedule three focused practice sessions this week for: " + ", ".join(weak) + ".")
    if strengths:
        actions.append("Maintain strong performance in: " + ", ".join(strengths) + ".")
    if average >= 85:
        actions.append("Try advanced problems and peer teaching to deepen understanding.")
    elif average >= 70:
        actions.append("Use timed practice tests and review every incorrect answer.")
    elif average >= 50:
        actions.append("Create a daily 30-minute revision plan and review concepts before solving questions.")
    else:
        actions.append("Meet a teacher or mentor and make a weekly recovery plan with small goals.")
    if not actions:
        actions.append("Continue a balanced revision schedule and check progress every week.")
    return {"average": average, "weak_subjects": weak, "strong_subjects": strengths,
            "failed_subjects": failed, "actions": actions,
            "explanation": "Suggestions are generated from the student's marks and configured thresholds."}


def class_recommendations(students) -> list[dict]:
    """Generate recommendations for each student, keeping identity visible."""
    result = []
    for student in students:
        recommendation = recommend_for_student(student)
        recommendation["roll_no"] = student.roll_no
        recommendation["name"] = student.name
        result.append(recommendation)
    return result
