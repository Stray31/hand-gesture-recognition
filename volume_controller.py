import math
import time

from actions import volume_step


class VolumeController:
    """
    Volume mode controller.

    - Toggle mode with right hand index+pinky hold.
    - In mode, only volume gestures should be processed by the caller.
    - Left hand index-only (all others down) -> volume up.
    - Left hand thumb-only (all others down) -> volume down.
    - Right hand open palm pauses volume changes while visible.
    """

    def __init__(
        self,
        toggle_hold_seconds: float = 1.0,
        toggle_cooldown: float = 1.0,
        volume_step_cooldown: float = 0.10,
    ):
        self.toggle_hold_seconds = float(toggle_hold_seconds)
        self.toggle_cooldown = float(toggle_cooldown)
        self.volume_step_cooldown = float(volume_step_cooldown)

        self.active = False
        self._toggle_hold_start = None
        self._last_toggle_time = 0.0

        self._last_volume_step_time = 0.0

        self.last_event_text = "Ready"
        self.last_event_time = 0.0
        self.event_show_seconds = 1.0

    def set_event(self, text: str):
        self.last_event_text = text
        self.last_event_time = time.time()

    def event_visible(self) -> bool:
        return (time.time() - self.last_event_time) <= self.event_show_seconds

    @staticmethod
    def _finger_up(landmarks, tip_idx, pip_idx):
        return landmarks[tip_idx].y < landmarks[pip_idx].y

    @classmethod
    def _finger_down(cls, landmarks, tip_idx, pip_idx):
        return not cls._finger_up(landmarks, tip_idx, pip_idx)

    @staticmethod
    def _dist(a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

    def _is_open_palm(self, landmarks):
        index_up = self._finger_up(landmarks, 8, 6)
        middle_up = self._finger_up(landmarks, 12, 10)
        ring_up = self._finger_up(landmarks, 16, 14)
        pinky_up = self._finger_up(landmarks, 20, 18)
        return index_up and middle_up and ring_up and pinky_up

    def _is_right_index_pinky_only(self, right_landmarks):
        index_up = self._finger_up(right_landmarks, 8, 6)
        middle_down = self._finger_down(right_landmarks, 12, 10)
        ring_down = self._finger_down(right_landmarks, 16, 14)
        pinky_up = self._finger_up(right_landmarks, 20, 18)
        return index_up and middle_down and ring_down and pinky_up

    def _is_left_index_only(self, left_landmarks):
        index_up = self._finger_up(left_landmarks, 8, 6)
        middle_down = self._finger_down(left_landmarks, 12, 10)
        ring_down = self._finger_down(left_landmarks, 16, 14)
        pinky_down = self._finger_down(left_landmarks, 20, 18)
        return index_up and middle_down and ring_down and pinky_down

    def _is_left_thumb_only(self, left_landmarks):
        # Left-hand thumb extension heuristic (same orientation logic used elsewhere).
        thumb_up = left_landmarks[4].x < left_landmarks[3].x
        index_down = self._finger_down(left_landmarks, 8, 6)
        middle_down = self._finger_down(left_landmarks, 12, 10)
        ring_down = self._finger_down(left_landmarks, 16, 14)
        pinky_down = self._finger_down(left_landmarks, 20, 18)
        return thumb_up and index_down and middle_down and ring_down and pinky_down

    def _reset_tracking(self):
        pass

    def reset_all(self):
        self.active = False
        self._toggle_hold_start = None
        self._reset_tracking()

    def update_mode_toggle(self, right_landmarks, enabled=True):
        now = time.time()
        if not enabled or right_landmarks is None:
            self._toggle_hold_start = None
            return

        can_toggle = (now - self._last_toggle_time) >= self.toggle_cooldown
        pose_detected = self._is_right_index_pinky_only(right_landmarks)

        if pose_detected and can_toggle:
            if self._toggle_hold_start is None:
                self._toggle_hold_start = now
            elif (now - self._toggle_hold_start) >= self.toggle_hold_seconds:
                self._toggle_hold_start = None
                self._last_toggle_time = now
                self.active = not self.active
                self._reset_tracking()
                self.set_event("VOLUME MODE ON" if self.active else "VOLUME MODE OFF")
        else:
            self._toggle_hold_start = None

    def update_control(self, left_landmarks, right_landmarks, enabled=True):
        if not enabled or not self.active:
            self._reset_tracking()
            return
        if left_landmarks is None:
            self._reset_tracking()
            return

        # Right open palm acts as "hold volume" safety in volume mode.
        if right_landmarks is not None and self._is_open_palm(right_landmarks):
            return

        now = time.time()
        if (now - self._last_volume_step_time) < self.volume_step_cooldown:
            return

        if self._is_left_thumb_only(left_landmarks):
            volume_step("down")
            self._last_volume_step_time = now
            self.set_event("VOLUME DOWN")
        elif self._is_left_index_only(left_landmarks):
            volume_step("up")
            self._last_volume_step_time = now
            self.set_event("VOLUME UP")
