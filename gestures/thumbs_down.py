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

        # Thumb landmarks: tip=4, pip=3
        # For thumbs down, thumb tip should be lower (higher y value) than pip
        thumb_down = landmarks[4].y > landmarks[3].y
        
        # Other fingers should be down (folded)
        index_down = not finger_extended(8, 6)
        middle_down = not finger_extended(12, 10)
        ring_down = not finger_extended(16, 14)
        pinky_down = not finger_extended(20, 18)

        # Thumbs down: thumb extended downward, all others folded
        if thumb_down and index_down and middle_down and ring_down and pinky_down:
            return True
        return False
