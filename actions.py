import ctypes

import pyautogui


VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_KEYUP = 0x0002


def _tap_virtual_key(vk_code):
    user32 = ctypes.windll.user32
    user32.keybd_event(vk_code, 0, 0, 0)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def _change_volume(direction):
    # Use Windows media virtual keys first; fall back to pyautogui if needed.
    try:
        if direction == "up":
            _tap_virtual_key(VK_VOLUME_UP)
        elif direction == "down":
            _tap_virtual_key(VK_VOLUME_DOWN)
        else:
            _tap_virtual_key(VK_VOLUME_MUTE)
        return
    except Exception:
        pass

    key_name = {
        "up": "volumeup",
        "down": "volumedown",
        "mute": "volumemute",
    }[direction]
    pyautogui.press(key_name)


def volume_step(direction):
    if direction not in ("up", "down", "mute"):
        return
    _change_volume(direction)

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
        volume_step("up")
        print("[ACTION] ThumbsUp -> Volume Up")

    elif gesture_name == "ThumbsDown":
        volume_step("down")
        print("[ACTION] ThumbsDown -> Volume Down")
