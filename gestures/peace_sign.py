from .gesture_base import Gesture

class PeaceSign(Gesture):
    """
    Mouse Mode detection (kept name PeaceSign for compatibility):
    - ring + pinky folded
    - index OR middle can be extended
    Allows index to go down for dragging while staying in mouse mode.
    """
    def __init__(self):
        super().__init__("PeaceSign")

    def detect(self, landmarks, hand_type):
        # Right hand only for mouse mode (keep if you want)
        if hand_type != "Right":
            return False

        def finger_extended(tip_idx, pip_idx):
            return landmarks[tip_idx].y < landmarks[pip_idx].y

        index_up  = finger_extended(8, 6)
        middle_up = finger_extended(12, 10)
        ring_up   = finger_extended(16, 14)
        pinky_up  = finger_extended(20, 18)

        ring_down = not ring_up
        pinky_down = not pinky_up

        # Mouse Mode condition
        return ring_down and pinky_down and (index_up or middle_up)
