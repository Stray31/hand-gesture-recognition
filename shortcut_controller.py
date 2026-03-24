import time
import pyautogui

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False


class ShortcutController:
    """Alt-Tab package gesture with persistent Alt hold + left-hand navigation."""

    def __init__(
        self,
        fist_frames_required: int = 3,
        release_frames_required: int = 2,
        lost_hand_timeout: float = 0.25,
        tab_cooldown: float = 0.20,
        tap_frames_required: int = 2,
    ):
        self.fist_frames_required = max(1, int(fist_frames_required))
        self.release_frames_required = max(1, int(release_frames_required))
        self.lost_hand_timeout = float(lost_hand_timeout)
        self.combo_frames_required = max(1, int(tap_frames_required))
        self.tap_frames_required = max(1, int(tap_frames_required))
        self.tab_cooldown = float(tab_cooldown)

        self._combo_frames = 0
        self._fist_frames = 0
        self._release_frames = 0
        self._last_tab_time = 0.0
        self._last_seen_hands_time = 0.0

        self._index_only_frames = 0
        self._middle_only_frames = 0
        self._index_action_ready = True
        self._middle_action_ready = True

        self.alt_held = False

        self.last_event_text = "Ready"
        self.last_event_time = 0.0
        self.event_show_seconds = 1.0

    def set_event(self, text: str):
        self.last_event_text = text
        self.last_event_time = time.time()

    def event_visible(self) -> bool:
        return (time.time() - self.last_event_time) <= self.event_show_seconds

    @staticmethod
    def _finger_up(landmarks, tip_idx, pip_idx) -> bool:
        return landmarks[tip_idx].y < landmarks[pip_idx].y

    @classmethod
    def _finger_down(cls, landmarks, tip_idx, pip_idx) -> bool:
        return not cls._finger_up(landmarks, tip_idx, pip_idx)

    def _is_fist(self, landmarks) -> bool:
        index_down = self._finger_down(landmarks, 8, 6)
        middle_down = self._finger_down(landmarks, 12, 10)
        ring_down = self._finger_down(landmarks, 16, 14)
        pinky_down = self._finger_down(landmarks, 20, 18)
        return index_down and middle_down and ring_down and pinky_down

    def _is_left_index_middle_only(self, landmarks) -> bool:
        index_up = self._finger_up(landmarks, 8, 6)
        middle_up = self._finger_up(landmarks, 12, 10)
        ring_down = self._finger_down(landmarks, 16, 14)
        pinky_down = self._finger_down(landmarks, 20, 18)
        return index_up and middle_up and ring_down and pinky_down

    def _is_left_index_only(self, landmarks) -> bool:
        index_up = self._finger_up(landmarks, 8, 6)
        middle_down = self._finger_down(landmarks, 12, 10)
        ring_down = self._finger_down(landmarks, 16, 14)
        pinky_down = self._finger_down(landmarks, 20, 18)
        return index_up and middle_down and ring_down and pinky_down

    def _is_left_middle_only(self, landmarks) -> bool:
        index_down = self._finger_down(landmarks, 8, 6)
        middle_up = self._finger_up(landmarks, 12, 10)
        ring_down = self._finger_down(landmarks, 16, 14)
        pinky_down = self._finger_down(landmarks, 20, 18)
        return index_down and middle_up and ring_down and pinky_down

    def _press_alt_tab_once(self):
        pyautogui.keyDown("alt")
        pyautogui.press("tab")

    def _ensure_alt_released(self):
        if self.alt_held:
            try:
                pyautogui.keyUp("alt")
            except Exception:
                pass
        self.alt_held = False
        self._release_frames = 0
        self._index_only_frames = 0
        self._middle_only_frames = 0
        self._index_action_ready = True
        self._middle_action_ready = True

    def force_release_alt(self):
        self._ensure_alt_released()
        self._combo_frames = 0
        self._fist_frames = 0

    def update(self, left_landmarks, right_landmarks):
        now = time.time()

        if left_landmarks is None or right_landmarks is None:
            self._combo_frames = 0
            self._fist_frames = 0
            if self.alt_held and (now - self._last_seen_hands_time) >= self.lost_hand_timeout:
                self._ensure_alt_released()
            elif self.alt_held:
                self._release_frames += 1
                if self._release_frames >= self.release_frames_required:
                    self._ensure_alt_released()
            return

        self._last_seen_hands_time = now

        right_fist = self._is_fist(right_landmarks)
        combo_on = right_fist and self._is_left_index_middle_only(left_landmarks)

        if right_fist:
            self._fist_frames += 1
            self._release_frames = 0
        else:
            self._fist_frames = 0
            if self.alt_held:
                self._release_frames += 1
                if self._release_frames >= self.release_frames_required:
                    self._ensure_alt_released()
            return

        if (not self.alt_held) and combo_on:
            self._combo_frames += 1
            if self._combo_frames >= self.combo_frames_required:
                self._combo_frames = 0
                self._last_tab_time = now
                self._press_alt_tab_once()
                self.alt_held = True
                self.set_event("ALT+TAB HOLD")
                return
        else:
            self._combo_frames = 0

        if not self.alt_held:
            return

        if self._fist_frames < self.fist_frames_required:
            return

        if (now - self._last_tab_time) < self.tab_cooldown:
            return

        index_only = self._is_left_index_only(left_landmarks)
        middle_only = self._is_left_middle_only(left_landmarks)

        if index_only and not middle_only:
            self._index_only_frames += 1
            self._middle_only_frames = 0
            self._middle_action_ready = True
            if self._index_only_frames >= self.tap_frames_required and self._index_action_ready:
                pyautogui.hotkey("shift", "tab")
                self._last_tab_time = now
                self._index_action_ready = False
                self.set_event("ALT+TAB PREV")
        elif middle_only and not index_only:
            self._middle_only_frames += 1
            self._index_only_frames = 0
            self._index_action_ready = True
            if self._middle_only_frames >= self.tap_frames_required and self._middle_action_ready:
                pyautogui.press("tab")
                self._last_tab_time = now
                self._middle_action_ready = False
                self.set_event("ALT+TAB NEXT")
        else:
            self._index_only_frames = 0
            self._middle_only_frames = 0
            self._index_action_ready = True
            self._middle_action_ready = True
