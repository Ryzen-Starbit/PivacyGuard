import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QFont
from core.face_engine import FaceEngine
from gui.main_window import MainWindow
from gui.setup_wizard import SetupWizard

def main():
    os.chdir(PROJECT_ROOT)
    app = QApplication(sys.argv)
    app.setApplicationName("PrivacyGuard AI")
    app.setOrganizationName("PrivacyGuard")
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    face_engine = FaceEngine(data_dir=os.path.join(PROJECT_ROOT, "data", "authorized_faces"))
    face_engine.load_authorized_faces()
    if not face_engine.list_authorized_users():
        print("[Startup] No authorized users found — opening setup wizard.")
        wizard = SetupWizard(face_engine)
        result = wizard.exec()
        if result != SetupWizard.DialogCode.Accepted:
            reply = QMessageBox.question(
                None,
                "No Authorized User",
                "You haven't registered an authorized face.\n\n"
                "PrivacyGuard will flag EVERYONE as an intruder.\n\n"
                "Continue without registering?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                sys.exit(0)
    window = MainWindow(face_engine)
    window.show()
    sys.exit(app.exec())
if __name__ == "__main__":
    main()