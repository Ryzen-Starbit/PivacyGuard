import time
from typing import Optional
try:
    from plyer import notification as plyer_notify
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    print("[Notification] plyer not installed - desktop notifications disabled.")

class NotificationManager:
    #Sends desktop notifications with cooldown control
    APP_NAME = "PrivacyGuard"
    APP_ICON = ""  
    def __init__(self, cooldown_seconds: int = 12):
        self.cooldown_seconds = cooldown_seconds
        self._last_sent: float = 0.0
        self.available = PLYER_AVAILABLE
        if not self.available:
            print("[Notification] Running without desktop notifications.")

    def send_intruder_alert(self, face_count: int = 1, threat_level: str = "HIGH",
                             reason: str = "") -> bool:
        #Returns True if notification was sent, False if on cooldown or unavailable
        if not self._can_send():
            return False
        emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(threat_level, "⚠")
        title = f"⚠  Intruder Detected — {self.APP_NAME}"
        message = (
            f"{emoji} Threat Level: {threat_level}\n"
            f"Faces detected: {face_count}\n"
            f"{reason}"
        ).strip()
        return self._send(title, message)

    def send_user_absent_alert(self) -> bool:
        if not self._can_send():
            return False
        return self._send(
            f"⚠  User Left — {self.APP_NAME}",
            "Authorized user is no longer visible.\nComputer may be unattended."
        )

    def send_clear_alert(self) -> bool:
        if time.time() - self._last_sent < 3:
            return False
        return self._send(
            f"✅  All Clear — {self.APP_NAME}",
            "No intruders detected. Monitoring continues."
        )

    def _can_send(self) -> bool:
        return self.available and (time.time() - self._last_sent >= self.cooldown_seconds)

    def _send(self, title: str, message: str) -> bool:
        try:
            plyer_notify.notify(
                title=title,
                message=message,
                app_name=self.APP_NAME,
                timeout=6,     
            )
            self._last_sent = time.time()
            return True
        except Exception as e:
            print(f"[Notification] Failed to send: {e}")
            return False

    def set_cooldown(self, seconds: int):
        self.cooldown_seconds = max(3, seconds)