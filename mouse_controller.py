import time
import math
import pyautogui

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False


class MouseController:
    """
    Handles:
    - cursor movement using MediaPipe landmarks
    - smoothing, sensitivity, deadzone
    - optional thumb-freeze (clutch)
    """

    def __init__(
        self,
        sensitivity: float = 1.0,
        deadzone: float = 0.03,
        smoothing: float = 0.45,
        mouse_hz: int = 60,
        use_thumb_freeze: bool = True,
    ):
        self.enabled = True

        self.sensitivity = sensitivity
        self.deadzone = deadzone
        self.smoothing = smoothing

        self.mouse_hz = mouse_hz
        self._last_mouse_time = 0.0

        self._smoothed_x = None
        self._smoothed_y = None
        self._screen_size = pyautogui.size()

        self.use_thumb_freeze = use_thumb_freeze
        self._freeze_now = False

    def reset(self):
        self._smoothed_x = None
        self._smoothed_y = None
        self._last_mouse_time = 0.0
        self._freeze_now = False

    @staticmethod
    def _thumb_extended(landmarks, hand_type: str) -> bool:
        """
        Simple thumb extension test:
        Right hand: thumb tip.x > thumb IP.x
        Left hand : thumb tip.x < thumb IP.x
        """
        tip = landmarks[4]
        ip = landmarks[3]
        if hand_type == "Right":
            return tip.x > ip.x
        return tip.x < ip.x

    @staticmethod
    def _get_point_mcp9(landmarks):
        p = landmarks[9]  # middle MCP
        return float(p.x), float(p.y)

    def freeze_active(self) -> bool:
        return self._freeze_now

    def update(self, landmarks, hand_type: str):
        """
        Call every frame during mouse mode.
        Moves cursor unless frozen/disabled/throttled.
        """
        self._freeze_now = False

        if not self.enabled:
            return

        if self.use_thumb_freeze and self._thumb_extended(landmarks, hand_type):
            self._freeze_now = True
            return

        now = time.time()
        if now - self._last_mouse_time < (1.0 / max(1, self.mouse_hz)):
            return
        self._last_mouse_time = now

        x, y = self._get_point_mcp9(landmarks)

        cx = x - 0.5
        cy = y - 0.5

        dist = math.sqrt(cx * cx + cy * cy)
        if dist < self.deadzone:
            return

        # Smooth exit from deadzone (prevents jump)
        if dist > 0:
            max_dist = 0.7071
            new_dist = (dist - self.deadzone) / max(1e-6, (max_dist - self.deadzone))
            new_dist = max(0.0, min(1.0, new_dist))
            scale = new_dist / dist
            cx *= scale
            cy *= scale

        # Sensitivity
        cx *= self.sensitivity
        cy *= self.sensitivity

        target_norm_x = max(0.0, min(1.0, 0.5 + cx))
        target_norm_y = max(0.0, min(1.0, 0.5 + cy))

        screen_w, screen_h = self._screen_size
        target_x = target_norm_x * screen_w
        target_y = target_norm_y * screen_h

        # EMA smoothing: higher alpha = more responsive
        if self._smoothed_x is None or self._smoothed_y is None:
            self._smoothed_x, self._smoothed_y = target_x, target_y
        else:
            alpha = self.smoothing
            self._smoothed_x = (1 - alpha) * self._smoothed_x + alpha * target_x
            self._smoothed_y = (1 - alpha) * self._smoothed_y + alpha * target_y

        pyautogui.moveTo(int(self._smoothed_x), int(self._smoothed_y))
