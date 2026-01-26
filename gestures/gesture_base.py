class Gesture:
    """
    Base class for all gestures.
    Each gesture must implement the detect() method.
    """
    def __init__(self, name):
        self.name = name

    def detect(self, landmarks, hand_type):
        """
        landmarks: list of MediaPipe landmarks for the hand
        hand_type: "Left" or "Right"
        Returns True if gesture is detected
        """
        raise NotImplementedError
