import os
import cv2
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox, QFrame, QSizePolicy,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QImage, QPixmap

class RegisterWorker(QObject):
    finished = pyqtSignal(bool)   

    def __init__(self, face_engine, image_path: str, name: str):
        super().__init__()
        self.face_engine = face_engine
        self.image_path = image_path
        self.name = name

    def run(self):
        result = self.face_engine.register_face(self.image_path, self.name)
        self.finished.emit(result)

class SetupWizard(QDialog):
    #Modal dialog for registering a new authorized face
    def __init__(self, face_engine, parent=None, edit_mode: bool = False):
        super().__init__(parent)
        self.face_engine = face_engine
        self.edit_mode = edit_mode
        self.captured_image_path: str | None = None
        self.webcam_capture = None
        self.webcam_timer = QTimer()
        self.webcam_timer.timeout.connect(self._update_webcam_preview)
        self._worker = None
        self._thread = None
        self.setWindowTitle("Register Authorized User — PrivacyGuard")
        self.setFixedSize(560, 650)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Register Authorized User" if not self.edit_mode else "Add New Face")
        title.setObjectName("wizardTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        subtitle = QLabel(
            "Register a face so PrivacyGuard knows who is authorized\n"
            "You can add multiple people as authorized viewers"
        )
        subtitle.setObjectName("wizardSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        layout.addWidget(self._divider())
        name_label = QLabel("Person's Name")
        name_label.setObjectName("fieldLabel")
        layout.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g.  Kambaqt, Manhoos, User 1")
        self.name_input.setObjectName("nameInput")
        layout.addWidget(self.name_input)
        preview_label = QLabel("Face Preview")
        preview_label.setObjectName("fieldLabel")
        layout.addWidget(preview_label)
        self.preview = QLabel("No image selected")
        self.preview.setObjectName("previewBox")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setFixedHeight(220)
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.preview)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_file = QPushButton("📂  Choose Photo from Disk")
        self.btn_file.setObjectName("actionBtn")
        self.btn_file.clicked.connect(self._choose_file)
        btn_row.addWidget(self.btn_file)
        self.btn_webcam = QPushButton("📷  Capture from Webcam")
        self.btn_webcam.setObjectName("actionBtn")
        self.btn_webcam.clicked.connect(self._toggle_webcam)
        btn_row.addWidget(self.btn_webcam)
        layout.addLayout(btn_row)
        self.btn_snap = QPushButton("🔴  Take Snapshot")
        self.btn_snap.setObjectName("snapBtn")
        self.btn_snap.setVisible(False)
        self.btn_snap.clicked.connect(self._take_snapshot)
        layout.addWidget(self.btn_snap)
        self.progress = QProgressBar()
        self.progress.setObjectName("progressBar")
        self.progress.setRange(0, 0)   
        self.progress.setFixedHeight(6)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        self.progress_label = QLabel("Analyzing face... please wait")
        self.progress_label.setObjectName("progressLabel")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        layout.addWidget(self._divider())
        bottom_row = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.clicked.connect(self._cancel)
        bottom_row.addWidget(self.btn_cancel)
        self.btn_register = QPushButton("✅  Register Face")
        self.btn_register.setObjectName("registerBtn")
        self.btn_register.clicked.connect(self._register)
        bottom_row.addWidget(self.btn_register)
        layout.addLayout(bottom_row)

    def _toggle_webcam(self):
        if self.webcam_capture is None:
            self.webcam_capture = cv2.VideoCapture(0)
            if not self.webcam_capture.isOpened():
                QMessageBox.warning(self, "Webcam Error", "Could not open webcam.")
                self.webcam_capture = None
                return
            self.btn_webcam.setText("⏹  Stop Webcam")
            self.btn_snap.setVisible(True)
            self.webcam_timer.start(33)   # ~30fps preview
        else:
            self._stop_webcam()
            self.btn_webcam.setText("📷  Capture from Webcam")

    def _update_webcam_preview(self):
        if self.webcam_capture is None:
            return
        ret, frame = self.webcam_capture.read()
        if ret:
            self._show_cv_frame(frame)

    def _take_snapshot(self):
        if self.webcam_capture is None:
            return
        ret, frame = self.webcam_capture.read()
        if ret:
            import sys
            _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(_root, "data", "authorized_faces", "__temp_snapshot__" + str(id(self)) + ".jpg")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            cv2.imwrite(path, frame)
            self.captured_image_path = path
            self._stop_webcam()
            self.btn_webcam.setText("📷  Capture from Webcam")
            self._show_cv_frame(frame)
            self.btn_snap.setVisible(False)

    def _stop_webcam(self):
        self.webcam_timer.stop()
        if self.webcam_capture:
            self.webcam_capture.release()
            self.webcam_capture = None

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Face Image", "",
            "Images (*.jpg *.jpeg *.png *.bmp)"
        )
        if path:
            self.captured_image_path = path
            img = cv2.imread(path)
            if img is not None:
                self._show_cv_frame(img)

    def _register(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Enter a name for this person.")
            return
        if not self.captured_image_path:
            QMessageBox.warning(self, "No Image", "Choose or capture a face photo.")
            return
        self._set_controls_enabled(False)
        self.progress.setVisible(True)
        self.progress_label.setVisible(True)
        self._thread = QThread()
        self._worker = RegisterWorker(self.face_engine, self.captured_image_path, name)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_register_done)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_register_done(self, success: bool):
        # Cleanup temp snapshot
        if self.captured_image_path and self.captured_image_path.endswith("__temp_snapshot__.jpg"):
            try:
                os.remove(self.captured_image_path)
            except Exception:
                pass
        self.progress.setVisible(False)
        self.progress_label.setVisible(False)
        self._set_controls_enabled(True)
        if success:
            name = self.name_input.text().strip()
            QMessageBox.information(self, "Success", f"✅  '{name}' registered successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "No Face Detected",
                                 "No face was found in that image\n")

    def _set_controls_enabled(self, enabled: bool):
        self.btn_register.setEnabled(enabled)
        self.btn_cancel.setEnabled(enabled)
        self.btn_file.setEnabled(enabled)
        self.btn_webcam.setEnabled(enabled)
        self.name_input.setEnabled(enabled)
        if not enabled:
            self.btn_register.setText("⏳  Processing...")
        else:
            self.btn_register.setText("✅  Register Face")

    def _cancel(self):
        self._stop_webcam()
        self.reject()

    def closeEvent(self, event):
        self._stop_webcam()
        super().closeEvent(event)

    def _show_cv_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.preview.setPixmap(
            pixmap.scaled(self.preview.width(), self.preview.height(),
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
        )

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("divider")
        return line

    def _stylesheet(self):
        return """
        QDialog {
            background-color: #0f1117;
            color: #e0e6f0;
            font-family: 'Segoe UI', sans-serif;
        }
        QLabel#wizardTitle {
            font-size: 20px;
            font-weight: 700;
            color: #00e5ff;
            letter-spacing: 1px;
        }
        QLabel#wizardSubtitle {
            font-size: 12px;
            color: #7a8ba0;
        }
        QLabel#fieldLabel {
            font-size: 12px;
            font-weight: 600;
            color: #a0b0c0;
            margin-top: 4px;
        }
        QLabel#progressLabel {
            font-size: 11px;
            color: #00b8d4;
        }
        QLineEdit#nameInput {
            background: #1a1f2e;
            border: 1px solid #2a3a4a;
            border-radius: 6px;
            color: #e0e6f0;
            padding: 8px 12px;
            font-size: 14px;
        }
        QLineEdit#nameInput:focus { border: 1px solid #00e5ff; }
        QLabel#previewBox {
            background: #1a1f2e;
            border: 1px dashed #2a3a4a;
            border-radius: 8px;
            color: #4a5a6a;
            font-size: 13px;
        }
        QPushButton#actionBtn {
            background: #1a2a3a;
            border: 1px solid #2a4a6a;
            border-radius: 6px;
            color: #80c8e8;
            padding: 9px 16px;
            font-size: 13px;
        }
        QPushButton#actionBtn:hover { background: #1e3a50; border-color: #00b8d4; }
        QPushButton#actionBtn:disabled { color: #3a5060; border-color: #1a2a3a; }
        QPushButton#snapBtn {
            background: #3a0a0a;
            border: 1px solid #cc2222;
            border-radius: 6px;
            color: #ff6666;
            padding: 9px 16px;
            font-size: 13px;
        }
        QPushButton#snapBtn:hover { background: #500a0a; }
        QPushButton#registerBtn {
            background: #003a2a;
            border: 1px solid #00aa66;
            border-radius: 6px;
            color: #00ff99;
            padding: 10px 24px;
            font-size: 14px;
            font-weight: 600;
        }
        QPushButton#registerBtn:hover { background: #005a3a; }
        QPushButton#registerBtn:disabled { background: #001a10; color: #006644; border-color: #004422; }
        QPushButton#cancelBtn {
            background: #1a1f2e;
            border: 1px solid #2a3a4a;
            border-radius: 6px;
            color: #7a8ba0;
            padding: 10px 24px;
            font-size: 14px;
        }
        QPushButton#cancelBtn:hover { background: #242938; }
        QPushButton#cancelBtn:disabled { color: #3a4a5a; }
        QProgressBar#progressBar {
            background: #1a1f2e;
            border: none;
            border-radius: 3px;
        }
        QProgressBar#progressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #00b8d4, stop:1 #00e5ff);
            border-radius: 3px;
        }
        QFrame#divider { color: #1e2a38; }
        """