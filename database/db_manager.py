import os
import sqlite3
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@dataclass
class IntrusionRecord:
    id: int
    timestamp: str
    date: str
    time: str
    threat_level: str
    face_count: int
    unknown_count: int
    reason: str
    gaze_direction: str
    shoulder_surf: bool
    intruder_image: str
    screenshot_path: str

class DBManager:
    def __init__(self, db_path: str = "database/privacy_guard.db"):
        self.db_path = os.path.join(PROJECT_ROOT, db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def init(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS intrusions (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT NOT NULL,
                    date            TEXT NOT NULL,
                    time            TEXT NOT NULL,
                    threat_level    TEXT NOT NULL,
                    face_count      INTEGER DEFAULT 1,
                    unknown_count   INTEGER DEFAULT 1,
                    reason          TEXT DEFAULT '',
                    gaze_direction  TEXT DEFAULT 'UNKNOWN',
                    shoulder_surf   INTEGER DEFAULT 0,
                    intruder_image  TEXT DEFAULT '',
                    screenshot_path TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_date ON intrusions(date)
            """)
        print(f"[DBManager] Database ready at: {self.db_path}")

    def log_intrusion(
        self,
        threat_level: str,
        face_count: int,
        unknown_count: int,
        reason: str = "",
        gaze_direction: str = "UNKNOWN",
        shoulder_surf: bool = False,
        intruder_image: str = "",
        screenshot_path: str = "",
    ) -> int:
        now = datetime.now()
        ts   = now.strftime("%Y-%m-%d %H:%M:%S")
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")
        with self._connect() as conn:
            cursor = conn.execute("""
                INSERT INTO intrusions
                  (timestamp, date, time, threat_level, face_count, unknown_count,
                   reason, gaze_direction, shoulder_surf, intruder_image, screenshot_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ts, date, time, threat_level, face_count, unknown_count,
                  reason, gaze_direction, int(shoulder_surf),
                  intruder_image, screenshot_path))
            return cursor.lastrowid

    def update_paths(self, record_id: int, intruder_image: str = "", screenshot_path: str = ""):
        with self._connect() as conn:
            conn.execute("""
                UPDATE intrusions
                SET intruder_image = ?, screenshot_path = ?
                WHERE id = ?
            """, (intruder_image, screenshot_path, record_id))

    def get_all_intrusions(self, limit: int = 500) -> List[IntrusionRecord]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT id, timestamp, date, time, threat_level, face_count,
                       unknown_count, reason, gaze_direction, shoulder_surf,
                       intruder_image, screenshot_path
                FROM intrusions
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()

        return [IntrusionRecord(
            id=r[0], timestamp=r[1], date=r[2], time=r[3],
            threat_level=r[4], face_count=r[5], unknown_count=r[6],
            reason=r[7], gaze_direction=r[8], shoulder_surf=bool(r[9]),
            intruder_image=r[10], screenshot_path=r[11]
        ) for r in rows]

    def get_stats(self) -> dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM intrusions").fetchone()[0]
            today = datetime.now().strftime("%Y-%m-%d")
            today_count = conn.execute(
                "SELECT COUNT(*) FROM intrusions WHERE date = ?", (today,)
            ).fetchone()[0]
            high_count = conn.execute(
                "SELECT COUNT(*) FROM intrusions WHERE threat_level = 'HIGH'"
            ).fetchone()[0]
        return {
            "total": total,
            "today": today_count,
            "high_threat": high_count,
        }

    def delete_record(self, record_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM intrusions WHERE id = ?", (record_id,))

    def clear_all(self):
        with self._connect() as conn:
            conn.execute("DELETE FROM intrusions")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn