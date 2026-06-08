"""عميل API للروبوت — يسحب القراءات والصور من سيرفر الراسبيري (/api/v1/...).

كل الدوال تتعامل مع الأعطال بسلاسة وترجع None بدل رمي استثناء، حتى لا
يتعطّل الـ pipeline لو انقطعت الشبكة لحظة.
"""
import requests
import numpy as np


class RobotClient:
    def __init__(self, base_url, timeout=3.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ── أدوات داخلية ──
    def _get_json(self, path, params=None):
        try:
            r = requests.get(self.base_url + path, params=params, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def _get_bytes(self, path, params=None):
        try:
            r = requests.get(self.base_url + path, params=params, timeout=self.timeout)
            r.raise_for_status()
            if r.headers.get("Content-Type", "").startswith("image/"):
                return r.content
            return None
        except Exception:
            return None

    # ── الاتصال ──
    def health(self):
        return self._get_json("/api/v1/health")

    def online(self):
        return self.health() is not None

    # ── القراءات ──
    def readings(self):
        """لقطة مجمّعة: imu, gps, lidar, soil, environment, thermal, servos."""
        return self._get_json("/api/v1/readings")

    def gps(self):
        return self._get_json("/api/v1/gps")

    def soil(self):
        return self._get_json("/api/v1/soil")

    def thermal(self, full=False):
        return self._get_json("/api/v1/thermal", params={"full": 1} if full else None)

    # ── الصور ──
    def rgb_frame(self, quality=80):
        """يرجّع لقطة كاميرا RGB كمصفوفة BGR (ndarray) أو None."""
        data = self._get_bytes("/api/v1/camera/rgb.jpg", params={"q": quality})
        return self._decode(data)

    def thermal_frame(self, quality=85):
        """يرجّع الصورة الحرارية الملوّنة كمصفوفة BGR أو None."""
        data = self._get_bytes("/api/v1/camera/thermal.jpg", params={"q": quality})
        return self._decode(data)

    @staticmethod
    def _decode(data):
        if not data:
            return None
        try:
            import cv2
            arr = np.frombuffer(data, dtype=np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception:
            return None
