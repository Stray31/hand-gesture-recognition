import math
import time
import tkinter as tk

import cv2
import mediapipe as mp
from PIL import Image, ImageTk

from camera import CameraManager
from utils import (
    BG, CARD, CARD_SOFT, TEXT, SUBTEXT, SUCCESS, DARK,
    make_card, make_label, make_soft_button, make_pill_button
)

from gestures.swipe_left import SwipeLeft
from gestures.swipe_right import SwipeRight
from gestures.peace_sign import PeaceSign
from actions import trigger_action

from mouse_controller import MouseController
from click_controller import ClickController
from shortcut_controller import ShortcutController
from mode_controller import ModeController


class RecognitionScreen(tk.Frame):
    def __init__(self, master, on_show_about, on_exit_to_tutorial):
        super().__init__(master, bg=BG)

        self.on_show_about = on_show_about
        self.on_exit_to_tutorial = on_exit_to_tutorial

        # -----------------------------
        # MediaPipe setup
        # -----------------------------
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=0,
            min_detection_confidence=0.55,
            min_tracking_confidence=0.55,
        )

        # -----------------------------
        # Camera / rendering
        # -----------------------------
        self.camera = CameraManager(index=0, width=960, height=540)
        self.camera_running = False
        self.camera_job = None

        self.SHOW_LANDMARKS = False
        self.SHOW_LANDMARK_NUMBERS = False

        self.FRAME_DELAY_MS = 20
        self.MP_WIDTH = 256
        self.MP_HEIGHT = 144

        # -----------------------------
        # Hand validity filter
        # -----------------------------
        self.HAND_SCORE_MIN = 0.80
        self.PALM_MIN = 0.07
        self.PALM_MAX = 0.60

        # -----------------------------
        # Gesture state
        # -----------------------------
        self.is_ready = False
        self.current_gesture = None
        self.last_gesture = "Waiting for input"

        self.last_action_time = 0.0
        self.COOLDOWN = 1.5

        self.GESTURE_FRAMES_REQUIRED = 3
        self.gesture_queue_left = []
        self.gesture_queue_right = []

        self.GESTURES = [SwipeLeft(), SwipeRight(), PeaceSign()]

        # -----------------------------
        # Controllers
        # -----------------------------
        self.mouse = MouseController(
            sensitivity=1.0,
            deadzone=0.03,
            smoothing=0.45,
            mouse_hz=60,
            use_thumb_freeze=True,
        )

        self.clicks = ClickController(
            left_down_frames_required=2,
            left_up_frames_required=2,
            right_tap_frames_required=2,
            right_click_cooldown=0.45,
        )

        self.shortcuts = ShortcutController(
            fist_frames_required=3,
            release_frames_required=2,
            lost_hand_timeout=0.25,
            tab_cooldown=0.20,
            tap_frames_required=2,
        )

        self.modes = ModeController(
            lock_hold_seconds=1.0,
            lock_toggle_cooldown=1.0,
            pinch_threshold=0.055,
            pinch_release_threshold=0.070,
            scroll_reference_landmark=9,
            scroll_hz=30,
            scroll_deadzone=0.010,
            scroll_gain=1800.0,
            scroll_smoothing=0.55,
            scroll_clamp=1200,
        )

        self.build_ui()
        self.refresh_ui()

        # start camera AFTER the screen has rendered
        self.after(180, self.start_camera)

    # -----------------------------
    # UI
    # -----------------------------
    def build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        shell = tk.Frame(self, bg=BG, padx=34, pady=30)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        top = tk.Frame(shell, bg=BG)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)

        left_actions = tk.Frame(top, bg=BG)
        left_actions.grid(row=0, column=0, sticky="w")

        make_soft_button(left_actions, "Information", self.handle_show_about).pack(side="left", padx=(0, 10))
        make_soft_button(left_actions, "Exit", self.handle_exit).pack(side="left")

        self.right_status = tk.Frame(top, bg=BG)
        self.right_status.grid(row=0, column=1, sticky="e")

        self.ready_btn = make_pill_button(
            self.right_status,
            "Standby Mode",
            self.toggle_ready,
            active=False
        )
        self.ready_btn.pack(anchor="e")

        self.gesture_scan_label = make_label(
            self.right_status,
            "Current Gesture: Scanning...",
            size=10,
            fg=SUBTEXT,
            bg=BG
        )
        self.gesture_scan_label.pack(anchor="e", pady=(8, 0))

        body = tk.Frame(shell, bg=BG)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        body.rowconfigure(1, weight=0)

        cam_card = make_card(body, bg=CARD)
        cam_card.grid(row=0, column=0, sticky="nsew", pady=(0, 18))
        cam_card.columnconfigure(0, weight=1)
        cam_card.rowconfigure(1, weight=1)

        header = tk.Frame(cam_card, bg=CARD, padx=26, pady=22)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        make_label(header, "Recognition Dashboard", size=20, weight="bold", bg=CARD).grid(row=0, column=0, sticky="w")
        make_label(header, "Live camera feed and gesture tracking", size=10, fg=SUBTEXT, bg=CARD).grid(row=1, column=0, sticky="w", pady=(4, 0))

        preview_wrap = tk.Frame(cam_card, bg=CARD, padx=26, pady=0)
        preview_wrap.grid(row=1, column=0, sticky="nsew")
        preview_wrap.columnconfigure(0, weight=1)
        preview_wrap.rowconfigure(0, weight=1)

        self.camera_box = tk.Frame(
            preview_wrap,
            bg=DARK,
            highlightthickness=1,
            highlightbackground="#232428"
        )
        self.camera_box.grid(row=0, column=0, sticky="nsew")
        self.camera_box.columnconfigure(0, weight=1)
        self.camera_box.rowconfigure(0, weight=1)

        self.video_label = tk.Label(self.camera_box, bg=DARK, bd=0)
        self.video_label.place(relx=0.5, rely=0.5, anchor="center")

        # subtle center message only, no big dark rectangle
        self.camera_placeholder = make_label(
            self.camera_box,
            "Starting camera...",
            size=12,
            weight="bold",
            fg="#d0d3d8",
            bg=DARK,
            justify="center"
        )
        self.camera_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # only corner accents, directly on top of camera view
        self.corner_tl = self._corner(self.camera_box, 0.30, 0.22, "nw")
        self.corner_tr = self._corner(self.camera_box, 0.70, 0.22, "ne")
        self.corner_bl = self._corner(self.camera_box, 0.30, 0.78, "sw")
        self.corner_br = self._corner(self.camera_box, 0.70, 0.78, "se")

        info_wrap = tk.Frame(cam_card, bg=CARD, padx=26, pady=18)
        info_wrap.grid(row=2, column=0, sticky="ew")

        info_row = tk.Frame(info_wrap, bg=CARD)
        info_row.pack(fill="x")
        info_row.columnconfigure(0, weight=1)
        info_row.columnconfigure(1, weight=1)

        left_info = tk.Frame(info_row, bg=CARD)
        left_info.grid(row=0, column=0, sticky="w")

        self.status_label = make_label(
            left_info,
            "Status: STANDBY",
            size=11,
            weight="bold",
            fg=SUBTEXT,
            bg=CARD
        )
        self.status_label.pack(anchor="w")

        self.event_label = make_label(
            left_info,
            "Event: Waiting for activation",
            size=10,
            fg=SUBTEXT,
            bg=CARD
        )
        self.event_label.pack(anchor="w", pady=(4, 0))

        right_info = tk.Frame(info_row, bg=CARD)
        right_info.grid(row=0, column=1, sticky="e")

        self.debug_label = make_label(
            right_info,
            "Left: None | Right: None",
            size=10,
            fg=SUBTEXT,
            bg=CARD
        )
        self.debug_label.pack(anchor="e")

        self.system_mode_label = make_label(
            right_info,
            "Mode: Standby",
            size=10,
            fg=SUBTEXT,
            bg=CARD
        )
        self.system_mode_label.pack(anchor="e", pady=(4, 0))

        bottom_card = make_card(body, bg="#f2f2f4")
        bottom_card.grid(row=1, column=0, sticky="ew")

        bottom_inner = tk.Frame(bottom_card, bg="#f2f2f4", padx=26, pady=22)
        bottom_inner.pack(fill="x")

        make_label(
            bottom_inner,
            "Last Gesture Performed",
            size=10,
            weight="bold",
            fg="#7a7a80",
            bg="#f2f2f4"
        ).pack()

        self.last_gesture_label = make_label(
            bottom_inner,
            self.last_gesture,
            size=22,
            weight="bold",
            fg="#111111",
            bg="#f2f2f4"
        )
        self.last_gesture_label.pack(pady=(6, 0))

    def _corner(self, parent, relx, rely, anchor):
        corner = tk.Frame(parent, bg="#ffffff", width=18, height=18)
        corner.place(relx=relx, rely=rely, anchor=anchor)
        corner.pack_propagate(False)
        return corner

    # -----------------------------
    # Helpers
    # -----------------------------
    def _dist(self, a, b) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    def valid_hand_shape(self, landmarks) -> bool:
        wrist = landmarks[0]
        mcp9 = landmarks[9]
        mcp5 = landmarks[5]
        mcp17 = landmarks[17]

        palm_len = self._dist(wrist, mcp9)
        palm_wid = self._dist(mcp5, mcp17)

        if palm_len < self.PALM_MIN or palm_wid < self.PALM_MIN:
            return False
        if palm_len > self.PALM_MAX or palm_wid > 0.85:
            return False
        return True

    # -----------------------------
    # Camera lifecycle
    # -----------------------------
    def start_camera(self):
        ok = self.camera.start()
        if not ok:
            self.camera_placeholder.config(text="Unable to access camera")
            return

        self.camera_running = True
        self.update_camera_frame()

    def stop_camera(self):
        self.camera_running = False
        if self.camera_job is not None:
            try:
                self.after_cancel(self.camera_job)
            except Exception:
                pass
            self.camera_job = None
        self.camera.release()

    def destroy(self):
        self.stop_camera()
        try:
            self.hands.close()
        except Exception:
            pass
        super().destroy()

    # -----------------------------
    # Navigation handlers
    # -----------------------------
    def handle_show_about(self):
        self.stop_camera()
        self.on_show_about()

    def handle_exit(self):
        self.stop_camera()
        self.on_exit_to_tutorial()

    # -----------------------------
    # UI state
    # -----------------------------
    def toggle_ready(self):
        self.is_ready = not self.is_ready

        if not self.is_ready:
            self.current_gesture = None
            self.mouse.reset()
            self.clicks.force_release_left()
            self.shortcuts.force_release_alt()

        self.refresh_ui()

    def refresh_ui(self):
        if self.is_ready:
            self.ready_btn.config(
                text="System Ready",
                bg="#ffffff",
                fg="#000000",
                activebackground="#ffffff",
                activeforeground="#000000",
            )
            self.gesture_scan_label.config(
                text=f"Current Gesture: {self.current_gesture or 'Scanning...'}",
                fg=TEXT
            )
        else:
            self.ready_btn.config(
                text="Standby Mode",
                bg=CARD_SOFT,
                fg=SUBTEXT,
                activebackground=CARD_SOFT,
                activeforeground=SUBTEXT,
            )
            self.gesture_scan_label.config(
                text="Current Gesture: Scanning...",
                fg=SUBTEXT
            )

        self.last_gesture_label.config(text=self.last_gesture)

    # -----------------------------
    # Main camera + recognition loop
    # -----------------------------
    def update_camera_frame(self):
        if not self.camera_running:
            return

        frame_start = time.time()

        ok, frame = self.camera.read()
        if not ok or frame is None:
            self.camera_job = self.after(self.FRAME_DELAY_MS, self.update_camera_frame)
            return

        frame = cv2.flip(frame, 1)

        # process smaller frame for speed
        small = cv2.resize(frame, (self.MP_WIDTH, self.MP_HEIGHT), interpolation=cv2.INTER_AREA)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb_small)

        frame_gesture_left = None
        frame_gesture_right = None

        left_landmarks = None
        right_landmarks = None
        left_score = 0.0
        right_score = 0.0

        detected_hand_landmarks = []

        if result.multi_hand_landmarks and result.multi_handedness:
            for idx, hlm in enumerate(result.multi_hand_landmarks):
                handed = result.multi_handedness[idx].classification[0]
                hand_type = handed.label
                score = float(handed.score)

                if score < self.HAND_SCORE_MIN:
                    continue
                if not self.valid_hand_shape(hlm.landmark):
                    continue

                detected_hand_landmarks.append(hlm)

                if hand_type == "Left":
                    left_landmarks = hlm.landmark
                    left_score = score
                else:
                    right_landmarks = hlm.landmark
                    right_score = score

        if not self.is_ready:
            self.current_gesture = None
            self.debug_label.config(text="Left: None | Right: None", fg=SUBTEXT)
            self.system_mode_label.config(text="Mode: Standby", fg=SUBTEXT)
            self.status_label.config(text="Status: STANDBY", fg=SUBTEXT)
            self.event_label.config(text="Event: Waiting for activation", fg=SUBTEXT)

        else:
            self.modes.update_lock(left_landmarks, right_landmarks)

            if self.modes.locked:
                self.clicks.force_release_left()
                self.shortcuts.force_release_alt()
                self.mouse.reset()

                self.gesture_queue_left.clear()
                self.gesture_queue_right.clear()

                confirmed_left = None
                confirmed_right = None
                self.current_gesture = "SYSTEM LOCKED"
                self.last_gesture = "System Locked"

                self.debug_label.config(text="Left: LOCKED | Right: LOCKED", fg="#ff5a5f")

            else:
                self.shortcuts.update(left_landmarks, right_landmarks)
                self.modes.update_scroll(left_landmarks, right_landmarks)

                if self.shortcuts.alt_held or self.modes.scroll_active:
                    self.clicks.force_release_left()
                else:
                    if result.multi_hand_landmarks and result.multi_handedness:
                        for idx, hlm in enumerate(result.multi_hand_landmarks):
                            handed = result.multi_handedness[idx].classification[0]
                            hand_type = handed.label
                            score = float(handed.score)

                            if score < self.HAND_SCORE_MIN:
                                continue
                            if not self.valid_hand_shape(hlm.landmark):
                                continue

                            for gesture in self.GESTURES:
                                if gesture.detect(hlm.landmark, hand_type):
                                    if hand_type == "Left":
                                        frame_gesture_left = gesture.name
                                    else:
                                        frame_gesture_right = gesture.name
                                        if gesture.name == "PeaceSign":
                                            self.mouse.update(hlm.landmark, hand_type)
                                            self.clicks.update(hlm.landmark)

                if not self.modes.scroll_active and not self.shortcuts.alt_held:
                    self.gesture_queue_left.append(frame_gesture_left)
                    if len(self.gesture_queue_left) > self.GESTURE_FRAMES_REQUIRED:
                        self.gesture_queue_left.pop(0)

                    confirmed_left = None
                    if (
                        len(self.gesture_queue_left) == self.GESTURE_FRAMES_REQUIRED
                        and self.gesture_queue_left.count(self.gesture_queue_left[0]) == len(self.gesture_queue_left)
                        and self.gesture_queue_left[0] is not None
                    ):
                        confirmed_left = self.gesture_queue_left[0]

                    self.gesture_queue_right.append(frame_gesture_right)
                    if len(self.gesture_queue_right) > self.GESTURE_FRAMES_REQUIRED:
                        self.gesture_queue_right.pop(0)

                    confirmed_right = None
                    if (
                        len(self.gesture_queue_right) == self.GESTURE_FRAMES_REQUIRED
                        and self.gesture_queue_right.count(self.gesture_queue_right[0]) == len(self.gesture_queue_right)
                        and self.gesture_queue_right[0] is not None
                    ):
                        confirmed_right = self.gesture_queue_right[0]
                else:
                    confirmed_left = None
                    confirmed_right = None
                    self.gesture_queue_left.clear()
                    self.gesture_queue_right.clear()

                now = time.time()
                if confirmed_right and confirmed_right != "PeaceSign" and (now - self.last_action_time > self.COOLDOWN):
                    trigger_action(confirmed_right, "Right")
                    self.last_action_time = now
                    self.gesture_queue_right = []

                if confirmed_left and (now - self.last_action_time > self.COOLDOWN):
                    trigger_action(confirmed_left, "Left")
                    self.last_action_time = now
                    self.gesture_queue_left = []

                active_gesture = confirmed_left or confirmed_right
                if frame_gesture_right == "PeaceSign":
                    active_gesture = "PeaceSign"

                self.current_gesture = active_gesture
                if active_gesture:
                    self.last_gesture = active_gesture

                self.debug_label.config(
                    text=f"Left: {confirmed_left if confirmed_left else 'None'} | Right: {confirmed_right if confirmed_right else 'None'}",
                    fg=TEXT
                )

            status_parts = ["MOUSE ON" if self.mouse.enabled else "MOUSE OFF"]
            mode_parts = []

            if self.modes.locked:
                status_parts.append("LOCKED")
                mode_parts.append("Locked")
            else:
                mode_parts.append("Active")

            if self.modes.scroll_active:
                status_parts.append("SCROLL")
                mode_parts.append("Scroll")

            if self.mouse.freeze_active():
                status_parts.append("FREEZE")
                mode_parts.append("Freeze")

            if self.clicks.left_is_held:
                status_parts.append("DRAGGING")
                mode_parts.append("Drag")

            if self.shortcuts.alt_held:
                status_parts.append("ALT-HELD")
                mode_parts.append("Alt-Tab")

            if (left_landmarks is not None) and (not self.modes.locked):
                status_parts.append(f"L:{left_score:.2f}")
            if (right_landmarks is not None) and (not self.modes.locked):
                status_parts.append(f"R:{right_score:.2f}")

            self.status_label.config(
                text="Status: " + " | ".join(status_parts),
                fg=SUCCESS if not self.modes.locked else "#ff5a5f"
            )

            self.system_mode_label.config(
                text="Mode: " + (" | ".join(mode_parts) if mode_parts else "Active"),
                fg=TEXT if not self.modes.locked else "#ff5a5f"
            )

            if self.modes.event_visible():
                self.event_label.config(text=f"Event: {self.modes.last_event_text}", fg=TEXT)
            elif self.shortcuts.event_visible():
                self.event_label.config(text=f"Event: {self.shortcuts.last_event_text}", fg=TEXT)
            elif self.clicks.event_visible():
                self.event_label.config(text=f"Event: {self.clicks.last_event_text}", fg=TEXT)
            else:
                self.event_label.config(text="Event: -", fg=SUBTEXT)

        # draw landmarks only if enabled
        render_frame = frame
        if self.SHOW_LANDMARKS and detected_hand_landmarks:
            render_frame = frame.copy()
            for hlm in detected_hand_landmarks:
                self.mp_drawing.draw_landmarks(render_frame, hlm, self.mp_hands.HAND_CONNECTIONS)

        # fit to preview
        box_w = max(self.camera_box.winfo_width() - 2, 640)
        box_h = max(self.camera_box.winfo_height() - 2, 360)

        frame_h, frame_w = render_frame.shape[:2]
        scale = min(box_w / frame_w, box_h / frame_h)
        new_w = int(frame_w * scale)
        new_h = int(frame_h * scale)

        render_frame = cv2.resize(render_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(render_frame, cv2.COLOR_BGR2RGB)

        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)

        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

        if not self.is_ready:
            self.camera_placeholder.config(
                text="Perform activation gesture\nto enable recognition",
                fg="#d0d3d8"
            )
        elif self.modes.locked:
            self.camera_placeholder.config(
                text="SYSTEM LOCKED\nHold open palm to unlock",
                fg="#ff5a5f"
            )
        else:
            self.camera_placeholder.config(text="")

        self.refresh_ui()

        frame_time_ms = (time.time() - frame_start) * 1000.0
        delay = max(1, self.FRAME_DELAY_MS - int(frame_time_ms / 4))
        self.camera_job = self.after(delay, self.update_camera_frame)