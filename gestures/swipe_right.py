from .gesture_base import Gesture

class SwipeRight(Gesture):
    def __init__(self):
        super().__init__("SwipeRight")

    def detect(self, landmarks, hand_type):
        if hand_type != "Left":
            return False  # only left hand triggers this gesture

        wrist = landmarks[0]
        index_tip = landmarks[8]
        index_mcp = landmarks[5]
        pinky_mcp = landmarks[17]

        hand_width = ((index_mcp.x - pinky_mcp.x)**2 + (index_mcp.y - pinky_mcp.y)**2) ** 0.5
        if hand_width == 0:
            hand_width = 0.001

        dx_ratio = (index_tip.x - wrist.x) / hand_width
        dy = abs(index_tip.y - wrist.y)

        if dx_ratio > 1.2 and dy < 0.3:
            return True
        return False
