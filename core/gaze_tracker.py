import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("[GazeTracker] mediapipe not installed — gaze tracking disabled.")

@dataclass
class GazeResult:
    gaze_direction: str        # "SCREEN", "LEFT", "RIGHT", "UP", "DOWN", "UNKNOWN"
    is_looking_at_screen: bool
    left_ear: float            
    right_ear: float           
    eyes_open: bool
    confidence: float          

class GazeTracker:
    #Tracks eye gaze for a single face using MediaPipe Face Mesh

    LEFT_EYE_TOP    = 159
    LEFT_EYE_BOTTOM = 145
    LEFT_EYE_LEFT   = 33
    LEFT_EYE_RIGHT  = 133
    LEFT_IRIS_CENTER = 468

    RIGHT_EYE_TOP    = 386
    RIGHT_EYE_BOTTOM = 374
    RIGHT_EYE_LEFT   = 362
    RIGHT_EYE_RIGHT  = 263
    RIGHT_IRIS_CENTER = 473

    NOSE_TIP   = 1
    CHIN       = 152
    LEFT_EAR   = 234
    RIGHT_EAR  = 454

    EAR_THRESHOLD = 0.20       # below this = eyes closed
    SCREEN_GAZE_THRESHOLD = 0.35   

    def __init__(self):
        self.available = MEDIAPIPE_AVAILABLE
        self._face_mesh = None
        self._last_result: Optional[GazeResult] = None
        if self.available:
            self._init_mediapipe()

    def _init_mediapipe(self):
        try:
            mp_face_mesh = mp.solutions.face_mesh
            self._face_mesh = mp_face_mesh.FaceMesh(
                max_num_faces=4,
                refine_landmarks=True,    # enables iris landmarks (468-477)
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        except Exception as e:
            print(f"[GazeTracker] Failed to init MediaPipe: {e}")
            self.available = False

    def analyze(self, frame: np.ndarray) -> Optional[GazeResult]:
        if not self.available or self._face_mesh is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._face_mesh.process(rgb)
        rgb.flags.writeable = True

        if not results.multi_face_landmarks:
            return GazeResult(
                gaze_direction="UNKNOWN",
                is_looking_at_screen=False,
                left_ear=0.0, right_ear=0.0,
                eyes_open=False, confidence=0.0
            )
        landmarks = results.multi_face_landmarks[0].landmark
        h, w = frame.shape[:2]
        def lm(idx):
            l = landmarks[idx]
            return np.array([l.x * w, l.y * h])

        left_ear  = self._ear(lm(self.LEFT_EYE_TOP),  lm(self.LEFT_EYE_BOTTOM),
                               lm(self.LEFT_EYE_LEFT), lm(self.LEFT_EYE_RIGHT))
        right_ear = self._ear(lm(self.RIGHT_EYE_TOP), lm(self.RIGHT_EYE_BOTTOM),
                               lm(self.RIGHT_EYE_LEFT), lm(self.RIGHT_EYE_RIGHT))
        eyes_open = (left_ear > self.EAR_THRESHOLD and right_ear > self.EAR_THRESHOLD)

        gaze_dir = "UNKNOWN"
        is_screen = False
        confidence = 0.0
        try:
            left_iris   = lm(self.LEFT_IRIS_CENTER)
            left_ratio  = self._iris_ratio(left_iris, lm(self.LEFT_EYE_LEFT), lm(self.LEFT_EYE_RIGHT))

            right_iris  = lm(self.RIGHT_IRIS_CENTER)
            right_ratio = self._iris_ratio(right_iris, lm(self.RIGHT_EYE_LEFT), lm(self.RIGHT_EYE_RIGHT))

            avg_ratio = (left_ratio + right_ratio) / 2.0

            nose   = lm(self.NOSE_TIP)
            l_ear  = lm(self.LEFT_EAR)
            r_ear  = lm(self.RIGHT_EAR)
            face_center_x = (l_ear[0] + r_ear[0]) / 2
            head_turn = (nose[0] - face_center_x) / max((r_ear[0] - l_ear[0]), 1)

            if not eyes_open:
                gaze_dir = "CLOSED"
                is_screen = False
                confidence = 0.9
            elif abs(head_turn) > 0.25:
                gaze_dir = "LEFT" if head_turn < 0 else "RIGHT"
                is_screen = False
                confidence = min(1.0, abs(head_turn) * 2)
            elif avg_ratio < 0.35:
                gaze_dir = "LEFT"
                is_screen = False
                confidence = 0.7
            elif avg_ratio > 0.65:
                gaze_dir = "RIGHT"
                is_screen = False
                confidence = 0.7
            else:
                gaze_dir = "SCREEN"
                is_screen = True
                center_dist = abs(avg_ratio - 0.5)
                confidence = max(0.5, 1.0 - center_dist * 3)
        except (IndexError, ZeroDivisionError):
            gaze_dir = "UNKNOWN"

        result = GazeResult(
            gaze_direction=gaze_dir,
            is_looking_at_screen=is_screen,
            left_ear=left_ear,
            right_ear=right_ear,
            eyes_open=eyes_open,
            confidence=confidence
        )
        self._last_result = result
        return result

    def annotate_frame(self, frame: np.ndarray, result: GazeResult) -> np.ndarray:
        #Draw gaze direction indicator on frame (bottom-right corner)
        h, w = frame.shape[:2]
        color = (0, 220, 0) if result.is_looking_at_screen else (0, 140, 255)
        icon  = "👁 SCREEN" if result.is_looking_at_screen else f"👁 {result.gaze_direction}"
        text_x, text_y = w - 200, h - 20
        cv2.rectangle(frame, (text_x - 8, text_y - 18), (w - 8, text_y + 6), (20, 20, 20), -1)
        cv2.putText(frame, f"Gaze: {result.gaze_direction}  {result.confidence:.0%}",
                    (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 1, cv2.LINE_AA)
        return frame

    @staticmethod
    def _ear(top, bottom, left, right) -> float:
        vertical   = np.linalg.norm(top - bottom)
        horizontal = np.linalg.norm(left - right)
        return float(vertical / (horizontal + 1e-6))

    @staticmethod
    def _iris_ratio(iris, eye_left, eye_right) -> float:
        #0.0 = iris at left corner, 1.0 = iris at right corner
        total = np.linalg.norm(eye_right - eye_left) + 1e-6
        dist  = np.linalg.norm(iris - eye_left)
        return float(np.clip(dist / total, 0.0, 1.0))