import tkinter as tk

BG = "#f5f5f7"
BG_ACCENT = "#ededf0"
CARD = "#ffffff"
CARD_SOFT = "#f2f2f4"
TEXT = "#1d1d1f"
SUBTEXT = "#6e6e73"
BORDER = "#e5e5ea"
SUCCESS = "#34c759"
WARNING = "#ff9f0a"
DARK = "#0b0c0d"


def apply_app_window_style(root: tk.Tk):
    root.configure(bg=BG)


def make_card(parent, bg=CARD, border=BORDER, **kwargs):
    return tk.Frame(
        parent,
        bg=bg,
        highlightthickness=1,
        highlightbackground=border,
        bd=0,
        **kwargs
    )


def make_label(parent, text, size=12, weight="normal", fg=TEXT, bg=None, **kwargs):
    if bg is None:
        bg = parent.cget("bg")

    return tk.Label(
        parent,
        text=text,
        font=("Segoe UI", size, weight),
        fg=fg,
        bg=bg,
        bd=0,
        **kwargs
    )


def make_primary_button(parent, text, command, padx=24, pady=14):
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI", 11, "bold"),
        bg="#000000",
        fg="#ffffff",
        activebackground="#111111",
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        padx=padx,
        pady=pady,
        cursor="hand2"
    )


def make_soft_button(parent, text, command, padx=18, pady=10):
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI", 10, "bold"),
        bg=CARD_SOFT,
        fg=TEXT,
        activebackground="#e9e9ec",
        activeforeground=TEXT,
        relief="flat",
        bd=0,
        padx=padx,
        pady=pady,
        cursor="hand2"
    )


def make_pill_button(parent, text, command, active=False):
    bg = "#ffffff" if active else CARD_SOFT
    fg = "#000000" if active else SUBTEXT

    return tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI", 10, "bold"),
        bg=bg,
        fg=fg,
        activebackground=bg,
        activeforeground=fg,
        relief="flat",
        bd=0,
        padx=20,
        pady=10,
        cursor="hand2"
    )