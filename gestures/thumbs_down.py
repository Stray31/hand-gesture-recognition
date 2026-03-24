from .gesture_base import Gesture

class ThumbsDown(Gesture):
    """
    Thumbs Down gesture detection:
    - Thumb extended downward
    - All other fingers folded down
    """
    def __init__(self):
        super().__init__("ThumbsDown")

    def detect(self, landmarks, hand_type):
        # Right hand only
        if hand_type != "Right":
            return False

        def finger_extended(tip_idx, pip_idx):
            return landmarks[tip_idx].y < landmarks[pip_idx].y

        # Check thumb is DOWN (y coordinate larger/lower on screen)
        # Thumb: tip=4, ip=3, mcp=2
        thumb_down = landmarks[4].y > landmarks[3].y > landmarks[2].y
        
        # All other fingers should be DOWN (folded)
        index_down = not finger_extended(8, 6)
        middle_down = not finger_extended(12, 10)
        ring_down = not finger_extended(16, 14)
        pinky_down = not finger_extended(20, 18)

        # Thumbs down: thumb extended down, all others folded
        if thumb_down and index_down and middle_down and ring_down and pinky_down:
            return True
        return False

