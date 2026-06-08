"""خطّاف كشف الأعشاب بـ YOLO — المرحلة 2.

يُحمّل النموذج كسولاً (lazy) فقط لو ultralytics مثبّت والنموذج موجود وكان
yolo.enabled=true في config. وإلا يبقى غير فعّال (detect ترجع []) فلا يتعطّل
الـ pipeline. بعد تدريب نموذجك على أعشابك، ضع weeds.pt في models/ وفعّله.
"""
import os


class WeedDetector:
    def __init__(self, model_path=None, conf=0.35, enabled=False):
        self.conf = conf
        self.available = False
        self.reason = "disabled"
        self.model = None
        if not enabled:
            return
        try:
            from ultralytics import YOLO
        except Exception:
            self.reason = "ultralytics غير مثبّت (pip install ultralytics)"
            return
        # لو ما في نموذج مخصّص، استخدم yolov8n العام (يُنزَّل تلقائياً عند توفّر نت)
        path = model_path if (model_path and os.path.exists(model_path)) else "yolov8n.pt"
        try:
            self.model = YOLO(path)
            self.available = True
            self.reason = f"loaded: {path}"
        except Exception as e:
            self.reason = f"تعذّر تحميل النموذج: {e}"

    def detect(self, bgr):
        """يرجّع قائمة كشوفات: [{label, conf, bbox:(x,y,w,h)} ...]."""
        if not self.available or bgr is None:
            return []
        try:
            res = self.model.predict(bgr, conf=self.conf, verbose=False)
        except Exception:
            return []
        out = []
        for rr in res:
            names = rr.names
            for box in rr.boxes:
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                out.append({
                    "label": names.get(int(box.cls[0]), str(int(box.cls[0]))),
                    "conf": round(float(box.conf[0]), 3),
                    "bbox": (int(x1), int(y1), int(x2 - x1), int(y2 - y1)),
                })
        return out
