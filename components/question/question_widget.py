# question/question_widget.py
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QProgressBar
from PySide6.QtCore import Qt

class QuestionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #101010;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setAlignment(Qt.AlignCenter)

        # Boot Title
        title = QLabel("Ask a question.")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            background-color: #101010;
            color: white;
            font-size: 48px;
            font-weight: bold;
            font-family: 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
            padding: 40px;
            border-radius: 20px;
        """)

        layout.addWidget(title)