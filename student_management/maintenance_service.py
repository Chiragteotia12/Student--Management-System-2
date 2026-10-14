"""Storage maintenance helpers for diagnostics and safe cleanup."""
import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable
from .config import BACKUP_DIR, DATABASE_PATH, SUBJECTS
from .logger import get_logger

LOGGER = get_logger(__name__)


def database_health(database_path: str | Path = DATABASE_PATH) -> dict:
    """Return a compact health report without exposing record contents."""
    path = Path(database_path)
    if not path.exists():
        return {"exists": False, "size_bytes": 0, "integrity": "missing", "student_count": 0,
                "user_count": 0, "last_modified": None}
    report = {"exists": True, "size_bytes": path.stat().st_size, "integrity": "unknown",
              "student_count": 0, "user_count": 0, "last_modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")}
    try:
        with sqlite3.connect(path) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            report["integrity"] = integrity[0] if integrity else "unknown"
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "students" in tables:
                report["student_count"] = connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            if "users" in tables:
                report["user_count"] = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    except sqlite3.DatabaseError as exc:
        LOGGER.exception("Database health check failed for %s", path)
        report["integrity"] = f"error: {exc.__class__.__name__}"
    return report


def list_backups(backup_directory: str | Path = BACKUP_DIR) -> list[dict]:
    """List database backup metadata, newest first."""
    directory = Path(backup_directory)
    if not directory.exists():
        return []
    result = []
    for path in directory.glob("*.db"):
        try:
            stat = path.stat()
            result.append({"path": path, "name": path.name, "size_bytes": stat.st_size,
                           "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")})
        except OSError:
            LOGGER.warning("Could not inspect backup file %s", path)
    return sorted(result, key=lambda item: item["modified_at"], reverse=True)


def prune_backups(backup_directory: str | Path = BACKUP_DIR, keep: int = 10, dry_run: bool = True) -> dict:
    """Plan or perform cleanup while retaining the newest requested backups.

    The default is a dry run so callers must explicitly opt in to deletion.
    Files with other extensions are never touched.
    """
    if keep < 1:
        raise ValueError("At least one backup must be retained.")
    backups = list_backups(backup_directory)
    remove = backups[keep:]
    deleted, errors = [], []
    if not dry_run:
        for item in remove:
            try:
                item["path"].unlink()
                deleted.append(item["name"])
            except OSError as exc:
                errors.append({"name": item["name"], "error": str(exc)})
                LOGGER.exception("Failed to remove old backup %s", item["path"])
    return {"dry_run": dry_run, "keep": keep, "available": len(backups),
            "candidates": [item["name"] for item in remove], "deleted": deleted, "errors": errors}


def validate_csv_file(source: str | Path) -> dict:
    """Preflight a CSV import and report missing headers and malformed row widths."""
    path = Path(source)
    result = {"path": str(path), "readable": False, "headers": [], "missing_headers": [],
              "row_count": 0, "malformed_rows": [], "valid_shape": False}
    if not path.exists() or not path.is_file():
        result["error"] = "File does not exist."
        return result
    required = {"roll_no", "name", "age", "course", *SUBJECTS}
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            headers = next(reader, [])
            result["headers"] = headers
            result["missing_headers"] = sorted(required - set(headers))
            expected_width = len(headers)
            for line_number, row in enumerate(reader, start=2):
                result["row_count"] += 1
                if len(row) != expected_width:
                    result["malformed_rows"].append({"line": line_number, "expected_columns": expected_width,
                                                       "actual_columns": len(row)})
        result["readable"] = True
        result["valid_shape"] = not result["missing_headers"] and not result["malformed_rows"]
    except (OSError, UnicodeError, csv.Error) as exc:
        result["error"] = f"Could not read CSV: {exc}"
        LOGGER.exception("CSV preflight failed for %s", path)
    return result


def format_bytes(size_bytes: int) -> str:
    """Format a non-negative byte count using human-readable binary units."""
    if size_bytes < 0:
        raise ValueError("File size cannot be negative.")
    value = float(size_bytes)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TiB"


def summarize_maintenance(database_path: str | Path = DATABASE_PATH,
                          backup_directory: str | Path = BACKUP_DIR) -> dict:
    """Combine database health and backup inventory for a support checklist."""
    health = database_health(database_path)
    backups = list_backups(backup_directory)
    total_backup_bytes = sum(item["size_bytes"] for item in backups)
    return {
        "database": health,
        "database_size": format_bytes(health["size_bytes"]),
        "backup_count": len(backups),
        "backup_size_bytes": total_backup_bytes,
        "backup_size": format_bytes(total_backup_bytes),
        "latest_backup": backups[0]["name"] if backups else None,
        "integrity_ok": health["integrity"] == "ok",
    }


def format_health_report(summary: dict) -> str:
    """Render a concise text-only storage report for support requests."""
    database = summary["database"]
    integrity = "healthy" if summary["integrity_ok"] else database["integrity"]
    latest = summary["latest_backup"] or "No backup found"
    lines = [
        "Student Management System — Storage Health",
        f"Database exists: {'yes' if database['exists'] else 'no'}",
        f"Database integrity: {integrity}",
        f"Student records: {database['student_count']}",
        f"Local accounts: {database['user_count']}",
        f"Database size: {summary['database_size']}",
        f"Backups available: {summary['backup_count']}",
        f"Backup storage used: {summary['backup_size']}",
        f"Latest backup: {latest}",
    ]
    if not summary["integrity_ok"]:
        lines.append("Action: create a copy of the database before attempting recovery.")
    elif summary["backup_count"] == 0:
        lines.append("Action: create a backup before performing maintenance.")
    else:
        lines.append("Action: no immediate storage action is indicated by this check.")
    return "\n".join(lines)
