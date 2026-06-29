import os
import cv2
import numpy as np
from datetime import datetime
from typing import Optional, Tuple
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class CaptureEngine:
    def __init__(
        self,
        intruder_dir: str = "data/intruder_captures",
        screenshot_dir: str = "data/screenshots",
    ):
        self.intruder_dir   = os.path.join(PROJECT_ROOT, intruder_dir)
        self.screenshot_dir = os.path.join(PROJECT_ROOT, screenshot_dir)
        os.makedirs(self.intruder_dir,   exist_ok=True)
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self._check_screenshot_backend()

    def _check_screenshot_backend(self):
        #Detect which screenshot library is available
        try:
            import mss
            self._screenshot_backend = "mss"
        except ImportError:
            try:
                import pyautogui
                self._screenshot_backend = "pyautogui"
            except ImportError:
                self._screenshot_backend = None
                print("[CaptureEngine] No screenshot backend found. "
                      "Install mss:  pip install mss")

    def save_intruder_face(self,frame: np.ndarray,face_location: Optional[Tuple[int, int, int, int]] = None,padding: int = 30, ) -> str:
        #Crops the intruder's face from the frame and saves it, if face_location is None, saves the full frame instead
        ts       = self._timestamp()
        filename = f"intruder_{ts}.jpg"
        path     = os.path.join(self.intruder_dir, filename)
        if face_location is not None:
            top, right, bottom, left = face_location
            h, w = frame.shape[:2]
            top    = max(0, top    - padding)
            left   = max(0, left   - padding)
            bottom = min(h, bottom + padding)
            right  = min(w, right  + padding)
            face_crop = frame[top:bottom, left:right]
            if face_crop.size > 0:
                cv2.imwrite(path, face_crop)
            else:
                cv2.imwrite(path, frame)
        else:
            cv2.imwrite(path, frame)
        print(f"[CaptureEngine] Intruder face saved: {path}")
        return path

    def save_screenshot(self) -> str:
        #Captures the full screen and saves it
        ts       = self._timestamp()
        filename = f"screenshot_{ts}.jpg"
        path     = os.path.join(self.screenshot_dir, filename)
        try:
            if self._screenshot_backend == "mss":
                return self._screenshot_mss(path)
            elif self._screenshot_backend == "pyautogui":
                return self._screenshot_pyautogui(path)
            else:
                print("[CaptureEngine] No screenshot backend available.")
                return ""
        except Exception as e:
            print(f"[CaptureEngine] Screenshot failed: {e}")
            return ""

    def save_both(self,frame: np.ndarray,face_location: Optional[Tuple[int, int, int, int]] = None,) -> Tuple[str, str]:
        #Convenience method: saves intruder face + screenshot together
        intruder_path    = self.save_intruder_face(frame, face_location)
        screenshot_path  = self.save_screenshot()
        return intruder_path, screenshot_path

    def _screenshot_mss(self, path: str) -> str:
        import mss
        import mss.tools
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            bgra = np.array(img)
            bgr  = cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)
            cv2.imwrite(path, bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(f"[CaptureEngine] Screenshot saved: {path}")
        return path

    def _screenshot_pyautogui(self, path: str) -> str:
        import pyautogui
        img = pyautogui.screenshot()
        img.save(path)
        print(f"[CaptureEngine] Screenshot saved: {path}")
        return path

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime("%Y_%m_%d_%H_%M_%S")