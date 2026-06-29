import os
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QSpinBox, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt
DEFAULT_SETTINGS = {
    "recognition_tolerance": 50,
    "alert_cooldown_sec":    10,
    "frame_skip":             2,
    "absence_alert_sec":     10,
    "capture_cooldown_sec":   5,
    "absence_alert_enabled": True,
    "tray_on_minimize":      False,
    "lightweight_mode":      False,
    "adaptive_frame_skip":   True,
    "auto_cleanup_days":     30,
    "auto_cleanup_enabled":  False,
}
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "settings.json"
)
def load_settings() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                saved = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(saved)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)
def save_settings(settings: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(settings, f, indent=2)

class SettingsDialog(QDialog):
    def __init__(self, face_engine, main_window, parent=None):
        super().__init__(parent)
        self.face_engine  = face_engine
        self.main_window  = main_window
        self.settings     = load_settings()

        self.setWindowTitle("Settings — PrivacyGuard")
        self.setFixedSize(520, 660)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()
        self._load_values()
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(28, 22, 28, 22)
        title = QLabel("⚙  Settings")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        layout.addWidget(self._divider())
        layout.addWidget(self._section("DETECTION"))
        self.tolerance_slider, self.tolerance_val = self._slider_row(
            layout, "Recognition Sensitivity",
            "Higher = easier to match (lenient) | Lower = stricter",
            min_val=20, max_val=80, step=5
        )
        self.tolerance_slider.valueChanged.connect(
            lambda v: self.tolerance_val.setText(f"{v}%")
        )
        self.frame_skip_spin = self._spinbox_row(
            layout, "Frame Skip",
            "Analyze every Nth frame. Higher = faster but less responsive.",
            min_val=1, max_val=8
        )
        layout.addWidget(self._divider())
        layout.addWidget(self._section("ALERTS & COOLDOWNS"))
        self.cooldown_spin = self._spinbox_row(
            layout, "Alert Cooldown (seconds)", "", min_val=3, max_val=60
        )
        self.capture_cooldown_spin = self._spinbox_row(
            layout, "Capture Cooldown (seconds)", "", min_val=3, max_val=60
        )
        layout.addWidget(self._divider())
        layout.addWidget(self._section("ABSENCE DETECTION"))
        self.absence_enabled_cb = QCheckBox("Alert when authorized user leaves frame")
        self.absence_enabled_cb.setObjectName("settingsCheck")
        layout.addWidget(self.absence_enabled_cb)
        self.absence_delay_spin = self._spinbox_row(
            layout, "Absence Alert Delay (seconds)", "", min_val=3, max_val=60
        )
        layout.addWidget(self._divider())
        layout.addWidget(self._section("PERFORMANCE"))
        self.lightweight_cb = QCheckBox("Lightweight mode  (disables gaze tracking — faster on slow machines)")
        self.lightweight_cb.setObjectName("settingsCheck")
        layout.addWidget(self.lightweight_cb)
        self.adaptive_skip_cb = QCheckBox("Adaptive frame skip  (auto-adjusts based on CPU speed)")
        self.adaptive_skip_cb.setObjectName("settingsCheck")
        layout.addWidget(self.adaptive_skip_cb)
        layout.addWidget(self._divider())
        layout.addWidget(self._section("STORAGE & CLEANUP"))
        self.cleanup_enabled_cb = QCheckBox("Auto-delete old captures and screenshots")
        self.cleanup_enabled_cb.setObjectName("settingsCheck")
        layout.addWidget(self.cleanup_enabled_cb)
        self.cleanup_days_spin = self._spinbox_row(
            layout, "Delete files older than (days)", "", min_val=1, max_val=365
        )

        btn_cleanup_now = QPushButton("🗑  Run Cleanup Now")
        btn_cleanup_now.setObjectName("cleanupBtn")
        btn_cleanup_now.clicked.connect(self._run_cleanup_now)
        layout.addWidget(btn_cleanup_now)
        layout.addWidget(self._divider())

        layout.addWidget(self._section("SYSTEM"))
        self.tray_cb = QCheckBox("Minimize to system tray instead of taskbar")
        self.tray_cb.setObjectName("settingsCheck")
        layout.addWidget(self.tray_cb)
        layout.addStretch()
        layout.addWidget(self._divider())
        btn_row = QHBoxLayout()
        btn_reset = QPushButton("Reset Defaults")
        btn_reset.setObjectName("resetBtn")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("cancelBtn")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_apply = QPushButton("✅  Apply")
        btn_apply.setObjectName("applyBtn")
        btn_apply.clicked.connect(self._apply)
        btn_row.addWidget(btn_apply)
        layout.addLayout(btn_row)

    def _slider_row(self, layout, label_text, tooltip, min_val, max_val, step=1):
        row_label = QLabel(label_text)
        row_label.setObjectName("settingLabel")
        row_label.setToolTip(tooltip)
        layout.addWidget(row_label)
        row = QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setSingleStep(step)
        slider.setObjectName("settingsSlider")
        row.addWidget(slider, stretch=1)
        val_label = QLabel("50%")
        val_label.setObjectName("sliderVal")
        val_label.setFixedWidth(40)
        row.addWidget(val_label)
        layout.addLayout(row)
        return slider, val_label

    def _spinbox_row(self, layout, label_text, tooltip, min_val, max_val):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setObjectName("settingLabel")
        lbl.setToolTip(tooltip)
        row.addWidget(lbl, stretch=1)
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setObjectName("settingsSpin")
        spin.setFixedWidth(70)
        row.addWidget(spin)
        layout.addLayout(row)
        return spin

    def _section(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("sectionLabel")
        return lbl

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("divider")
        return line

    def _load_values(self):
        s = self.settings
        self.tolerance_slider.setValue(s["recognition_tolerance"])
        self.tolerance_val.setText(f"{s['recognition_tolerance']}%")
        self.frame_skip_spin.setValue(s["frame_skip"])
        self.cooldown_spin.setValue(s["alert_cooldown_sec"])
        self.capture_cooldown_spin.setValue(s["capture_cooldown_sec"])
        self.absence_enabled_cb.setChecked(s["absence_alert_enabled"])
        self.absence_delay_spin.setValue(s["absence_alert_sec"])
        self.tray_cb.setChecked(s["tray_on_minimize"])
        self.lightweight_cb.setChecked(s.get("lightweight_mode", False))
        self.adaptive_skip_cb.setChecked(s.get("adaptive_frame_skip", True))
        self.cleanup_enabled_cb.setChecked(s.get("auto_cleanup_enabled", False))
        self.cleanup_days_spin.setValue(s.get("auto_cleanup_days", 30))

    def _apply(self):
        s = self.settings
        s["recognition_tolerance"] = self.tolerance_slider.value()
        s["frame_skip"]            = self.frame_skip_spin.value()
        s["alert_cooldown_sec"]    = self.cooldown_spin.value()
        s["capture_cooldown_sec"]  = self.capture_cooldown_spin.value()
        s["absence_alert_enabled"] = self.absence_enabled_cb.isChecked()
        s["absence_alert_sec"]     = self.absence_delay_spin.value()
        s["tray_on_minimize"]      = self.tray_cb.isChecked()
        s["lightweight_mode"]      = self.lightweight_cb.isChecked()
        s["adaptive_frame_skip"]   = self.adaptive_skip_cb.isChecked()
        s["auto_cleanup_enabled"]  = self.cleanup_enabled_cb.isChecked()
        s["auto_cleanup_days"]     = self.cleanup_days_spin.value()
        save_settings(s)
        tol = 0.3 + (s["recognition_tolerance"] / 100.0) * 0.4
        self.face_engine.set_tolerance(tol)
        mw = self.main_window
        if hasattr(mw, '_worker') and mw._worker:
            mw._worker._frame_skip = s["frame_skip"]
        mw._alert_cooldown_max    = s["alert_cooldown_sec"] * 30
        mw._capture_cooldown_max  = s["capture_cooldown_sec"] * 30
        mw._absence_alert_sec     = s["absence_alert_sec"]
        mw._absence_alert_enabled = s["absence_alert_enabled"]
        mw._tray_on_minimize      = s["tray_on_minimize"]
        if hasattr(mw, 'perf_manager'):
            mw.perf_manager.set_lightweight(s["lightweight_mode"])
            mw._apply_lightweight_mode(s["lightweight_mode"])
        QMessageBox.information(self, "Settings Saved", "✅  Settings applied successfully.")
        self.accept()

    def _run_cleanup_now(self):
        if not hasattr(self.main_window, 'perf_manager'):
            QMessageBox.warning(self, "Not Available", "Performance manager not initialized.")
            return
        days = self.cleanup_days_spin.value()
        result = self.main_window.perf_manager.cleanup_old_files(days=days)
        QMessageBox.information(
            self, "Cleanup Complete",
            f"✅  Deleted {result['deleted']} file(s) older than {days} days."
        )

    def _reset_defaults(self):
        self.settings = dict(DEFAULT_SETTINGS)
        self._load_values()

    def _stylesheet(self):
        return """
        QDialog { background-color: #0f1117; color: #e0e6f0; font-family: 'Segoe UI', sans-serif; }
        QLabel#panelTitle { font-size: 18px; font-weight: 700; color: #00e5ff; }
        QLabel#sectionLabel { font-size: 10px; font-weight: 700; color: #3a5a6a; letter-spacing: 2px; padding-top: 2px; }
        QLabel#settingLabel { font-size: 13px; color: #a0b8c8; }
        QLabel#sliderVal { font-size: 13px; color: #00e5ff; font-weight: 700; }
        QSlider#settingsSlider::groove:horizontal { height: 4px; background: #1a2a3a; border-radius: 2px; }
        QSlider#settingsSlider::handle:horizontal {
            background: #00b8d4; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
        }
        QSlider#settingsSlider::sub-page:horizontal { background: #00b8d4; border-radius: 2px; }
        QSpinBox#settingsSpin {
            background: #1a1f2e; border: 1px solid #2a3a4a; border-radius: 5px;
            color: #e0e6f0; padding: 4px 8px; font-size: 13px;
            selection-background-color: #1a2a3a; selection-color: #e0e6f0;
        }
        QSpinBox#settingsSpin:focus { border-color: #00e5ff; }
        QCheckBox#settingsCheck { color: #a0b8c8; font-size: 12px; spacing: 8px; }
        QCheckBox#settingsCheck::indicator {
            width: 18px; height: 18px; border: 1px solid #2a4050; border-radius: 4px; background: #1a1f2e;
        }
        QCheckBox#settingsCheck::indicator:checked { background: #003a28; border: 2px solid #00aa66; border-radius: 3px; image: url(assets/check.svg); }
        QPushButton#applyBtn {
            background: #003a2a; border: 1px solid #00aa66; border-radius: 6px;
            color: #00ff99; padding: 9px 22px; font-size: 13px; font-weight: 600;
        }
        QPushButton#applyBtn:hover { background: #005a3a; }
        QPushButton#cancelBtn {
            background: #1a1f2e; border: 1px solid #2a3a4a; border-radius: 6px;
            color: #7a8ba0; padding: 9px 22px; font-size: 13px;
        }
        QPushButton#cancelBtn:hover { background: #242938; }
        QPushButton#resetBtn {
            background: #1a1020; border: 1px solid #3a1a3a; border-radius: 6px;
            color: #aa66aa; padding: 9px 16px; font-size: 12px;
        }
        QPushButton#cleanupBtn {
            background: #1a1008; border: 1px solid #4a3a08; border-radius: 6px;
            color: #ccaa44; padding: 7px 16px; font-size: 12px;
        }
        QPushButton#cleanupBtn:hover { background: #282010; }
        QFrame#divider { color: #1e2a38; }
        """