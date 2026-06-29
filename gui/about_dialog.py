import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
VERSION = "1.0.0"
PHASES  = "Phases 1–6 Complete"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
class AboutDialog(QDialog):
    def __init__(self, perf_manager=None, parent=None):
        super().__init__(parent)
        self.perf_manager = perf_manager
        self.setWindowTitle("About PrivacyGuard AI")
        self.setFixedSize(480, 520)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(28, 24, 28, 24)
        title = QLabel("🛡  PrivacyGuard AI")
        title.setObjectName("bigTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        ver = QLabel(f"Version {VERSION}  ·  {PHASES}")
        ver.setObjectName("versionLabel")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ver)
        tagline = QLabel("Real-time privacy protection using AI & computer vision")
        tagline.setObjectName("tagline")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setWordWrap(True)
        lay.addWidget(tagline)
        lay.addWidget(self._divider())
        lay.addWidget(self._section("FEATURES"))
        features = [
            ("👤", "Authorized face recognition"),
            ("👁",  "Real-time eye gaze tracking"),
            ("🧍", "Shoulder surfing detection"),
            ("📸", "Auto intruder capture + screenshot"),
            ("🗄",  "SQLite intrusion database"),
            ("📊", "Analytics dashboard + PDF export"),
            ("🔔", "Desktop notifications + tray icon"),
            ("⚙",  "Configurable settings + lightweight mode"),
        ]
        grid = QGridLayout()
        grid.setSpacing(4)
        for i, (icon, text) in enumerate(features):
            row, col = divmod(i, 2)
            lbl = QLabel(f"{icon}  {text}")
            lbl.setObjectName("featureLabel")
            grid.addWidget(lbl, row, col)
        lay.addLayout(grid)
        lay.addWidget(self._divider())
        lay.addWidget(self._section("SYSTEM"))
        sys_grid = QGridLayout()
        sys_grid.setSpacing(4)

        import platform
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        sys_items = [
            ("Python",    py_ver),
            ("Platform",  platform.system() + " " + platform.release()),
        ]
        if self.perf_manager:
            storage = self.perf_manager.get_storage_stats()
            disk    = self.perf_manager.check_disk_space()
            sys_items += [
                ("Captures",    f"{storage['captures']['count']} files  ({storage['captures']['size_mb']} MB)"),
                ("Screenshots", f"{storage['screenshots']['count']} files  ({storage['screenshots']['size_mb']} MB)"),
                ("Free Disk",   f"{disk['free_gb']} GB"),
            ]
        for i, (k, v) in enumerate(sys_items):
            row, col = divmod(i, 1)
            lbl = QLabel(f"<span style='color:#5a8a9a'>{k}:</span>  {v}")
            lbl.setObjectName("sysLabel")
            sys_grid.addWidget(lbl, i, 0)
        lay.addLayout(sys_grid)
        lay.addStretch()
        lay.addWidget(self._divider())
        credit = QLabel("Built as an AI/ML portfolio project")
        credit.setObjectName("creditLabel")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(credit)
        btn = QPushButton("Close")
        btn.setObjectName("closeBtn")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)

    def _section(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("sectionLabel")
        return lbl

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("divider")
        return line

    def _stylesheet(self):
        return """
        QDialog { background: #0f1117; color: #d0dce8; font-family: 'Segoe UI', sans-serif; }
        QLabel#bigTitle { font-size: 22px; font-weight: 800; color: #00e5ff; letter-spacing: 2px; }
        QLabel#versionLabel { font-size: 12px; color: #4a8a9a; }
        QLabel#tagline { font-size: 12px; color: #7a9aaa; }
        QLabel#sectionLabel { font-size: 10px; font-weight: 700; color: #3a5a6a; letter-spacing: 2px; }
        QLabel#featureLabel { font-size: 12px; color: #a0b8c8; padding: 2px 0; }
        QLabel#sysLabel { font-size: 11px; color: #8ab0c0; font-family: 'Consolas', monospace; }
        QLabel#creditLabel { font-size: 11px; color: #3a5a6a; }
        QPushButton#closeBtn {
            background: #111622; border: 1px solid #1a2a38; border-radius: 6px;
            color: #7a8ba0; font-size: 13px; padding: 8px;
        }
        QPushButton#closeBtn:hover { background: #1a2030; }
        QFrame#divider { color: #1a2a38; }
        """