# agent.md - AI Agent Development Guide

Quick reference for AI assistants working on this gesture recognition project.

## Quick Start Commands

### Setup
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Run Application
```bash
python app.py
```

### Development Requirements
- **Python 3.10.x** (REQUIRED - MediaPipe unstable on 3.11+)
- All dependencies in `requirements.txt`

---

## Architecture Summary

**Data Flow:**
```
Camera Frame → camera.py → MediaPipe Hand Tracking → gestures/ 
→ actions.py → Controllers → System Actions
```

**Key Principle:** Gesture detection is SEPARATE from system control.

---

## File Responsibilities

| File | Responsibility |
|------|---|
| `app.py` | Main loop, frame processing, gesture coordination |
| `camera.py` | Webcam capture, frame preprocessing |
| `gestures/*.py` | Hand landmark analysis, gesture detection |
| `actions.py` | Gesture → action mapping |
| `*_controller.py` | System control (mouse, click, keyboard, mode) |
| `ui_*.py` | UI/UX components |

---

## Adding Features

### Add a New Gesture
1. Create `gestures/my_gesture.py`
2. Inherit from `Gesture` in `gesture_base.py`
3. Implement `detect(hand_landmarks)` → returns gesture name or None
4. Add mapping in `actions.py` → what the gesture does

### Add a New Action
1. Update `actions.py` to handle gesture → system command
2. Use existing controllers or create new one if needed
3. Keep gesture logic OUT of controllers

---

## Important Rules

### DO
✅ Add new gestures in `/gestures` as separate files  
✅ Keep controllers focused on system interaction  
✅ Use **ASCII-only** for console logs (no Unicode arrows)  
✅ Maintain Python 3.10 compatibility  
✅ Keep heavy operations outside frame loop  

### DON'T
❌ Put gesture detection inside controllers  
❌ Block the frame loop  
❌ Mix UI logic with gesture detection  
❌ Commit `venv/`, `__pycache__/`, `*.pyc`  

---

## Console Logging Format

**Correct:**
```python
print("[GESTURE] SwipeLeft detected")
print("[ACTION] SwipeLeft --> Next Slide")
print("[MOUSE] Movement: (100, 200)")
```

**Wrong:**
```python
print("SwipeLeft → Next Slide")  # Unicode arrow causes issues
```

Use **[TAG]** prefix for clarity. ASCII only.

---

## Common Tasks

### Debug Gesture Detection
Check `gestures/` files → look at hand landmark logic  
Verify gesture name matches mapping in `actions.py`

### Improve Mouse Performance
Edit `mouse_controller.py` → smoothing, sensitivity, deadzone

### Add UI Feature
Create new file `ui_feature.py` → keep separate from logic

### Test New Gesture
1. Add to `gestures/`
2. Map in `actions.py`
3. Run `python app.py`
4. Test with webcam

---

## Performance Targets
- Camera capture: ~30 FPS
- UI rendering: ~15 FPS
- Optimization: Frame downscaling, mouse smoothing, async operations

---

## AI Assistant Workflow

When asked to work on this project:

1. **Understand the request** - clarify scope and requirements
2. **Check existing code** - how is this done elsewhere?
3. **Follow architecture** - use the patterns established
4. **Test changes** - run `python app.py` to verify
5. **Keep it modular** - separate concerns by file

---

## File References

- **CLAUDE.md** - Detailed architecture & system design
- **README.txt** - Project documentation
- **requirements.txt** - All Python dependencies
- **.gitignore** - Excluded files (venv, pycache, etc.)

---

Last updated: Session-based development guide
