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

    def _refresh_list(self):
        """Reload the user list from the face engine."""
        self.user_list.clear()
        users = self.face_engine.list_authorized_users()
        if not users:
            placeholder = QListWidgetItem("  No authorized users registered yet.")
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
            QMessageBox.information(self, "No Selection", "Please select a user to remove.")
            return

        name = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Confirm Removal",
            f"Remove '{name}' from authorized users?\n\nThey will be treated as an intruder.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            removed = self.face_engine.remove_face(name)
            if removed > 0:
                QMessageBox.information(self, "Removed", f"✅  '{name}' removed ({removed} image(s) deleted).")
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