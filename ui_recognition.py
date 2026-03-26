import math
import time
import tkinter as tk
from types import SimpleNamespace

import cv2
import mediapipe as mp
import pyautogui
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
from zoom_controller import ZoomController
from volume_controller import VolumeController


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
        self.camera = CameraManager(index=0, width=640, height=360)
        self.camera_running = False
        self.camera_job = None

        self.SHOW_LANDMARKS = False
        self.SHOW_LANDMARK_NUMBERS = False

        self.FRAME_DELAY_MS = 16
        self.MP_WIDTH = 224
        self.MP_HEIGHT = 126
        self.MP_PROCESS_INTERVAL = 1.0 / 18.0
        self._last_mp_time = 0.0
        self._cached_result = None
        self._camera_fail_streak = 0
        self._last_camera_restart = 0.0
        self._camera_restart_cooldown = 2.0
        self._last_box_size = (640, 360)
        self._last_status_snapshot = None
        self._last_ui_frame_time = 0.0
        self._last_loop_alive_time = 0.0
        self._watchdog_job = None

        self.PIP_HOLD_SECONDS = 1.0
        self.PIP_TOGGLE_COOLDOWN = 1.2
        self._left_ok_hold_start = None
        self._last_pip_toggle_time = 0.0
        self.pip_active = False
        self.pip_window = None
        self.pip_border = None
        self.pip_label = None
        self.pip_message = None
        self.PIP_WIDTH = 360
        self.PIP_HEIGHT = 220

        self.MOUSE_LOCK_HOLD_SECONDS = 0.7
        self.MOUSE_LOCK_TOGGLE_COOLDOWN = 1.0
        self._left_pinky_hold_start = None
        self._last_mouse_lock_toggle_time = 0.0
        self.mouse_locked = False

        self.ZOOM_CLICK_FRAMES_REQUIRED = 2
        self.ZOOM_CLICK_COOLDOWN = 0.45
        self._zoom_click_frames = 0
        self._zoom_click_release_frames = 0
        self._zoom_click_armed = True
        self._last_zoom_click_time = 0.0

        # -----------------------------
        # Hand validity filter
        # -----------------------------
        self.HAND_SCORE_MIN = 0.72
        self.PALM_MIN = 0.05
        self.PALM_MAX = 0.60

        # -----------------------------
        # Gesture state
        # -----------------------------
        self.is_ready = False
        self.current_gesture = None
        self.last_gesture = "Waiting for input"

        self.last_action_time = 0.0
        self.COOLDOWN = 1.5
        self.GESTURE_ACTION_GUARD = 0.45
        self._gesture_lock_until = 0.0

        self.GESTURE_FRAMES_REQUIRED = 4
        self.gesture_queue_left = []
        self.gesture_queue_right = []

        self.GESTURES = [SwipeLeft(), SwipeRight(), PeaceSign()]
        self.SCROLL_ENABLED = False  # Temporary: disable pinch scroll until redesigned.

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

        self.zoom = ZoomController(
            distance_delta_threshold=0.022,
            zoom_cooldown=0.030,
            wheel_step=45,
            smooth_alpha=0.78,
            enter_hold_seconds=1.0,
            exit_hold_seconds=1.0,
            toggle_cooldown=1.0,
            zoom_gain=520.0,
            zoom_decay=0.86,
            max_wheel_per_tick=60,
            output_mode="auto",
            title_refresh_seconds=0.5,
            control_requires_open_palms=True,
        )

        self.volume = VolumeController(
            toggle_hold_seconds=1.0,
            toggle_cooldown=1.0,
            volume_step_cooldown=0.10,
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

    def _update_label(self, widget, **kwargs):
        if widget is None:
            return
        current = getattr(widget, "_last_config", {})
        pending = {key: value for key, value in kwargs.items() if current.get(key) != value}
        if pending:
            widget.config(**pending)
            current.update(pending)
            widget._last_config = current

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

    @staticmethod
    def _finger_up(landmarks, tip_idx, pip_idx):
        return landmarks[tip_idx].y < landmarks[pip_idx].y

    @classmethod
    def _finger_down(cls, landmarks, tip_idx, pip_idx):
        return not cls._finger_up(landmarks, tip_idx, pip_idx)

    def _reset_zoom_click_state(self):
        self._zoom_click_frames = 0
        self._zoom_click_release_frames = 0
        self._zoom_click_armed = True

    def _is_left_zoom_click_gesture(self, left_landmarks):
        if left_landmarks is None:
            return False

        index_up = self._finger_up(left_landmarks, 8, 6)
        middle_up = self._finger_up(left_landmarks, 12, 10)
        ring_down = self._finger_down(left_landmarks, 16, 14)
        pinky_down = self._finger_down(left_landmarks, 20, 18)
        return index_up and middle_up and ring_down and pinky_down

    def _handle_zoom_mode_click(self, left_landmarks):
        now = time.time()
        pose_on = self._is_left_zoom_click_gesture(left_landmarks)

        if pose_on:
            self._zoom_click_frames += 1
            self._zoom_click_release_frames = 0
        else:
            self._zoom_click_frames = 0
            self._zoom_click_release_frames += 1
            if self._zoom_click_release_frames >= 1:
                self._zoom_click_armed = True
            return

        if (now - self._last_zoom_click_time) < self.ZOOM_CLICK_COOLDOWN:
            return

        if self._zoom_click_armed and self._zoom_click_frames >= self.ZOOM_CLICK_FRAMES_REQUIRED:
            pyautogui.click(button="left")
            self._zoom_click_armed = False
            self._last_zoom_click_time = now
            self._zoom_click_frames = 0
            self.zoom.set_event("ZOOM MODE LEFT CLICK")

    def _is_left_pinky_only(self, left_landmarks):
        if left_landmarks is None:
            return False

        index_up = self._finger_up(left_landmarks, 8, 6)
        middle_up = self._finger_up(left_landmarks, 12, 10)
        ring_up = self._finger_up(left_landmarks, 16, 14)
        pinky_up = self._finger_up(left_landmarks, 20, 18)
        return pinky_up and (not index_up) and (not middle_up) and (not ring_up)

    def _is_left_ok_sign(self, left_landmarks):
        if left_landmarks is None:
            return False

        thumb_tip = left_landmarks[4]
        index_tip = left_landmarks[8]
        pinch_dist = self._dist(thumb_tip, index_tip)

        middle_up = self._finger_up(left_landmarks, 12, 10)
        ring_up = self._finger_up(left_landmarks, 16, 14)
        pinky_up = self._finger_up(left_landmarks, 20, 18)
        index_folded = self._finger_down(left_landmarks, 8, 6)

        return pinch_dist <= 0.045 and middle_up and ring_up and pinky_up and index_folded

    def _update_mouse_lock(self, left_landmarks):
        now = time.time()
        pinky_only = self._is_left_pinky_only(left_landmarks)
        can_toggle = (now - self._last_mouse_lock_toggle_time) >= self.MOUSE_LOCK_TOGGLE_COOLDOWN

        if pinky_only and can_toggle:
            if self._left_pinky_hold_start is None:
                self._left_pinky_hold_start = now
            elif (now - self._left_pinky_hold_start) >= self.MOUSE_LOCK_HOLD_SECONDS:
                self._left_pinky_hold_start = None
                self._last_mouse_lock_toggle_time = now
                self.mouse_locked = not self.mouse_locked

                if self.mouse_locked:
                    self.mouse.enabled = False
                    self.mouse.reset()
                    self.clicks.force_release_left()
                    self.last_gesture = "Mouse Lock On"
                else:
                    self.mouse.enabled = True
                    self.last_gesture = "Mouse Lock Off"
        else:
            self._left_pinky_hold_start = None

    @staticmethod
    def _resize_to_fit(frame_bgr, target_w, target_h):
        frame_h, frame_w = frame_bgr.shape[:2]
        scale = min(target_w / frame_w, target_h / frame_h)
        new_w = max(1, int(frame_w * scale))
        new_h = max(1, int(frame_h * scale))
        return cv2.resize(frame_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # -----------------------------
    # Camera lifecycle
    # -----------------------------
    def start_camera(self):
        ok = self.camera.start()
        if not ok:
            self.camera_placeholder.config(text="Unable to access camera")
            return

        self.camera_running = True
        self._camera_fail_streak = 0
        self._last_ui_frame_time = time.time()
        self._last_loop_alive_time = time.time()
        if self._watchdog_job is None:
            self._watchdog_job = self.after(350, self.camera_watchdog)
        self.update_camera_frame()

    def stop_camera(self):
        self.camera_running = False
        try:
            self.zoom.force_release_ctrl()
        except Exception:
            pass
        if self.camera_job is not None:
            try:
                self.after_cancel(self.camera_job)
            except Exception:
                pass
            self.camera_job = None
        if self._watchdog_job is not None:
            try:
                self.after_cancel(self._watchdog_job)
            except Exception:
                pass
            self._watchdog_job = None
        self.camera.release()
        self._destroy_pip_window()

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
            self.mouse_locked = False
            self.mouse.enabled = True
            self.zoom.reset_all()
            self._reset_zoom_click_state()
            self.volume.reset_all()

        self.refresh_ui()

    def refresh_ui(self):
        if self.is_ready:
            self._update_label(self.ready_btn,
                text="System Ready",
                bg="#ffffff",
                fg="#000000",
                activebackground="#ffffff",
                activeforeground="#000000",
            )
            self._update_label(self.gesture_scan_label,
                text=f"Current Gesture: {self.current_gesture or 'Scanning...'}",
                fg=TEXT
            )
        else:
            self._update_label(self.ready_btn,
                text="Standby Mode",
                bg=CARD_SOFT,
                fg=SUBTEXT,
                activebackground=CARD_SOFT,
                activeforeground=SUBTEXT,
            )
            self._update_label(self.gesture_scan_label,
                text="Current Gesture: Scanning...",
                fg=SUBTEXT
            )

        self._update_label(self.last_gesture_label, text=self.last_gesture)

    def _restart_camera_if_needed(self):
        now = time.time()
        if (now - self._last_camera_restart) < self._camera_restart_cooldown:
            return

        self._last_camera_restart = now
        self.camera.release()
        if self.camera.start():
            self._camera_fail_streak = 0
            self._cached_result = None
            self._last_mp_time = 0.0
            self._last_ui_frame_time = time.time()
            self._last_loop_alive_time = time.time()

    def _destroy_pip_window(self):
        self.pip_active = False
        if self.pip_window is not None:
            try:
                self.pip_window.destroy()
            except Exception:
                pass
        self.pip_window = None
        self.pip_border = None
        self.pip_label = None
        self.pip_message = None

    def _set_pip_active(self, active):
        if active == self.pip_active and (
            (not active) or (self.pip_window is not None and self.pip_window.winfo_exists())
        ):
            if active:
                self._position_pip_window()
                self._update_pip_state()
            return

        self.pip_active = active
        self._last_pip_toggle_time = time.time()

        if not active:
            self._destroy_pip_window()
            return

        if self.pip_window is None or not self.pip_window.winfo_exists():
            pip = tk.Toplevel(self)
            pip.overrideredirect(True)
            pip.attributes("-topmost", True)
            pip.configure(bg="#ffffff")

            border = tk.Frame(
                pip,
                bg="#ffffff",
                highlightthickness=3,
                highlightbackground="#ffffff",
                bd=0,
            )
            border.pack(fill="both", expand=True)

            label = tk.Label(border, bg=DARK, bd=0)
            label.pack(fill="both", expand=True)

            message = make_label(
                border,
                "Recognition Active",
                size=10,
                weight="bold",
                fg="#ffffff",
                bg=DARK,
                padx=10,
                pady=6,
            )
            message.place(relx=0.03, rely=0.05, anchor="nw")

            self.pip_window = pip
            self.pip_border = border
            self.pip_label = label
            self.pip_message = message

        self._position_pip_window()
        self._update_pip_state()

    def _position_pip_window(self):
        if self.pip_window is None or not self.pip_window.winfo_exists():
            return

        pad = 18
        x = max(0, self.winfo_screenwidth() - self.PIP_WIDTH - pad)
        y = pad + 8
        try:
            # Re-assert topmost every update; some apps can steal z-order.
            self.pip_window.attributes("-topmost", True)
            self.pip_window.lift()
        except Exception:
            pass
        self.pip_window.geometry(f"{self.PIP_WIDTH}x{self.PIP_HEIGHT}+{x}+{y}")

    def _update_pip_state(self):
        if self.pip_window is None or not self.pip_window.winfo_exists():
            return

        if self.modes.locked:
            border_color = "#ff3b30"
            message_text = "Recognition Paused"
            message_bg = "#2a0e0e"
        elif self.volume.active:
            border_color = "#42c778"
            message_text = "Volume Mode"
            message_bg = "#10281b"
        elif self.zoom.active:
            border_color = "#2f9cff"
            message_text = "Zoom Mode"
            message_bg = "#0c2036"
        elif self.mouse_locked:
            border_color = "#ff9f0a"
            message_text = "Mouse Locked"
            message_bg = "#2d1f08"
        else:
            border_color = "#ffffff"
            message_text = "Recognition Active"
            message_bg = DARK

        self._update_label(self.pip_border, bg=border_color, highlightbackground=border_color)
        self._update_label(self.pip_message, text=message_text, bg=message_bg, fg="#ffffff")

    def _update_left_ok_pip(self, left_landmarks):
        now = time.time()
        left_ok_detected = self._is_left_ok_sign(left_landmarks)
        can_toggle = (now - self._last_pip_toggle_time) >= self.PIP_TOGGLE_COOLDOWN

        if left_ok_detected and can_toggle:
            if self._left_ok_hold_start is None:
                self._left_ok_hold_start = now
            elif (now - self._left_ok_hold_start) >= self.PIP_HOLD_SECONDS:
                self._left_ok_hold_start = None
                self._set_pip_active(not self.pip_active)
                self.last_gesture = "PiP On" if self.pip_active else "PiP Off"
        else:
            self._left_ok_hold_start = None

    def camera_watchdog(self):
        self._watchdog_job = None
        if not self.camera_running:
            return

        now = time.time()
        stale_loop = (now - self._last_loop_alive_time) > 0.9
        stale_frame = (now - self._last_ui_frame_time) > 1.2

        if stale_loop or stale_frame:
            self._restart_camera_if_needed()
            if self.camera_job is None:
                self.update_camera_frame()

        self._watchdog_job = self.after(350, self.camera_watchdog)

    def _process_hands(self, frame):
        now = time.time()
        if self._cached_result is not None and (now - self._last_mp_time) < self.MP_PROCESS_INTERVAL:
            return self._cached_result

        small = cv2.resize(frame, (self.MP_WIDTH, self.MP_HEIGHT), interpolation=cv2.INTER_AREA)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        self._cached_result = self.hands.process(rgb_small)
        self._last_mp_time = now
        return self._cached_result

    def _collect_hand_data(self, result):
        hand_data = []

        if not (result and result.multi_hand_landmarks and result.multi_handedness):
            return hand_data

        for idx, hlm in enumerate(result.multi_hand_landmarks):
            handed = result.multi_handedness[idx].classification[0]
            score = float(handed.score)
            if score < self.HAND_SCORE_MIN:
                continue
            if not self.valid_hand_shape(hlm.landmark):
                continue

            hand_data.append(
                SimpleNamespace(
                    landmarks=hlm.landmark,
                    hand_type=handed.label,
                    score=score,
                    hand_landmarks=hlm,
                )
            )

        return hand_data

    def _update_status_panel(self, *, debug_text, debug_fg, status_text, status_fg, mode_text, mode_fg, event_text, event_fg):
        snapshot = (debug_text, debug_fg, status_text, status_fg, mode_text, mode_fg, event_text, event_fg)
        if snapshot == self._last_status_snapshot:
            return

        self._last_status_snapshot = snapshot
        self._update_label(self.debug_label, text=debug_text, fg=debug_fg)
        self._update_label(self.status_label, text=status_text, fg=status_fg)
        self._update_label(self.system_mode_label, text=mode_text, fg=mode_fg)
        self._update_label(self.event_label, text=event_text, fg=event_fg)

    def _fit_preview_size(self):
        current = (self.camera_box.winfo_width(), self.camera_box.winfo_height())
        if current[0] > 0 and current[1] > 0:
            self._last_box_size = current

        box_w = max(self._last_box_size[0] - 2, 640)
        box_h = max(self._last_box_size[1] - 2, 360)
        return box_w, box_h

    # -----------------------------
    # Main camera + recognition loop
    # -----------------------------
    def update_camera_frame(self):
        if not self.camera_running:
            return
        frame_start = time.time()
        delay = self.FRAME_DELAY_MS
        self._last_loop_alive_time = frame_start

        try:
            ok, frame = self.camera.read()
            if not ok or frame is None:
                self._camera_fail_streak += 1
                if self._camera_fail_streak >= 12:
                    self._restart_camera_if_needed()
                return
            self._camera_fail_streak = 0

            frame = cv2.flip(frame, 1)
            result = self._process_hands(frame)
            hand_data = self._collect_hand_data(result)

            frame_gesture_left = None
            frame_gesture_right = None

            left_landmarks = None
            right_landmarks = None
            left_score = 0.0
            right_score = 0.0

            detected_hand_landmarks = [item.hand_landmarks for item in hand_data]

            for item in hand_data:
                if item.hand_type == "Left":
                    left_landmarks = item.landmarks
                    left_score = item.score
                else:
                    right_landmarks = item.landmarks
                    right_score = item.score

            self.volume.update_mode_toggle(right_landmarks, enabled=self.is_ready)
            if not self.volume.active:
                self._update_left_ok_pip(left_landmarks)
            else:
                self._left_ok_hold_start = None
            if self.is_ready:
                if not self.volume.active:
                    self._update_mouse_lock(left_landmarks)
                else:
                    self._left_pinky_hold_start = None
                self.mouse.enabled = (not self.mouse_locked) and (not self.volume.active)
            else:
                self._left_pinky_hold_start = None
                self._left_ok_hold_start = None
                self.volume.reset_all()

            if not self.is_ready:
                self.current_gesture = None
                self.zoom.reset_all()
                self._update_status_panel(
                    debug_text="Left: None | Right: None",
                    debug_fg=SUBTEXT,
                    status_text="Status: STANDBY",
                    status_fg=SUBTEXT,
                    mode_text="Mode: Standby",
                    mode_fg=SUBTEXT,
                    event_text="Event: Waiting for activation",
                    event_fg=SUBTEXT,
                )
            else:
                if (not self.volume.active) or self.modes.locked:
                    self.modes.update_lock(left_landmarks, right_landmarks)

                if self.modes.locked:
                    self.clicks.force_release_left()
                    self.shortcuts.force_release_alt()
                    self.mouse.reset()
                    self.zoom.reset_all()
                    self._reset_zoom_click_state()
                    self.volume.update_control(None, None, enabled=False)

                    self.gesture_queue_left.clear()
                    self.gesture_queue_right.clear()

                    confirmed_left = None
                    confirmed_right = None
                    self.current_gesture = "SYSTEM LOCKED"
                    self.last_gesture = "System Locked"
                    debug_text = "Left: LOCKED | Right: LOCKED"
                else:
                    if self.volume.active:
                        self.shortcuts.force_release_alt()
                        self.clicks.force_release_left()
                        self.mouse.reset()
                        self.zoom.reset_all()
                        self._reset_zoom_click_state()
                        self.modes.update_scroll(None, None)
                        self.volume.update_control(left_landmarks, right_landmarks, enabled=True)
                    else:
                        self.volume.update_control(None, None, enabled=False)
                        self.zoom.update(
                            left_landmarks,
                            right_landmarks,
                            enabled=(not self.modes.scroll_active and not self.shortcuts.alt_held),
                        )
                        if self.zoom.active:
                            self.shortcuts.force_release_alt()
                            self.clicks.force_release_left()
                            self.mouse.reset()
                            self.modes.update_scroll(None, None)
                            self._handle_zoom_mode_click(left_landmarks)
                        else:
                            self._reset_zoom_click_state()
                            self.shortcuts.update(left_landmarks, right_landmarks)
                            if self.SCROLL_ENABLED:
                                self.modes.update_scroll(left_landmarks, right_landmarks)
                            else:
                                self.modes.update_scroll(None, None)

                    if self.shortcuts.alt_held or self.modes.scroll_active or self.zoom.active:
                        self.clicks.force_release_left()
                    else:
                        gesture_guard_active = time.time() < self._gesture_lock_until
                        for item in hand_data:
                            matched = []
                            for gesture in self.GESTURES:
                                if gesture.detect(item.landmarks, item.hand_type):
                                    matched.append(gesture.name)

                            # Ambiguous frame (multiple gestures) is ignored to prevent cross-triggering.
                            detected_name = matched[0] if len(matched) == 1 else None

                            if item.hand_type == "Left":
                                frame_gesture_left = detected_name
                            else:
                                frame_gesture_right = detected_name
                                if (not gesture_guard_active) and detected_name == "PeaceSign" and (not self.mouse_locked):
                                    self.mouse.update(item.landmarks, item.hand_type)
                                    self.clicks.update(item.landmarks)
                                elif self.mouse_locked:
                                    self.clicks.force_release_left()

                    if not self.modes.scroll_active and not self.shortcuts.alt_held and not self.zoom.active:
                        if time.time() < self._gesture_lock_until:
                            confirmed_left = None
                            confirmed_right = None
                            self.gesture_queue_left.clear()
                            self.gesture_queue_right.clear()
                        else:
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
                        self._gesture_lock_until = now + self.GESTURE_ACTION_GUARD
                        self.gesture_queue_right = []

                    if confirmed_left and (now - self.last_action_time > self.COOLDOWN):
                        trigger_action(confirmed_left, "Left")
                        self.last_action_time = now
                        self._gesture_lock_until = now + self.GESTURE_ACTION_GUARD
                        self.gesture_queue_left = []

                    active_gesture = confirmed_left or confirmed_right
                    if frame_gesture_right == "PeaceSign":
                        active_gesture = "PeaceSign"

                    self.current_gesture = active_gesture
                    if active_gesture:
                        self.last_gesture = active_gesture

                    debug_text = f"Left: {confirmed_left if confirmed_left else 'None'} | Right: {confirmed_right if confirmed_right else 'None'}"

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

                if self.pip_active:
                    status_parts.append("PIP")
                    mode_parts.append("PiP")
                if self.mouse_locked:
                    status_parts.append("MOUSE-LOCK")
                    mode_parts.append("MouseLock")
                if self.volume.active:
                    status_parts.append("VOLUME-MODE")
                    mode_parts.append("Volume")
                if self.zoom.active:
                    status_parts.append("ZOOM-MODE")
                    mode_parts.append("Zoom")

                if (left_landmarks is not None) and (not self.modes.locked):
                    status_parts.append(f"L:{left_score:.2f}")
                if (right_landmarks is not None) and (not self.modes.locked):
                    status_parts.append(f"R:{right_score:.2f}")

                if self.modes.event_visible():
                    event_text = f"Event: {self.modes.last_event_text}"
                    event_fg = TEXT
                elif self.shortcuts.event_visible():
                    event_text = f"Event: {self.shortcuts.last_event_text}"
                    event_fg = TEXT
                elif self.clicks.event_visible():
                    event_text = f"Event: {self.clicks.last_event_text}"
                    event_fg = TEXT
                elif self.zoom.event_visible():
                    event_text = f"Event: {self.zoom.last_event_text}"
                    event_fg = TEXT
                elif self.volume.event_visible():
                    event_text = f"Event: {self.volume.last_event_text}"
                    event_fg = TEXT
                else:
                    event_text = "Event: -"
                    event_fg = SUBTEXT

                self._update_status_panel(
                    debug_text=debug_text,
                    debug_fg=TEXT if not self.modes.locked else "#ff5a5f",
                    status_text="Status: " + " | ".join(status_parts),
                    status_fg=SUCCESS if not self.modes.locked else "#ff5a5f",
                    mode_text="Mode: " + (" | ".join(mode_parts) if mode_parts else "Active"),
                    mode_fg=TEXT if not self.modes.locked else "#ff5a5f",
                    event_text=event_text,
                    event_fg=event_fg,
                )

            render_frame = frame
            if self.SHOW_LANDMARKS and detected_hand_landmarks:
                render_frame = frame.copy()
                for hlm in detected_hand_landmarks:
                    self.mp_drawing.draw_landmarks(render_frame, hlm, self.mp_hands.HAND_CONNECTIONS)

            box_w, box_h = self._fit_preview_size()
            main_bgr = self._resize_to_fit(render_frame, box_w, box_h)
            main_rgb = cv2.cvtColor(main_bgr, cv2.COLOR_BGR2RGB)
            main_imgtk = ImageTk.PhotoImage(image=Image.fromarray(main_rgb))

            if self.pip_active:
                self._position_pip_window()
                pip_bgr = self._resize_to_fit(render_frame, self.PIP_WIDTH, self.PIP_HEIGHT)
                pip_rgb = cv2.cvtColor(pip_bgr, cv2.COLOR_BGR2RGB)
                pip_imgtk = ImageTk.PhotoImage(image=Image.fromarray(pip_rgb))
                self.pip_label.imgtk = pip_imgtk
                self.pip_label.configure(image=pip_imgtk)
                self.video_label.imgtk = None
                self.video_label.configure(image="")
                self._update_label(
                    self.camera_placeholder,
                    text="Camera moved to PiP\nHold LEFT OK sign for 1s to return",
                    fg="#d0d3d8",
                )
            elif not self.is_ready:
                self.video_label.imgtk = main_imgtk
                self.video_label.configure(image=main_imgtk)
                self._update_label(
                    self.camera_placeholder,
                    text="Perform activation gesture\nto enable recognition",
                    fg="#d0d3d8",
                )
            elif self.modes.locked:
                self.video_label.imgtk = main_imgtk
                self.video_label.configure(image=main_imgtk)
                self._update_label(
                    self.camera_placeholder,
                    text="SYSTEM LOCKED\nHold RIGHT pinky-only to unlock",
                    fg="#ff5a5f",
                )
            elif self.volume.active:
                self.video_label.imgtk = main_imgtk
                self.video_label.configure(image=main_imgtk)
                self._update_label(
                    self.camera_placeholder,
                    text="VOLUME MODE ACTIVE\nLeft index-only=UP | Left thumb-only=DOWN\nRight open palm holds level",
                    fg="#66d69a",
                )
            elif self.zoom.active:
                self.video_label.imgtk = main_imgtk
                self.video_label.configure(image=main_imgtk)
                self._update_label(
                    self.camera_placeholder,
                    text="ZOOM MODE ACTIVE\nSpread in/out (auto app zoom profile)",
                    fg="#76beff",
                )
            elif self.mouse_locked:
                self.video_label.imgtk = main_imgtk
                self.video_label.configure(image=main_imgtk)
                self._update_label(
                    self.camera_placeholder,
                    text="MOUSE LOCKED\nHold LEFT pinky-only to unlock",
                    fg="#ffb14a",
                )
            else:
                self.video_label.imgtk = main_imgtk
                self.video_label.configure(image=main_imgtk)
                self._update_label(self.camera_placeholder, text="")

            self._update_pip_state()
            self.refresh_ui()
            self._last_ui_frame_time = time.time()
            frame_time_ms = (self._last_ui_frame_time - frame_start) * 1000.0
            delay = max(1, self.FRAME_DELAY_MS - int(frame_time_ms / 2.5))
        except Exception as exc:
            print(f"[CAMERA LOOP] {exc}")
            self._camera_fail_streak += 1
            if self._camera_fail_streak >= 6:
                self._restart_camera_if_needed()
            delay = max(50, self.FRAME_DELAY_MS)
        finally:
            self._last_loop_alive_time = time.time()
            self.camera_job = self.after(delay, self.update_camera_frame)
