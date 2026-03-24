import math
import time

import pyautogui

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False


class ZoomController:
    """
    Two-hand zoom mode using Ctrl + mouse wheel.

    - Enter mode: both palms open for enter_hold_seconds
    - Exit mode : both fists for exit_hold_seconds
    - In mode   : spread out = zoom in, move in = zoom out
    """

    def __init__(
        self,
        distance_delta_threshold: float = 0.028,
        zoom_cooldown: float = 0.10,
        wheel_step: int = 120,
        smooth_alpha: float = 0.45,
        enter_hold_seconds: float = 1.5,
        exit_hold_seconds: float = 1.5,
        toggle_cooldown: float = 1.0,
    ):
        self.distance_delta_threshold = float(distance_delta_threshold)
        self.zoom_cooldown = float(zoom_cooldown)
        self.wheel_step = int(wheel_step)
        self.smooth_alpha = float(smooth_alpha)

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

    def reset_all(self):
        self.active = False
        self._enter_hold_start = None
        self._exit_hold_start = None
        self.reset_zoom_vector()

    def update(self, left_landmarks, right_landmarks, enabled=True):
        now = time.time()

        if not enabled or left_landmarks is None or right_landmarks is None:
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
                    self.reset_zoom_vector()
                    self.set_event("ZOOM MODE OFF")
                    return
            else:
                self._exit_hold_start = None

        if not self.active:
            return

        left_ref = left_landmarks[9]
        right_ref = right_landmarks[9]
        distance = self._dist(left_ref, right_ref)

        if self._last_distance is None:
            self._last_distance = distance
            return

        raw_delta = distance - self._last_distance
        self._smoothed_delta = (
            (self.smooth_alpha * self._smoothed_delta)
            + ((1.0 - self.smooth_alpha) * raw_delta)
        )
        self._last_distance = distance

        if (now - self._last_zoom_time) < self.zoom_cooldown:
            return

        if self._smoothed_delta > self.distance_delta_threshold:
            self._zoom(+self.wheel_step)
            self._last_zoom_time = now
            self.set_event("ZOOM IN")
            self._smoothed_delta = 0.0
        elif self._smoothed_delta < -self.distance_delta_threshold:
            self._zoom(-self.wheel_step)
            self._last_zoom_time = now
            self.set_event("ZOOM OUT")
            self._smoothed_delta = 0.0

    @staticmethod
    def _zoom(wheel_amount):
        try:
            pyautogui.keyDown("ctrl")
            pyautogui.scroll(wheel_amount)
        finally:
            pyautogui.keyUp("ctrl")
