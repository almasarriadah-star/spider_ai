"""تحميل الإعدادات من config.yaml مع تجاوزات من متغيّرات البيئة.

أولوية مصدر IP/المنفذ:  وسيط دالة  >  متغيّر بيئة  >  config.yaml
  - SPIDER_ROBOT_IP    يتجاوز robot.ip
  - SPIDER_ROBOT_PORT  يتجاوز robot.port
"""
import os
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")


def load_config(path=CONFIG_PATH):
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # تجاوزات البيئة (مفيدة عند تغيّر IP بسرعة)
    env_ip = os.environ.get("SPIDER_ROBOT_IP")
    env_port = os.environ.get("SPIDER_ROBOT_PORT")
    if env_ip:
        cfg.setdefault("robot", {})["ip"] = env_ip
    if env_port:
        cfg.setdefault("robot", {})["port"] = int(env_port)

    # حوّل المسارات النسبية للتخزين إلى مطلقة (بالنسبة لمجلد المشروع)
    st = cfg.setdefault("storage", {})
    st["db_path"] = _abs(st.get("db_path", "data/spider_ai.db"))
    st["frames_dir"] = _abs(st.get("frames_dir", "data/frames"))
    return cfg


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(BASE_DIR, p)


def base_url(cfg, ip=None, port=None):
    """يبني عنوان السيرفر. ip/port اختياريان لتجاوز ما في الإعدادات (مثلاً من الداشبورد)."""
    r = cfg.get("robot", {})
    ip = ip or r.get("ip", "192.168.1.50")
    port = port or r.get("port", 5000)
    return f"http://{ip}:{port}"
