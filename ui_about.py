import tkinter as tk
from utils import BG, CARD, SUBTEXT, make_card, make_label, make_soft_button


class AboutScreen(tk.Frame):
    def __init__(self, master, on_back, on_replay_tutorial, on_exit_app):
        super().__init__(master, bg=BG)

        self.on_back = on_back
        self.on_replay_tutorial = on_replay_tutorial
        self.on_exit_app = on_exit_app

        self.build_ui()

    def build_ui(self):
        shell = tk.Frame(self, bg=BG, padx=34, pady=30)
        shell.pack(fill="both", expand=True)

        top = tk.Frame(shell, bg=BG)
        top.pack(fill="x", pady=(0, 16))

        left = tk.Frame(top, bg=BG)
        left.pack(side="left")

        make_soft_button(left, "Back to Camera", self.on_back).pack(side="left", padx=(0, 10))
        make_soft_button(left, "Replay Tutorial", self.on_replay_tutorial).pack(side="left", padx=(0, 10))
        make_soft_button(left, "Exit", self.on_exit_app).pack(side="left")

        right = tk.Frame(top, bg=BG)
        right.pack(side="right")

        make_label(right, "Information", size=26, weight="bold", bg=BG).pack(anchor="e")
        make_label(right, "GestureFlow", size=10, fg=SUBTEXT, bg=BG).pack(anchor="e", pady=(4, 0))

        content_wrap = tk.Frame(shell, bg=BG)
        content_wrap.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(content_wrap, bg=BG, highlightthickness=0, bd=0)
        self.vbar = tk.Scrollbar(content_wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)

        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.grid_host = tk.Frame(self.canvas, bg=BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.grid_host, anchor="nw")

        self.grid_host.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

        self.grid_host.columnconfigure(0, weight=1)
        self.grid_host.columnconfigure(1, weight=1)
        self.grid_host.columnconfigure(2, weight=1)

        col1 = tk.Frame(self.grid_host, bg=BG)
        col1.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        col2 = tk.Frame(self.grid_host, bg=BG)
        col2.grid(row=0, column=1, sticky="nsew", padx=10)

        col3 = tk.Frame(self.grid_host, bg=BG)
        col3.grid(row=0, column=2, sticky="nsew", padx=(10, 0))

        self.section_card(
            col1,
            "Gesture List",
            [
                ("Swipe Left (Right Hand)", "Moves to next slide."),
                ("Swipe Right (Left Hand)", "Moves to previous slide."),
                ("Right Peace Sign", "Mouse mode (cursor and clicks)."),
                ("Left OK Sign", "Toggle PiP camera mode."),
                ("Right Pinky Only", "Lock/unlock recognition."),
                ("Left Pinky Only", "Mouse lock toggle."),
                ("Right Fist + Left Index/Middle", "Start Alt+Tab mode."),
                ("Volume Mode Toggle", "Right index+pinky hold."),
                ("Volume Up", "Left index-only in volume mode."),
                ("Volume Down", "Left thumb-only in volume mode."),
                ("Zoom Mode Enter", "Both palms open hold 1s."),
                ("Zoom Mode Exit", "Both fists hold 1s."),
            ],
        ).pack(fill="x", pady=(0, 16))

        self.section_card(
            col1,
            "System Pipeline",
            [
                ("01 Input Capture", "Raw video stream processing"),
                ("02 Landmark Detection", "Hand tracking landmarks"),
                ("03 Gesture Classification", "Pattern matching"),
                ("04 Action Trigger", "System command execution"),
            ],
        ).pack(fill="x")

        self.section_card(
            col2,
            "Usage Guidelines",
            [
                ("Optimal Lighting", "Use a well-lit environment."),
                ("Distance Control", "Stay around 1 to 2 feet from the camera."),
                ("Background Clarity", "Use a simple background."),
                ("Steady Pace", "Perform gestures at a moderate speed."),
            ],
        ).pack(fill="x", pady=(0, 16))

        self.section_card(
            col2,
            "System Requirements",
            [
                ("Hardware", "720p+ Webcam"),
                ("Processor", "Multi-core CPU"),
                ("Memory", "4GB+ RAM"),
            ],
        ).pack(fill="x")

        self.section_card(
            col3,
            "Project Team",
            [
                ("Romel Caadyang", "Quality Assurance"),
                ("Gabriel Angelo Minoza", "UI/UX Designer"),
                ("Noreen Mae Norcio", "Documentation Lead"),
                ("Janluke Pamular", "Lead Developer"),
            ],
        ).pack(fill="x")

    def _on_frame_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if not self.winfo_ismapped():
            return
        if hasattr(event, "delta") and event.delta:
            direction = -1 if event.delta > 0 else 1
        elif getattr(event, "num", None) == 4:
            direction = -1
        else:
            direction = 1
        self.canvas.yview_scroll(direction, "units")

    def section_card(self, parent, title, rows):
        card = make_card(parent, bg=CARD)
        inner = tk.Frame(card, bg=CARD, padx=22, pady=20)
        inner.pack(fill="both", expand=True)

        make_label(inner, title, size=16, weight="bold", bg=CARD).pack(anchor="w", pady=(0, 14))

        for main, sub in rows:
            row = tk.Frame(inner, bg=CARD)
            row.pack(fill="x", pady=6)

            make_label(row, main, size=11, weight="bold", bg=CARD).pack(anchor="w")
            make_label(row, sub, size=10, fg=SUBTEXT, bg=CARD, wraplength=280, justify="left").pack(anchor="w")

        return card
