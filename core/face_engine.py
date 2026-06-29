import os
import cv2
import numpy as np
import face_recognition
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

@dataclass
class FaceResult:
    location: Tuple[int, int, int, int]
    name: str
    confidence: float
    is_authorized: bool
    zone: str = "CENTER"
    encoding: Optional[np.ndarray] = None

@dataclass
class FrameAnalysis:
    faces: List[FaceResult] = field(default_factory=list)
    total_faces: int = 0
    authorized_count: int = 0
    unknown_count: int = 0
    intruder_detected: bool = False
    shoulder_surfing_detected: bool = False
    annotated_frame: Optional[np.ndarray] = None

class FaceEngine:
    def __init__(self, data_dir: str = "data/authorized_faces"):
        self.data_dir = data_dir
        self.authorized_encodings: List[np.ndarray] = []
        self.authorized_names: List[str] = []
        self.recognition_tolerance = 0.55  
        self._scale_factor = 0.5
        self._edge_zone_pct = 0.28
        self._unknown_frame_count = 0
        self._unknown_confirm_threshold = 8   # ~0.25s at 30fps
        os.makedirs(self.data_dir, exist_ok=True)

    def load_authorized_faces(self):
        self.authorized_encodings = []
        self.authorized_names = []
        supported = (".jpg", ".jpeg", ".png", ".bmp")
        if not os.path.isdir(self.data_dir):
            return
        for filename in os.listdir(self.data_dir):
            if not filename.lower().endswith(supported):
                continue
            path = os.path.join(self.data_dir, filename)
            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                raw_name = os.path.splitext(filename)[0]
                name = raw_name.rsplit("_", 1)[0] if raw_name and raw_name[-1].isdigit() else raw_name
                self.authorized_encodings.append(encodings[0])
                self.authorized_names.append(name)
            else:
                print(f"[FaceEngine] Warning: no face in {filename}, skipping.")
        print(f"[FaceEngine] Loaded {len(self.authorized_encodings)} authorized face(s).")

    def register_face(self, image_path: str, name: str) -> bool:
        import shutil
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)
        if not encodings:
            return False
        safe_name = name.strip().replace(" ", "_")
        existing = [f for f in os.listdir(self.data_dir) if f.startswith(safe_name)]
        suffix = f"_{len(existing) + 1}" if existing else ""
        ext = os.path.splitext(image_path)[1].lower() or ".jpg"
        dest = os.path.join(self.data_dir, f"{safe_name}{suffix}{ext}")
        shutil.copy2(image_path, dest)
        self.load_authorized_faces()
        return True

    def remove_face(self, name: str) -> int:
        safe_name = name.strip().replace(" ", "_")
        removed = 0
        for filename in os.listdir(self.data_dir):
            base = os.path.splitext(filename)[0]
            clean = base.rsplit("_", 1)[0] if base and base[-1].isdigit() else base
            if clean.lower() == safe_name.lower():
                os.remove(os.path.join(self.data_dir, filename))
                removed += 1
        self.load_authorized_faces()
        return removed

    def list_authorized_users(self) -> List[str]:
        return sorted(set(self.authorized_names))

    def set_tolerance(self, tolerance: float):
        self.recognition_tolerance = max(0.1, min(0.9, tolerance))

    def reset_buffers(self):
        #Call this when monitoring stops
        self._unknown_frame_count = 0

    def analyze_frame(self, frame: np.ndarray) -> FrameAnalysis:
        result = FrameAnalysis()
        small = cv2.resize(frame, (0, 0), fx=self._scale_factor, fy=self._scale_factor)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small, model="hog")
        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
        result.total_faces = len(face_locations)
        annotated = frame.copy()
        scale = 1.0 / self._scale_factor
        frame_w = frame.shape[1]
        edge_px = int(frame_w * self._edge_zone_pct)
        shoulder_surf = False

        for loc, encoding in zip(face_locations, face_encodings):
            top, right, bottom, left = loc
            top    = int(top    * scale)
            right  = int(right  * scale)
            bottom = int(bottom * scale)
            left   = int(left   * scale)
            face_result = self._classify_face(encoding, (top, right, bottom, left))
            face_center_x = (left + right) // 2
            if face_center_x < edge_px:
                face_result.zone = "LEFT_EDGE"
            elif face_center_x > frame_w - edge_px:
                face_result.zone = "RIGHT_EDGE"
            else:
                face_result.zone = "CENTER"
            if not face_result.is_authorized and face_result.zone in ("LEFT_EDGE", "RIGHT_EDGE"):
                shoulder_surf = True
            result.faces.append(face_result)
            if face_result.is_authorized:
                result.authorized_count += 1
            else:
                result.unknown_count += 1

            color = (0, 200, 0) if face_result.is_authorized else (0, 0, 220)
            cv2.rectangle(annotated, (left, top), (right, bottom), color, 2)
            zone_tag = " ◀SIDE" if face_result.zone == "LEFT_EDGE" else (" SIDE▶" if face_result.zone == "RIGHT_EDGE" else "")
            label = f"{face_result.name} {face_result.confidence:.0%}{zone_tag}"
            label_y = top - 10 if top > 30 else bottom + 20
            label_w = max(len(label) * 9 + 8, 60)
            cv2.rectangle(annotated, (left, label_y - 18), (left + label_w, label_y + 4), color, -1)
            cv2.putText(annotated, label, (left + 4, label_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
        # Status bar
        status = (f"Faces: {result.total_faces}  |  Auth: {result.authorized_count}  |  Unknown: {result.unknown_count}"
                  + ("  |  ⚠ SHOULDER SURF" if shoulder_surf else ""))
        bar_w = len(status) * 9 + 12
        cv2.rectangle(annotated, (0, 0), (bar_w, 28), (15, 15, 20), -1)
        cv2.putText(annotated, status, (6, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.56, (180, 255, 200), 1, cv2.LINE_AA)
        if result.unknown_count > 0:
            self._unknown_frame_count += 1
        else:
            self._unknown_frame_count = 0

        result.shoulder_surfing_detected = shoulder_surf
        result.intruder_detected = (
            self._unknown_frame_count >= self._unknown_confirm_threshold
        )
        return result

    def _classify_face(self, encoding, location):
        if not self.authorized_encodings:
            return FaceResult(location=location, name="Unknown",
                              confidence=0.0, is_authorized=False, encoding=encoding)
        distances = face_recognition.face_distance(self.authorized_encodings, encoding)
        best_idx  = int(np.argmin(distances))
        best_dist = distances[best_idx]
        confidence = max(0.0, 1.0 - (best_dist / 0.6))
        if best_dist <= self.recognition_tolerance:
            return FaceResult(location=location,
                              name=f"Auth: {self.authorized_names[best_idx]}",
                              confidence=confidence, is_authorized=True, encoding=encoding)
        return FaceResult(location=location, name="Unknown",
                          confidence=confidence, is_authorized=False, encoding=encoding)