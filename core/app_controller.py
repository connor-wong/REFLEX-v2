# core/app_controller.py
from PySide6.QtWidgets import QStackedWidget

class AppController(QStackedWidget):
    def __init__(self, boot_widget, vision_widget, question_widget):
        super().__init__()
        self.addWidget(boot_widget)
        self.addWidget(vision_widget)
        self.addWidget(question_widget)

        self.boot_widget = boot_widget
        self.vision_widget = vision_widget
        self.question_widget = question_widget

        self.current_mode = 0
        self.set_mode(0)  # Start in boot mode

    def set_mode(self, mode: int):
        if mode == self.current_mode:
            return

        # Pause old mode
        # if self.current_mode == 1:
        #     self.vision_widget.pauseEvent()

        self.current_mode = mode

        # Show new screen
        self.setCurrentIndex(mode)  # 0 = boot, 1 = vision, 2 = question

        # Resume new mode
        if mode == 0:  # Boot mode
            self.boot_widget.progress_bar.setValue(0)
        elif mode == 1: # Vision mode
            self.vision_widget.resumeEvent()