import pyautogui

def trigger_action(gesture_name, hand_type):
    if gesture_name == "SwipeLeft":
        pyautogui.press("right")  # next slide
        print("[ACTION] SwipeLeft -> Next Slide")

    elif gesture_name == "SwipeRight":
        pyautogui.press("left")   # previous slide
        print("[ACTION] SwipeRight -> Previous Slide")

    elif gesture_name == "PeaceSign":
        # Usually continuous (mouse), so we don't press keys here
        print("[ACTION] PeaceSign -> Mouse mode")

    elif gesture_name == "ThumbsUp":
        pyautogui.hotkey('shift', 'volumeup')  # volume up
        print("[ACTION] ThumbsUp -> Volume Up")

    elif gesture_name == "ThumbsDown":
        pyautogui.hotkey('shift', 'volumedown')  # volume down
        print("[ACTION] ThumbsDown -> Volume Down")
