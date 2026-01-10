# vision/vision_widget.py
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QImage
import cv2
import time
import threading
import queue
from ultralytics import YOLO

# Custom
from .custom_label import custom_annotate_segmentation

# Config
from config import MODEL_PATH, CAMERA_ID, IMG_SIZE


class VisionWidget(QWidget):
    palm_held = Signal()  # Custom signal emitted when "Palms" held for 3s
    thumb_held = Signal() # Custom signal emitted when "Thumbs up" held for 3s

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #000000;")
        self.setup_ui()

        # Palm tracking
        self.palm_detected = False
        self.palm_start_time = None
        self.PALM_HOLD_DURATION = 3.0

        self.start_vision_pipeline()

    def set_controller(self, controller):
        """Allow external access to the AppController"""
        self.controller = controller

    def current_mode(self) -> int:
        """Safely get current mode, returns -1 if controller not set"""
        if self.controller is None:
            return -1
        return self.controller.current_mode
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video display
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setScaledContents(True)
        self.video_label.setStyleSheet("background-color: #000000;")

        layout.addWidget(self.video_label)

        # FPS overlay (child of video_label for proper overlay)
        self.fps_label = QLabel("FPS: --", self.video_label)
        self.fps_label.move(10, 10)
        self.fps_label.setStyleSheet("""
            color: lime;
            font-size: 28px;
            font-weight: bold;
            padding: 12px 18px;
            background-color: rgba(0, 0, 0, 140);
            border-radius: 12px;
        """)
        self.fps_label.adjustSize()

    def start_vision_pipeline(self):
        self.model = YOLO(MODEL_PATH, task="segment")

        self.cap = cv2.VideoCapture(CAMERA_ID, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(CAMERA_ID)

        if not self.cap.isOpened():
            self.video_label.setText("Error: Could not open camera")
            return

        self.frame_q = queue.Queue(maxsize=1)
        self.result_q = queue.Queue(maxsize=1)
        self.stop_event = threading.Event()

        self.capture_thread = threading.Thread(target=self.capture_worker, daemon=True)
        self.inference_thread = threading.Thread(target=self.inference_worker, daemon=True)

        self.capture_thread.start()
        self.inference_thread.start()

        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_display)
        self.display_timer.start(30)

        self.last_time = time.time()
        self.frame_count = 0

    def capture_worker(self):
        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            if self.frame_q.full():
                try:
                    self.frame_q.get_nowait()
                except queue.Empty:
                    pass
            self.frame_q.put(frame)

    def inference_worker(self):
        while not self.stop_event.is_set():
            try:
                frame = self.frame_q.get(timeout=0.1)
            except queue.Empty:
                continue

            results = self.model(frame, imgsz=IMG_SIZE, verbose=False)

            # Vision mode
            if self.current_mode() == 1:
                # Check if "Palms" class is detected in this frame
                palm_detected_now = any("Palms" in results[0].names.get(cls_id, "") for cls_id in results[0].boxes.cls.int().tolist())

                # Update palm hold state
                if palm_detected_now:
                    if not self.palm_detected:
                        # First detection
                        self.palm_detected = True
                        self.palm_start_time = time.time()

                    elif (time.time() - self.palm_start_time) >= self.PALM_HOLD_DURATION: # Held for 3+ seconds → emit signal once
                        if not hasattr(self, '_palm_signal_emitted'):
                            self._palm_signal_emitted = True
                            self.palm_held.emit()  # Trigger mode change
                else:
                    # Palm not visible → reset
                    self.palm_detected = False
                    self.palm_start_time = None
                    if hasattr(self, '_palm_signal_emitted'):
                        del self._palm_signal_emitted  # Allow future triggers

                # Remap class names
                name_map = {
                    "Long hair": "Tie your hair",
                    "Lower legs": "Wear long pants",
                    "Exposed feet": "Wear covered shoes",
                    "Upper arms": "Wear short sleeve shirt"
                }

                for idx, label in results[0].names.items():
                    if label in name_map:
                        results[0].names[idx] = name_map[label]

                # Custom annotation
                annotated = custom_annotate_segmentation(
                    image=results[0].orig_img,
                    results=results[0],
                    alpha=0.4,
                    font_scale=0.7,
                    text_thickness=1,
                    box_thickness=2
                )

                if self.result_q.full():
                    try:
                        self.result_q.get_nowait()
                    except queue.Empty:
                        pass

                self.result_q.put(annotated)

    def update_display(self):
        if self.result_q.empty():
            return

        frame = self.result_q.get()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        scaled = pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled)

        # Update FPS
        self.frame_count += 1
        now = time.time()
        if now - self.last_time >= 1.0:
            fps = self.frame_count / (now - self.last_time)
            self.fps_label.setText(f"FPS: {fps:.1f}")
            self.fps_label.adjustSize()
            self.frame_count = 0
            self.last_time = now

    # =====================
    # Events
    # =====================

    def closeEvent(self, event):
        self.stop_event.set()
        if hasattr(self, "display_timer"):
            self.display_timer.stop()
        if hasattr(self, "cap"):
            self.cap.release()
        if event:
            event.accept()

    def pauseEvent(self):
        """Pause capture and inference"""
        if hasattr(self, 'stop_event'):
            self.stop_event.set()  # Signal threads to stop

        if hasattr(self, 'display_timer'):
            self.display_timer.stop()

        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()

        # Clear any pending frames
        while not self.result_q.empty():
            try:
                self.result_q.get_nowait()
            except:
                pass

        self.video_label.clear()
        self.video_label.setText("Vision Paused")
        self.fps_label.setText("FPS: --")

    def resumeEvent(self):
        """Resume capture and inference"""
        if hasattr(self, 'stop_event') and self.stop_event.is_set():
            self.start_vision_pipeline() # Restart everything