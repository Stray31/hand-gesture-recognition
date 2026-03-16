import tkinter as tk
from utils import BG, CARD, CARD_SOFT, SUBTEXT, TEXT, make_card, make_label, make_primary_button


class TutorialScreen(tk.Frame):
    def __init__(self, master, on_enter_experience):
        super().__init__(master, bg=BG)

        self.on_enter_experience = on_enter_experience
        self.step_index = 0

        self.steps = [
            {
                "icon": "✋",
                "title": "Welcome to GestureFlow",
                "description": "Experience the future of interaction with simple hand movements."
            },
            {
                "icon": "👍",
                "title": "The Ready Switch",
                "description": "Activate the system intentionally to avoid accidental inputs and unwanted gesture triggers."
            },
            {
                "icon": "🧠",
                "title": "Computer Vision Engine",
                "description": "The system tracks hand landmarks in real time to identify gestures and trigger desktop actions."
            },
            {
                "icon": "📷",
                "title": "Position Your Hand",
                "description": "Keep your hand around 1 to 2 feet away from the camera for better detection and tracking."
            },
            {
                "icon": "✨",
                "title": "Perform Gestures",
                "description": "Use swipes, peace sign, open palm, and other recognized hand poses to control the system."
            },
            {
                "icon": "🔒",
                "title": "Privacy First",
                "description": "All gesture processing runs locally on your device during the software session."
            },
        ]

        self.build_ui()
        self.render_step()

    def build_ui(self):
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)

        # subtle background blobs
        blob_left = tk.Frame(outer, bg="#ececef", width=320, height=320)
        blob_left.place(relx=0.06, rely=0.15)
        

        blob_right = tk.Frame(outer, bg="#ececef", width=300, height=300)
        blob_right.place(relx=0.76, rely=0.68)
        

        center = tk.Frame(outer, bg=BG)
        center.place(relx=0.5, rely=0.5, anchor="center")

        self.card = make_card(center, bg=CARD)
        self.card.pack()

        self.card.config(width=560, height=540)
        self.card.pack_propagate(False)

        self.inner = tk.Frame(self.card, bg=CARD, padx=56, pady=48)
        self.inner.pack(fill="both", expand=True)

        self.icon_shell = tk.Frame(self.inner, bg=CARD)
        self.icon_shell.pack(pady=(0, 24))

        self.icon_badge = tk.Frame(self.icon_shell, bg=CARD_SOFT, width=92, height=92)
        self.icon_badge.pack()
        self.icon_badge.pack_propagate(False)

        self.icon_label = make_label(self.icon_badge, "", size=36, bg=CARD_SOFT)
        self.icon_label.place(relx=0.5, rely=0.5, anchor="center")

        self.title_label = make_label(
            self.inner,
            "",
            size=27,
            weight="bold",
            bg=CARD,
            justify="center"
        )
        self.title_label.pack(pady=(0, 12))

        self.desc_label = make_label(
            self.inner,
            "",
            size=12,
            fg=SUBTEXT,
            bg=CARD,
            wraplength=420,
            justify="center"
        )
        self.desc_label.pack(pady=(0, 26))

        self.dots_frame = tk.Frame(self.inner, bg=CARD)
        self.dots_frame.pack(pady=(0, 30))

        bottom = tk.Frame(self.inner, bg=CARD)
        bottom.pack(side="bottom", fill="x")

        self.next_btn = make_primary_button(
            bottom,
            text="Next",
            command=self.next_step,
            padx=34,
            pady=14
        )
        self.next_btn.pack(fill="x")

    def render_step(self):
        step = self.steps[self.step_index]

        self.icon_label.config(text=step["icon"])
        self.title_label.config(text=step["title"])
        self.desc_label.config(text=step["description"])

        for child in self.dots_frame.winfo_children():
            child.destroy()

        for i in range(len(self.steps)):
            w = 34 if i == self.step_index else 10
            color = TEXT if i == self.step_index else "#d5d5da"
            dot = tk.Frame(self.dots_frame, bg=color, width=w, height=6)
            dot.pack(side="left", padx=4)
            dot.pack_propagate(False)

        self.next_btn.config(
            text="Enter Experience" if self.step_index == len(self.steps) - 1 else "Next"
        )

    def next_step(self):
        if self.step_index < len(self.steps) - 1:
            self.step_index += 1
            self.render_step()
        else:
            self.on_enter_experience()