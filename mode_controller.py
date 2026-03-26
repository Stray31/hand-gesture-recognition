import time
import math
import pyautogui

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False


class ModeController:
    """
    1) System Lock:
       - Right pinky-only held for lock_hold_seconds toggles LOCK/UNLOCK

    2) Scroll via RIGHT-HAND PINCH (reliable):
       - Pinch (thumb tip 4 + index tip 8 close) activates scroll clutch
       - While pinched: move reference landmark vertically to scroll
       - Release pinch: stop scrolling
    """

    def __init__(
        self,
        lock_hold_seconds: float = 1.0,
        lock_toggle_cooldown: float = 1.0,

        # Pinch detection
        pinch_threshold: float = 0.055,  # normalized distance; lower = stricter
        pinch_release_threshold: float = 0.070,  # hysteresis to prevent flicker

        # Scroll behavior
        scroll_reference_landmark: int = 9,  # 9 = middle MCP (stable)
        scroll_hz: int = 30,
        scroll_deadzone: float = 0.010,
        scroll_gain: float = 1800.0,        # higher = faster scroll
        scroll_smoothing: float = 0.55,     # 0..1, higher = smoother but more lag
        scroll_clamp: int = 1200,           # cap wheel movement per tick
    ):
        # Lock (right-hand pinky-only)
        self.locked = False
        self.lock_hold_seconds = lock_hold_seconds
        self.lock_toggle_cooldown = lock_toggle_cooldown
        self._right_pinky_hold_start = None
        self._last_lock_toggle_time = 0.0

        # Pinch
        self.pinch_threshold = float(pinch_threshold)
        self.pinch_release_threshold = float(pinch_release_threshold)
        self._pinch_active = False

        # Scroll
        self.scroll_active = False
        self.scroll_reference_landmark = int(scroll_reference_landmark)
        self.scroll_hz = int(scroll_hz)
        self.scroll_deadzone = float(scroll_deadzone)
        self.scroll_gain = float(scroll_gain)
        self.scroll_smoothing = float(scroll_smoothing)
        self.scroll_clamp = int(scroll_clamp)

        self._scroll_anchor_y = None
        self._scroll_velocity = 0.0
        self._scroll_last_time = 0.0

        # UI event
        self.last_event_text = "Ready"
        self.last_event_time = 0.0
        self.event_show_seconds = 1.2

    # ---------- UI helpers ----------
    def set_event(self, text: str):
        self.last_event_text = text
        self.last_event_time = time.time()

    def event_visible(self) -> bool:
        return (time.time() - self.last_event_time) <= self.event_show_seconds

    # ---------- Landmark helpers ----------
    @staticmethod
    def _finger_up(landmarks, tip_idx, pip_idx) -> bool:
        return landmarks[tip_idx].y < landmarks[pip_idx].y

    @staticmethod
    def _dist(a, b) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    def is_open_palm(self, landmarks) -> bool:
        # thumb ignored (inconsistent); require 4 fingers up
        index_up = self._finger_up(landmarks, 8, 6)
        middle_up = self._finger_up(landmarks, 12, 10)
        ring_up = self._finger_up(landmarks, 16, 14)
        pinky_up = self._finger_up(landmarks, 20, 18)
        return index_up and middle_up and ring_up and pinky_up

    def is_fist(self, landmarks) -> bool:
        index_down = not self._finger_up(landmarks, 8, 6)
        middle_down = not self._finger_up(landmarks, 12, 10)
        ring_down = not self._finger_up(landmarks, 16, 14)
        pinky_down = not self._finger_up(landmarks, 20, 18)
        return index_down and middle_down and ring_down and pinky_down

    def is_right_pinky_only(self, landmarks) -> bool:
        index_up = self._finger_up(landmarks, 8, 6)
        middle_up = self._finger_up(landmarks, 12, 10)
        ring_up = self._finger_up(landmarks, 16, 14)
        pinky_up = self._finger_up(landmarks, 20, 18)
        return pinky_up and (not index_up) and (not middle_up) and (not ring_up)

    def _pinch_now(self, landmarks) -> bool:
        # Thumb tip = 4, Index tip = 8
        d = self._dist(landmarks[4], landmarks[8])
        if self._pinch_active:
            # release hysteresis
            return d <= self.pinch_release_threshold
        return d <= self.pinch_threshold

    # ---------- Core update ----------
    def update_lock(self, left_landmarks, right_landmarks):
        """
        Always call every frame (even when locked).
        Toggles lock on right pinky-only hold.
        """
        now = time.time()

        right_pinky_detected = right_landmarks is not None and self.is_right_pinky_only(right_landmarks)

        can_toggle = (now - self._last_lock_toggle_time) >= self.lock_toggle_cooldown

        if right_pinky_detected and can_toggle:
            if self._right_pinky_hold_start is None:
                self._right_pinky_hold_start = now
            else:
                if (now - self._right_pinky_hold_start) >= self.lock_hold_seconds:
                    self.locked = not self.locked
                    self._last_lock_toggle_time = now
                    self._right_pinky_hold_start = None
                    self.set_event("SYSTEM LOCKED" if self.locked else "SYSTEM UNLOCKED")
                    self._reset_scroll_state()
        else:
            self._right_pinky_hold_start = None

    def update_scroll(self, left_landmarks, right_landmarks):
        """
        Pinch scroll clutch.
        Call only when NOT locked.
        """
        if self.locked:
            self._reset_scroll_state()
            return

        now = time.time()

        # Right hand pinch only.
        scroll_lm = None
        pinch = False

        if right_landmarks is not None and self._pinch_now(right_landmarks):
            scroll_lm = right_landmarks
            pinch = True

        self._pinch_active = pinch

        if not pinch or scroll_lm is None:
            if self.scroll_active:
                self.scroll_active = False
                self.set_event("SCROLL OFF")
            self._reset_scroll_state()
            return

        # Enter scroll mode when pinch starts
        if not self.scroll_active:
            self.scroll_active = True
            self.set_event("SCROLL ON (PINCH)")
            self._scroll_anchor_y = scroll_lm[self.scroll_reference_landmark].y
            self._scroll_velocity = 0.0
            self._scroll_last_time = 0.0
            return

        # Throttle scroll updates
        if self._scroll_last_time and (now - self._scroll_last_time) < (1.0 / self.scroll_hz):
            return
        self._scroll_last_time = now

        ref_y = scroll_lm[self.scroll_reference_landmark].y
        if self._scroll_anchor_y is None:
            self._scroll_anchor_y = ref_y
            return

        dy = ref_y - self._scroll_anchor_y  # + when hand moves down

        # Deadzone
        if abs(dy) < self.scroll_deadzone:
            self._scroll_velocity *= self.scroll_smoothing
            return

        # Smooth movement
        self._scroll_velocity = (self.scroll_smoothing * self._scroll_velocity) + ((1.0 - self.scroll_smoothing) * dy)

        # Convert to wheel (negative dy => move up => scroll up)
        amount = int(-self._scroll_velocity * self.scroll_gain)

        # Clamp
        if amount > self.scroll_clamp:
            amount = self.scroll_clamp
        elif amount < -self.scroll_clamp:
            amount = -self.scroll_clamp

        if amount != 0:
            pyautogui.scroll(amount)

        # Slowly “follow” your hand so you can keep scrolling without re-centering
        # (this prevents it from only working in one direction)
        self._scroll_anchor_y = (0.85 * self._scroll_anchor_y) + (0.15 * ref_y)

    def _reset_scroll_state(self):
        self._scroll_anchor_y = None
        self._scroll_velocity = 0.0
        self._scroll_last_time = 0.0
        self._pinch_active = False
