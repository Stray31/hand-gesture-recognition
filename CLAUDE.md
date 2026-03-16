# Gesture Slide Controller — AI Assistant Guide

This file helps AI assistants understand the architecture and coding rules of this thesis project.

The goal is to allow AI tools (ChatGPT, Claude, Copilot) to quickly understand the system without needing long conversation context.

---

# Project Overview

This project is a **vision-based hand gesture computer controller**.

It allows users to control the computer using **hand gestures captured from a webcam**.

The system uses:

• MediaPipe (hand tracking)  
• OpenCV (camera processing)  
• PyAutoGUI (system control)  
• Tkinter (UI display)

Core capabilities include:

- Mouse movement using hand tracking
- Left / Right click gestures
- Dragging
- Slide navigation gestures
- Alt-Tab switching
- System lock gesture
- Pinch scrolling

The application runs in **real-time using webcam input**.

---

# Required Environment

Python version required:


Python 3.10.x


MediaPipe is unstable on Python 3.11+.

Setup environment:


python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt


Do NOT commit:


venv/
pycache/
*.pyc


---

# Actual Project Structure


THESIS OFFICIAL/
│
├── gestures/
│ ├── init.py
│ ├── gesture_base.py
│ ├── swipe_left.py
│ ├── swipe_right.py
│ └── peace_sign.py
│
├── actions.py
├── app.py
├── camera.py
├── click_controller.py
├── mouse_controller.py
├── shortcut_controller.py
├── mode_controller.py
├── utils.py
│
├── requirements.txt
├── README.txt
├── CLAUDE.md
└── .gitignore


---

# System Architecture

The gesture pipeline follows this order:


Camera
↓
camera.py
↓
MediaPipe hand tracking
↓
gesture detection (gestures/)
↓
actions.py
↓
controllers
↓
system actions (mouse / keyboard)


---

# Main Files

### app.py
Main application entry point.

Responsibilities:

- Initialize camera
- Run MediaPipe
- Process frames
- Detect gestures
- Coordinate controllers
- Render UI

This file drives the **main frame loop**.

---

### camera.py

Handles webcam interaction.

Responsibilities:

- Webcam initialization
- Frame capture
- Frame preprocessing
- Frame resizing for MediaPipe

---

# Gesture System

Located in:


gestures/


Files:


gesture_base.py
swipe_left.py
swipe_right.py
peace_sign.py


Each gesture:

- inherits from `Gesture` (gesture_base.py)
- analyzes hand landmarks
- returns a gesture name if detected

Example return value:


"SWIPE_LEFT"


New gestures must be implemented as **separate files inside `/gestures`**.

---

# Controllers

Controllers execute system actions.

These files must **never contain gesture detection logic**.

### mouse_controller.py

Handles:

- cursor movement
- smoothing
- sensitivity
- deadzone filtering

---

### click_controller.py

Handles:

- left click
- right click
- click hold / drag
- click state

---

### shortcut_controller.py

Handles keyboard shortcuts such as:

- Alt + Tab
- Window switching

---

### mode_controller.py

Handles:

- system lock gesture
- pinch scroll mode
- interaction mode switching

---

# Gesture → Action Mapping

Handled inside:


actions.py


This file maps gestures to controller actions.

Example:


SWIPE_LEFT → Next Slide
SWIPE_RIGHT → Previous Slide


Uses `pyautogui`.

---

# Frame Processing Loop

Main loop:

1. Capture frame from webcam
2. Process frame with MediaPipe
3. Extract hand landmarks
4. Run gesture detectors
5. Map gesture to action
6. Execute controller command
7. Render UI

---

# Performance Goals

Target performance:

- Camera capture: ~30 FPS
- UI rendering: ~15 FPS

Optimization methods:

- Downscale frames before MediaPipe
- Smooth mouse movement
- Avoid blocking operations in frame loop

---

# Logging Rule (Important)

All console logs must use **ASCII characters only**.

Correct:


print("[ACTION] SwipeLeft -> Next Slide")


Wrong:


print("SwipeLeft → Next Slide")


Unicode arrows cause Windows encoding errors.

---

# Development Rules

When modifying the project:

DO NOT:

- put gesture logic inside controllers
- block the frame loop
- mix responsibilities across modules

DO:

- add new gestures inside `/gestures`
- keep controllers responsible for system interaction
- keep gesture detection modular

---

# AI Assistant Instructions

When generating code for this project:

1. Follow the existing architecture
2. Keep gesture detection separate from controllers
3. Avoid heavy operations inside the frame loop
4. Maintain Python 3.10 compatibility
5. Respect the project file structure

---

# Maintainers

Thesis project developers.

Primary developer: Luke