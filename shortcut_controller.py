import time
import pyautogui

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False


class ShortcutController:
    """
    Alt-Tab controller (REAL Alt hold):

    - Right hand: closed fist (held)  -> Alt DOWN
    - Left index tap                  -> Tab        (forward)
    - Left middle tap                 -> Shift+Tab  (backward)
    - Release fist / lose tracking    -> Alt UP (failsafe)

    Requires Alt-suppression fix in app.py to avoid Tk freeze.
    """

    def __init__(
        self,
        fist_frames_required: int = 3,
        release_frames_required: int = 2,
        lost_hand_timeout: float = 0.25,
        tab_cooldown: float = 0.18,
        tap_frames_required: int = 2,
    ):
        # Right fist stability
        self.fist_frames_required = fist_frames_required
        self.release_frames_required = release_frames_required
        self.lost_hand_timeout = lost_hand_timeout

        # Tap stability
        self.tap_frames_required = tap_frames_required
        self.tab_cooldown = tab_cooldown

        # Real key state
        self.alt_held = False

        # Right hand tracking
        self._right_fist_frames = 0
        self._right_release_frames = 0
        self._last_right_seen_time = 0.0

        # Left index (forward)
        self._index_down_frames = 0
        self._index_up_frames = 0

        # Left middle (backward)
        self._middle_down_frames = 0
        self._middle_up_frames = 0

        self._action_ready = True
        self._last_action_time = 0.0

        # UI feedback
        self.last_event_text = "Ready"
        self.last_event_time = 0.0
        self.event_show_seconds = 1.0

    # ---------------- UI helpers ----------------
    def set_event(self, text: str):
        self.last_event_text = text
        self.last_event_time = time.time()

    def event_visible(self) -> bool:
        return (time.time() - self.last_event_time) <= self.event_show_seconds

    # ---------------- Landmark helpers ----------------
    @staticmethod
    def _finger_down(landmarks, tip_idx, pip_idx) -> bool:
        return landmarks[tip_idx].y > landmarks[pip_idx].y

    def _is_fist(self, landmarks) -> bool:
        index = self._finger_down(landmarks, 8, 6)
        middle = self._finger_down(landmarks, 12, 10)
        ring = self._finger_down(landmarks, 16, 14)
        pinky = self._finger_down(landmarks, 20, 18)
        return index and middle and ring and pinky

    def _index_down(self, landmarks) -> bool:
        return self._finger_down(landmarks, 8, 6)

    def _middle_down(self, landmarks) -> bool:
        return self._finger_down(landmarks, 12, 10)

    # ---------------- Safety ----------------
    def force_release_alt(self):
        if self.alt_held:
            try:
                pyautogui.keyUp("alt")
            except Exception:
                pass
            self.alt_held = False
            self.set_event("ALT UP (forced)")

        self._right_fist_frames = 0
        self._right_release_frames = 0
        self._action_ready = True

    # ---------------- Main update ----------------
    def update(self, left_landmarks, right_landmarks):
        now = time.time()

        # -------- Right fist controls Alt --------
        if right_landmarks is not None:
            self._last_right_seen_time = now
            fist_now = self._is_fist(right_landmarks)
        else:
            fist_now = False

        if fist_now:
            self._right_fist_frames += 1
            self._right_release_frames = 0
        else:
            self._right_release_frames += 1
            self._right_fist_frames = 0

        # Alt DOWN
        if not self.alt_held and self._right_fist_frames >= self.fist_frames_required:
            pyautogui.keyDown("alt")
            self.alt_held = True
            self.set_event("ALT DOWN")
            self._right_fist_frames = 0
            self._action_ready = True

        # Safety: lose right hand
        if self.alt_held and (now - self._last_right_seen_time) > self.lost_hand_timeout:
            self.force_release_alt()
            return

        # Alt UP (fist released)
        if self.alt_held and self._right_release_frames >= self.release_frames_required:
            pyautogui.keyUp("alt")
            self.alt_held = False
            self.set_event("ALT UP")
            self._right_release_frames = 0
            return

        # -------- Left hand navigation --------
        if not self.alt_held or left_landmarks is None:
            return

        index_down = self._index_down(left_landmarks)
        middle_down = self._middle_down(left_landmarks)

        # Track index
        if index_down:
            self._index_down_frames += 1
            self._index_up_frames = 0
        else:
            self._index_up_frames += 1
            self._index_down_frames = 0

        # Track middle
        if middle_down:
            self._middle_down_frames += 1
            self._middle_up_frames = 0
        else:
            self._middle_up_frames += 1
            self._middle_down_frames = 0

        # Re-arm after fingers released
        if self._index_up_frames >= 1 and self._middle_up_frames >= 1:
            self._action_ready = True

        # Cooldown gate
        if (now - self._last_action_time) < self.tab_cooldown:
            return

        # -------- Forward (Index) --------
        if (
            self._action_ready
            and self._index_down_frames >= self.tap_frames_required
            and not middle_down
        ):
            pyautogui.press("tab")
            self._last_action_time = now
            self._action_ready = False
            self.set_event("ALT + TAB →")
            self._index_down_frames = 0
            return

        # -------- Backward (Middle) --------
        if (
            self._action_ready
            and self._middle_down_frames >= self.tap_frames_required
            and not index_down
        ):
            pyautogui.keyDown("shift")
            pyautogui.press("tab")
            pyautogui.keyUp("shift")

            self._last_action_time = now
            self._action_ready = False
            self.set_event("ALT + SHIFT + TAB ←")
            self._middle_down_frames = 0
            return
