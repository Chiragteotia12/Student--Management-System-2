"""Tests for student input validation."""
import unittest
from student_management.validators import validate_roll_no, validate_name, validate_age, validate_course, validate_mark, validate_marks, validate_student_fields, ValidationError
from student_management.config import SUBJECTS


class ValidatorTests(unittest.TestCase):
    def test_roll_number_trimming(self):
        self.assertEqual(validate_roll_no("  CS_001  "), "CS_001")

    def test_roll_number_rejects_spaces(self):
        with self.assertRaises(ValidationError):
            validate_roll_no("CS 001")

    def test_name_normalization(self):
        self.assertEqual(validate_name("  Ada   Lovelace "), "Ada Lovelace")

    def test_name_rejects_single_character(self):
        with self.assertRaises(ValidationError):
            validate_name("A")

    def test_age_range(self):
        self.assertEqual(validate_age("20"), 20)
        for value in ("9", "101", "twenty"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_age(value)

    def test_course_accepts_symbols(self):
        self.assertEqual(validate_course("B.Tech CSE"), "B.Tech CSE")

    def test_mark_boundaries(self):
        self.assertEqual(validate_mark("0"), 0)
        self.assertEqual(validate_mark("100"), 100)
        for value in ("-1", "101", "ten"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_mark(value)

    def test_all_subjects_required(self):
        with self.assertRaises(ValidationError):
            validate_marks({"Python": 80})

    def test_student_factory(self):
        student = validate_student_fields("CS001", "Ada Lovelace", "20", "B.Tech CSE", {s: "75" for s in SUBJECTS})
        self.assertEqual(student.average, 75.0)
        self.assertEqual(student.grade, "A")


if __name__ == "__main__":
    unittest.main()
