"""طبقة قاعدة بيانات SQLite (المدمجة ببايثون — لا تحتاج خادماً).

ملاحظة: sqflite للموبايل/Flutter؛ على لابتوب بايثون نستخدم sqlite3 المدمج.
نفتح اتصالاً جديداً عند كل عملية ليكون آمناً عبر الخيوط (الـ collector + الداشبورد).
الصور تُحفظ كملفات على القرص ويُخزَّن مسارها فقط.
"""
import os
import sqlite3
import time


def get_conn(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    conn = get_conn(db_path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL, lat REAL, lon REAL, gps_estimated INTEGER,
            grid_i INTEGER, grid_j INTEGER,
            soil_moisture REAL, thermal_avg REAL,
            veg_ratio REAL, green_ratio REAL, yellow_ratio REAL, brown_ratio REAL,
            leaf_health REAL, drought_score REAL, leaf_health_label TEXT,
            n_detections INTEGER, image_path TEXT
        );
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_id INTEGER, label TEXT, conf REAL,
            x INTEGER, y INTEGER, w INTEGER, h INTEGER,
            FOREIGN KEY(sample_id) REFERENCES samples(id)
        );
        CREATE INDEX IF NOT EXISTS idx_samples_grid ON samples(grid_i, grid_j);
        CREATE INDEX IF NOT EXISTS idx_det_sample ON detections(sample_id);
        """
    )
    conn.commit()
    conn.close()


def insert_sample(db_path, rec):
    conn = get_conn(db_path)
    cur = conn.execute(
        """INSERT INTO samples
        (ts, lat, lon, gps_estimated, grid_i, grid_j, soil_moisture, thermal_avg,
         veg_ratio, green_ratio, yellow_ratio, brown_ratio, leaf_health,
         drought_score, leaf_health_label, n_detections, image_path)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (rec.get("ts", time.time()), rec.get("lat"), rec.get("lon"),
         int(bool(rec.get("gps_estimated"))), rec.get("grid_i"), rec.get("grid_j"),
         rec.get("soil_moisture"), rec.get("thermal_avg"),
         rec.get("veg_ratio"), rec.get("green_ratio"), rec.get("yellow_ratio"),
         rec.get("brown_ratio"), rec.get("leaf_health"), rec.get("drought_score"),
         rec.get("leaf_health_label"), rec.get("n_detections", 0), rec.get("image_path")),
    )
    sid = cur.lastrowid
    for d in rec.get("detections", []):
        x, y, w, h = d.get("bbox", (0, 0, 0, 0))
        conn.execute(
            "INSERT INTO detections (sample_id,label,conf,x,y,w,h) VALUES (?,?,?,?,?,?,?)",
            (sid, d.get("label"), d.get("conf"), x, y, w, h),
        )
    conn.commit()
    conn.close()
    return sid


def recent_samples(db_path, limit=200):
    conn = get_conn(db_path)
    rows = conn.execute(
        "SELECT * FROM samples ORDER BY ts DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def zone_summary(db_path):
    """يجمّع العينات لكل خلية شبكة: متوسّط الجفاف + المركز + العدد."""
    conn = get_conn(db_path)
    rows = conn.execute(
        """SELECT grid_i, grid_j, COUNT(*) AS n,
                  AVG(lat) AS lat, AVG(lon) AS lon,
                  AVG(drought_score) AS drought,
                  AVG(soil_moisture) AS soil,
                  AVG(leaf_health) AS health
           FROM samples
           WHERE lat IS NOT NULL AND gps_estimated = 0
           GROUP BY grid_i, grid_j""",
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def counts(db_path):
    conn = get_conn(db_path)
    s = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    d = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
    z = conn.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM samples WHERE gps_estimated=0 GROUP BY grid_i,grid_j)"
    ).fetchone()[0]
    conn.close()
    return {"samples": s, "detections": d, "zones": z}
