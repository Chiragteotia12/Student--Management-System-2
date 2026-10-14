"""Small reusable utility functions."""
from datetime import datetime
from pathlib import Path


def timestamp_for_filename() -> str:
    """Return a filesystem-safe timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_filename(value: str, fallback: str = "report") -> str:
    """Convert user text into a conservative filename stem."""
    cleaned = "".join(character if character.isalnum() or character in "-_" else "_" for character in value.strip())
    cleaned = cleaned.strip("_.-")
    return cleaned[:80] or fallback


def ensure_parent(path: str | Path) -> Path:
    """Create a destination's parent folder and return the path."""
    result = Path(path)
    result.parent.mkdir(parents=True, exist_ok=True)
    return result


def format_percentage(value: float, digits: int = 1) -> str:
    """Format a percentage consistently for display."""
    return f"{value:.{digits}f}%"
