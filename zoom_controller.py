import math
import time
import ctypes

import pyautogui

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False
KEYEVENTF_KEYUP = 0x0002
VK_ADD = 0x6B
VK_SUBTRACT = 0x6D


class ZoomController:
    """
    Two-hand zoom mode with smooth continuous output.

    - Enter mode: both palms open for enter_hold_seconds
    - Exit mode : both fists for exit_hold_seconds
    - In mode   : spread out = zoom in, move in = zoom out
    """

    def __init__(
        self,
        distance_delta_threshold: float = 0.022,
        zoom_cooldown: float = 0.030,
        wheel_step: int = 45,
        smooth_alpha: float = 0.78,
        enter_hold_seconds: float = 1.0,
        exit_hold_seconds: float = 1.0,
        toggle_cooldown: float = 1.0,
        zoom_gain: float = 520.0,
        zoom_decay: float = 0.86,
        max_wheel_per_tick: int = 60,
        output_mode: str = "auto",
        title_refresh_seconds: float = 0.5,
        control_requires_open_palms: bool = True,
        min_zoom_level: int = 100,
        max_zoom_level: int = 260,
        zoom_level_step_up: int = 2,
        zoom_level_step_down: int = 1,
        ppt_min_zoom_level: int = 90,
        ppt_max_zoom_level: int = 220,
        ppt_zoom_in_step: int = 2,
        ppt_zoom_out_step: int = 1,
        ppt_zoom_out_hold_seconds: float = 0.30,
    ):
        self.distance_delta_threshold = float(distance_delta_threshold)
        self.zoom_cooldown = float(zoom_cooldown)
        self.wheel_step = int(wheel_step)
        self.smooth_alpha = float(smooth_alpha)
        self.zoom_gain = float(zoom_gain)
        self.zoom_decay = float(zoom_decay)
        self.max_wheel_per_tick = int(max_wheel_per_tick)
        self.output_mode = output_mode
        self.title_refresh_seconds = float(title_refresh_seconds)
        self.control_requires_open_palms = bool(control_requires_open_palms)
        self.min_zoom_level = int(min_zoom_level)
        self.max_zoom_level = int(max_zoom_level)
        self.zoom_level_step_up = int(zoom_level_step_up)
        self.zoom_level_step_down = int(zoom_level_step_down)
        self.ppt_min_zoom_level = int(ppt_min_zoom_level)
        self.ppt_max_zoom_level = int(ppt_max_zoom_level)
        self.ppt_zoom_in_step = int(ppt_zoom_in_step)
        self.ppt_zoom_out_step = int(ppt_zoom_out_step)
        self.ppt_zoom_out_hold_seconds = float(ppt_zoom_out_hold_seconds)

        self.enter_hold_seconds = float(enter_hold_seconds)
        self.exit_hold_seconds = float(exit_hold_seconds)
        self.toggle_cooldown = float(toggle_cooldown)

        self.active = False

        self._enter_hold_start = None
        self._exit_hold_start = None
        self._last_toggle_time = 0.0

        self._last_distance = None
        self._smoothed_delta = 0.0
        self._last_zoom_time = 0.0
        self._zoom_velocity = 0.0
        self._cached_window_title = ""
        self._last_title_time = 0.0
        self._ppt_virtual_zoom_level = 100
        self._ppt_zoom_out_hold_start = None
        self._ppt_guard_active = False
        self._ctrl_held = False
        self._virtual_zoom_level = self.min_zoom_level

        self.last_event_text = "Ready"
        self.last_event_time = 0.0
        self.event_show_seconds = 1.0

    def set_event(self, text: str):
        self.last_event_text = text
        self.last_event_time = time.time()

    def event_visible(self) -> bool:
        return (time.time() - self.last_event_time) <= self.event_show_seconds

    @staticmethod
    def _dist(a, b) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    @staticmethod
    def _finger_up(landmarks, tip_idx, pip_idx):
        return landmarks[tip_idx].y < landmarks[pip_idx].y

    def _is_open_palm(self, landmarks):
        index_up = self._finger_up(landmarks, 8, 6)
        middle_up = self._finger_up(landmarks, 12, 10)
        ring_up = self._finger_up(landmarks, 16, 14)
        pinky_up = self._finger_up(landmarks, 20, 18)
        return index_up and middle_up and ring_up and pinky_up

    def _is_fist(self, landmarks):
        index_down = not self._finger_up(landmarks, 8, 6)
        middle_down = not self._finger_up(landmarks, 12, 10)
        ring_down = not self._finger_up(landmarks, 16, 14)
        pinky_down = not self._finger_up(landmarks, 20, 18)
        return index_down and middle_down and ring_down and pinky_down

    def reset_zoom_vector(self):
        self._last_distance = None
        self._smoothed_delta = 0.0
        self._zoom_velocity = 0.0
        self._ppt_zoom_out_hold_start = None

    def reset_all(self):
        self.active = False
        self._enter_hold_start = None
        self._exit_hold_start = None
        self._ppt_guard_active = False
        self.force_release_ctrl()
        self._virtual_zoom_level = self.min_zoom_level
        self.reset_zoom_vector()

    def _hold_ctrl(self):
        if self._ctrl_held:
            return
        try:
            pyautogui.keyDown("ctrl")
            self._ctrl_held = True
        except Exception:
            self._ctrl_held = False

    def force_release_ctrl(self):
        if not self._ctrl_held:
            return
        try:
            pyautogui.keyUp("ctrl")
        except Exception:
            pass
        self._ctrl_held = False

    def update(self, left_landmarks, right_landmarks, enabled=True):
        now = time.time()

        if not enabled:
            self.force_release_ctrl()
            self._enter_hold_start = None
            self._exit_hold_start = None
            self.reset_zoom_vector()
            return

        if left_landmarks is None or right_landmarks is None:
            self._enter_hold_start = None
            self._exit_hold_start = None
            self.reset_zoom_vector()
            return

        can_toggle = (now - self._last_toggle_time) >= self.toggle_cooldown
        both_open_palms = self._is_open_palm(left_landmarks) and self._is_open_palm(right_landmarks)
        both_fists = self._is_fist(left_landmarks) and self._is_fist(right_landmarks)

        if not self.active and can_toggle:
            if both_open_palms:
                if self._enter_hold_start is None:
                    self._enter_hold_start = now
                elif (now - self._enter_hold_start) >= self.enter_hold_seconds:
                    self.active = True
                    self._last_toggle_time = now
                    self._enter_hold_start = None
                    self._virtual_zoom_level = self.min_zoom_level
                    self.reset_zoom_vector()
                    self.set_event("ZOOM MODE ON")
                    return
            else:
                self._enter_hold_start = None

        if self.active and can_toggle:
            if both_fists:
                if self._exit_hold_start is None:
                    self._exit_hold_start = now
                elif (now - self._exit_hold_start) >= self.exit_hold_seconds:
                    self.active = False
                    self._last_toggle_time = now
                    self._exit_hold_start = None
                    self.force_release_ctrl()
                    self.reset_zoom_vector()
                    self.set_event("ZOOM MODE OFF")
                    return
            else:
                self._exit_hold_start = None

        if not self.active:
            self.force_release_ctrl()
            return

        # In zoom mode, only allow zooming while both hands are open palms.
        if self.control_requires_open_palms and (not both_open_palms):
            self.reset_zoom_vector()
            return

        # While zoom mode is active, keep Ctrl held.
        self._hold_ctrl()

        left_ref = left_landmarks[9]
        right_ref = right_landmarks[9]
        distance = self._dist(left_ref, right_ref)

        left_width = self._dist(left_landmarks[5], left_landmarks[17])
        right_width = self._dist(right_landmarks[5], right_landmarks[17])
        hand_scale = max(0.001, (left_width + right_width) * 0.5)
        normalized_distance = distance / hand_scale

        if self._last_distance is None:
            self._last_distance = normalized_distance
            return

        raw_delta = normalized_distance - self._last_distance
        self._smoothed_delta = (
            (self.smooth_alpha * self._smoothed_delta)
            + ((1.0 - self.smooth_alpha) * raw_delta)
        )
        self._last_distance = normalized_distance

        if (now - self._last_zoom_time) < self.zoom_cooldown:
            return

        abs_delta = abs(self._smoothed_delta)
        if abs_delta >= self.distance_delta_threshold:
            # Convert stable hand motion into continuous zoom velocity.
            self._zoom_velocity = (
                (self.zoom_decay * self._zoom_velocity)
                + ((1.0 - self.zoom_decay) * self._smoothed_delta * self.zoom_gain)
            )

            wheel_amount = int(
                max(-self.max_wheel_per_tick, min(self.max_wheel_per_tick, self._zoom_velocity))
            )
            if wheel_amount != 0:
                applied = self._zoom(wheel_amount)
                self._last_zoom_time = now
                if applied > 0:
                    self.set_event("ZOOM IN")
                elif applied < 0:
                    self.set_event("ZOOM OUT")
                else:
                    self.set_event("ZOOM FLOOR 100%")
        else:
            self._zoom_velocity *= self.zoom_decay

    def _active_window_title(self) -> str:
        now = time.time()
        if (now - self._last_title_time) < self.title_refresh_seconds:
            return self._cached_window_title

        self._last_title_time = now
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd == 0:
                self._cached_window_title = ""
                return self._cached_window_title

            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                self._cached_window_title = ""
                return self._cached_window_title

            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            self._cached_window_title = (buffer.value or "").lower()
        except Exception:
            self._cached_window_title = ""

        return self._cached_window_title

    def _should_use_plain_scroll(self) -> bool:
        if self.output_mode == "scroll":
            return True
        if self.output_mode == "ctrl":
            return False

        # Auto profile: use plain scroll for image-centric viewers.
        title = self._active_window_title()
        image_keywords = (
            "photos",
            "photo",
            "image",
            "picture",
            "gallery",
            "viewer",
            "preview",
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".bmp",
            ".gif",
        )
        return any(word in title for word in image_keywords)

    def _is_powerpoint_slideshow(self) -> bool:
        title = self._active_window_title()
        return ("powerpoint" in title) and ("slide show" in title)

    @staticmethod
    def _tap_vk(vk_code: int):
        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(vk_code, 0, 0, 0)
            user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

    def _tap_zoom_key(self, zoom_in: bool):
        # Prefer numpad +/- virtual keys; fall back to pyautogui key names.
        vk = VK_ADD if zoom_in else VK_SUBTRACT
        try:
            self._tap_vk(vk)
            return
        except Exception:
            pass
        try:
            pyautogui.press("add" if zoom_in else "subtract")
        except Exception:
            pass

    def _powerpoint_zoom_by_key(self, wheel_amount: int):
        now = time.time()
        zooming_in = wheel_amount > 0
        magnitude = abs(wheel_amount)

        # Hard floor/ceiling for slideshow safety.
        if zooming_in:
            if self._ppt_virtual_zoom_level >= self.ppt_max_zoom_level:
                self._ppt_zoom_out_hold_start = None
                self.set_event("PPT MAX ZOOM")
                return
        else:
            if self._ppt_virtual_zoom_level <= self.ppt_min_zoom_level:
                self._ppt_zoom_out_hold_start = None
                self.set_event("PPT MIN ZOOM")
                return
            # Make zoom-out stricter and require a short hold to avoid accidental exits.
            if magnitude < 32:
                self._ppt_zoom_out_hold_start = None
                return
            if self._ppt_zoom_out_hold_start is None:
                self._ppt_zoom_out_hold_start = now
                return
            if (now - self._ppt_zoom_out_hold_start) < self.ppt_zoom_out_hold_seconds:
                return

        self._ppt_zoom_out_hold_start = None

        # Apply smaller, asymmetric steps (in > out) for safety.
        step = self.ppt_zoom_in_step if zooming_in else self.ppt_zoom_out_step
        target = self._ppt_virtual_zoom_level + (step if zooming_in else -step)
        target = max(self.ppt_min_zoom_level, min(self.ppt_max_zoom_level, target))
        if target == self._ppt_virtual_zoom_level:
            return

        taps = max(1, abs(target - self._ppt_virtual_zoom_level))
        for _ in range(taps):
            self._tap_zoom_key(zooming_in)
        self._ppt_virtual_zoom_level = target

    def _zoom(self, wheel_amount):
        if wheel_amount == 0:
            return 0

        # Hard safety for PowerPoint Slide Show:
        # block gesture-driven zoom-out entirely to prevent accidental slideshow exits.
        if self._is_powerpoint_slideshow() and wheel_amount < 0:
            self._zoom_velocity = 0.0
            self._smoothed_delta = 0.0
            return 0

        self._ppt_guard_active = False
        self._ppt_zoom_out_hold_start = None
        self._ppt_virtual_zoom_level = 100

        zooming_in = wheel_amount > 0
        if zooming_in:
            if self._virtual_zoom_level >= self.max_zoom_level:
                return 0
            self._virtual_zoom_level = min(
                self.max_zoom_level,
                self._virtual_zoom_level + self.zoom_level_step_up,
            )
        else:
            if self._virtual_zoom_level <= self.min_zoom_level:
                return 0
            self._virtual_zoom_level = max(
                self.min_zoom_level,
                self._virtual_zoom_level - self.zoom_level_step_down,
            )

        # Ctrl is intentionally held for entire zoom mode in this profile.
        pyautogui.scroll(wheel_amount)
        return 1 if zooming_in else -1
