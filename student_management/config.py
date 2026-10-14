"""Central application configuration."""
from pathlib import Path

APP_NAME = "AI Powered Student Management System"
APP_VERSION = "2.0.0"
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "students.db"
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "application.log"
BACKUP_DIR = DATA_DIR / "backups"
WINDOW_MIN_WIDTH = 1080
WINDOW_MIN_HEIGHT = 680
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin1234"
PASS_MARK = 40
MAX_MARK = 100
MIN_AGE = 10
MAX_AGE = 100
SUBJECTS = (
    "Python",
    "Design and Analysis of Algorithms",
    "Data Structures",
    "Web Technology",
    "Theory of Automata",
    "Database Management Systems",
    "Computer Networks",
)
GRADE_THRESHOLDS = ((90, "A+"), (75, "A"), (60, "B"), (40, "C"), (0, "Fail"))


def ensure_directories() -> None:
    """Create runtime directories when they do not exist yet."""
    for directory in (DATA_DIR, LOG_DIR, BACKUP_DIR):
        directory.mkdir(parents=True, exist_ok=True)
