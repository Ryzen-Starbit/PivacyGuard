import os
import time
import shutil
from datetime import datetime, timedelta
from collections import deque
from typing import Optional
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
class FPSTracker:
    #Tracks real-time FPS using a rolling window

    def __init__(self, window: int = 30):
        self._timestamps = deque(maxlen=window)

    def tick(self):
        self._timestamps.append(time.monotonic())
    @property
    def fps(self) -> float:
        if len(self._timestamps) < 2:
            return 0.0
        elapsed = self._timestamps[-1] - self._timestamps[0]
        if elapsed <= 0:
            return 0.0
        return (len(self._timestamps) - 1) / elapsed

class AdaptiveFrameSkip:
    """
    Adjusts frame_skip dynamically based on how long analysis takes
    Target: analysis should take < target_ms milliseconds
    If it takes longer, increase skip. If faster, decrease skip
    """

    def __init__(self, min_skip: int = 1, max_skip: int = 8, target_ms: float = 80.0):
        self.min_skip  = min_skip
        self.max_skip  = max_skip
        self.target_ms = target_ms
        self.current   = 2
        self._times    = deque(maxlen=10)

    def record(self, elapsed_ms: float):
        self._times.append(elapsed_ms)
        if len(self._times) < 5:
            return
        avg = sum(self._times) / len(self._times)
        if avg > self.target_ms * 1.3 and self.current < self.max_skip:
            self.current = min(self.max_skip, self.current + 1)
        elif avg < self.target_ms * 0.7 and self.current > self.min_skip:
            self.current = max(self.min_skip, self.current - 1)
    @property
    def skip(self) -> int:
        return self.current

class PerformanceManager:
    """
    Central performance manager
    Handles FPS tracking, adaptive skip, lightweight mode,disk space checks, and auto-cleanup"""
    def __init__(self):
        self.fps_tracker    = FPSTracker(window=30)
        self.adaptive_skip  = AdaptiveFrameSkip()
        self.lightweight    = False
        self._last_cleanup  = None

    def set_lightweight(self, enabled: bool):
        self.lightweight = enabled
        print(f"[Performance] Lightweight mode: {'ON' if enabled else 'OFF'}")

    def check_disk_space(self, min_gb: float = 0.5) -> dict:
        try:
            usage = shutil.disk_usage(PROJECT_ROOT)
            free_gb = usage.free / (1024 ** 3)
            return {
                "ok":      free_gb >= min_gb,
                "free_gb": round(free_gb, 2),
                "warning": f"Low disk space: {free_gb:.1f} GB free" if free_gb < min_gb else ""
            }
        except Exception as e:
            return {"ok": True, "free_gb": 0, "warning": ""}

    def cleanup_old_files(self, days: int = 30) -> dict:
        #Delete intruder captures and screenshots older than `days` days
        cutoff   = datetime.now() - timedelta(days=days)
        deleted  = 0
        errors   = 0
        dirs = [
            os.path.join(PROJECT_ROOT, "data", "intruder_captures"),
            os.path.join(PROJECT_ROOT, "data", "screenshots"),
        ]
        for folder in dirs:
            if not os.path.isdir(folder):
                continue
            for filename in os.listdir(folder):
                path = os.path.join(folder, filename)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(path))
                    if mtime < cutoff:
                        os.remove(path)
                        deleted += 1
                except Exception:
                    errors += 1
        print(f"[Performance] Cleanup: {deleted} files deleted, {errors} errors")
        self._last_cleanup = datetime.now()
        return {"deleted": deleted, "errors": errors}

    def get_storage_stats(self) -> dict:
        stats = {}
        for name, folder in [
            ("captures",    os.path.join(PROJECT_ROOT, "data", "intruder_captures")),
            ("screenshots", os.path.join(PROJECT_ROOT, "data", "screenshots")),
        ]:
            if not os.path.isdir(folder):
                stats[name] = {"count": 0, "size_mb": 0}
                continue
            files    = [f for f in os.listdir(folder)
                        if f.lower().endswith((".jpg", ".jpeg", ".png"))]
            total_sz = sum(
                os.path.getsize(os.path.join(folder, f))
                for f in files
            )
            stats[name] = {
                "count":   len(files),
                "size_mb": round(total_sz / (1024 * 1024), 1)
            }
        return stats