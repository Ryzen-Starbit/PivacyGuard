from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QFont, QKeySequence, QShortcut

class PrivacyOverlay(QWidget):
    """
    A translucent fullscreen window that obscures screen contents
    Shown automatically on intrusion; dismissed by user button or hotkey
    """

    def __init__(self, on_dismiss_callback=None):
        super().__init__()
        self.on_dismiss_callback = on_dismiss_callback
        self._blinking = False
        self._blink_state = True
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool                  
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowOpacity(0.92)
        self._build_ui()

        shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        shortcut.activated.connect(self._dismiss)
        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self._toggle_blink)
        self._blink_timer.start(600)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        self.alert_label = QLabel("⚠  INTRUDER DETECTED")
        self.alert_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alert_label.setStyleSheet("""
            color: #ff4040;
            font-family: 'Segoe UI', monospace;
            font-size: 36px;
            font-weight: 800;
            letter-spacing: 4px;
        """)
        layout.addWidget(self.alert_label)
        self.sub_label = QLabel("Screen protected — unauthorized viewer detected nearby.")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet("""
            color: #cc8888;
            font-size: 15px;
            font-family: 'Segoe UI', sans-serif;
        """)
        layout.addWidget(self.sub_label)
        self.dismiss_btn = QPushButton("✅  I'm Safe — Remove Overlay")
        self.dismiss_btn.setFixedSize(280, 48)
        self.dismiss_btn.clicked.connect(self._dismiss)
        self.dismiss_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 80, 40, 200);
                border: 2px solid #00cc66;
                border-radius: 10px;
                color: #00ff99;
                font-size: 14px;
                font-weight: 700;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background: rgba(0, 120, 60, 220);
            }
        """)
        layout.addWidget(self.dismiss_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("Press  Esc  to dismiss")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #664444; font-size: 11px; font-family: 'Segoe UI';")
        layout.addWidget(hint)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(10, 10, 20, 230)
        painter.fillRect(self.rect(), color)
        if self._blink_state:
            painter.setPen(QColor(200, 30, 30, 180))
            from PyQt6.QtGui import QPen
            pen = QPen(QColor(200, 30, 30, 180))
            pen.setWidth(6)
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(3, 3, -3, -3))

    def showFullScreen(self):
        super().showFullScreen()

    def show_overlay(self):
        #Expand to cover the entire screen and show
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    def hide_overlay(self):
        self.hide()

    def _dismiss(self):
        self.hide_overlay()
        if self.on_dismiss_callback:
            self.on_dismiss_callback()

    def _toggle_blink(self):
        self._blink_state = not self._blink_state
        self.update()   