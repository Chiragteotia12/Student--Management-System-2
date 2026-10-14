"""Application startup and dependency wiring."""
import tkinter as tk
from tkinter import messagebox
from .config import APP_NAME, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, ensure_directories
from .database import StudentRepository
from .logger import get_logger
from .ui.dashboard import Dashboard
from .ui.login_window import LoginWindow

LOGGER = get_logger(__name__)


def run() -> None:
    """Initialize storage and launch the login-first desktop application."""
    ensure_directories()
    root = tk.Tk()
    root.withdraw()
    root.title(APP_NAME)
    try:
        repository = StudentRepository()
        repository.ensure_default_user(DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD)
    except Exception as exc:
        LOGGER.exception("Application startup failed")
        messagebox.showerror("Startup error", f"The application could not initialize its database.\n\n{exc}")
        root.destroy()
        return
    dashboard_holder = {}
    def show_dashboard(user: dict) -> None:
        """Construct the dashboard only after successful authentication."""
        dashboard_holder["dashboard"] = Dashboard(root, repository, user)
    LoginWindow(root, repository, show_dashboard)
    root.mainloop()
