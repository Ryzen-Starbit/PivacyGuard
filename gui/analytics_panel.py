import os
import io
from datetime import datetime, timedelta
from collections import defaultdict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QFileDialog, QMessageBox, QScrollArea,
    QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage

try:
    import matplotlib
    matplotlib.use("Agg")  
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[Analytics] matplotlib not installed — charts disabled.")
DARK_BG    = "#0d1018"
CARD_BG    = "#111622"
GRID_COLOR = "#1a2a38"
TEXT_COLOR = "#8ab0c0"
CYAN       = "#00e5ff"
GREEN      = "#00cc66"
ORANGE     = "#ffaa00"
RED        = "#ff4444"

def _fig_to_pixmap(fig) -> QPixmap:
    #Convert a matplotlib figure to a QPixmap
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor(), dpi=100)
    buf.seek(0)
    data = buf.read()
    pixmap = QPixmap()
    pixmap.loadFromData(data)
    plt.close(fig)
    return pixmap

def make_daily_chart(records, width=5, height=3) -> QPixmap:
    if not MATPLOTLIB_AVAILABLE:
        return QPixmap()
    today = datetime.now().date()
    days  = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    counts = defaultdict(int)
    for rec in records:
        counts[rec.date] += 1
    labels = [d.strftime("%d %b") for d in days]
    values = [counts[d.strftime("%Y-%m-%d")] for d in days]
    colors = [RED if v > 0 else GRID_COLOR for v in values]
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(CARD_BG)
    bars = ax.bar(labels, values, color=colors, width=0.55, zorder=2)
    ax.set_title("Daily Intrusions (Last 7 Days)", color=CYAN, fontsize=11, pad=10)
    ax.set_ylabel("Intrusions", color=TEXT_COLOR, fontsize=9)
    ax.tick_params(colors=TEXT_COLOR, labelsize=8)
    ax.spines[:].set_color(GRID_COLOR)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5, zorder=1)
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                    str(val), ha="center", va="bottom", color=RED, fontsize=9, fontweight="bold")
    fig.tight_layout()
    return _fig_to_pixmap(fig)

def make_hourly_chart(records, width=5, height=3) -> QPixmap:
    #Bar chart showing which hours have most intrusions
    if not MATPLOTLIB_AVAILABLE:
        return QPixmap()
    hourly = defaultdict(int)
    for rec in records:
        try:
            hour = int(rec.time.split(":")[0])
            hourly[hour] += 1
        except Exception:
            pass
    hours  = list(range(24))
    values = [hourly[h] for h in hours]
    peak   = max(values) if values else 0
    colors = [RED if v == peak and v > 0 else (ORANGE if v > 0 else GRID_COLOR) for v in values]
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(CARD_BG)
    ax.bar(hours, values, color=colors, width=0.7, zorder=2)
    ax.set_title("Intrusions by Hour of Day", color=CYAN, fontsize=11, pad=10)
    ax.set_xlabel("Hour (24h)", color=TEXT_COLOR, fontsize=9)
    ax.set_ylabel("Count", color=TEXT_COLOR, fontsize=9)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 2)])
    ax.tick_params(colors=TEXT_COLOR, labelsize=8)
    ax.spines[:].set_color(GRID_COLOR)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5, zorder=1)
    fig.tight_layout()
    return _fig_to_pixmap(fig)

def make_threat_pie(records, width=4, height=3.5) -> QPixmap:
    #Pie chart of threat level distribution
    if not MATPLOTLIB_AVAILABLE:
        return QPixmap()
    counts = defaultdict(int)
    for rec in records:
        counts[rec.threat_level] += 1
    labels = []
    sizes  = []
    colors_list = []
    color_map = {"HIGH": RED, "MEDIUM": ORANGE, "LOW": GREEN}
    for level in ["HIGH", "MEDIUM", "LOW"]:
        if counts[level] > 0:
            labels.append(f"{level} ({counts[level]})")
            sizes.append(counts[level])
            colors_list.append(color_map[level])
    if not sizes:
        sizes  = [1]
        labels = ["No data"]
        colors_list = [GRID_COLOR]
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)
    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, colors=colors_list,
        autopct="%1.0f%%", startangle=90,
        wedgeprops={"edgecolor": DARK_BG, "linewidth": 2},
        pctdistance=0.75
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontsize(9)
        t.set_fontweight("bold")
    ax.legend(labels, loc="lower center", bbox_to_anchor=(0.5, -0.12),
              ncol=len(labels), fontsize=8,
              facecolor=CARD_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
    ax.set_title("Threat Level Breakdown", color=CYAN, fontsize=11, pad=10)
    fig.tight_layout()
    return _fig_to_pixmap(fig)

class AnalyticsDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Analytics — PrivacyGuard")
        self.setMinimumSize(1060, 700)
        self.setStyleSheet(self._stylesheet())
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(18, 16, 18, 16)
        header = QHBoxLayout()
        title = QLabel("📊  Privacy Analytics")
        title.setObjectName("panelTitle")
        header.addWidget(title)
        header.addStretch()
        self.btn_refresh = QPushButton("🔄  Refresh")
        self.btn_refresh.setObjectName("actionBtn")
        self.btn_refresh.clicked.connect(self._load_data)
        header.addWidget(self.btn_refresh)
        self.btn_export = QPushButton("📄  Export PDF Report")
        self.btn_export.setObjectName("exportBtn")
        self.btn_export.clicked.connect(self._export_pdf)
        header.addWidget(self.btn_export)
        root.addLayout(header)
        root.addWidget(self._divider())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("scrollArea")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setObjectName("scrollContent")
        content_lay = QVBoxLayout(content)
        content_lay.setSpacing(14)
        content_lay.setContentsMargins(0, 0, 0, 0)

        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(10)
        self.card_total   = self._stat_card("Total Intrusions", "0", CYAN)
        self.card_today   = self._stat_card("Today",            "0", GREEN)
        self.card_week    = self._stat_card("This Week",        "0", ORANGE)
        self.card_high_pct = self._stat_card("High Threat %",  "0%", RED)
        self.card_peak_hr  = self._stat_card("Peak Hour",      "—",  "#aa88ff")
        self.card_avg_day  = self._stat_card("Avg / Day",      "0",  TEXT_COLOR)

        for card in [self.card_total, self.card_today, self.card_week,
                     self.card_high_pct, self.card_peak_hr, self.card_avg_day]:
            self.stats_row.addWidget(card)
        content_lay.addLayout(self.stats_row)
        charts_row = QHBoxLayout()
        charts_row.setSpacing(10)
        self.daily_chart_label  = self._chart_box("Daily Intrusions")
        self.hourly_chart_label = self._chart_box("Hourly Distribution")
        self.threat_chart_label = self._chart_box("Threat Breakdown")

        charts_row.addWidget(self.daily_chart_label,  stretch=5)
        charts_row.addWidget(self.hourly_chart_label, stretch=5)
        charts_row.addWidget(self.threat_chart_label, stretch=4)
        content_lay.addLayout(charts_row)
        content_lay.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)
        root.addWidget(self._divider())
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("Close")
        btn_close.setObjectName("closeBtn")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

    def _load_data(self):
        records = self.db_manager.get_all_intrusions(limit=1000)
        stats   = self.db_manager.get_stats()
        today = datetime.now().date()
        week_start = today - timedelta(days=6)
        week_count = sum(
            1 for r in records
            if r.date >= week_start.strftime("%Y-%m-%d")
        )
        total = stats["total"]
        high_count = stats["high_threat"]
        high_pct = int((high_count / total * 100)) if total > 0 else 0
        from collections import defaultdict
        hourly = defaultdict(int)
        for rec in records:
            try:
                hour = int(rec.time.split(":")[0])
                hourly[hour] += 1
            except Exception:
                pass
        peak_hour = max(hourly, key=hourly.get) if hourly else None
        peak_str  = f"{peak_hour:02d}:00" if peak_hour is not None else "—"

        daily = defaultdict(int)
        for rec in records:
            daily[rec.date] += 1
        avg = round(sum(daily.values()) / len(daily), 1) if daily else 0
        self._update_stat_card(self.card_total,    str(total))
        self._update_stat_card(self.card_today,    str(stats["today"]))
        self._update_stat_card(self.card_week,     str(week_count))
        self._update_stat_card(self.card_high_pct, f"{high_pct}%")
        self._update_stat_card(self.card_peak_hr,  peak_str)
        self._update_stat_card(self.card_avg_day,  str(avg))

        if MATPLOTLIB_AVAILABLE:
            daily_px  = make_daily_chart(records)
            hourly_px = make_hourly_chart(records)
            threat_px = make_threat_pie(records)
            self._set_chart(self.daily_chart_label,  daily_px)
            self._set_chart(self.hourly_chart_label, hourly_px)
            self._set_chart(self.threat_chart_label, threat_px)
        else:
            for lbl in [self.daily_chart_label, self.hourly_chart_label, self.threat_chart_label]:
                inner = lbl.findChild(QLabel, "chartImage")
                if inner:
                    inner.setText("Install matplotlib\nfor charts:\npip install matplotlib")

    def _export_pdf(self):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors as rl_colors
            from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                             Table, TableStyle, Image as RLImage)
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
        except ImportError:
            QMessageBox.critical(self, "Missing Library",
                                 "reportlab is not installed.\n\nRun:\n  pip install reportlab")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Report", f"PrivacyGuard_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            "PDF Files (*.pdf)"
        )
        if not path:
            return
        try:
            records = self.db_manager.get_all_intrusions(limit=500)
            stats   = self.db_manager.get_stats()
            self._build_pdf(path, records, stats)
            QMessageBox.information(self, "Export Complete", f"✅  Report saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"PDF export failed:\n{str(e)}")

    def _build_pdf(self, path, records, stats):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors as rl_colors
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, Image as RLImage,
                                         HRFlowable)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        doc  = SimpleDocTemplate(path, pagesize=A4,
                                  leftMargin=2*cm, rightMargin=2*cm,
                                  topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story  = []

        # Title
        title_style = ParagraphStyle("title", fontSize=20, textColor=rl_colors.HexColor("#00e5ff"),
                                     spaceAfter=6, fontName="Helvetica-Bold")
        sub_style   = ParagraphStyle("sub",   fontSize=10, textColor=rl_colors.grey, spaceAfter=12)
        head_style  = ParagraphStyle("head",  fontSize=13, textColor=rl_colors.HexColor("#00b8d4"),
                                     spaceAfter=6, fontName="Helvetica-Bold", spaceBefore=14)
        body_style  = ParagraphStyle("body",  fontSize=9,  textColor=rl_colors.HexColor("#cccccc"))

        story.append(Paragraph("🛡 PrivacyGuard AI — Intrusion Report", title_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", sub_style))
        story.append(HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor("#1a2a3a")))
        story.append(Spacer(1, 0.3*cm))

        # Summary stats
        story.append(Paragraph("Summary Statistics", head_style))
        summary_data = [
            ["Metric", "Value"],
            ["Total Intrusions",   str(stats["total"])],
            ["Today",              str(stats["today"])],
            ["High Threat Events", str(stats["high_threat"])],
            ["High Threat %",      f"{int(stats['high_threat']/max(stats['total'],1)*100)}%"],
        ]
        t = Table(summary_data, colWidths=[8*cm, 8*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), rl_colors.HexColor("#111622")),
            ("TEXTCOLOR",   (0,0), (-1,0), rl_colors.HexColor("#00e5ff")),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [rl_colors.HexColor("#0d1018"), rl_colors.HexColor("#111622")]),
            ("TEXTCOLOR",   (0,1), (-1,-1), rl_colors.HexColor("#c0d0e0")),
            ("GRID",        (0,0), (-1,-1), 0.5, rl_colors.HexColor("#1a2a3a")),
            ("ALIGN",       (0,0), (-1,-1), "CENTER"),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ]))
        story.append(t)

        if MATPLOTLIB_AVAILABLE:
            story.append(Paragraph("Charts", head_style))
            charts = [
                ("Daily Intrusions (Last 7 Days)", make_daily_chart(records, width=7, height=3)),
                ("Intrusions by Hour",             make_hourly_chart(records, width=7, height=3)),
                ("Threat Level Breakdown",         make_threat_pie(records, width=5, height=3.5)),
            ]
            for chart_title, pixmap in charts:
                if pixmap.isNull():
                    continue
                story.append(Paragraph(chart_title, body_style))
                # Save pixmap to temp PNG
                tmp = f"data/__tmp_chart_{chart_title[:5]}.png"
                pixmap.save(tmp)
                story.append(RLImage(tmp, width=14*cm, height=6*cm))
                story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph("Intrusion Log", head_style))
        headers = ["ID", "Date", "Time", "Threat", "Faces", "Gaze", "Reason"]
        table_data = [headers]
        for rec in records[:100]:   # max 100 rows in PDF
            reason = rec.reason[:40] + "…" if len(rec.reason) > 40 else rec.reason
            table_data.append([
                str(rec.id), rec.date, rec.time, rec.threat_level,
                str(rec.face_count), rec.gaze_direction, reason
            ])
        col_widths = [1*cm, 2.8*cm, 2*cm, 2*cm, 1.5*cm, 1.8*cm, 5.9*cm]
        log_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        threat_color_map = {
            "HIGH":   rl_colors.HexColor("#ff3333"),
            "MEDIUM": rl_colors.HexColor("#ffaa00"),
            "LOW":    rl_colors.HexColor("#00cc66"),
        }
        style = [
            ("BACKGROUND",  (0,0), (-1,0), rl_colors.HexColor("#111622")),
            ("TEXTCOLOR",   (0,0), (-1,0), rl_colors.HexColor("#00e5ff")),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 7.5),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [rl_colors.HexColor("#0d1018"), rl_colors.HexColor("#111622")]),
            ("TEXTCOLOR",   (0,1), (-1,-1), rl_colors.HexColor("#c0d0e0")),
            ("GRID",        (0,0), (-1,-1), 0.3, rl_colors.HexColor("#1a2a3a")),
            ("ALIGN",       (0,0), (-1,-1), "CENTER"),
            ("ALIGN",       (6,0), (6,-1), "LEFT"),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",  (0,0), (-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ]
        for i, rec in enumerate(records[:100], start=1):
            c = threat_color_map.get(rec.threat_level)
            if c:
                style.append(("TEXTCOLOR", (3, i), (3, i), c))
                style.append(("FONTNAME",  (3, i), (3, i), "Helvetica-Bold"))
        log_table.setStyle(TableStyle(style))
        story.append(log_table)
        doc.build(story)

        import glob
        for f in glob.glob("data/__tmp_chart_*.png"):
            try:
                os.remove(f)
            except Exception:
                pass

    def _stat_card(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("statCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        val_lbl = QLabel(value)
        val_lbl.setObjectName("statValue")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_lbl.setStyleSheet(f"color: {color}; font-size: 26px; font-weight: 800;")
        lay.addWidget(val_lbl)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("statTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title_lbl)
        card._value_label = val_lbl
        return card

    def _update_stat_card(self, card: QFrame, value: str):
        card._value_label.setText(value)

    def _chart_box(self, title: str) -> QFrame:
        box = QFrame()
        box.setObjectName("chartBox")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)
        img_lbl = QLabel("Loading chart...")
        img_lbl.setObjectName("chartImage")
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_lbl.setMinimumHeight(220)
        img_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(img_lbl)
        box._img_label = img_lbl
        return box

    def _set_chart(self, box: QFrame, pixmap: QPixmap):
        lbl = box._img_label
        if not pixmap.isNull():
            lbl.setPixmap(
                pixmap.scaled(lbl.width() or 400, lbl.height() or 240,
                              Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
            )

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("divider")
        return line
    
    def _stylesheet(self):
        return """
        QDialog, QWidget#scrollContent {
            background-color: #0b0e15; color: #d0dce8;
            font-family: 'Segoe UI', sans-serif;
        }
        QScrollArea#scrollArea { background: transparent; border: none; }
        QLabel#panelTitle { font-size: 18px; font-weight: 700; color: #00e5ff; }
        QFrame#statCard {
            background: #111622; border: 1px solid #1a2a38;
            border-radius: 8px; min-width: 120px;
        }
        QLabel#statValue { font-size: 26px; font-weight: 800; }
        QLabel#statTitle { font-size: 10px; color: #5a7a8a; letter-spacing: 1px; }
        QFrame#chartBox {
            background: #0d1018; border: 1px solid #1a2230;
            border-radius: 8px; min-height: 240px;
        }
        QLabel#chartImage { color: #3a5060; font-size: 12px; }
        QPushButton#actionBtn {
            background: #111622; border: 1px solid #1e3040; border-radius: 6px;
            color: #80a0b8; font-size: 13px; padding: 7px 16px;
        }
        QPushButton#actionBtn:hover { background: #182030; }
        QPushButton#exportBtn {
            background: #1a2a0a; border: 1px solid #4a8a22; border-radius: 6px;
            color: #88cc44; font-size: 13px; padding: 7px 16px; font-weight: 600;
        }
        QPushButton#exportBtn:hover { background: #243a10; }
        QPushButton#closeBtn {
            background: #111622; border: 1px solid #1a2a38; border-radius: 6px;
            color: #7a8ba0; font-size: 13px; padding: 7px 20px;
        }
        QPushButton#closeBtn:hover { background: #1a2030; }
        QFrame#divider { color: #1a2a38; }
        QScrollBar:vertical { background: #0d1018; width: 8px; border-radius: 4px; }
        QScrollBar::handle:vertical { background: #1e3040; border-radius: 4px; min-height: 20px; }
        """