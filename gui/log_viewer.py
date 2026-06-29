import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class LogViewerDialog(QDialog):
    COLUMNS      = ["ID", "Date", "Time", "Threat", "Faces", "Unknown", "Gaze", "Shoulder", "Reason"]
    COL_WIDTHS   = [45,   105,    80,     75,       60,      75,        80,     80]   
    THREAT_COLORS = {"HIGH": "#ff3333", "MEDIUM": "#ffaa00", "LOW": "#00cc66"}

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._records   = []
        self.setWindowTitle("Intrusion Log - PrivacyGuard")
        self.setMinimumSize(1120, 660)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()
        self._load_records()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)
        header_row = QHBoxLayout()
        title = QLabel("📋  Intrusion Log")
        title.setObjectName("panelTitle")
        header_row.addWidget(title)
        header_row.addStretch()
        self.lbl_total = QLabel("Total: 0")
        self.lbl_today = QLabel("Today: 0")
        self.lbl_high  = QLabel("High: 0")
        for lbl in [self.lbl_total, self.lbl_today, self.lbl_high]:
            lbl.setObjectName("statLabel")
            header_row.addWidget(lbl)
            header_row.addSpacing(10)
        root.addLayout(header_row)
        root.addWidget(self._divider())
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = QTableWidget()
        self.table.setObjectName("logTable")
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for i, w in enumerate(self.COL_WIDTHS):
            self.table.setColumnWidth(i, w)
        self.table.horizontalHeader().setSectionResizeMode(
            len(self.COLUMNS) - 1, QHeaderView.ResizeMode.Stretch
        )
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        splitter.addWidget(self.table)
        preview_panel = QFrame()
        preview_panel.setObjectName("previewPanel")
        preview_panel.setFixedWidth(310)
        prev_lay = QVBoxLayout(preview_panel)
        prev_lay.setSpacing(8)
        prev_lay.setContentsMargins(10, 10, 10, 10)
        prev_lay.addWidget(self._section_label("INTRUDER FACE"))
        self.intruder_preview = QLabel("Select a row\nto preview")
        self.intruder_preview.setObjectName("imagePreview")
        self.intruder_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.intruder_preview.setFixedHeight(190)
        prev_lay.addWidget(self.intruder_preview)
        prev_lay.addWidget(self._section_label("SCREENSHOT"))
        self.screenshot_preview = QLabel("No screenshot")
        self.screenshot_preview.setObjectName("imagePreview")
        self.screenshot_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_preview.setFixedHeight(180)
        prev_lay.addWidget(self.screenshot_preview)

        self.detail_label = QLabel("")
        self.detail_label.setObjectName("detailLabel")
        self.detail_label.setWordWrap(True)
        prev_lay.addWidget(self.detail_label)
        prev_lay.addStretch()

        splitter.addWidget(preview_panel)
        splitter.setSizes([790, 310])
        root.addWidget(splitter, stretch=1)
        root.addWidget(self._divider())

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("🔄  Refresh")
        btn_refresh.setObjectName("actionBtn")
        btn_refresh.clicked.connect(self._load_records)
        btn_row.addWidget(btn_refresh)
        btn_clear = QPushButton("🗑  Clear All Records")
        btn_clear.setObjectName("dangerBtn")
        btn_clear.clicked.connect(self._clear_all)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.setObjectName("closeBtn")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

    def _load_records(self):
        records = self.db_manager.get_all_intrusions()
        stats   = self.db_manager.get_stats()
        self.lbl_total.setText(f"Total: {stats['total']}")
        self.lbl_today.setText(f"Today: {stats['today']}")
        self.lbl_high.setText(f"High: {stats['high_threat']}")
        self.table.setRowCount(len(records))
        self._records = records
        for row, rec in enumerate(records):
            vals = [
                str(rec.id), rec.date, rec.time, rec.threat_level,
                str(rec.face_count), str(rec.unknown_count),
                rec.gaze_direction, "YES" if rec.shoulder_surf else "NO",
                rec.reason,
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 3:   # threat level
                    item.setForeground(QColor(self.THREAT_COLORS.get(val, "#888888")))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                self.table.setItem(row, col, item)

    def _on_row_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._records):
            return
        rec = self._records[row]
        self._load_image_preview(self.intruder_preview, rec.intruder_image, "No face captured")
        self._load_image_preview(self.screenshot_preview, rec.screenshot_path, "No screenshot")
        self.detail_label.setText(
            f"ID: {rec.id}\n"
            f"Time: {rec.timestamp}\n"
            f"Threat: {rec.threat_level}\n"
            f"Faces: {rec.face_count}  Unknown: {rec.unknown_count}\n"
            f"Gaze: {rec.gaze_direction}\n"
            f"Shoulder surfing: {'Yes' if rec.shoulder_surf else 'No'}\n\n"
            f"{rec.reason}"
        )

    def _load_image_preview(self, label, path, placeholder):
        from PyQt6.QtGui import QPixmap
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            label.setPixmap(
                pixmap.scaled(label.width(), label.height(),
                              Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
            )
        else:
            label.setText(placeholder)
            label.setPixmap(QPixmap())

    def _clear_all(self):
        reply = QMessageBox.question(
            self, "Clear All Records",
            "Delete ALL intrusion records?\nThis does NOT delete saved image files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.clear_all()
            self._load_records()
            self.intruder_preview.setText("No face captured")
            self.screenshot_preview.setText("No screenshot")
            self.detail_label.setText("")

    def _section_label(self, text):
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
        QDialog { background-color: #0b0e15; color: #d0dce8; font-family: 'Segoe UI', sans-serif; }
        QLabel#panelTitle { font-size: 18px; font-weight: 700; color: #00e5ff; }
        QLabel#statLabel {
            font-size: 12px; color: #7a9aaa; background: #111622;
            border: 1px solid #1a2a38; border-radius: 5px; padding: 3px 10px;
        }
        QLabel#sectionLabel { font-size: 10px; font-weight: 700; color: #3a5a6a; letter-spacing: 2px; }
        QLabel#imagePreview {
            background: #111622; border: 1px solid #1a2a38;
            border-radius: 6px; color: #3a5060; font-size: 12px;
        }
        QLabel#detailLabel {
            font-size: 11px; color: #7a9aaa; font-family: 'Consolas', monospace;
        }
        QFrame#previewPanel { background: #0d1018; border: 1px solid #1a2230; border-radius: 8px; }
        QTableWidget#logTable {
            background: #0d1018; border: 1px solid #1a2230;
            gridline-color: #1a2230; color: #c0d0e0; font-size: 12px;
            selection-background-color: #1e3a50;
            alternate-background-color: #0f1420;
            outline: none;
        }
        QTableWidget#logTable::item { padding: 5px 4px; }
        QTableWidget#logTable::item:selected {
            background-color: #1e3a50; color: #c0d0e0;
            outline: none;
        }
        QTableWidget#logTable::item:focus { outline: none; border: none; }
        QHeaderView::section {
            background: #111622; color: #5a8a9a; font-size: 11px; font-weight: 700;
            letter-spacing: 1px; border: none; border-bottom: 1px solid #1a2a38; padding: 6px 4px;
        }
        QPushButton#actionBtn {
            background: #111622; border: 1px solid #1e3040;
            border-radius: 6px; color: #80a0b8; font-size: 13px; padding: 7px 18px;
        }
        QPushButton#actionBtn:hover { background: #182030; }
        QPushButton#dangerBtn {
            background: #1a0808; border: 1px solid #662222;
            border-radius: 6px; color: #cc4444; font-size: 13px; padding: 7px 18px;
        }
        QPushButton#dangerBtn:hover { background: #280a0a; }
        QPushButton#closeBtn {
            background: #111622; border: 1px solid #1a2a38;
            border-radius: 6px; color: #7a8ba0; font-size: 13px; padding: 7px 20px;
        }
        QPushButton#closeBtn:hover { background: #1a2030; }
        QFrame#divider { color: #1a2a38; }
        QScrollBar:vertical { background: #0d1018; width: 8px; border-radius: 4px; }
        QScrollBar::handle:vertical { background: #1e3040; border-radius: 4px; min-height: 20px; }
        """