"""Tests for grades, summaries, rankings, and aggregate statistics."""
import unittest
from student_management.academic_service import calculate_grade, calculate_average, weak_subjects, strongest_subjects, class_statistics, rank_students, improvement_delta
from student_management.config import SUBJECTS
from student_management.models import Student


def make_student(roll, name, marks):
    """Create a compact test fixture with all configured subjects."""
    return Student(roll, name, 20, "B.Tech CSE", {subject: marks for subject in SUBJECTS})


class GradeTests(unittest.TestCase):
    def test_grade_boundaries(self):
        self.assertEqual(calculate_grade(100), "A+")
        self.assertEqual(calculate_grade(90), "A+")
        self.assertEqual(calculate_grade(89.99), "A")
        self.assertEqual(calculate_grade(75), "A")
        self.assertEqual(calculate_grade(60), "B")
        self.assertEqual(calculate_grade(40), "C")
        self.assertEqual(calculate_grade(39.99), "Fail")

    def test_average_rounding(self):
        self.assertEqual(calculate_average({"a": 80, "b": 91, "c": 90}), 87.0)
        self.assertEqual(calculate_average({}), 0.0)

    def test_weak_subjects_are_sorted(self):
        marks = {"Python": 70, "DBMS": 30, "Networks": 55}
        self.assertEqual(weak_subjects(marks, 60), ["DBMS", "Networks"])

    def test_strongest_subject_ties(self):
        self.assertEqual(strongest_subjects({"Python": 90, "DBMS": 90, "Networks": 70}), ["Python", "DBMS"])

    def test_empty_class_statistics(self):
        stats = class_statistics([])
        self.assertEqual(stats["student_count"], 0)
        self.assertEqual(stats["class_average"], 0.0)
        self.assertEqual(set(stats["subject_averages"]), set(SUBJECTS))

    def test_class_statistics(self):
        students = [make_student("1", "Asha", 90), make_student("2", "Bala", 30)]
        stats = class_statistics(students)
        self.assertEqual(stats["student_count"], 2)
        self.assertEqual(stats["class_average"], 60.0)
        self.assertEqual(stats["pass_percentage"], 50.0)
        self.assertEqual(stats["grade_distribution"], {"A+": 1, "Fail": 1})

    def test_ranking_is_stable(self):
        students = [make_student("2", "Zed", 80), make_student("1", "Ava", 80), make_student("3", "Bee", 60)]
        self.assertEqual([s.name for s in rank_students(students)], ["Ava", "Zed", "Bee"])

    def test_improvement_delta(self):
        result = improvement_delta({"Python": 60, "DBMS": 80}, {"Python": 75, "DBMS": 70})
        self.assertEqual(result["deltas"], {"Python": 15, "DBMS": -10})
        self.assertEqual(result["improved"], ["Python"])
        self.assertEqual(result["declined"], ["DBMS"])


if __name__ == "__main__":
    unittest.main()
