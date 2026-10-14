"""Tests for safe storage diagnostics and maintenance helpers."""
import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path
from student_management.maintenance_service import database_health, list_backups, prune_backups, validate_csv_file, format_bytes, summarize_maintenance, format_health_report
from student_management.config import SUBJECTS


class MaintenanceServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_database(self):
        report = database_health(self.root / "missing.db")
        self.assertFalse(report["exists"])
        self.assertEqual(report["integrity"], "missing")



    def test_database_health(self):
        path = self.root / "health.db"

        connection = sqlite3.connect(path)
        try:
            connection.execute(
                "CREATE TABLE students (id INTEGER)"
            )
            connection.execute(
                "INSERT INTO students VALUES (1)"
            )
            connection.execute(
                "CREATE TABLE users (id INTEGER)"
            )
            connection.commit()
        finally:
            connection.close()

        report = database_health(path)

        self.assertEqual(report["integrity"], "ok")
        self.assertEqual(report["student_count"], 1)
        self.assertEqual(report["user_count"], 0)




    def test_list_and_prune_backups_dry_run(self):
        folder = self.root / "backups"
        folder.mkdir()
        for name in ("a.db", "b.db", "c.db"):
            (folder / name).write_bytes(b"SQLite placeholder")
        backups = list_backups(folder)
        self.assertEqual(len(backups), 3)
        plan = prune_backups(folder, keep=1)
        self.assertTrue(plan["dry_run"])
        self.assertEqual(len(plan["candidates"]), 2)
        self.assertEqual(len(list(folder.glob("*.db"))), 3)

    def test_prune_requires_positive_keep(self):
        with self.assertRaises(ValueError):
            prune_backups(self.root, keep=0)

    def test_csv_preflight_valid_file(self):
        path = self.root / "valid.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["roll_no", "name", "age", "course", *SUBJECTS])
            writer.writerow(["CS01", "Ada Lovelace", 20, "CSE", *([90] * len(SUBJECTS))])
        report = validate_csv_file(path)
        self.assertTrue(report["readable"])
        self.assertTrue(report["valid_shape"])
        self.assertEqual(report["row_count"], 1)

    def test_csv_preflight_missing_headers(self):
        path = self.root / "bad.csv"
        path.write_text("roll_no,name\nCS01,Ada\n", encoding="utf-8")
        report = validate_csv_file(path)
        self.assertFalse(report["valid_shape"])
        self.assertIn("course", report["missing_headers"])

    def test_csv_preflight_malformed_width(self):
        path = self.root / "bad_width.csv"
        path.write_text("roll_no,name,age,course\nCS01,Ada\n", encoding="utf-8")
        report = validate_csv_file(path)
        self.assertEqual(len(report["malformed_rows"]), 1)

    def test_format_bytes(self):
        self.assertEqual(format_bytes(512), "512 B")
        self.assertEqual(format_bytes(1024), "1.0 KiB")
        with self.assertRaises(ValueError):
            format_bytes(-1)

    def test_maintenance_summary(self):
        summary = summarize_maintenance(self.root / "missing.db", self.root / "missing_backups")
        self.assertFalse(summary["integrity_ok"])
        self.assertEqual(summary["backup_count"], 0)
        self.assertIsNone(summary["latest_backup"])
        report = format_health_report(summary)
        self.assertIn("Database exists: no", report)
        self.assertIn("No backup found", report)


if __name__ == "__main__":
    unittest.main()
