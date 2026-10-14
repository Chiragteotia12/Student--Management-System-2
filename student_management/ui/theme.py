"""Theme constants and ttk styling."""
from tkinter import ttk

LIGHT = {"background": "#f5f3ff", "surface": "#ffffff", "header": "#5935a5",
         "text": "#211a32", "muted": "#655d76", "accent": "#6f42c1", "danger": "#c83d50",
         "success": "#247a55", "field": "#ffffff", "tree": "#ffffff"}
DARK = {"background": "#181321", "surface": "#241b35", "header": "#120e1b",
        "text": "#f6f2ff", "muted": "#c3b9d7", "accent": "#9874ed", "danger": "#ed6576",
        "success": "#65c79a", "field": "#312442", "tree": "#2b203d"}


def apply_tree_style(style: ttk.Style, palette: dict) -> None:
    """Apply consistent treeview colors for the selected palette."""
    style.configure("Treeview", background=palette["tree"], foreground=palette["text"],
                    fieldbackground=palette["tree"], rowheight=27, font=("Segoe UI", 10))
    style.configure("Treeview.Heading", background=palette["header"], foreground="#ffffff",
                    font=("Segoe UI", 10, "bold"), padding=7)
    style.map("Treeview", background=[("selected", palette["accent"])], foreground=[("selected", "#ffffff")])
    style.configure("TNotebook.Tab", padding=(12, 7), font=("Segoe UI", 10, "bold"))
    style.configure("TCombobox", padding=5)


def palette_for(dark_mode: bool) -> dict:
    """Return a fresh copy of the requested color palette."""
    return dict(DARK if dark_mode else LIGHT)
