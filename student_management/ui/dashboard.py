"""Main Tkinter dashboard and student-management workflows."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from ..academic_service import class_statistics, rank_students
from ..config import APP_NAME, SUBJECTS, ensure_directories
from ..database import StudentRepository
from ..models import Student
from ..recommendation_service import recommend_for_student
from ..report_service import write_student_report, write_class_report
from ..utils import safe_filename, timestamp_for_filename
from ..validators import validate_student_fields, ValidationError
from .theme import LIGHT, DARK, apply_tree_style, palette_for


class Dashboard:
    """Build the application UI and coordinate repository/service calls."""
    def __init__(self, root: tk.Tk, repository: StudentRepository, user: dict):
        self.root = root
        self.repository = repository
        self.user = user
        self.dark_mode = False
        self.palette = dict(LIGHT)
        self.selected_roll = None
        self.fields = {}
        self.mark_vars = {}
        self.search_var = tk.StringVar()
        self.course_filter_var = tk.StringVar(value="All courses")
        self.status_var = tk.StringVar(value="Ready")
        self.style = ttk.Style()
        self._configure_window()
        self._build_header()
        self._build_layout()
        self.refresh_students()
        self.refresh_statistics()

    def _configure_window(self):
        """Configure root geometry and native ttk theme."""
        self.root.title(f"{APP_NAME} v2.0")
        self.root.geometry("1440x850")
        self.root.minsize(1080, 680)
        self.root.configure(bg=self.palette["background"])
        self.style.theme_use("clam")
        apply_tree_style(self.style, self.palette)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_header(self):
        """Build the colored title bar and quick actions."""
        self.header = tk.Frame(self.root, bg=self.palette["header"], padx=22, pady=12)
        self.header.pack(fill="x")
        title_area = tk.Frame(self.header, bg=self.palette["header"])
        title_area.pack(side="left", fill="x", expand=True)
        tk.Label(title_area, text=APP_NAME, font=("Segoe UI", 20, "bold"),
                 bg=self.palette["header"], fg="white").pack(anchor="w")
        tk.Label(title_area, text=f"Signed in as {self.user['username']} · Academic insights · SQLite storage",
                 font=("Segoe UI", 10), bg=self.palette["header"], fg="#eee6ff").pack(anchor="w", pady=(3, 0))
        actions = tk.Frame(self.header, bg=self.palette["header"])
        actions.pack(side="right")
        ttk.Button(actions, text="Change password", command=self.change_password).pack(side="left", padx=4)
        ttk.Button(actions, text="Toggle theme", command=self.toggle_theme).pack(side="left", padx=4)
        ttk.Button(actions, text="Backup DB", command=self.backup_database).pack(side="left", padx=4)

    def _build_layout(self):
        """Create the entry form, table, search bar, and analytics panel."""
        self.body = tk.Frame(self.root, bg=self.palette["background"], padx=12, pady=12)
        self.body.pack(fill="both", expand=True)
        self.left = tk.Frame(self.body, bg=self.palette["surface"], padx=14, pady=12, width=365)
        self.left.pack(side="left", fill="y", padx=(0, 12))
        self.left.pack_propagate(False)
        self.right = tk.Frame(self.body, bg=self.palette["surface"], padx=12, pady=12)
        self.right.pack(side="left", fill="both", expand=True)
        self._build_form()
        self._build_table()
        self._build_status()

    def _build_form(self):
        """Create profile and subject mark input controls."""
        tk.Label(self.left, text="Student details", font=("Segoe UI", 17, "bold"),
                 bg=self.palette["surface"], fg=self.palette["header"]).pack(anchor="w", pady=(0, 10))
        canvas = tk.Canvas(self.left, bg=self.palette["surface"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.left, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=self.palette["surface"])
        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw", width=320)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        for label, key in (("Roll number", "roll_no"), ("Full name", "name"), ("Age", "age"), ("Course", "course")):
            tk.Label(inner, text=label, bg=self.palette["surface"], fg=self.palette["text"],
                     font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(6, 2))
            variable = tk.StringVar()
            self.fields[key] = variable
            ttk.Entry(inner, textvariable=variable).pack(fill="x", pady=(0, 3))
        tk.Label(inner, text="Marks (0–100)", font=("Segoe UI", 12, "bold"),
                 bg=self.palette["surface"], fg=self.palette["header"]).pack(anchor="w", pady=(12, 4))
        for subject in SUBJECTS:
            tk.Label(inner, text=subject, bg=self.palette["surface"], fg=self.palette["text"],
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 1))
            variable = tk.StringVar(value="0")
            self.mark_vars[subject] = variable
            ttk.Entry(inner, textvariable=variable).pack(fill="x")
        buttons = tk.Frame(self.left, bg=self.palette["surface"])
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Add student", command=self.add_student).grid(row=0, column=0, sticky="ew", padx=2, pady=3)
        ttk.Button(buttons, text="Update selected", command=self.update_student).grid(row=0, column=1, sticky="ew", padx=2, pady=3)
        ttk.Button(buttons, text="Clear form", command=self.clear_form).grid(row=1, column=0, sticky="ew", padx=2, pady=3)
        ttk.Button(buttons, text="Delete selected", command=self.delete_student).grid(row=1, column=1, sticky="ew", padx=2, pady=3)
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

    def _build_table(self):
        """Create search/filter controls and a sortable student table."""
        search = tk.Frame(self.right, bg=self.palette["surface"])
        search.pack(fill="x", pady=(0, 10))
        tk.Label(search, text="Search", bg=self.palette["surface"], fg=self.palette["text"]).pack(side="left", padx=(0, 5))
        search_entry = ttk.Entry(search, textvariable=self.search_var, width=25)
        search_entry.pack(side="left", padx=(0, 8))
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_students())
        ttk.Button(search, text="Refresh", command=self.refresh_students).pack(side="left", padx=3)
        ttk.Button(search, text="Import CSV", command=self.import_csv).pack(side="left", padx=3)
        ttk.Button(search, text="Export CSV", command=self.export_csv).pack(side="left", padx=3)
        ttk.Button(search, text="Class report", command=self.export_class_report).pack(side="left", padx=3)
        ttk.Button(search, text="Student report", command=self.export_student_report).pack(side="left", padx=3)
        ttk.Button(search, text="Clear all", command=self.clear_all).pack(side="left", padx=3)
        self.count_label = tk.Label(search, text="0 students", bg=self.palette["surface"], fg=self.palette["muted"])
        self.count_label.pack(side="right")
        columns = ("roll", "name", "age", "course", "average", "grade", "status", "weak", "strong")
        self.tree = ttk.Treeview(self.right, columns=columns, show="headings", selectmode="browse")
        headings = {"roll": "Roll No", "name": "Name", "age": "Age", "course": "Course", "average": "Average",
                    "grade": "Grade", "status": "Status", "weak": "Weak subjects", "strong": "Strong subjects"}
        widths = {"roll": 95, "name": 150, "age": 55, "course": 125, "average": 80, "grade": 65,
                  "status": 90, "weak": 180, "strong": 180}
        for column in columns:
            self.tree.heading(column, text=headings[column], command=lambda c=column: self.sort_by(c, False))
            self.tree.column(column, width=widths[column], minwidth=50, anchor="w")
        yscroll = ttk.Scrollbar(self.right, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(self.right, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.pack(side="top", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.show_student_analysis)
        self.stats_frame = tk.Frame(self.right, bg=self.palette["surface"], pady=10)
        self.stats_frame.pack(fill="x")
        self.stats_label = tk.Label(self.stats_frame, text="Class analytics will appear here.",
                                    justify="left", anchor="w", bg=self.palette["surface"], fg=self.palette["text"],
                                    font=("Segoe UI", 10))
        self.stats_label.pack(fill="x")

    def _build_status(self):
        """Add a small status bar below the main content."""
        bar = tk.Label(self.root, textvariable=self.status_var, anchor="w", padx=12, pady=5,
                       bg=self.palette["header"], fg="white", font=("Segoe UI", 9))
        bar.pack(fill="x", side="bottom")

    def _collect_student(self) -> Student:
        """Validate values from the form and return a Student model."""
        marks = {subject: variable.get() for subject, variable in self.mark_vars.items()}
        return validate_student_fields(self.fields["roll_no"].get(), self.fields["name"].get(),
                                       self.fields["age"].get(), self.fields["course"].get(), marks)

    def add_student(self):
        """Validate and insert the student currently entered in the form."""
        try:
            student = self._collect_student()
            self.repository.add_student(student)
        except (ValidationError, ValueError) as exc:
            messagebox.showerror("Cannot add student", str(exc), parent=self.root)
            return
        self.clear_form()
        self.refresh_students()
        self.refresh_statistics()
        self.status_var.set(f"Added {student.name} ({student.roll_no}).")
        messagebox.showinfo("Student added", f"{student.name} was saved successfully.", parent=self.root)

    def update_student(self):
        """Update the selected student's record from the form."""
        if not self.selected_roll:
            messagebox.showwarning("Select a student", "Select a row in the table first.", parent=self.root)
            return
        try:
            student = self._collect_student()
            if student.roll_no != self.selected_roll:
                raise ValidationError("Roll number cannot be changed while editing a record.")
            self.repository.update_student(student)
        except (ValidationError, ValueError) as exc:
            messagebox.showerror("Cannot update student", str(exc), parent=self.root)
            return
        self.refresh_students()
        self.refresh_statistics()
        self.status_var.set(f"Updated {student.name}.")
        messagebox.showinfo("Student updated", "The record was updated.", parent=self.root)

    def delete_student(self):
        """Delete the selected record after confirmation."""
        if not self.selected_roll:
            messagebox.showwarning("Select a student", "Select a row in the table first.", parent=self.root)
            return
        student = self.repository.get_student(self.selected_roll)
        if not student:
            self.refresh_students()
            return
        if not messagebox.askyesno("Confirm deletion", f"Delete {student.name} ({student.roll_no})?", parent=self.root):
            return
        self.repository.delete_student(student.roll_no)
        self.clear_form()
        self.refresh_students()
        self.refresh_statistics()
        self.status_var.set(f"Deleted {student.roll_no}.")

    def clear_all(self):
        """Clear all records only after explicit confirmation."""
        count = self.repository.count_students()
        if not count:
            messagebox.showinfo("No records", "There are no student records to clear.", parent=self.root)
            return
        if not messagebox.askyesno("Clear all records", f"Permanently delete all {count} student records?", parent=self.root):
            return
        self.repository.clear_students()
        self.clear_form()
        self.refresh_students()
        self.refresh_statistics()
        self.status_var.set("All student records were cleared.")

    def clear_form(self):
        """Reset all profile fields and subject marks."""
        for variable in self.fields.values():
            variable.set("")
        for variable in self.mark_vars.values():
            variable.set("0")
        self.selected_roll = None
        self.tree.selection_remove(self.tree.selection())
        self.status_var.set("Form cleared.")

    def refresh_students(self):
        """Reload the visible table from persistent storage."""
        selected_roll = self.selected_roll
        for item in self.tree.get_children():
            self.tree.delete(item)
        records = self.repository.list_students(search=self.search_var.get())
        for student in records:
            weak = ", ".join(subject for subject, mark in sorted(student.marks.items(), key=lambda pair: pair[1]) if mark < 60) or "—"
            strong = ", ".join(subject for subject, mark in student.marks.items() if mark >= 85) or "—"
            self.tree.insert("", "end", iid=student.roll_no, values=(student.roll_no, student.name, student.age,
                student.course, f"{student.average:.2f}%", student.grade, "Pass" if student.passed else "Review", weak, strong))
        self.count_label.configure(text=f"{len(records)} student(s)")
        if selected_roll and self.tree.exists(selected_roll):
            self.tree.selection_set(selected_roll)
        self.refresh_statistics()

    def refresh_statistics(self):
        """Refresh aggregate academic indicators under the table."""
        records = self.repository.list_students()
        stats = class_statistics(records)
        if not records:
            message = "No student data yet. Add a student to see class analytics."
        else:
            grade_text = ", ".join(f"{grade}: {count}" for grade, count in sorted(stats["grade_distribution"].items()))
            best_subject = max(stats["subject_averages"], key=stats["subject_averages"].get)
            lowest_subject = min(stats["subject_averages"], key=stats["subject_averages"].get)
            message = (f"Students: {stats['student_count']}    Class average: {stats['class_average']}%    "
                       f"Pass rate: {stats['pass_percentage']}%    Median: {stats['median_average']}%\n"
                       f"Highest average: {stats['highest_average']}%    Lowest average: {stats['lowest_average']}%\n"
                       f"Grade distribution: {grade_text}\n"
                       f"Best subject average: {best_subject} ({stats['subject_averages'][best_subject]}%)    "
                       f"Needs attention: {lowest_subject} ({stats['subject_averages'][lowest_subject]}%)")
        self.stats_label.configure(text=message)

    def on_select(self, _event=None):
        """Populate the form when the user selects a table row."""
        selection = self.tree.selection()
        if not selection:
            return
        roll = selection[0]
        student = self.repository.get_student(roll)
        if not student:
            return
        self.selected_roll = student.roll_no
        for key, value in (("roll_no", student.roll_no), ("name", student.name),
                           ("age", str(student.age)), ("course", student.course)):
            self.fields[key].set(value)
        for subject in SUBJECTS:
            self.mark_vars[subject].set(str(student.marks[subject]))
        self.status_var.set(f"Selected {student.name} — click Update selected to save edits.")

    def sort_by(self, column: str, reverse: bool):
        """Sort the currently displayed rows by a selected column."""
        rows = [(self.tree.set(item, column), item) for item in self.tree.get_children("")]
        if column == "average":
            rows.sort(key=lambda pair: float(pair[0].rstrip("%")), reverse=reverse)
        elif column == "age":
            rows.sort(key=lambda pair: int(pair[0]), reverse=reverse)
        else:
            rows.sort(key=lambda pair: pair[0].casefold(), reverse=reverse)
        for index, (_value, item) in enumerate(rows):
            self.tree.move(item, "", index)
        self.tree.heading(column, command=lambda: self.sort_by(column, not reverse))

    def show_student_analysis(self, _event=None):
        """Show a detailed recommendation popup for the selected student."""
        selection = self.tree.selection()
        if not selection:
            return
        student = self.repository.get_student(selection[0])
        if not student:
            return
        analysis = recommend_for_student(student)
        actions = "\n\n".join(f"• {item}" for item in analysis["actions"])
        failed = ", ".join(analysis["failed_subjects"]) or "None"
        messagebox.showinfo("Academic insight", f"Student: {student.name}\nAverage: {analysis['average']}%\n"
            f"Grade: {student.grade}\nSubjects below pass mark: {failed}\n\nStudy plan:\n{actions}\n\n"
            f"{analysis['explanation']}", parent=self.root)

    def export_csv(self):
        """Export visible search results to a CSV file."""
        destination = filedialog.asksaveasfilename(parent=self.root, title="Export students", defaultextension=".csv",
            initialfile=f"students_{timestamp_for_filename()}.csv", filetypes=[("CSV files", "*.csv")])
        if not destination:
            return
        records = self.repository.list_students(search=self.search_var.get())
        count = self.repository.export_csv(destination, records)
        self.status_var.set(f"Exported {count} students.")
        messagebox.showinfo("Export complete", f"Saved {count} records to:\n{destination}", parent=self.root)

    def import_csv(self):
        """Import validated student records from a CSV file."""
        source = filedialog.askopenfilename(parent=self.root, title="Import students", filetypes=[("CSV files", "*.csv")])
        if not source:
            return
        try:
            result = self.repository.import_csv(source)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Import failed", str(exc), parent=self.root)
            return
        self.refresh_students()
        self.refresh_statistics()
        message = f"Imported: {result['imported']}\nSkipped duplicates: {result['skipped']}\nErrors: {len(result['errors'])}"
        if result["errors"]:
            message += "\n\n" + "\n".join(result["errors"][:8])
        messagebox.showinfo("Import results", message, parent=self.root)

    def export_class_report(self):
        """Write a class-level CSV summary and ranking report."""
        destination = filedialog.asksaveasfilename(parent=self.root, title="Save class report", defaultextension=".csv",
            initialfile=f"class_report_{timestamp_for_filename()}.csv", filetypes=[("CSV files", "*.csv")])
        if not destination:
            return
        path = write_class_report(self.repository.list_students(), destination)
        self.status_var.set(f"Class report saved to {path.name}.")
        messagebox.showinfo("Report saved", f"Class report saved to:\n{path}", parent=self.root)

    def export_student_report(self):
        """Write a standalone HTML report for the selected student."""
        if not self.selected_roll:
            messagebox.showwarning("Select a student", "Select a student first.", parent=self.root)
            return
        student = self.repository.get_student(self.selected_roll)
        if not student:
            return
        destination = filedialog.asksaveasfilename(parent=self.root, title="Save student report", defaultextension=".html",
            initialfile=f"{safe_filename(student.name)}_report.html", filetypes=[("HTML report", "*.html")])
        if destination:
            write_student_report(student, destination)
            messagebox.showinfo("Report saved", f"Saved report to:\n{destination}", parent=self.root)

    def backup_database(self):
        """Create a database backup using SQLite's backup support."""
        try:
            path = self.repository.backup()
        except Exception as exc:
            messagebox.showerror("Backup failed", str(exc), parent=self.root)
            return
        self.status_var.set(f"Database backup created: {path.name}")
        messagebox.showinfo("Backup complete", f"Backup saved to:\n{path}", parent=self.root)

    def change_password(self):
        """Open a small dialog for changing the signed-in user's password."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Change password")
        dialog.geometry("360x270")
        dialog.transient(self.root)
        dialog.grab_set()
        variables = [tk.StringVar(), tk.StringVar(), tk.StringVar()]
        for label, variable in zip(("Current password", "New password", "Confirm new password"), variables):
            tk.Label(dialog, text=label).pack(anchor="w", padx=20, pady=(12, 2))
            ttk.Entry(dialog, textvariable=variable, show="*").pack(fill="x", padx=20)
        def save():
            """Validate the confirmation and persist the new password."""
            if variables[1].get() != variables[2].get():
                messagebox.showerror("Password mismatch", "New passwords do not match.", parent=dialog)
                return
            try:
                self.repository.change_password(self.user["username"], variables[0].get(), variables[1].get())
            except ValueError as exc:
                messagebox.showerror("Cannot change password", str(exc), parent=dialog)
                return
            messagebox.showinfo("Password changed", "Your password has been changed.", parent=dialog)
            dialog.destroy()
        ttk.Button(dialog, text="Save password", command=save).pack(pady=18)

    def toggle_theme(self):
        """Switch palette and update primary widget colors."""
        self.dark_mode = not self.dark_mode
        self.palette = palette_for(self.dark_mode)
        self.root.configure(bg=self.palette["background"])
        self.body.configure(bg=self.palette["background"])
        for widget in (self.left, self.right, self.stats_frame):
            widget.configure(bg=self.palette["surface"])
        self.header.configure(bg=self.palette["header"])
        for widget in self.header.winfo_children():
            widget.configure(bg=self.palette["header"])
            for child in widget.winfo_children():
                child.configure(bg=self.palette["header"])
        self.stats_label.configure(bg=self.palette["surface"], fg=self.palette["text"])
        apply_tree_style(self.style, self.palette)
        self.status_var.set("Dark theme enabled." if self.dark_mode else "Light theme enabled.")

    def close(self):
        """Ask before closing the app and flush UI state."""
        if messagebox.askyesno("Exit", "Close Student Management System?", parent=self.root):
            self.root.destroy()
