import time
import pyautogui

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False


class ClickController:
    """
    Handles:
    - left click hold/release (drag) using index finger DOWN/UP (debounced)
    - right click using middle finger DOWN (debounced + cooldown + re-arm)
    """

    def __init__(
        self,
        left_down_frames_required: int = 2,
        left_up_frames_required: int = 2,
        right_tap_frames_required: int = 2,
        right_click_cooldown: float = 0.45,
    ):
        self.left_is_held = False

        self.left_down_frames_required = left_down_frames_required
        self.left_up_frames_required = left_up_frames_required
        self.right_tap_frames_required = right_tap_frames_required
        self.right_click_cooldown = right_click_cooldown

        self.left_down_frames = 0
        self.left_up_frames = 0

        self.middle_down_frames = 0
        self.middle_up_frames = 0

        self.right_click_ready = True
        self.last_right_click_time = 0.0

        self.last_event_text = "Ready"
        self.last_event_time = 0.0
        self.event_show_seconds = 1.0

    @staticmethod
    def _finger_up(landmarks, tip_idx, ip_idx) -> bool:
        return landmarks[tip_idx].y < landmarks[ip_idx].y

    @classmethod
    def _finger_down(cls, landmarks, tip_idx, ip_idx) -> bool:
        return not cls._finger_up(landmarks, tip_idx, ip_idx)

    def set_event(self, text: str):
        self.last_event_text = text
        self.last_event_time = time.time()

    def event_visible(self) -> bool:
        return (time.time() - self.last_event_time) <= self.event_show_seconds

    def force_release_left(self):
        if self.left_is_held:
            pyautogui.mouseUp(button="left")
            self.left_is_held = False
            self.set_event("LEFT UP (forced)")

    def update(self, landmarks):
        """
        Call every frame during mouse mode.
        Index DOWN => left mouseDown (debounced)
        Index UP   => left mouseUp (debounced)
        Middle DOWN (tap) => right click (debounced + cooldown + re-arm)
        """
        index_is_down = self._finger_down(landmarks, 8, 6)
        middle_is_down = self._finger_down(landmarks, 12, 10)

        # ---- LEFT HOLD / RELEASE (debounced) ----
        if index_is_down:
            self.left_down_frames += 1
            self.left_up_frames = 0
        else:
            self.left_up_frames += 1
            self.left_down_frames = 0

        if (not self.left_is_held) and self.left_down_frames >= self.left_down_frames_required:
            pyautogui.mouseDown(button="left")
            self.left_is_held = True
            self.set_event("LEFT DOWN (drag started)")
            self.left_down_frames = 0

        if self.left_is_held and self.left_up_frames >= self.left_up_frames_required:
            pyautogui.mouseUp(button="left")
            self.left_is_held = False
            self.set_event("LEFT UP (drag released)")
            self.left_up_frames = 0

        # ---- RIGHT CLICK (debounced + cooldown) ----
        now = time.time()

        if middle_is_down:
            self.middle_down_frames += 1
            self.middle_up_frames = 0
        else:
            self.middle_up_frames += 1
            self.middle_down_frames = 0

        # re-arm after finger goes up at least 1 frame
        if self.middle_up_frames >= 1:
            self.right_click_ready = True

        if (
            self.right_click_ready
            and self.middle_down_frames >= self.right_tap_frames_required
            and (now - self.last_right_click_time) > self.right_click_cooldown
        ):
            pyautogui.click(button="right")
            self.last_right_click_time = now
            self.right_click_ready = False
            self.set_event("RIGHT CLICK")
            self.middle_down_frames = 0
