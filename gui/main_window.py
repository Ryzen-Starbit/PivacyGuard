import os
import cv2
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame, QCheckBox,
    QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QImage, QPixmap
from gui.settings_panel import load_settings

class CaptureWorker(QObject):
    done = pyqtSignal(int, str, str)
    def __init__(self, capture_engine, db_manager, frame, face_location,
                 threat_level, face_count, unknown_count, reason,
                 gaze_direction, shoulder_surf):
        super().__init__()
        self.capture_engine = capture_engine
        self.db_manager     = db_manager
        self.frame          = frame.copy()
        self.face_location  = face_location
        self.threat_level   = threat_level
        self.face_count     = face_count
        self.unknown_count  = unknown_count
        self.reason         = reason
        self.gaze_direction = gaze_direction
        self.shoulder_surf  = shoulder_surf

    def run(self):
        record_id = self.db_manager.log_intrusion(
            threat_level=self.threat_level,
            face_count=self.face_count,
            unknown_count=self.unknown_count,
            reason=self.reason,
            gaze_direction=self.gaze_direction,
            shoulder_surf=self.shoulder_surf,
        )
        intruder_path, screenshot_path = self.capture_engine.save_both(
            self.frame, self.face_location
        )
        self.db_manager.update_paths(record_id, intruder_path, screenshot_path)
        self.done.emit(record_id, intruder_path, screenshot_path)

class FrameWorker(QObject):
    analysis_ready = pyqtSignal(object, object, object)
    error = pyqtSignal(str)
    def __init__(self, face_engine, gaze_tracker):
        super().__init__()
        self.face_engine    = face_engine
        self.gaze_tracker   = gaze_tracker
        self._running       = False
        self._cap           = None
        self._frame_skip    = 2
        self._frame_counter = 0

    def start_capture(self):
        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            self.error.emit("Could not open webcam.")
            return
        self._running = True
        self._loop()

    def _loop(self):
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                continue
            self._frame_counter += 1
            if self._frame_counter % self._frame_skip != 0:
                self.analysis_ready.emit(None, None, frame)
                continue
            analysis = self.face_engine.analyze_frame(frame)
            gaze = self.gaze_tracker.analyze(frame)
            if gaze and analysis.annotated_frame is not None:
                self.gaze_tracker.annotate_frame(analysis.annotated_frame, gaze)
            self.analysis_ready.emit(analysis, gaze, frame)
            QThread.msleep(1)
        if self._cap:
            self._cap.release()

    def stop(self):
        self._running = False

class MainWindow(QMainWindow):
    def __init__(self, face_engine):
        super().__init__()
        self.face_engine       = face_engine
        self.monitoring        = False
        self.overlay_enabled   = True
        self.overlay_dismissed = False
        self._last_analysis    = None
        self._last_raw_frame   = None
        self._worker           = None
        self._thread           = None
        self._overlay_window   = None
        self._prev_threat      = "LOW"
        self._capture_threads  = []
        self._threat_clear_count = 0

        cfg = load_settings()
        self._alert_cooldown        = 0
        self._alert_cooldown_max    = cfg["alert_cooldown_sec"] * 30
        self._capture_cooldown      = 0
        self._capture_cooldown_max  = cfg["capture_cooldown_sec"] * 30
        self._absence_alert_enabled = cfg["absence_alert_enabled"]
        self._absence_alert_sec     = cfg["absence_alert_sec"]
        self._absence_frames        = 0         
        self._absence_alerted       = False      
        self._tray_on_minimize      = cfg["tray_on_minimize"]
        from core.gaze_tracker   import GazeTracker
        from core.threat_engine  import ThreatEngine
        from alerts.notification import NotificationManager
        self.gaze_tracker  = GazeTracker()
        self.threat_engine = ThreatEngine()
        self.notif_manager = NotificationManager(cooldown_seconds=12)
        from core.capture_engine import CaptureEngine
        from database.db_manager import DBManager
        self.capture_engine = CaptureEngine()
        self.db_manager     = DBManager()
        self.db_manager.init()
        from core.frame_processor import PerformanceManager
        self.perf_manager = PerformanceManager()
        self.perf_manager.set_lightweight(cfg.get("lightweight_mode", False))
        disk = self.perf_manager.check_disk_space()
        if not disk["ok"]:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Low Disk Space",
                f"⚠ {disk['warning']}\nCaptures may fail.")
        if cfg.get("auto_cleanup_enabled", False):
            self.perf_manager.cleanup_old_files(days=cfg.get("auto_cleanup_days", 30))

        from gui.tray_manager import TrayManager
        self.tray_manager = TrayManager(self)
        self.tray_manager.setup()
        self.setWindowTitle("PrivacyGuard AI  —  Privacy & Intruder Monitor")
        self.setMinimumSize(1160, 720)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()
        self._init_overlay()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._build_header())
        content = QHBoxLayout()
        content.setSpacing(0)
        content.setContentsMargins(12, 12, 12, 12)
        content.addWidget(self._build_feed_panel(), stretch=3)
        content.addSpacing(12)
        content.addWidget(self._build_status_panel(), stretch=1)
        root.addLayout(content, stretch=1)
        root.addWidget(self._build_control_bar())

    def _build_header(self):
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(54)
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(20, 0, 20, 0)
        logo = QLabel("🛡  PrivacyGuard AI")
        logo.setObjectName("logoLabel")
        hlay.addWidget(logo)
        hlay.addStretch()
        self.status_pill = QLabel("● IDLE")
        self.status_pill.setObjectName("idlePill")
        hlay.addWidget(self.status_pill)
        return header

    def _build_feed_panel(self):
        panel = QFrame()
        panel.setObjectName("feedPanel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        self.feed_label = QLabel()
        self.feed_label.setObjectName("feedLabel")
        self.feed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feed_label.setText("Webcam feed will appear here.\nPress  START MONITORING  below.")
        self.feed_label.setMinimumSize(640, 480)
        self.feed_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(self.feed_label)
        return panel

    def _build_status_panel(self):
        panel = QFrame()
        panel.setObjectName("statusPanel")
        panel.setFixedWidth(290)
        lay = QVBoxLayout(panel)
        lay.setSpacing(8)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.addWidget(self._section_label("LIVE STATUS"))
        self.card_user     = self._status_card("Authorized User",  "—",    "neutral")
        self.card_faces    = self._status_card("Faces Detected",   "0",    "neutral")
        self.card_threat   = self._status_card("Threat Level",     "—",    "neutral")
        self.card_intruder = self._status_card("Intruder",         "NONE", "safe")
        self.card_gaze     = self._status_card("Gaze Direction",   "—",    "neutral")
        self.card_shoulder = self._status_card("Shoulder Surfing", "NONE", "safe")
        self.card_absence  = self._status_card("User Absence",     "OK",   "safe")
        self.card_captures = self._status_card("Captures Today",   "0",    "neutral")
        self.card_fps      = self._status_card("Live FPS",         "—",    "neutral")

        for card in [self.card_user, self.card_faces, self.card_threat,
                     self.card_intruder, self.card_gaze, self.card_shoulder,
                     self.card_absence, self.card_captures, self.card_fps]:
            lay.addWidget(card)

        lay.addWidget(self._divider())
        lay.addWidget(self._section_label("ALERT LOG"))
        self.alert_log = QTextEdit()
        self.alert_log.setObjectName("alertLog")
        self.alert_log.setReadOnly(True)
        self.alert_log.setPlaceholderText("No alerts yet...")
        lay.addWidget(self.alert_log, stretch=1)
        btn_clear = QPushButton("Clear Log")
        btn_clear.setObjectName("clearLogBtn")
        btn_clear.clicked.connect(self.alert_log.clear)
        lay.addWidget(btn_clear)
        return panel

    def _build_control_bar(self):
        bar = QFrame()
        bar.setObjectName("controlBar")
        bar.setFixedHeight(64)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(12)

        self.btn_monitor = QPushButton("▶  START MONITORING")
        self.btn_monitor.setObjectName("startBtn")
        self.btn_monitor.setFixedHeight(42)
        self.btn_monitor.setFixedWidth(210)
        self.btn_monitor.clicked.connect(self._toggle_monitoring)
        lay.addWidget(self.btn_monitor)
        lay.addWidget(self._vdivider())
        btn_users = QPushButton("👥  Manage Users")
        btn_users.setObjectName("controlBtn")
        btn_users.setFixedHeight(42)
        btn_users.clicked.connect(self._open_user_manager)
        lay.addWidget(btn_users)
        lay.addWidget(self._vdivider())
        btn_logs = QPushButton("📋  View Logs")
        btn_logs.setObjectName("controlBtn")
        btn_logs.setFixedHeight(42)
        btn_logs.clicked.connect(self._open_log_viewer)
        lay.addWidget(btn_logs)
        lay.addWidget(self._vdivider())
        btn_analytics = QPushButton("📊  Analytics")
        btn_analytics.setObjectName("controlBtn")
        btn_analytics.setFixedHeight(42)
        btn_analytics.clicked.connect(self._open_analytics)
        lay.addWidget(btn_analytics)
        lay.addWidget(self._vdivider())
        btn_settings = QPushButton("⚙  Settings")
        btn_settings.setObjectName("controlBtn")
        btn_settings.setFixedHeight(42)
        btn_settings.clicked.connect(self._open_settings)
        lay.addWidget(btn_settings)
        lay.addWidget(self._vdivider())
        self.overlay_checkbox = QCheckBox("Privacy Overlay")
        self.overlay_checkbox.setObjectName("overlayCheck")
        self.overlay_checkbox.setChecked(True)
        self.overlay_checkbox.stateChanged.connect(self._overlay_toggled)
        lay.addWidget(self.overlay_checkbox)
        lay.addStretch()
        btn_about = QPushButton("ℹ  About")
        btn_about.setObjectName("controlBtn")
        btn_about.setFixedHeight(42)
        btn_about.clicked.connect(self._open_about)
        lay.addWidget(btn_about)
        return bar

    def _init_overlay(self):
        from gui.overlay_window import PrivacyOverlay
        self._overlay_window = PrivacyOverlay(on_dismiss_callback=self._on_overlay_dismissed)

    def _overlay_toggled(self, state):
        self.overlay_enabled = bool(state)
        if not self.overlay_enabled and self._overlay_window:
            self._overlay_window.hide_overlay()

    def _on_overlay_dismissed(self):
        self.overlay_dismissed = True
        self._log_alert("ℹ  Overlay dismissed by user.")

    def _show_overlay_if_needed(self, intruder: bool):
        if not self.overlay_enabled or self._overlay_window is None:
            return
        if intruder:
            self._threat_clear_count = 0
            if not self.overlay_dismissed:
                if not self._overlay_window.isVisible():
                    self._overlay_window.show_overlay()
                    self.tray_manager.set_status("alert")
        else:
            self._threat_clear_count += 1
            if self._threat_clear_count >= 90:
                self.overlay_dismissed = False
                self._threat_clear_count = 0
            if self._overlay_window.isVisible():
                self._overlay_window.hide_overlay()
            if self.monitoring:
                self.tray_manager.set_status("monitoring")

    def _toggle_monitoring(self):
        if not self.monitoring:
            self._start_monitoring()
        else:
            self._stop_monitoring()

    def _start_monitoring(self):
        if not self.face_engine.list_authorized_users():
            reply = QMessageBox.question(
                self, "No Authorized Users",
                "No authorized faces registered.\nContinue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self._open_user_manager()
                return
        self.monitoring        = True
        self._absence_frames   = 0
        self._absence_alerted  = False
        self._capture_cooldown = 0
        self.btn_monitor.setText("⏹  STOP MONITORING")
        self.btn_monitor.setObjectName("stopBtn")
        self.status_pill.setText("● MONITORING")
        self.status_pill.setObjectName("activePill")
        self._refresh_stylesheet()
        self.tray_manager.set_status("monitoring")
        self._thread = QThread()
        self._worker = FrameWorker(self.face_engine, self.gaze_tracker)
        self._worker.moveToThread(self._thread)
        self._worker.analysis_ready.connect(self._handle_analysis)
        self._worker.error.connect(self._handle_webcam_error)
        self._thread.started.connect(self._worker.start_capture)
        self._thread.start()

    def _stop_monitoring(self):
        self._threat_clear_count = 0
        self.overlay_dismissed = False
        self.face_engine.reset_buffers()
        self.monitoring = False
        self.btn_monitor.setText("▶  START MONITORING")
        self.btn_monitor.setObjectName("startBtn")
        self.status_pill.setText("● IDLE")
        self.status_pill.setObjectName("idlePill")
        self._refresh_stylesheet()
        self.tray_manager.set_status("idle")
        if self._worker:
            self._worker.stop()
        if self._thread:
            self._thread.quit()
            self._thread.wait(2000)
        if self._overlay_window:
            self._overlay_window.hide_overlay()

        self.feed_label.setText("Monitoring stopped.\nPress  START MONITORING  to resume.")
        self._reset_cards()

    def _handle_webcam_error(self, msg):
        self._stop_monitoring()
        QMessageBox.critical(self, "Webcam Error", msg)

    def _handle_analysis(self, analysis, gaze, raw_frame):
        self._last_raw_frame = raw_frame
        if not self.monitoring:
            return
        frame_to_show = (analysis.annotated_frame
                         if (analysis and analysis.annotated_frame is not None)
                         else raw_frame)
        if frame_to_show is not None:
            self._display_frame(frame_to_show)

        self.perf_manager.fps_tracker.tick()
        fps = self.perf_manager.fps_tracker.fps
        if fps > 0:
            self._set_card(self.card_fps, f"{fps:.1f}", "safe" if fps >= 15 else "warning")
        if analysis is None:
            return
        self._last_analysis   = analysis
        # Lightweight mode — skip gaze
        if self.perf_manager.lightweight:
            gaze = None
        gaze_on_screen        = gaze.is_looking_at_screen if gaze else False
        gaze_direction        = gaze.gaze_direction if gaze else "UNKNOWN"
        threat = self.threat_engine.assess(
            total_faces=analysis.total_faces,
            authorized_count=analysis.authorized_count,
            unknown_count=analysis.unknown_count,
            gaze_on_screen=gaze_on_screen,
            gaze_direction=gaze_direction,
            authorized_present=analysis.authorized_count > 0,
        )
        emoji = self.threat_engine.level_emoji(threat.level)
        absence_text  = "OK"
        absence_state = "safe"
        if self._absence_alert_enabled and self.face_engine.list_authorized_users():
            if analysis.authorized_count == 0 and analysis.total_faces == 0:
                self._absence_frames += 1
                fps_threshold = self._absence_alert_sec * 30
                elapsed_sec   = int(self._absence_frames / 30)
                if self._absence_frames >= fps_threshold and not self._absence_alerted:
                    self._absence_alerted = True
                    ts = datetime.now().strftime("%H:%M:%S")
                    self._log_alert(f"👤 [{ts}] Authorized user absent for {self._absence_alert_sec}s — computer may be unattended")
                    self.notif_manager.send_user_absent_alert()
                    self.tray_manager.show_alert_balloon(
                        "⚠ User Absent — PrivacyGuard",
                        "Authorized user left the camera view."
                    )
                if elapsed_sec > 0:
                    absence_text  = f"ABSENT {elapsed_sec}s"
                    absence_state = "warning" if elapsed_sec < self._absence_alert_sec else "danger"
            else:
                if self._absence_alerted:
                    ts = datetime.now().strftime("%H:%M:%S")
                    self._log_alert(f"✅ [{ts}] Authorized user returned")
                self._absence_frames  = 0
                self._absence_alerted = False

        auth_text   = "PRESENT" if analysis.authorized_count > 0 else ("—" if analysis.total_faces == 0 else "ABSENT")
        auth_state  = "safe" if analysis.authorized_count > 0 else ("danger" if analysis.total_faces > 0 else "neutral")
        face_state  = "safe" if analysis.total_faces <= 1 else "danger"
        t_state     = {"LOW": "safe", "MEDIUM": "warning", "HIGH": "danger"}.get(threat.level, "neutral")
        intr_text   = "⚠ DETECTED" if threat.intruder_detected else "NONE"
        intr_state  = "danger" if threat.intruder_detected else "safe"
        gaze_state  = "safe" if gaze_on_screen else "neutral"
        shld_text   = "⚠ DETECTED" if analysis.shoulder_surfing_detected else "NONE"
        shld_state  = "danger" if analysis.shoulder_surfing_detected else "safe"
        stats = self.db_manager.get_stats()
        self._set_card(self.card_user,     auth_text,                 auth_state)
        self._set_card(self.card_faces,    str(analysis.total_faces), face_state)
        self._set_card(self.card_threat,   f"{emoji} {threat.level}", t_state)
        self._set_card(self.card_intruder, intr_text,                 intr_state)
        self._set_card(self.card_gaze,     gaze_direction if gaze else "N/A", gaze_state)
        self._set_card(self.card_shoulder, shld_text,                 shld_state)
        self._set_card(self.card_absence,  absence_text,              absence_state)
        self._set_card(self.card_captures, str(stats["today"]),       "neutral")
        self._show_overlay_if_needed(threat.intruder_detected)
        prev_num = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "—": -1}.get(self._prev_threat, -1)
        curr_num = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "—": -1}.get(threat.level, -1)
        if threat.should_alert and curr_num > prev_num:
            self.notif_manager.send_intruder_alert(
                face_count=analysis.total_faces,
                threat_level=threat.level,
                reason=threat.reason
            )
            self.tray_manager.show_alert_balloon(
                f"⚠ {threat.level} Threat — PrivacyGuard",
                threat.reason
            )
        self._capture_cooldown -= 1
        if threat.intruder_detected and self._capture_cooldown <= 0:
            face_loc = next(
                (f.location for f in analysis.faces if not f.is_authorized), None
            )
            self._trigger_capture(
                frame=raw_frame, face_location=face_loc,
                threat_level=threat.level,
                face_count=analysis.total_faces,
                unknown_count=analysis.unknown_count,
                reason=threat.reason,
                gaze_direction=gaze_direction,
                shoulder_surf=analysis.shoulder_surfing_detected,
            )
            self._capture_cooldown = self._capture_cooldown_max
        self._prev_threat = threat.level
        self._alert_cooldown -= 1
        if threat.intruder_detected and self._alert_cooldown <= 0:
            ts = datetime.now().strftime("%H:%M:%S")
            self._log_alert(
                f"⚠ [{ts}] {emoji} {threat.level} — {threat.reason}"
                + (f" | Gaze: {gaze_direction}" if gaze else "")
                + (" | ⚠ Shoulder surf" if analysis.shoulder_surfing_detected else "")
            )
            self._alert_cooldown = self._alert_cooldown_max
        if not threat.intruder_detected and self._prev_threat in ("MEDIUM", "HIGH"):
            ts = datetime.now().strftime("%H:%M:%S")
            self._log_alert(f"✅ [{ts}] Threat cleared")

    def _trigger_capture(self, frame, face_location, threat_level, face_count,
                          unknown_count, reason, gaze_direction, shoulder_surf):
        import threading

        def _do_capture():
            try:
                record_id = self.db_manager.log_intrusion(
                    threat_level=threat_level,
                    face_count=face_count,
                    unknown_count=unknown_count,
                    reason=reason,
                    gaze_direction=gaze_direction,
                    shoulder_surf=shoulder_surf,
                )
                intruder_path, screenshot_path = self.capture_engine.save_both(
                    frame.copy(), face_location
                )
                self.db_manager.update_paths(record_id, intruder_path, screenshot_path)
                # Use QTimer to call back on main thread safely
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._on_capture_done(
                    record_id, intruder_path, screenshot_path
                ))
            except Exception as e:
                print(f"[Capture] Error: {e}")
                import traceback
                traceback.print_exc()

        t = threading.Thread(target=_do_capture, daemon=True)
        t.start()

    def _on_capture_done(self, record_id, intruder_path, screenshot_path):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_alert(f"📸 [{ts}] Evidence saved — Record #{record_id}")

    def _cleanup_thread(self, thread, worker):
        try:
            self._capture_threads.remove((thread, worker))
        except ValueError:
            pass

    def _display_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)
        self.feed_label.setPixmap(
            pixmap.scaled(
                self.feed_label.width(), self.feed_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

    def _status_card(self, title, value, state):
        card = QFrame()
        card.setObjectName("statusCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(10, 7, 10, 7)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("cardTitle")
        lay.addWidget(title_lbl)
        lay.addStretch()
        value_lbl = QLabel(value)
        value_lbl.setObjectName("cardValue")
        lay.addWidget(value_lbl)
        self._set_card(card, value, state)
        return card

    def _set_card(self, card, value, state):
        vl = card.findChild(QLabel, "cardValue")
        if vl:
            vl.setText(value)
            colors = {"neutral":"#4a5a6a","safe":"#00cc66","warning":"#ffaa00","danger":"#ff3333"}
            vl.setStyleSheet(f"color:{colors.get(state,'#4a5a6a')};font-size:13px;font-weight:700;")

    def _reset_cards(self):
        for card, val, state in [
            (self.card_user,     "—",    "neutral"),
            (self.card_faces,    "0",    "neutral"),
            (self.card_threat,   "—",    "neutral"),
            (self.card_intruder, "NONE", "safe"),
            (self.card_gaze,     "—",    "neutral"),
            (self.card_shoulder, "NONE", "safe"),
            (self.card_absence,  "OK",   "safe"),
            (self.card_captures, "0",    "neutral"),
            (self.card_fps,      "—",    "neutral"),
        ]:
            self._set_card(card, val, state)

    def _log_alert(self, text):
        self.alert_log.append(text)
        self.alert_log.verticalScrollBar().setValue(
            self.alert_log.verticalScrollBar().maximum()
        )

    def _open_user_manager(self):
        from gui.user_manager import UserManagerDialog
        UserManagerDialog(self.face_engine, parent=self).exec()

    def _open_log_viewer(self):
        from gui.log_viewer import LogViewerDialog
        LogViewerDialog(self.db_manager, parent=self).exec()

    def _open_analytics(self):
        from gui.analytics_panel import AnalyticsDialog
        AnalyticsDialog(self.db_manager, parent=self).exec()

    def _open_settings(self):
        from gui.settings_panel import SettingsDialog
        SettingsDialog(self.face_engine, self, parent=self).exec()

    def _open_about(self):
        from gui.about_dialog import AboutDialog
        AboutDialog(self.perf_manager, parent=self).exec()

    def _apply_lightweight_mode(self, enabled: bool):
        """Called from settings — update gaze label in control bar."""
        if enabled:
            self._log_alert("ℹ  Lightweight mode ON — gaze tracking disabled")
        else:
            self._log_alert("ℹ  Lightweight mode OFF — gaze tracking enabled")

    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        if (event.type() == QEvent.Type.WindowStateChange
                and self.isMinimized()
                and self._tray_on_minimize):
            event.ignore()
            self.hide()
            self.tray_manager.show_alert_balloon(
                "PrivacyGuard AI",
                "Running in background. Double-click tray icon to restore."
            )
        else:
            super().changeEvent(event)

    def closeEvent(self, event):
        self._stop_monitoring()
        self.tray_manager.hide_tray()
        if self._overlay_window:
            self._overlay_window.close()
        event.accept()

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("sectionLabel")
        return lbl

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("divider")
        return line

    def _vdivider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setObjectName("vdivider")
        return line

    def _refresh_stylesheet(self):
        self.setStyleSheet(self._stylesheet())

    def _stylesheet(self):
        return """
        QMainWindow, QWidget {
            background-color: #0b0e15; color: #d0dce8;
            font-family: 'Segoe UI', sans-serif;
        }
        QFrame#header {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0f1520,stop:1 #0b1828);
            border-bottom: 1px solid #1a2a3a;
        }
        QLabel#logoLabel { font-size: 18px; font-weight: 700; color: #00e5ff; letter-spacing: 1px; }
        QLabel#idlePill {
            font-size: 12px; color: #4a6a7a; padding: 4px 12px;
            background: #0f1a24; border: 1px solid #1a2a38; border-radius: 12px;
        }
        QLabel#activePill {
            font-size: 12px; color: #00ff99; padding: 4px 12px;
            background: #003a20; border: 1px solid #00aa55; border-radius: 12px;
        }
        QFrame#feedPanel { background: #0d1018; border: 1px solid #1a2230; border-radius: 10px; }
        QLabel#feedLabel { color: #3a4a5a; font-size: 14px; }
        QFrame#statusPanel { background: #0d1018; border: 1px solid #1a2230; border-radius: 10px; }
        QLabel#sectionLabel { font-size: 10px; font-weight: 700; color: #3a5a6a; letter-spacing: 2px; padding-top: 4px; }
        QFrame#statusCard { background: #111622; border: 1px solid #1a2a38; border-radius: 6px; }
        QLabel#cardTitle { font-size: 11px; color: #5a7a8a; }
        QTextEdit#alertLog {
            background: #080c12; border: 1px solid #1a2230; border-radius: 6px;
            color: #8ab0c0; font-family: 'Consolas','Courier New',monospace; font-size: 11px; padding: 6px;
        }
        QPushButton#clearLogBtn {
            background: #111622; border: 1px solid #1a2a38; border-radius: 5px;
            color: #4a6a7a; padding: 4px; font-size: 11px;
        }
        QPushButton#clearLogBtn:hover { color: #8aabbb; }
        QFrame#controlBar { background: #0d1018; border-top: 1px solid #1a2230; }
        QPushButton#startBtn {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #003a30,stop:1 #004a20);
            border: 1px solid #00aa66; border-radius: 8px; color: #00ff99;
            font-size: 14px; font-weight: 700; padding: 0 28px; min-width: 200px;
        }
        QPushButton#startBtn:hover { background: #005a40; }
        QPushButton#stopBtn {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3a0808,stop:1 #500a0a);
            border: 1px solid #cc2222; border-radius: 8px; color: #ff6666;
            font-size: 14px; font-weight: 700; padding: 0 28px; min-width: 200px;
        }
        QPushButton#stopBtn:hover { background: #601010; }
        QPushButton#controlBtn {
            background: #111622; border: 1px solid #1e3040; border-radius: 8px;
            color: #80a0b8; font-size: 13px; padding: 0 16px;
        }
        QPushButton#controlBtn:hover { background: #182030; border-color: #2a4a60; }
        QCheckBox#overlayCheck { color: #7a9aaa; font-size: 13px; spacing: 8px; }
        QCheckBox#overlayCheck::indicator {
            width: 18px; height: 18px; border: 2px solid #2a4050;
            border-radius: 3px; background: #111622;
        }
        QCheckBox#overlayCheck::indicator:checked {
            background: #003a28; border: 2px solid #00cc66;
            border-radius: 3px;
            image: url(assets/check.svg);
        }
        QFrame#vdivider { color: #1a2a38; }
        QFrame#divider  { color: #1a2a38; }
        QLabel#phaseLbl { font-size: 11px; color: #2a4050; letter-spacing: 1px; }
        """