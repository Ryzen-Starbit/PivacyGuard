from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter
from PyQt6.QtCore import Qt, QSize

def _make_shield_icon(color: str = "#00e5ff") -> QIcon:
    size = 32
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    from PyQt6.QtGui import QBrush, QPen, QPolygonF
    from PyQt6.QtCore import QPointF
    shield = QPolygonF([
        QPointF(16,  2),
        QPointF(30,  8),
        QPointF(30, 18),
        QPointF(16, 30),
        QPointF( 2, 18),
        QPointF( 2,  8),
    ])
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon(shield)
    painter.end()
    return QIcon(pixmap)

class TrayManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.tray = None
        self._monitoring = False

    def setup(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("[TrayManager] System tray not available on this system.")
            return
        self.tray = QSystemTrayIcon(self.main_window)
        self.tray.setIcon(_make_shield_icon("#00e5ff"))
        self.tray.setToolTip("PrivacyGuard AI — Idle")
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #111622; color: #d0dce8;
                border: 1px solid #1a2a38; font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
                padding: 4px;
            }
            QMenu::item { padding: 7px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #1e3a50; color: #00e5ff; }
            QMenu::separator { background: #1a2a38; height: 1px; margin: 4px 8px; }
        """)
        self.action_show = menu.addAction("🛡  Show Dashboard")
        self.action_show.triggered.connect(self._show_window)
        menu.addSeparator()
        self.action_toggle = menu.addAction("▶  Start Monitoring")
        self.action_toggle.triggered.connect(self._toggle_monitoring)
        menu.addSeparator()
        action_quit = menu.addAction("✕  Quit PrivacyGuard")
        action_quit.triggered.connect(self._quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def set_status(self, status: str):
        if self.tray is None:
            return
        colors = {
            "idle":       "#4a6a7a",
            "monitoring": "#00e5ff",
            "alert":      "#ff3333",
        }
        labels = {
            "idle":       "PrivacyGuard AI — Idle",
            "monitoring": "PrivacyGuard AI — Monitoring",
            "alert":      "PrivacyGuard AI — ⚠ INTRUDER DETECTED",
        }
        self.tray.setIcon(_make_shield_icon(colors.get(status, "#00e5ff")))
        self.tray.setToolTip(labels.get(status, "PrivacyGuard AI"))
        if status == "monitoring":
            self._monitoring = True
            self.action_toggle.setText("⏹  Stop Monitoring")
        elif status == "idle":
            self._monitoring = False
            self.action_toggle.setText("▶  Start Monitoring")

    def show_alert_balloon(self, title: str, message: str):
        if self.tray and self.tray.isVisible():
            self.tray.showMessage(
                title, message,
                QSystemTrayIcon.MessageIcon.Warning,
                4000   # ms
            )

    def hide_tray(self):
        if self.tray:
            self.tray.hide()

    def _show_window(self):
        self.main_window.showNormal()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _toggle_monitoring(self):
        self.main_window._toggle_monitoring()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _quit(self):
        self.main_window._stop_monitoring()
        self.hide_tray()
        QApplication.quit()