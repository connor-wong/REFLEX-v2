# main.py
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QTimer

# Widgets
from components.boot.boot_widget import BootWidget
from components.vision.vision_widget import VisionWidget
from components.question.question_widget import QuestionWidget

# Config
from config import WINDOW_WIDTH, WINDOW_HEIGHT

# Core
from core.app_controller import AppController

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("REFLEX UI")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet("background-color: #101010;")

        # Create widgets
        boot = BootWidget()
        vision = VisionWidget()
        question = QuestionWidget()

        # Controller manages switching and pausing
        self.controller = AppController(boot, vision, question)
        self.setCentralWidget(self.controller)  

        # Give VisionWidget access to the controller
        vision.set_controller(self.controller)

        # Connect palm gesture → switch to question mode
        vision.palm_held.connect(lambda: self.controller.set_mode(2))

        # Start boot animation (3 seconds total boot time)
        self.start_boot_animation(duration_ms=3000)

    def start_boot_animation(self, duration_ms):
        """Animate the boot progress bar smoothly over the given duration"""
        steps = 100  # 1% increments for super smooth
        interval_ms = duration_ms // steps
        progress = 0

        def update():
            nonlocal progress
            progress += 1
            self.controller.boot_widget.progress_bar.setValue(progress)

            if progress < 100:
                QTimer.singleShot(interval_ms, update)
            else:
                self.controller.set_mode(1) # Boot complete → switch to vision mode

        # Start the animation
        QTimer.singleShot(interval_ms, update)


app = QApplication([])
app.setStyle("Fusion")

window = MainWindow()
window.show()

app.exec()