"""Tests for detailed class analytics and risk indicators."""
import unittest
from student_management.analytics_service import subject_summary, score_bands, identify_at_risk, compare_courses, build_dashboard_payload
from student_management.config import SUBJECTS
from student_management.models import Student


def student(roll, name, mark, course="B.Tech CSE"):
    """Create a complete student fixture with a uniform mark profile."""
    return Student(roll, name, 20, course, {subject: mark for subject in SUBJECTS})


class AnalyticsServiceTests(unittest.TestCase):
    def test_subject_summary_for_empty_class(self):
        summary = subject_summary([])
        self.assertEqual(summary[SUBJECTS[0]]["count"], 0)
        self.assertEqual(summary[SUBJECTS[0]]["pass_rate"], 0.0)

    def test_subject_summary_for_two_students(self):
        summary = subject_summary([student("CS01", "Ada", 30), student("CS02", "Grace", 90)])
        self.assertEqual(summary[SUBJECTS[0]]["average"], 60.0)
        self.assertEqual(summary[SUBJECTS[0]]["median"], 60.0)
        self.assertEqual(summary[SUBJECTS[0]]["minimum"], 30)
        self.assertEqual(summary[SUBJECTS[0]]["maximum"], 90)
        self.assertEqual(summary[SUBJECTS[0]]["pass_rate"], 50.0)

    def test_score_bands_cover_all_records(self):
        records = [student("CS01", "A", 30), student("CS02", "B", 45),
                   student("CS03", "C", 55), student("CS04", "D", 65),
                   student("CS05", "E", 80), student("CS06", "F", 95)]
        bands = score_bands(records)
        self.assertEqual(sum(bands.values()), len(records))
        self.assertEqual(bands["0–39"], 1)
        self.assertEqual(bands["90–100"], 1)

    def test_at_risk_identifies_failed_subjects(self):
        records = [student("CS01", "Ada", 30), student("CS02", "Grace", 85)]
        risk = identify_at_risk(records)
        self.assertEqual([item["roll_no"] for item in risk], ["CS01"])
        self.assertTrue(risk[0]["failed_subjects"])

    def test_course_comparison(self):
        records = [student("CS01", "Ada", 80, "CSE"), student("CS02", "Grace", 60, "CSE"),
                   student("CS03", "Lin", 90, "ECE")]
        comparison = compare_courses(records)
        self.assertEqual(comparison["CSE"]["student_count"], 2)
        self.assertEqual(comparison["CSE"]["average"], 70.0)
        self.assertEqual(comparison["ECE"]["highest"], 90.0)

    def test_dashboard_payload_has_consistent_counts(self):
        payload = build_dashboard_payload([student("CS01", "Ada", 85), student("CS02", "Grace", 95)])
        self.assertEqual(payload["student_count"], 2)
        self.assertEqual(payload["average_score"], 90.0)
        self.assertEqual(sum(payload["score_bands"].values()), 2)
        self.assertEqual(payload["best_subject"], SUBJECTS[0])

    def test_course_comparison_empty(self):
        self.assertEqual(compare_courses([]), {})


if __name__ == "__main__":
    unittest.main()
