import cv2
import mediapipe as mp
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import math

# Windows-only: prevents Alt key from freezing Tk UI
import ctypes
from ctypes import wintypes

from gestures.swipe_left import SwipeLeft
from gestures.swipe_right import SwipeRight
from gestures.peace_sign import PeaceSign
from actions import trigger_action

from mouse_controller import MouseController
from click_controller import ClickController
from shortcut_controller import ShortcutController
from mode_controller import ModeController  # NEW

# -----------------------------
# MediaPipe setup
# -----------------------------
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    model_complexity=0,
    min_detection_confidence=0.65,
    min_tracking_confidence=0.65,
)

# -----------------------------
# Visual overlay toggles
# -----------------------------
SHOW_LANDMARKS = True
SHOW_LANDMARK_NUMBERS = True

# -----------------------------
# Loop timing (FIX)
# -----------------------------
FRAME_DELAY_MS = 10

# UI preview FPS (drawing + PIL conversion)
last_ui_time = 0.0
UI_HZ = 15

# -----------------------------
# Safety filter (face false positives)
# -----------------------------
HAND_SCORE_MIN = 0.80
PALM_MIN = 0.07
PALM_MAX = 0.60

def _dist(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)

def valid_hand_shape(landmarks) -> bool:
    wrist = landmarks[0]
    mcp9 = landmarks[9]
    mcp5 = landmarks[5]
    mcp17 = landmarks[17]

    palm_len = _dist(wrist, mcp9)
    palm_wid = _dist(mcp5, mcp17)

    if palm_len < PALM_MIN or palm_wid < PALM_MIN:
        return False
    if palm_len > PALM_MAX or palm_wid > 0.85:
        return False
    return True

def draw_landmark_numbers(frame, hand_landmarks):
    h, w, _ = frame.shape
    for i, lm in enumerate(hand_landmarks.landmark):
        cx, cy = int(lm.x * w), int(lm.y * h)
        cv2.circle(frame, (cx, cy), 3, (0, 0, 255), -1)
        cv2.putText(
            frame, str(i), (cx + 4, cy - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45,
            (255, 255, 255), 1, cv2.LINE_AA
        )

# -----------------------------
# Windows/Tk Alt freeze fix
# -----------------------------
def make_window_toolwindow_and_suppress_alt(root: tk.Tk):
    """
    Prevents Alt from putting the focused Tk window into Windows "menu mode",
    which can stall UI updates and make the camera preview appear frozen.
    """
    try:
        if root.tk.call("tk", "windowingsystem") != "win32":
            return
    except Exception:
        return

    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080

    user32 = ctypes.windll.user32
    hwnd = wintypes.HWND(root.winfo_id())

    exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_TOOLWINDOW)

    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOZORDER = 0x0004
    SWP_FRAMECHANGED = 0x0020
    user32.SetWindowPos(hwnd, None, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)

    def _block_alt(event):
        return "break"

    root.bind_all("<KeyPress-Alt_L>", _block_alt)
    root.bind_all("<KeyRelease-Alt_L>", _block_alt)
    root.bind_all("<KeyPress-Alt_R>", _block_alt)
    root.bind_all("<KeyRelease-Alt_R>", _block_alt)
    root.bind_all("<Alt-KeyPress>", _block_alt)
    root.bind_all("<Alt-KeyRelease>", _block_alt)

# -----------------------------
# App state
# -----------------------------
running = False
cap = None

last_action_time = 0
COOLDOWN = 1.5

GESTURE_FRAMES_REQUIRED = 3
gesture_queue_left = []
gesture_queue_right = []

# MediaPipe downscale (speed)
MP_WIDTH = 320
MP_HEIGHT = 180

# Gesture objects
GESTURES = [SwipeLeft(), SwipeRight(), PeaceSign()]

# Controllers
mouse = MouseController(
    sensitivity=1.0,
    deadzone=0.03,
    smoothing=0.45,
    mouse_hz=60,
    use_thumb_freeze=True,
)
clicks = ClickController(
    left_down_frames_required=2,
    left_up_frames_required=2,
    right_tap_frames_required=2,
    right_click_cooldown=0.45,
)
shortcuts = ShortcutController(
    fist_frames_required=3,
    release_frames_required=2,
    lost_hand_timeout=0.25,
    tab_cooldown=0.20,
    tap_frames_required=2,
)

# NEW: lock + scroll controller
modes = ModeController(
    lock_hold_seconds=1.0,
    lock_toggle_cooldown=1.0,

    pinch_threshold=0.055,
    pinch_release_threshold=0.070,

    scroll_reference_landmark=9,
    scroll_hz=30,
    scroll_deadzone=0.010,
    scroll_gain=1800.0,
    scroll_smoothing=0.55,
    scroll_clamp=1200,
)



# -----------------------------
# Tkinter UI
# -----------------------------
root = tk.Tk()
make_window_toolwindow_and_suppress_alt(root)
root.title("Gesture Slide Controller")
root.geometry("900x880")
root.configure(bg="#202124")

debug_label = tk.Label(root, text="Left: None | Right: None",
                       font=("Segoe UI", 14), fg="lime", bg="#202124")
debug_label.pack(pady=10)

camera_label = tk.Label(root, bg="black")
camera_label.pack()

status_label = tk.Label(root, text="Status: READY",
                        font=("Segoe UI", 12, "bold"),
                        fg="#00e676", bg="#202124")
status_label.pack(pady=(8, 0))

event_label = tk.Label(root, text="Event: Ready",
                       font=("Segoe UI", 11),
                       fg="#ffd54f", bg="#202124")
event_label.pack(pady=(2, 10))

# Calibration UI
calib_frame = tk.Frame(root, bg="#202124")
calib_frame.pack(pady=10)

tk.Label(calib_frame, text="Calibration",
         font=("Segoe UI", 12, "bold"),
         fg="#fff", bg="#202124").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

def _update_sensitivity(val): mouse.sensitivity = float(val)
def _update_deadzone(val): mouse.deadzone = float(val)
def _update_smoothing(val): mouse.smoothing = float(val)

tk.Label(calib_frame, text="Sensitivity", fg="#ddd", bg="#202124").grid(row=1, column=0, sticky="w")
sens_scale = tk.Scale(
    calib_frame, from_=0.5, to=2.5, resolution=0.05,
    orient="horizontal", length=260,
    bg="#202124", fg="#ddd", highlightthickness=0,
    troughcolor="#3a3b3c", command=_update_sensitivity
)
sens_scale.set(mouse.sensitivity)
sens_scale.grid(row=1, column=1, padx=10)

tk.Label(calib_frame, text="Deadzone", fg="#ddd", bg="#202124").grid(row=2, column=0, sticky="w")
dz_scale = tk.Scale(
    calib_frame, from_=0.00, to=0.15, resolution=0.005,
    orient="horizontal", length=260,
    bg="#202124", fg="#ddd", highlightthickness=0,
    troughcolor="#3a3b3c", command=_update_deadzone
)
dz_scale.set(mouse.deadzone)
dz_scale.grid(row=2, column=1, padx=10)

tk.Label(calib_frame, text="Smoothing", fg="#ddd", bg="#202124").grid(row=3, column=0, sticky="w")
sm_scale = tk.Scale(
    calib_frame, from_=0.0, to=0.80, resolution=0.02,
    orient="horizontal", length=260,
    bg="#202124", fg="#ddd", highlightthickness=0,
    troughcolor="#3a3b3c", command=_update_smoothing
)
sm_scale.set(mouse.smoothing)
sm_scale.grid(row=3, column=1, padx=10)

mouse_var = tk.BooleanVar(value=True)
def _toggle_mouse():
    mouse.enabled = mouse_var.get()
    mouse.reset()
    clicks.force_release_left()
    clicks.set_event("Mouse mode toggled")

mouse_chk = tk.Checkbutton(
    calib_frame, text="Enable Mouse Mode (PeaceSign)",
    variable=mouse_var, command=_toggle_mouse,
    fg="#ddd", bg="#202124",
    activebackground="#202124", activeforeground="#fff",
    selectcolor="#202124"
)
mouse_chk.grid(row=4, column=0, columnspan=3, sticky="w", pady=(6, 0))

thumb_var = tk.BooleanVar(value=mouse.use_thumb_freeze)
def _toggle_thumb_freeze():
    mouse.use_thumb_freeze = thumb_var.get()
    clicks.set_event("Thumb freeze toggled")

thumb_chk = tk.Checkbutton(
    calib_frame, text="Thumb up = Freeze cursor",
    variable=thumb_var, command=_toggle_thumb_freeze,
    fg="#ddd", bg="#202124",
    activebackground="#202124", activeforeground="#fff",
    selectcolor="#202124"
)
thumb_chk.grid(row=5, column=0, columnspan=3, sticky="w", pady=(2, 0))

overlay_var = tk.BooleanVar(value=SHOW_LANDMARKS)
numbers_var = tk.BooleanVar(value=SHOW_LANDMARK_NUMBERS)
def _toggle_overlay():
    global SHOW_LANDMARKS
    SHOW_LANDMARKS = overlay_var.get()
def _toggle_numbers():
    global SHOW_LANDMARK_NUMBERS
    SHOW_LANDMARK_NUMBERS = numbers_var.get()

overlay_chk = tk.Checkbutton(
    calib_frame, text="Show hand landmarks overlay",
    variable=overlay_var, command=_toggle_overlay,
    fg="#ddd", bg="#202124",
    activebackground="#202124", activeforeground="#fff",
    selectcolor="#202124"
)
overlay_chk.grid(row=6, column=0, columnspan=3, sticky="w", pady=(6, 0))

numbers_chk = tk.Checkbutton(
    calib_frame, text="Show landmark numbers (slower)",
    variable=numbers_var, command=_toggle_numbers,
    fg="#ddd", bg="#202124",
    activebackground="#202124", activeforeground="#fff",
    selectcolor="#202124"
)
numbers_chk.grid(row=7, column=0, columnspan=3, sticky="w", pady=(2, 0))

gesture_help = tk.Label(
    calib_frame,
    text="NEW: Hold OPEN PALM (1s) = Lock/Unlock | 3 Fingers (Idx+Mid+Ring) = Scroll Mode",
    font=("Segoe UI", 10),
    fg="#aaa", bg="#202124"
)
gesture_help.grid(row=8, column=0, columnspan=3, sticky="w", pady=(8, 0))

gesture_label = tk.Label(root, text="Gesture: None",
                         font=("Segoe UI", 14), fg="lime", bg="#202124")
gesture_label.pack(pady=10)

# Buttons
def start_camera():
    global running, cap
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to open camera!")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    cap.set(cv2.CAP_PROP_FPS, 30)

    running = True
    start_button.config(state=tk.DISABLED)
    quit_button.config(state=tk.NORMAL)
    clicks.set_event("Camera started")
    update_frame()

def quit_app():
    global running, cap
    running = False
    if cap:
        cap.release()
    clicks.force_release_left()
    shortcuts.force_release_alt()
    root.destroy()

button_frame = tk.Frame(root, bg="#202124")
button_frame.pack(pady=10)

start_button = ttk.Button(button_frame, text="▶ Start Recognition", command=start_camera)
start_button.grid(row=0, column=0, padx=10)

quit_button = ttk.Button(button_frame, text="⏹ Quit", command=quit_app, state=tk.DISABLED)
quit_button.grid(row=0, column=1, padx=10)

# -----------------------------
# Camera loop
# -----------------------------
def update_frame():
    global last_action_time, gesture_queue_left, gesture_queue_right, last_ui_time

    if not running or cap is None:
        return

    frame_start = time.time()

    ret, frame = cap.read()
    if not ret:
        root.after(FRAME_DELAY_MS, update_frame)
        return

    frame = cv2.flip(frame, 1)

    small = cv2.resize(frame, (MP_WIDTH, MP_HEIGHT), interpolation=cv2.INTER_AREA)
    rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_small)

    frame_gesture_left = None
    frame_gesture_right = None

    left_landmarks = None
    right_landmarks = None
    left_score = 0.0
    right_score = 0.0

    if result.multi_hand_landmarks and result.multi_handedness:
        for idx, hlm in enumerate(result.multi_hand_landmarks):
            handed = result.multi_handedness[idx].classification[0]
            hand_type = handed.label
            score = float(handed.score)

            if score < HAND_SCORE_MIN:
                continue
            if not valid_hand_shape(hlm.landmark):
                continue

            if hand_type == "Left":
                left_landmarks = hlm.landmark
                left_score = score
            else:
                right_landmarks = hlm.landmark
                right_score = score
    else:
        left_landmarks = None
        right_landmarks = None

    # 1) Lock system is ALWAYS processed (even when locked)
    modes.update_lock(left_landmarks, right_landmarks)

    # If locked: release everything and skip all other logic
    if modes.locked:
        clicks.force_release_left()
        shortcuts.force_release_alt()
        mouse.reset()

        # Clear gesture queues so nothing triggers on unlock
        gesture_queue_left.clear()
        gesture_queue_right.clear()

        confirmed_left = None
        confirmed_right = None

        # UI labels
        debug_label.config(text="Left: LOCKED | Right: LOCKED", fg="#ff5252")
        gesture_label.config(text="Gesture: SYSTEM LOCKED (hold open palm 1s to unlock)")

    else:
        # 2) Shortcuts (Alt-tab) have priority over scroll/mouse
        shortcuts.update(left_landmarks, right_landmarks)

        # 3) Scroll mode (three fingers) next priority
        modes.update_scroll(left_landmarks, right_landmarks)

        # If scrolling or Alt held, pause click/drag
        if shortcuts.alt_held or modes.scroll_active:
            clicks.force_release_left()
        else:
            # Normal gesture processing
            if result.multi_hand_landmarks and result.multi_handedness:
                for idx, hlm in enumerate(result.multi_hand_landmarks):
                    handed = result.multi_handedness[idx].classification[0]
                    hand_type = handed.label
                    score = float(handed.score)

                    if score < HAND_SCORE_MIN:
                        continue
                    if not valid_hand_shape(hlm.landmark):
                        continue

                    for gesture in GESTURES:
                        if gesture.detect(hlm.landmark, hand_type):
                            if hand_type == "Left":
                                frame_gesture_left = gesture.name
                            else:
                                frame_gesture_right = gesture.name
                                if gesture.name == "PeaceSign":
                                    mouse.update(hlm.landmark, hand_type)
                                    clicks.update(hlm.landmark)

        # Slide gesture queues (only when not locked and not in scroll mode)
        if not modes.scroll_active and not shortcuts.alt_held:
            gesture_queue_left.append(frame_gesture_left)
            if len(gesture_queue_left) > GESTURE_FRAMES_REQUIRED:
                gesture_queue_left.pop(0)

            confirmed_left = None
            if (
                len(gesture_queue_left) == GESTURE_FRAMES_REQUIRED
                and gesture_queue_left.count(gesture_queue_left[0]) == len(gesture_queue_left)
                and gesture_queue_left[0] is not None
            ):
                confirmed_left = gesture_queue_left[0]

            gesture_queue_right.append(frame_gesture_right)
            if len(gesture_queue_right) > GESTURE_FRAMES_REQUIRED:
                gesture_queue_right.pop(0)

            confirmed_right = None
            if (
                len(gesture_queue_right) == GESTURE_FRAMES_REQUIRED
                and gesture_queue_right.count(gesture_queue_right[0]) == len(gesture_queue_right)
                and gesture_queue_right[0] is not None
            ):
                confirmed_right = gesture_queue_right[0]
        else:
            confirmed_left = None
            confirmed_right = None
            gesture_queue_left.clear()
            gesture_queue_right.clear()

        # Trigger non-mouse gestures
        now = time.time()
        if confirmed_right and confirmed_right != "PeaceSign" and (now - last_action_time > COOLDOWN):
            trigger_action(confirmed_right, "Right")
            last_action_time = now
            gesture_queue_right = []
        if confirmed_left and (now - last_action_time > COOLDOWN):
            trigger_action(confirmed_left, "Left")
            last_action_time = now
            gesture_queue_left = []

        # UI labels
        debug_label.config(
            text=f"Left: {confirmed_left if confirmed_left else 'None'} | Right: {confirmed_right if confirmed_right else 'None'}",
            fg="lime",
        )
        gesture_label.config(text=f"Gesture: {confirmed_left or confirmed_right or 'None'}")

    # Status line
    status_parts = ["MOUSE ON" if mouse.enabled else "MOUSE OFF"]
    if modes.locked:
        status_parts.append("LOCKED")
    if modes.scroll_active:
        status_parts.append("SCROLL")
    if mouse.freeze_active():
        status_parts.append("FREEZE")
    if clicks.left_is_held:
        status_parts.append("DRAGGING")
    if shortcuts.alt_held:
        status_parts.append("ALT-HELD")
    if (left_landmarks is not None) and (not modes.locked):
        status_parts.append(f"L:{left_score:.2f}")
    if (right_landmarks is not None) and (not modes.locked):
        status_parts.append(f"R:{right_score:.2f}")

    status_label.config(text="Status: " + " | ".join(status_parts))

    # Show most recent event across controllers
    if modes.event_visible():
        event_label.config(text=f"Event: {modes.last_event_text}")
    elif shortcuts.event_visible():
        event_label.config(text=f"Event: {shortcuts.last_event_text}")
    elif clicks.event_visible():
        event_label.config(text=f"Event: {clicks.last_event_text}")
    else:
        event_label.config(text="Event: —")

    # Preview rendering + overlay
    now = time.time()
    if now - last_ui_time >= (1.0 / UI_HZ):
        last_ui_time = now

        if SHOW_LANDMARKS and result.multi_hand_landmarks:
            for hlm in result.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hlm, mp_hands.HAND_CONNECTIONS)
                if SHOW_LANDMARK_NUMBERS:
                    draw_landmark_numbers(frame, hlm)

        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(image=img)
        camera_label.imgtk = imgtk
        camera_label.config(image=imgtk)

    frame_time_ms = (time.time() - frame_start) * 1000.0
    delay = FRAME_DELAY_MS if frame_time_ms < 30 else 1
    root.after(delay, update_frame)

root.mainloop()
