import threading
import time

import cv2


class CameraManager:
    def __init__(self, index=0, width=640, height=360):
        self.index = index
        self.width = width
        self.height = height
        self.cap = None

        self._reader_thread = None
        self._running = False
        self._lock = threading.Lock()
        self._latest_frame = None
        self._last_frame_time = 0.0
        self._read_failures = 0

    def start(self):
        if self._running and self.cap is not None:
            return True

        start_t = time.time()

        self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = None
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._running = True
        self._latest_frame = None
        self._last_frame_time = 0.0
        self._read_failures = 0

        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            name="GestureFlowCamera",
            daemon=True,
        )
        self._reader_thread.start()

        deadline = time.time() + 2.0
        while self._latest_frame is None and time.time() < deadline and self._running:
            time.sleep(0.01)

        if self._latest_frame is None:
            self.release()
            return False

        print(f"[CAMERA] Opened in {time.time() - start_t:.2f}s")
        return True

    def _reader_loop(self):
        while self._running and self.cap is not None:
            ok, frame = self.cap.read()
            if ok and frame is not None:
                with self._lock:
                    self._latest_frame = frame
                    self._last_frame_time = time.time()
                self._read_failures = 0
                continue

            self._read_failures += 1
            if self._read_failures >= 15:
                self._restart_capture()
                self._read_failures = 0
            time.sleep(0.01)

    def _restart_capture(self):
        if self.cap is not None:
            self.cap.release()

        self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
        if self.cap is None or not self.cap.isOpened():
            self.cap = None
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def read(self, max_age=0.35):
        if not self._running or self.cap is None:
            return False, None

        with self._lock:
            frame = None if self._latest_frame is None else self._latest_frame.copy()
            frame_time = self._last_frame_time

        if frame is None:
            return False, None
        if frame_time and (time.time() - frame_time) > max_age:
            return False, None
        return True, frame

    def release(self):
        self._running = False

        if self._reader_thread is not None:
            self._reader_thread.join(timeout=0.5)
            self._reader_thread = None

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        with self._lock:
            self._latest_frame = None
            self._last_frame_time = 0.0
