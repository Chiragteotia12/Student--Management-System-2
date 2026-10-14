"""Integration tests for SQLite persistence and CSV exchange."""

import csv
import tempfile
import unittest
from pathlib import Path

from student_management.config import SUBJECTS
from student_management.database import StudentRepository
from student_management.models import Student


def make_student(roll="CS001", name="Ada Lovelace", marks=None):
    """Return a valid student fixture."""
    return Student(
        roll,
        name,
        20,
        "B.Tech CSE",
        marks or {subject: 80 for subject in SUBJECTS},
    )


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = StudentRepository(self.root / "test.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_add_get_and_count(self):
        student = self.repo.add_student(make_student())
        self.assertIsNotNone(student.student_id)
        self.assertEqual(self.repo.count_students(), 1)
        self.assertEqual(self.repo.get_student("CS001").name, "Ada Lovelace")

    def test_duplicate_roll_rejected_case_insensitively(self):
        self.repo.add_student(make_student())
        with self.assertRaises(ValueError):
            self.repo.add_student(
                make_student(roll="cs001", name="Grace Hopper")
            )

    def test_update_student(self):
        self.repo.add_student(make_student())
        updated = make_student(
            name="Grace Hopper",
            marks={subject: 95 for subject in SUBJECTS},
        )
        self.repo.update_student(updated)
        self.assertEqual(self.repo.get_student("CS001").name, "Grace Hopper")
        self.assertEqual(self.repo.get_student("CS001").average, 95.0)

    def test_delete_and_clear(self):
        self.repo.add_student(make_student())
        self.assertTrue(self.repo.delete_student("CS001"))
        self.assertFalse(self.repo.delete_student("CS001"))

        self.repo.add_student(make_student("CS002", "Grace Hopper"))
        self.assertEqual(self.repo.clear_students(), 1)
        self.assertEqual(self.repo.count_students(), 0)

    def test_search_matches_name_and_course(self):
        self.repo.add_student(make_student())
        self.repo.add_student(make_student("CS002", "Grace Hopper"))

        self.assertEqual(len(self.repo.list_students(search="ada")), 1)
        self.assertEqual(len(self.repo.list_students(search="B.Tech")), 2)

    def test_search_matches_roll_number_case_insensitively(self):
        self.repo.add_student(make_student(roll="CS001"))
        results = self.repo.list_students(search="cs001")
        self.assertEqual([student.roll_no for student in results], ["CS001"])

    def test_search_trims_surrounding_whitespace(self):
        self.repo.add_student(make_student())
        results = self.repo.list_students(search="  ada  ")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Ada Lovelace")

    def test_course_filter_is_case_insensitive(self):
        self.repo.add_student(make_student())
        results = self.repo.list_students(course="b.tech cse")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].roll_no, "CS001")

    def test_search_and_course_filter_work_together(self):
        self.repo.add_student(make_student("CS001", "Ada Lovelace"))
        self.repo.add_student(make_student("CS002", "Grace Hopper"))

        results = self.repo.list_students(
            search="ada",
            course="B.Tech CSE",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].roll_no, "CS001")

    def test_list_students_limit(self):
        self.repo.add_student(make_student("CS001", "Ada Lovelace"))
        self.repo.add_student(make_student("CS002", "Grace Hopper"))
        self.repo.add_student(make_student("CS003", "Alan Turing"))

        results = self.repo.list_students(limit=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(
            [student.name for student in results],
            ["Ada Lovelace", "Alan Turing"],
        )

    def test_list_students_offset(self):
        self.repo.add_student(make_student("CS001", "Ada Lovelace"))
        self.repo.add_student(make_student("CS002", "Grace Hopper"))
        self.repo.add_student(make_student("CS003", "Alan Turing"))

        results = self.repo.list_students(limit=2, offset=2)

        self.assertEqual(
            [student.name for student in results],
            ["Grace Hopper"],
        )

    def test_list_students_pagination_with_search_and_course(self):
        self.repo.add_student(make_student("CS001", "Ada Lovelace"))
        self.repo.add_student(make_student("CS002", "Grace Hopper"))
        self.repo.add_student(make_student("CS003", "Ada Byron"))

        results = self.repo.list_students(
            search="ada",
            course="B.Tech CSE",
            limit=1,
            offset=1,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].roll_no, "CS001")

    def test_list_students_rejects_invalid_pagination(self):
        for invalid_limit in (0, -1, True, 1.5):
            with self.subTest(limit=invalid_limit):
                with self.assertRaises(ValueError):
                    self.repo.list_students(limit=invalid_limit)

        for invalid_offset in (-1, True, 1.5):
            with self.subTest(offset=invalid_offset):
                with self.assertRaises(ValueError):
                    self.repo.list_students(offset=invalid_offset)

    def test_all_courses_filter_returns_every_student(self):
        self.repo.add_student(make_student("CS001", "Ada Lovelace"))
        self.repo.add_student(make_student("CS002", "Grace Hopper"))

        results = self.repo.list_students(course="All courses")
        self.assertEqual(len(results), 2)

    def test_search_with_no_match_returns_empty_list(self):
        self.repo.add_student(make_student())

        self.assertEqual(
            self.repo.list_students(search="student-does-not-exist"),
            [],
        )

    def test_csv_round_trip(self):
        self.repo.add_student(make_student())
        output = self.root / "students.csv"
        self.repo.export_csv(output)

        second = StudentRepository(self.root / "second.db")
        result = second.import_csv(output)

        self.assertEqual(result["imported"], 1)
        self.assertEqual(second.get_student("CS001").name, "Ada Lovelace")

    def test_csv_duplicate_is_skipped(self):
        self.repo.add_student(make_student())
        output = self.root / "students.csv"
        self.repo.export_csv(output)

        result = self.repo.import_csv(output)
        self.assertEqual(result["skipped"], 1)

    def test_backup_integrity(self):
        self.repo.add_student(make_student())
        backup = self.repo.backup(self.root / "backup.db")

        restored = StudentRepository(self.root / "restored.db")
        restored.restore_backup(backup)

        self.assertEqual(restored.count_students(), 1)

    def test_authentication_and_password_change(self):
        self.repo.ensure_default_user("admin", "admin1234")

        self.assertIsNotNone(self.repo.authenticate("admin", "admin1234"))
        self.assertIsNone(self.repo.authenticate("admin", "wrong-password"))

        self.repo.change_password("admin", "admin1234", "newpassword123")

        self.assertIsNone(self.repo.authenticate("admin", "admin1234"))
        self.assertIsNotNone(
            self.repo.authenticate("admin", "newpassword123")
        )


if __name__ == "__main__":
    unittest.main()
