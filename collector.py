"""جامع البيانات (الـ pipeline) — يسحب من الروبوت، يحلّل، ويخزّن في SQLite.

دورة العمل لكل نبضة:
  1) GPS → لو تقديري/محاكاة (estimated) و skip_estimated_gps مفعّل → تجاهُل
  2) صورة RGB + readings (تربة/حرارة كحقول مساعدة)
  3) تحليل اللون/الصحة (color_health) + كشف الأعشاب (YOLO اختياري)
  4) دمج درجة الجفاف حسب الأوزان (الآن: اللون فقط)
  5) حفظ الصورة + إدراج صف في SQLite (مع خلية الشبكة)

يعمل كسكربت مستقل (python collector.py) أو ككائن داخل الداشبورد عبر خيط.
"""
import os
import time
import threading

from config import load_config, base_url
from robot_client import RobotClient
from vision.color_health import analyze as analyze_color
from vision.weeds_yolo import WeedDetector
import grid
import db


def fuse_drought(color_score, soil_moisture, thermal_avg, weights):
    """يدمج مصادر الجفاف حسب الأوزان. المصادر غير المتاحة تُتجاهَل تلقائياً."""
    comps, wsum = 0.0, 0.0
    wc = weights.get("color", 1.0)
    if color_score is not None and wc:
        comps += wc * color_score
        wsum += wc
    ws = weights.get("soil", 0.0)
    if soil_moisture is not None and ws:
        comps += ws * (1.0 - min(1.0, max(0.0, soil_moisture / 100.0)))  # تربة أجفّ → أعلى
        wsum += ws
    wt = weights.get("thermal", 0.0)
    if thermal_avg is not None and wt:
        t = min(1.0, max(0.0, (thermal_avg - 20.0) / 25.0))               # 20°C→0 .. 45°C→1
        comps += wt * t
        wsum += wt
    return round(comps / wsum, 3) if wsum else None


class Collector:
    def __init__(self, cfg=None, ip=None, port=None):
        self.cfg = cfg or load_config()
        self.client = RobotClient(base_url(self.cfg, ip, port),
                                  timeout=self.cfg["robot"].get("timeout_s", 3.0))
        y = self.cfg["vision"]["yolo"]
        model = y.get("model_path")
        if model and not os.path.isabs(model):
            model = os.path.join(os.path.dirname(os.path.abspath(__file__)), model)
        self.detector = WeedDetector(model, y.get("conf", 0.35), y.get("enabled", False))
        self.db_path = self.cfg["storage"]["db_path"]
        self.frames_dir = self.cfg["storage"]["frames_dir"]
        os.makedirs(self.frames_dir, exist_ok=True)
        db.init_db(self.db_path)

        self._stop = threading.Event()
        self._thread = None
        self.last = None        # آخر نتيجة (للعرض الحي بالداشبورد)
        self.stats = {"ticks": 0, "stored": 0, "skipped_estimated": 0, "errors": 0}

    # ── نبضة واحدة ──
    def tick(self):
        self.stats["ticks"] += 1
        gps = self.client.gps()
        if gps is None:
            self.stats["errors"] += 1
            self.last = {"error": "تعذّر الاتصال بالروبوت"}
            return self.last

        estimated = bool(gps.get("estimated", True))
        frame = self.client.rgb_frame()
        readings = self.client.readings() or {}
        soil = (readings.get("soil") or {}).get("moisture_pct")
        thermal = (readings.get("thermal") or {}).get("avg_c")

        color = analyze_color(frame, self.cfg["vision"].get("exg_threshold", 0.10))
        detections = self.detector.detect(frame)
        drought = fuse_drought(color["drought_score_color"], soil, thermal,
                               self.cfg["drought"]["weights"])

        gi = gj = None
        if gps.get("lat") is not None:
            gi, gj = grid.cell_indices(gps["lat"], gps["lon"],
                                       self.cfg["grid"]["cell_size_m"])

        result = {
            "ts": time.time(), "lat": gps.get("lat"), "lon": gps.get("lon"),
            "gps_estimated": estimated, "grid_i": gi, "grid_j": gj,
            "soil_moisture": soil, "thermal_avg": thermal,
            "drought_score": drought, "detections": detections,
            "n_detections": len(detections), **color,
        }
        result["status"] = grid.status_from_score(
            drought, self.cfg["drought"]["irrigate_threshold"],
            self.cfg["drought"]["dry_threshold"])
        self.last = result

        # تجاهُل التخزين للمواقع التقديرية (لكن نُبقي العرض الحي)
        if estimated and self.cfg["collector"].get("skip_estimated_gps", True):
            self.stats["skipped_estimated"] += 1
            result["stored"] = False
            return result

        # حفظ الصورة
        img_path = None
        if frame is not None and self.cfg["collector"].get("save_frames", True):
            try:
                import cv2
                img_path = os.path.join(self.frames_dir, f"{int(result['ts']*1000)}.jpg")
                cv2.imwrite(img_path, frame)
            except Exception:
                img_path = None
        result["image_path"] = img_path
        db.insert_sample(self.db_path, result)
        self.stats["stored"] += 1
        result["stored"] = True
        return result

    # ── حلقة الخيط ──
    def _loop(self):
        interval = self.cfg["collector"].get("poll_interval_s", 2.0)
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as e:
                self.stats["errors"] += 1
                self.last = {"error": str(e)}
            self._stop.wait(interval)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="Collector", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()


if __name__ == "__main__":
    c = Collector()
    print(f"Spider-AI Collector → {c.client.base_url}")
    print(f"YOLO: {c.detector.reason}")
    print("Ctrl+C للإيقاف.\n")
    try:
        interval = c.cfg["collector"].get("poll_interval_s", 2.0)
        while True:
            r = c.tick()
            if r.get("error"):
                print(f"  ⚠ {r['error']}")
            else:
                print(f"  drought={r.get('drought_score')} status={r.get('status')} "
                      f"health={r.get('leaf_health_label')} "
                      f"gps=({r.get('lat')},{r.get('lon')}) "
                      f"{'[stored]' if r.get('stored') else '[skipped:estimated]'}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nتوقّف.")
