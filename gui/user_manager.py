class _WebcamCaptureDialog(QDialog):
    #Shows a live webcam feed User presses Space or clicks Capture and registers the face immediately also can be used while monitoring is running in the background

    def __init__(self, face_engine, name: str, parent=None):
        super().__init__(parent)
        self.face_engine = face_engine
        self.name        = name
        self._cap        = None
        self._captured   = None   # numpy frame

        self.setWindowTitle(f"Webcam Capture — {name}")
        self.setFixedSize(520, 460)
        self.setStyleSheet("""
            QDialog { background: #0f1117; color: #e0e6f0; font-family: 'Segoe UI'; }
            QLabel#feedLbl { background: #1a1f2e; border: 1px dashed #2a3a4a; border-radius: 6px; }
            QLabel#instrLbl { color: #7a9aaa; font-size: 12px; }
            QPushButton#captureBtn {
                background: #003a2a; border: 1px solid #00aa66;
                border-radius: 6px; color: #00ff99; font-size: 14px;
                font-weight: 700; padding: 10px 28px;
            }
            QPushButton#captureBtn:hover { background: #005a3a; }
            QPushButton#retakeBtn {
                background: #1a1f2e; border: 1px solid #2a3a4a;
                border-radius: 6px; color: #7a8ba0; font-size: 13px; padding: 9px 20px;
            }
            QPushButton#cancelBtn {
                background: #1a1f2e; border: 1px solid #2a3a4a;
                border-radius: 6px; color: #7a8ba0; font-size: 13px; padding: 9px 20px;
            }
        """)
        self._build_ui()
        self._start_webcam()

    def _build_ui(self):
        import cv2
        from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 16, 20, 16)
        self.feed_lbl = QLabel("Starting webcam...")
        self.feed_lbl.setObjectName("feedLbl")
        self.feed_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feed_lbl.setFixedHeight(340)
        lay.addWidget(self.feed_lbl)
        self.instr_lbl = QLabel(f"Position face clearly, then click Capture  ·  Registering as: {self.name}")
        self.instr_lbl.setObjectName("instrLbl")
        self.instr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.instr_lbl)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(self.btn_cancel)
        self.btn_retake = QPushButton("↩  Retake")
        self.btn_retake.setObjectName("retakeBtn")
        self.btn_retake.setVisible(False)
        self.btn_retake.clicked.connect(self._retake)
        btn_row.addWidget(self.btn_retake)
        self.btn_capture = QPushButton("📷  Capture & Register")
        self.btn_capture.setObjectName("captureBtn")
        self.btn_capture.clicked.connect(self._capture)
        btn_row.addWidget(self.btn_capture)
        lay.addLayout(btn_row)

        # Timer for live feed
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_feed)

    def _start_webcam(self):
        import cv2
        self._cap = cv2.VideoCapture(0)
        if self._cap.isOpened():
            self._timer.start(33)
        else:
            self.feed_lbl.setText("Could not open webcam it may be in use by monitoring.")

    def _update_feed(self):
        import cv2
        from PyQt6.QtGui import QImage, QPixmap
        if self._cap is None or not self._cap.isOpened():
            return
        ret, frame = self._cap.read()
        if not ret:
            return
        self._current_frame = frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qt_img)
        self.feed_lbl.setPixmap(
            pix.scaled(self.feed_lbl.width(), self.feed_lbl.height(),
                       Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        )

    def _capture(self):
        import cv2, os, tempfile
        from PyQt6.QtWidgets import QMessageBox
        if not hasattr(self, '_current_frame') or self._current_frame is None:
            QMessageBox.warning(self, "No Frame", "Webcam not ready.")
            return
        self._timer.stop()
        frame = self._current_frame
        tmp_path = os.path.join(tempfile.gettempdir(), f"pg_quickreg_{id(self)}.jpg")
        cv2.imwrite(tmp_path, frame)
        self.btn_capture.setText("⏳  Processing...")
        self.btn_capture.setEnabled(False)
        self.btn_cancel.setEnabled(False)

        import threading
        def _do_register():
            success = self.face_engine.register_face(tmp_path, self.name)
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._on_register_done(success))
        threading.Thread(target=_do_register, daemon=True).start()

    def _on_register_done(self, success: bool):
        from PyQt6.QtWidgets import QMessageBox
        if success:
            QMessageBox.information(self, "Registered",
                f"✅  '{self.name}' registered successfully!"
                "They will be recognized as authorized from the next frame.")
            self._cleanup()
            self.accept()
        else:
            QMessageBox.critical(self, "No Face Detected",
                "No face found in that frame, please try again with better lighting.")
            self._retake()

    def _retake(self):
        self.btn_capture.setText("📷  Capture & Register")
        self.btn_capture.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.btn_retake.setVisible(False)
        self._timer.start(33)

    def _cancel(self):
        self._cleanup()
        self.reject()

    def _cleanup(self):
        self._timer.stop()
        if self._cap:
            self._cap.release()
            self._cap = None

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        from PyQt6.QtCore import Qt as QtCore
        if event.key() == QtCore.Key.Key_Space:
            self._capture()
        elif event.key() == QtCore.Key.Key_Escape:
            self._cancel()
        else:
            super().keyPressEvent(event)

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class UserManagerDialog(QDialog):
    #Dialog for adding / removing authorized users
    def __init__(self, face_engine, parent=None):
        super().__init__(parent)
        self.face_engine = face_engine
        self.setWindowTitle("Manage Authorized Users — PrivacyGuard")
        self.setFixedSize(480, 500)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)
        title = QLabel("Authorized Users")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        subtitle = QLabel(
            "These people will NOT trigger intruder alerts\n"
            "You can add or remove users at any time, even during monitoring"
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        layout.addWidget(self._divider())

        self.user_list = QListWidget()
        self.user_list.setObjectName("userList")
        self.user_list.setMinimumHeight(240)
        layout.addWidget(self.user_list)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_add = QPushButton("➕  Add User")
        self.btn_add.setObjectName("addBtn")
        self.btn_add.clicked.connect(self._add_user)
        btn_row.addWidget(self.btn_add)

        self.btn_webcam = QPushButton("📷  Quick Webcam")
        self.btn_webcam.setObjectName("webcamBtn")
        self.btn_webcam.clicked.connect(self._quick_webcam_register)
        btn_row.addWidget(self.btn_webcam)

        self.btn_remove = QPushButton("🗑  Remove Selected")
        self.btn_remove.setObjectName("removeBtn")
        self.btn_remove.clicked.connect(self._remove_selected)
        btn_row.addWidget(self.btn_remove)
        layout.addLayout(btn_row)
        layout.addWidget(self._divider())
        self.btn_close = QPushButton("Close")
        self.btn_close.setObjectName("closeBtn")
        self.btn_close.clicked.connect(self.accept)
        layout.addWidget(self.btn_close)

    def _quick_webcam_register(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Enter Name", "Name for this person:")
        if not ok or not name.strip():
            return
        dlg = _WebcamCaptureDialog(self.face_engine, name.strip(), parent=self)
        if dlg.exec():
            self._refresh_list()

    def _refresh_list(self):
        #Reload the user list from the face engine
        self.user_list.clear()
        users = self.face_engine.list_authorized_users()
        if not users:
            placeholder = QListWidgetItem("  No authorized users registered yet")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.user_list.addItem(placeholder)
            return
        counts: dict[str, int] = {}
        for name in self.face_engine.authorized_names:
            counts[name] = counts.get(name, 0) + 1
        for user in users:
            n = counts.get(user, 0)
            item = QListWidgetItem(f"  👤  {user}    ({n} image{'s' if n != 1 else ''} registered)")
            item.setData(Qt.ItemDataRole.UserRole, user)   # store raw name
            self.user_list.addItem(item)

    def _add_user(self):
        from gui.setup_wizard import SetupWizard
        wizard = SetupWizard(self.face_engine, parent=self, edit_mode=True)
        wizard.exec()
        self._refresh_list()

    def _remove_selected(self):
        item = self.user_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            QMessageBox.information(self, "No Selection", "Please select a user to remove")
            return

        name = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Confirm Removal",
            f"Remove '{name}' from authorized users?\n\nThey will be treated as an intruder",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            removed = self.face_engine.remove_face(name)
            if removed > 0:
                QMessageBox.information(self, "Removed", f"✅  '{name}' removed ({removed} image(s) deleted)")
            else:
                QMessageBox.warning(self, "Not Found", f"Could not find files for '{name}'.")
            self._refresh_list()

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
        QLabel#panelTitle {
            font-size: 18px;
            font-weight: 700;
            color: #00e5ff;
        }
        QLabel#subtitle {
            font-size: 12px;
            color: #7a8ba0;
        }
        QListWidget#userList {
            background: #1a1f2e;
            border: 1px solid #2a3a4a;
            border-radius: 8px;
            color: #d0dce8;
            font-size: 13px;
            padding: 6px;
        }
        QListWidget#userList::item { padding: 10px 6px; border-radius: 4px; }
        QListWidget#userList::item:selected { background: #1e3a50; color: #00e5ff; }
        QListWidget#userList::item:hover { background: #1a2a3a; }
        QPushButton#addBtn {
            background: #003a2a;
            border: 1px solid #00aa66;
            border-radius: 6px;
            color: #00ff99;
            padding: 9px 20px;
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton#addBtn:hover { background: #005a3a; }
        QPushButton#webcamBtn {
            background: #0a1a3a; border: 1px solid #2a4a8a;
            border-radius: 6px; color: #80aaff; padding: 9px 14px; font-size: 13px;
        }
        QPushButton#webcamBtn:hover { background: #102050; }
        QPushButton#removeBtn {
            background: #3a0a0a;
            border: 1px solid #cc2222;
            border-radius: 6px;
            color: #ff6666;
            padding: 9px 20px;
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton#removeBtn:hover { background: #500a0a; }
        QPushButton#closeBtn {
            background: #1a1f2e;
            border: 1px solid #2a3a4a;
            border-radius: 6px;
            color: #7a8ba0;
            padding: 9px 20px;
            font-size: 13px;
        }
        QPushButton#closeBtn:hover { background: #242938; }
        QFrame#divider { color: #1e2a38; }
        """