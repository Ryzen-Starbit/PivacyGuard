"""
Threat Levels:
  LOW    - Only the authorized user, looking at screen
  MEDIUM - Multiple people nearby but not staring or authorized user absent
  HIGH   - Unknown person with gaze directed at screen
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class ThreatAssessment:
    level: str             
    level_num: int          
    reason: str             
    intruder_detected: bool
    should_alert: bool      
    color: tuple           

class ThreatEngine:

    COLORS = {
        "LOW":    (0, 200, 80),    # green
        "MEDIUM": (0, 165, 255),   # orange
        "HIGH":   (0, 0, 220),     # red
    }
    def assess(
        self,
        total_faces: int,
        authorized_count: int,
        unknown_count: int,
        gaze_on_screen: bool,
        gaze_direction: str = "UNKNOWN",
        authorized_present: bool = False,
    ) -> ThreatAssessment:
        """
        Returns a ThreatAssessment based on current frame data.

        Parameters:
            total_faces       : total faces detected in frame
            authorized_count  : how many are recognized as authorized
            unknown_count     : how many are NOT recognized
            gaze_on_screen    : True if any face's gaze is directed at screen
            gaze_direction    : gaze string for context
            authorized_present: whether the registered owner is in frame
        """

        if total_faces == 0:
            return ThreatAssessment(
                level="LOW", level_num=0,
                reason="No one detected",
                intruder_detected=False,
                should_alert=False,
                color=self.COLORS["LOW"]
            )

        # HIGH: Unknown person looking at screen
        if unknown_count > 0 and gaze_on_screen:
            return ThreatAssessment(
                level="HIGH", level_num=2,
                reason=f"Unknown person staring at screen ({unknown_count} intruder{'s' if unknown_count > 1 else ''})",
                intruder_detected=True,
                should_alert=True,
                color=self.COLORS["HIGH"]
            )

        # HIGH: Unknown person present (not looking)
        if unknown_count > 0 and total_faces > 1:
            return ThreatAssessment(
                level="HIGH", level_num=2,
                reason=f"Unauthorized person detected near screen",
                intruder_detected=True,
                should_alert=True,
                color=self.COLORS["HIGH"]
            )

        # MEDIUM: Single unknown person (could be shoulder surfing)
        if unknown_count == 1 and authorized_count == 0:
            return ThreatAssessment(
                level="HIGH", level_num=2,
                reason="Unrecognized user at computer",
                intruder_detected=True,
                should_alert=True,
                color=self.COLORS["HIGH"]
            )

        # MEDIUM: Multiple authorized people (crowding)
        if total_faces > 1 and unknown_count == 0:
            return ThreatAssessment(
                level="MEDIUM", level_num=1,
                reason=f"{total_faces} people detected (authorized but crowded)",
                intruder_detected=False,
                should_alert=False,
                color=self.COLORS["MEDIUM"]
            )

        # MEDIUM: Authorized user looking away + someone else nearby
        if authorized_count >= 1 and not gaze_on_screen and total_faces > 1:
            return ThreatAssessment(
                level="MEDIUM", level_num=1,
                reason="Multiple people, screen attention unclear",
                intruder_detected=False,
                should_alert=False,
                color=self.COLORS["MEDIUM"]
            )

        # LOW: Only authorized user
        return ThreatAssessment(
            level="LOW", level_num=0,
            reason="Authorized user only",
            intruder_detected=False,
            should_alert=False,
            color=self.COLORS["LOW"]
        )

    def level_emoji(self, level: str) -> str:
        return {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(level, "⚪")