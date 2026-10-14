"""Login screen with a first-run administrator setup message."""
import tkinter as tk
from tkinter import messagebox, ttk
from ..config import APP_NAME, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from ..database import StudentRepository


class LoginWindow:
    """Collect credentials and open the main application after authentication."""
    def __init__(self, root: tk.Tk, repository: StudentRepository, on_success):
        self.root = root
        self.repository = repository
        self.on_success = on_success
        self.window = tk.Toplevel(root)
        self.window.title("Sign in")
        self.window.geometry("420x370")
        self.window.resizable(False, False)
        self.window.configure(bg="#f5f3ff")
        self.window.protocol("WM_DELETE_WINDOW", self._close)
        self._center()
        self._build()
        self.username_entry.focus_set()
        self.window.bind("<Return>", lambda _event: self.login())

    def _center(self):
        """Place the login dialog near the center of the screen."""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 420) // 2
        y = (self.window.winfo_screenheight() - 370) // 2
        self.window.geometry(f"420x370+{x}+{y}")

    def _build(self):
        """Create the login controls."""
        frame = tk.Frame(self.window, bg="#ffffff", padx=32, pady=26)
        frame.pack(fill="both", expand=True, padx=18, pady=18)
        tk.Label(frame, text="Welcome back", font=("Segoe UI", 22, "bold"),
                 fg="#5935a5", bg="#ffffff").pack(anchor="w")
        tk.Label(frame, text=APP_NAME, font=("Segoe UI", 9), fg="#655d76",
                 bg="#ffffff", wraplength=320).pack(anchor="w", pady=(4, 18))
        tk.Label(frame, text="Username", bg="#ffffff", anchor="w").pack(fill="x")
        self.username_var = tk.StringVar(value=DEFAULT_ADMIN_USERNAME)
        self.username_entry = ttk.Entry(frame, textvariable=self.username_var, font=("Segoe UI", 11))
        self.username_entry.pack(fill="x", pady=(4, 12))
        tk.Label(frame, text="Password", bg="#ffffff", anchor="w").pack(fill="x")
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(frame, textvariable=self.password_var, show="*", font=("Segoe UI", 11))
        self.password_entry.pack(fill="x", pady=(4, 18))
        ttk.Button(frame, text="Sign in", command=self.login).pack(fill="x", ipady=5)
        tk.Label(frame, text="First run: admin / admin1234", bg="#ffffff", fg="#655d76",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(12, 0))

    def login(self):
        """Validate credentials and transfer control to the dashboard."""
        user = self.repository.authenticate(self.username_var.get(), self.password_var.get())
        if not user:
            messagebox.showerror("Sign in failed", "Username or password is incorrect.", parent=self.window)
            self.password_var.set("")
            self.password_entry.focus_set()
            return
        self.window.destroy()
        self.root.deiconify()
        self.on_success(user)

    def _close(self):
        """Close the application when the login dialog is dismissed."""
        self.root.destroy()
