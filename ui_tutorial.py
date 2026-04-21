import tkinter as tk
from pathlib import Path
try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None
from utils import BG, CARD, CARD_SOFT, SUBTEXT, TEXT, make_card, make_label, make_primary_button, make_soft_button


class TutorialScreen(tk.Frame):
    def __init__(self, master, on_enter_experience):
        super().__init__(master, bg=BG)

        self.on_enter_experience = on_enter_experience
        self.step_index = 0

        self.steps = [
            {
                "icon": "01",
                "title": "Welcome to GestureFlow",
                "description": "Experience the future of interaction with simple hand movements.",
            },
            {
                "icon": "02",
                "title": "The Ready Switch",
                "description": "Activate the system intentionally to avoid accidental inputs and unwanted gesture triggers.",
            },
            {
                "icon": "03",
                "title": "Computer Vision Engine",
                "description": "The system tracks hand landmarks in real time to identify gestures and trigger desktop actions.",
            },
            {
                "icon": "04",
                "title": "Position Your Hand",
                "description": "Keep your hand around 1 to 2 feet away from the camera for better detection and tracking.",
            },
            {
                "icon": "05",
                "title": "Perform Gestures",
                "description": "Use swipes, peace sign, open palm, and other recognized hand poses to control the system.",
            },

            {
                "icon": "06",
                "title": "Gesture Reference",
                "description": "Place your gesture images in these slots so users can visually verify each pose.",
                "show_gallery": True,
            },
        ]
        self.gesture_slots = [f"Gesture {i:02d}" for i in range(1, 21)]
        self.gesture_image_dir = Path(__file__).resolve().parent / "assets" / "gestures"
        self._gesture_photo_refs = []
        self._gesture_details = self._build_gesture_details()

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

        self.skip_btn = make_soft_button(
            outer,
            text="Skip Tutorial",
            command=self.on_enter_experience,
            padx=16,
            pady=9,
        )
        self.skip_btn.place(relx=0.93, rely=0.08, anchor="center")

        center = tk.Frame(outer, bg=BG)
        center.place(relx=0.5, rely=0.5, anchor="center")

        self.card = make_card(center, bg=CARD)
        self.card.pack()

        self.card.config(width=620, height=660)
        self.card.pack_propagate(False)

        self.inner = tk.Frame(self.card, bg=CARD, padx=56, pady=48)
        self.inner.pack(fill="both", expand=True)

        self.icon_shell = tk.Frame(self.inner, bg=CARD)
        self.icon_shell.pack(pady=(0, 24))

        self.icon_badge = tk.Frame(self.icon_shell, bg=CARD_SOFT, width=92, height=92)
        self.icon_badge.pack()
        self.icon_badge.pack_propagate(False)

        self.icon_label = make_label(self.icon_badge, "", size=24, bg=CARD_SOFT)
        self.icon_label.place(relx=0.5, rely=0.5, anchor="center")

        self.title_label = make_label(
            self.inner,
            "",
            size=27,
            weight="bold",
            bg=CARD,
            justify="center",
        )
        self.title_label.pack(pady=(0, 12))

        self.desc_label = make_label(
            self.inner,
            "",
            size=12,
            fg=SUBTEXT,
            bg=CARD,
            wraplength=460,
            justify="center",
        )
        self.desc_label.pack(pady=(0, 26))

        self.gallery_wrap = tk.Frame(self.inner, bg=CARD)
        self.gallery_canvas = tk.Canvas(
            self.gallery_wrap,
            bg=CARD,
            highlightthickness=0,
            bd=0,
            width=470,
            height=220,
        )
        self.gallery_scroll = tk.Scrollbar(
            self.gallery_wrap,
            orient="vertical",
            command=self.gallery_canvas.yview,
        )
        self.gallery_canvas.configure(yscrollcommand=self.gallery_scroll.set)

        self.gallery_inner = tk.Frame(self.gallery_canvas, bg=CARD)
        self._gallery_window = self.gallery_canvas.create_window((0, 0), window=self.gallery_inner, anchor="nw")
        self.gallery_canvas.pack(side="left", fill="both", expand=True)
        self.gallery_scroll.pack(side="right", fill="y")

        self.gallery_inner.bind("<Configure>", self._on_gallery_inner_configure)
        self.gallery_canvas.bind("<Configure>", self._on_gallery_canvas_configure)
        self._build_gallery_placeholders()

        self.dots_frame = tk.Frame(self.inner, bg=CARD)
        self.dots_frame.pack(pady=(0, 30))

        bottom = tk.Frame(self.inner, bg=CARD)
        bottom.pack(side="bottom", fill="x")

        self.next_btn = make_primary_button(
            bottom,
            text="Next",
            command=self.next_step,
            padx=34,
            pady=14,
        )
        self.next_btn.pack(fill="x")

    def _on_gallery_inner_configure(self, _event):
        self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox("all"))

    def _on_gallery_canvas_configure(self, event):
        self.gallery_canvas.itemconfigure(self._gallery_window, width=event.width)

    def _build_gallery_placeholders(self):
        for child in self.gallery_inner.winfo_children():
            child.destroy()
        self._gesture_photo_refs = []

        columns = 4
        for i, label in enumerate(self.gesture_slots):
            row = i // columns
            col = i % columns

            tile = tk.Frame(
                self.gallery_inner,
                bg=CARD_SOFT,
                width=105,
                height=120,
                highlightthickness=1,
                highlightbackground="#d7d8de",
            )
            tile.grid(row=row, column=col, padx=8, pady=8, sticky="n")
            tile.pack_propagate(False)

            image_box = tk.Frame(tile, bg="#ececf1", width=78, height=60)
            image_box.pack(pady=(10, 8))
            image_box.pack_propagate(False)

            image_path = self._resolve_gesture_image_path(i + 1)
            if image_path is not None:
                photo = self._load_gesture_thumbnail(image_path)
                if photo is not None:
                    self._gesture_photo_refs.append(photo)
                    tk.Label(image_box, image=photo, bg="#ececf1", bd=0).place(relx=0.5, rely=0.5, anchor="center")
                else:
                    self._render_placeholder_label(image_box)
            else:
                self._render_placeholder_label(image_box)

            make_label(
                tile,
                label,
                size=9,
                fg=TEXT,
                bg=CARD_SOFT,
                justify="center",
            ).pack()

            self._bind_tile_click(tile, i + 1)

    def _bind_gallery_mousewheel(self):
        self.gallery_canvas.bind_all("<MouseWheel>", self._on_gallery_mousewheel)
        self.gallery_canvas.bind_all("<Button-4>", self._on_gallery_mousewheel)
        self.gallery_canvas.bind_all("<Button-5>", self._on_gallery_mousewheel)

    def _unbind_gallery_mousewheel(self):
        self.gallery_canvas.unbind_all("<MouseWheel>")
        self.gallery_canvas.unbind_all("<Button-4>")
        self.gallery_canvas.unbind_all("<Button-5>")

    def _on_gallery_mousewheel(self, event):
        if not self.gallery_wrap.winfo_ismapped():
            return

        if hasattr(event, "delta") and event.delta:
            direction = -1 if event.delta > 0 else 1
        elif getattr(event, "num", None) == 4:
            direction = -1
        else:
            direction = 1
        self.gallery_canvas.yview_scroll(direction, "units")

    def _resolve_gesture_image_path(self, index):
        stem = f"gesture_{index:02d}"
        for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            candidate = self.gesture_image_dir / f"{stem}{ext}"
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _render_placeholder_label(parent):
        make_label(
            parent,
            "Image\nPlaceholder",
            size=8,
            fg="#7f8088",
            bg="#ececf1",
            justify="center",
        ).place(relx=0.5, rely=0.5, anchor="center")

    @staticmethod
    def _load_gesture_thumbnail(path):
        if Image is None or ImageTk is None:
            return None
        try:
            image = Image.open(path).convert("RGB")
            resampling = getattr(Image, "Resampling", Image)
            image.thumbnail((74, 56), resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception:
            return None

    @staticmethod
    def _build_gesture_details():
        details = {
            1: ("Swipe Left", "Moves to next slide.", "Use right hand. Extend index and sweep left."),
            2: ("Swipe Right", "Moves to previous slide.", "Use left hand. Extend index and sweep right."),
            3: ("Mouse Mode (Right Peace)", "Enables cursor movement and click gestures.", "Right hand peace sign: index+middle up, ring+pinky down."),
            4: ("Left Click / Drag", "Performs left click and supports hold for drag.", "In mouse mode, bend right index finger down."),
            5: ("Right Click", "Performs right click.", "In mouse mode, tap right middle finger down."),
            6: ("Mouse Freeze", "Temporarily pauses cursor movement.", "Extend right thumb while in mouse mode."),
            7: ("PiP Toggle", "Moves camera feed to picture-in-picture window.", "Left OK sign (thumb+index touch, middle/ring/pinky up) hold 1s."),
            8: ("System Lock", "Pauses all recognition actions.", "Right pinky-only hold for 1s to lock/unlock."),
            9: ("Mouse Lock", "Disables mouse interaction.", "Left pinky-only hold for 0.7s."),
            10: ("Alt+Tab Start", "Opens app switcher and keeps Alt held.", "Right fist + left index+middle up."),
            11: ("Alt+Tab Next", "Moves to next app while Alt is held.", "Keep right fist; left middle-only gesture."),
            12: ("Alt+Tab Previous", "Moves to previous app while Alt is held.", "Keep right fist; left index-only gesture."),
            13: ("Volume Mode Toggle", "Enters/exits volume-only controls.", "Right index+pinky up hold 1s."),
            14: ("Volume Up", "Raises system volume.", "In volume mode: left index-only."),
            15: ("Volume Down", "Lowers system volume.", "In volume mode: left thumb-only."),
            16: ("Volume Hold", "Freezes volume changes temporarily.", "In volume mode: show right open palm."),
            17: ("Zoom Mode Enter", "Activates zoom-only controls.", "Both open palms hold 1s."),
            18: ("Zoom In", "Zooms in based on hand spread.", "In zoom mode: spread two open palms outward."),
            19: ("Zoom Out Guard", "Zoom-out is restricted for slideshow safety.", "Inward movement attempts zoom-out but floor guards apply."),
            20: ("Zoom Mode Exit", "Returns to normal gesture set.", "Both fists hold 1s."),
        }
        return details

    def _bind_tile_click(self, tile, gesture_index):
        def _open(_event=None):
            self._open_gesture_detail(gesture_index)

        tile.bind("<Button-1>", _open)
        tile.bind("<Enter>", lambda _e: tile.configure(highlightbackground="#9fa4b6"))
        tile.bind("<Leave>", lambda _e: tile.configure(highlightbackground="#d7d8de"))

        for child in tile.winfo_children():
            child.bind("<Button-1>", _open)
            for grand in child.winfo_children():
                grand.bind("<Button-1>", _open)

    def _open_gesture_detail(self, gesture_index):
        title, purpose, howto = self._gesture_details.get(
            gesture_index,
            (
                f"Gesture {gesture_index:02d}",
                "Purpose not set yet.",
                "Activation details will be added here.",
            ),
        )

        popup = tk.Toplevel(self)
        popup.title(f"{title} Details")
        popup.configure(bg=CARD)
        popup.geometry("560x520")
        popup.transient(self.winfo_toplevel())
        popup.grab_set()

        try:
            popup.attributes("-alpha", 0.0)
        except Exception:
            pass

        shell = tk.Frame(popup, bg=CARD, padx=24, pady=22)
        shell.pack(fill="both", expand=True)

        make_label(shell, title, size=22, weight="bold", bg=CARD).pack(anchor="w", pady=(0, 8))
        make_label(shell, "Gesture Preview", size=10, fg=SUBTEXT, bg=CARD).pack(anchor="w", pady=(0, 8))

        image_panel = tk.Frame(shell, bg=CARD_SOFT, width=500, height=240, highlightthickness=1, highlightbackground="#d7d8de")
        image_panel.pack(fill="x")
        image_panel.pack_propagate(False)

        image_path = self._resolve_gesture_image_path(gesture_index)
        if image_path is not None:
            photo = self._load_popup_image(image_path)
            if photo is not None:
                lbl = tk.Label(image_panel, image=photo, bg=CARD_SOFT, bd=0)
                lbl.image = photo
                lbl.place(relx=0.5, rely=0.5, anchor="center")
            else:
                self._render_popup_placeholder(image_panel, gesture_index)
        else:
            self._render_popup_placeholder(image_panel, gesture_index)

        info = tk.Frame(shell, bg=CARD)
        info.pack(fill="x", pady=(14, 12))
        make_label(info, f"What it does: {purpose}", size=11, fg=TEXT, bg=CARD, wraplength=500, justify="left").pack(anchor="w", pady=(0, 8))
        make_label(info, f"How to activate: {howto}", size=11, fg=SUBTEXT, bg=CARD, wraplength=500, justify="left").pack(anchor="w")

        make_primary_button(shell, "Close", popup.destroy, padx=22, pady=10).pack(anchor="e", pady=(12, 0))

        self._fade_in_popup(popup)

    @staticmethod
    def _render_popup_placeholder(parent, index):
        make_label(
            parent,
            f"Gesture {index:02d}\nImage Placeholder",
            size=14,
            fg="#7f8088",
            bg=CARD_SOFT,
            justify="center",
        ).place(relx=0.5, rely=0.5, anchor="center")

    @staticmethod
    def _load_popup_image(path):
        if Image is None or ImageTk is None:
            return None
        try:
            image = Image.open(path).convert("RGB")
            resampling = getattr(Image, "Resampling", Image)
            image.thumbnail((480, 220), resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception:
            return None

    def _fade_in_popup(self, popup):
        try:
            alpha = float(popup.attributes("-alpha"))
        except Exception:
            return

        alpha += 0.12
        if alpha >= 1.0:
            try:
                popup.attributes("-alpha", 1.0)
            except Exception:
                pass
            return

        try:
            popup.attributes("-alpha", alpha)
        except Exception:
            return
        popup.after(16, lambda: self._fade_in_popup(popup))

    def render_step(self):
        step = self.steps[self.step_index]

        self.icon_label.config(text=step["icon"])
        self.title_label.config(text=step["title"])
        self.desc_label.config(text=step["description"])

        if step.get("show_gallery"):
            self.gallery_wrap.pack(fill="x", pady=(0, 18))
            self._bind_gallery_mousewheel()
        else:
            self._unbind_gallery_mousewheel()
            self.gallery_wrap.pack_forget()

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
