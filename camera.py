import cv2
import time


class CameraManager:
    def __init__(self, index=0, width=640, height=360):
        self.index = index
        self.width = width
        self.height = height
        self.cap = None

    def start(self):
        if self.cap is not None:
            return True

        start_t = time.time()

        # Windows: DirectShow usually opens much faster than default backend
        self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            self.cap = None
            return False

        # Keep startup simple and lightweight
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        # Do NOT force FPS yet; some webcams stall when this is set
        # self.cap.set(cv2.CAP_PROP_FPS, 30)

        # warm up a few frames
        for _ in range(5):
            self.cap.read()

        print(f"[CAMERA] Opened in {time.time() - start_t:.2f}s")
        return True

    def read(self):
        if self.cap is None:
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None