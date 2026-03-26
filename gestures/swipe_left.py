from .gesture_base import Gesture


class SwipeLeft(Gesture):
    def __init__(self):
        super().__init__("SwipeLeft")

    def detect(self, landmarks, hand_type):
        if hand_type != "Right":
            return False  # only right hand triggers this gesture

        wrist = landmarks[0]
        index_tip = landmarks[8]
        index_mcp = landmarks[5]
        pinky_mcp = landmarks[17]

        # Hand width for scale invariance
        hand_width = ((index_mcp.x - pinky_mcp.x) ** 2 + (index_mcp.y - pinky_mcp.y) ** 2) ** 0.5
        if hand_width == 0:
            hand_width = 0.001

        dx_ratio = (index_tip.x - wrist.x) / hand_width
        dy = abs(index_tip.y - wrist.y)

        if dx_ratio < -1.2 and dy < 0.3:
            return True
        return False
