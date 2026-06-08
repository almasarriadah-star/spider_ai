"""داشبورد Streamlit — واجهة مشروع التحليل الذكي على اللابتوب.

التبويبات: بثّ حي (صورة + تحليل) · خريطة الجفاف/الري · قاعدة البيانات · الإعدادات.
IP الروبوت قابل للتغيير من الشريط الجانبي (لأنه يتغيّر كثيراً).

التشغيل:  streamlit run dashboard.py
"""
import os
import time
import pandas as pd
import streamlit as st

from config import load_config, base_url
from collector import Collector, fuse_drought
import db
import grid

st.set_page_config(page_title="Spider-AI", page_icon="🕷️", layout="wide")


def inject_test_images(cfg, db_path):
    """يمرّر صور test_images/ عبر تحليل اللون ويخزّنها بإحداثيات تجريبية متباعدة.
    للتجربة الكاملة (تخزين + خريطة) قبل توفّر GPS حقيقي."""
    import glob, os, time
    import cv2
    from vision.color_health import analyze
    base = os.path.dirname(os.path.abspath(__file__))
    files = sorted(glob.glob(os.path.join(base, "test_images", "**", "*.jpg"), recursive=True))
    olat, olon = 34.0684, 36.7467
    cell_m = cfg["grid"]["cell_size_m"]
    step = 0.00005  # ~5.5م → خلايا شبكة مختلفة
    n = 0
    for i, f in enumerate(files):
        img = cv2.imread(f)
        if img is None:
            continue
        color = analyze(img, cfg["vision"].get("exg_threshold", 0.10))
        lat = olat + (i // 4) * step
        lon = olon + (i % 4) * step
        drought = fuse_drought(color["drought_score_color"], None, None,
                               cfg["drought"]["weights"])
        gi, gj = grid.cell_indices(lat, lon, cell_m)
        db.insert_sample(db_path, {
            "ts": time.time(), "lat": lat, "lon": lon, "gps_estimated": False,
            "grid_i": gi, "grid_j": gj, "soil_moisture": None, "thermal_avg": None,
            "drought_score": drought, "n_detections": 0, "image_path": f, **color,
        })
        n += 1
    return n

cfg = load_config()
# مركز افتراضي للخريطة عند غياب أي بيانات/موقع (قابل للضبط من config.yaml → map.center)
DEFAULT_CENTER = cfg.get("map", {}).get("center", [34.0684, 36.7467])

# ── الحالة عبر الجلسة ──
if "collector" not in st.session_state:
    st.session_state.collector = None

# ── الشريط الجانبي: الاتصال والتحكّم ──
st.sidebar.title("🕷️ Spider-AI")
st.sidebar.caption("تحليل ذكي لبيانات الروبوت العنكبوتي")

ip = st.sidebar.text_input("IP الروبوت (الراسبيري)", value=cfg["robot"]["ip"])
port = st.sidebar.number_input("المنفذ", value=int(cfg["robot"]["port"]), step=1)
st.sidebar.caption(f"العنوان: http://{ip}:{port}")

col_a, col_b = st.sidebar.columns(2)
start = col_a.button("▶ تشغيل الجمع", use_container_width=True)
stop = col_b.button("⏹ إيقاف", use_container_width=True)

if start:
    c = Collector(cfg, ip=ip, port=int(port))
    c.start()
    st.session_state.collector = c
    st.sidebar.success("بدأ الجمع")
if stop and st.session_state.collector:
    st.session_state.collector.stop()
    st.sidebar.warning("توقّف الجمع")

coll = st.session_state.collector
db_path = cfg["storage"]["db_path"]
db.init_db(db_path)

# فحص الاتصال
if coll:
    online = coll.client.online()
    st.sidebar.markdown(f"الاتصال: {'🟢 متصل' if online else '🔴 غير متصل'}")
    st.sidebar.markdown(f"الجمع: {'🟢 شغّال' if coll.running else '⚪ متوقّف'}")
    st.sidebar.caption(f"YOLO: {coll.detector.reason}")
    st.sidebar.json(coll.stats)

auto = st.sidebar.checkbox("تحديث تلقائي (2 ثانية)", value=True)

st.sidebar.divider()
st.sidebar.subheader("🧪 اختبار بدون GPS")
store_estimated = st.sidebar.checkbox(
    "خزّن حتى المواقع التقديرية", value=False,
    help="عادةً تُتجاهَل مواقع المحاكاة/الافتراضية لتجنّب تكدّسها على نقطة واحدة. "
         "فعّلها مؤقّتاً لتجربة التخزين قبل توفّر GPS fix.")
if coll:
    coll.cfg["collector"]["skip_estimated_gps"] = not store_estimated
if st.sidebar.button("حقن صور الاختبار في القاعدة", use_container_width=True):
    nn = inject_test_images(cfg, db_path)
    st.sidebar.success(f"أُدخلت {nn} عينة تجريبية — افتح تبويب «خريطة الجفاف»")

# ── التبويبات ──
t_live, t_map, t_db, t_cfg = st.tabs(["📷 بثّ حي", "🗺️ خريطة الجفاف", "🗄️ قاعدة البيانات", "⚙️ الإعدادات"])

# ════════════════ بثّ حي ════════════════
with t_live:
    st.subheader("اللقطة الحالية + التحليل")
    if not coll:
        st.info("اضغط «تشغيل الجمع» من الشريط الجانبي للبدء.")
    else:
        r = coll.last
        if not r:
            st.info("بانتظار أول نبضة…")
        elif r.get("error"):
            st.error(r["error"])
        else:
            c1, c2 = st.columns([2, 1])
            with c1:
                frame = coll.client.rgb_frame()
                if frame is not None:
                    try:
                        import cv2
                        det = coll.detector.detect(frame)
                        for d in det:
                            x, y, w, h = d["bbox"]
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                            cv2.putText(frame, f"{d['label']} {d['conf']}", (x, max(15, y - 5)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                        st.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                                 caption="كاميرا الروبوت (RGB)", use_container_width=True)
                    except Exception as e:
                        st.warning(f"تعذّر عرض الصورة: {e}")
                else:
                    st.warning("لا توجد صورة من الكاميرا (تحقّق من الاتصال/الكاميرا).")
            with c2:
                status = r.get("status", "—")
                color = grid.STATUS_COLORS.get(status, "#888")
                st.markdown(f"### الحالة: <span style='color:{color}'>{status}</span>",
                            unsafe_allow_html=True)
                st.metric("درجة الجفاف", r.get("drought_score"))
                st.metric("صحة الأوراق", r.get("leaf_health_label"))
                st.progress(min(1.0, float(r.get("leaf_health") or 0)), text="نسبة الخضرة")
                st.write({
                    "أخضر": r.get("green_frac"), "أصفر": r.get("yellow_frac"),
                    "بنّي": r.get("brown_frac"), "غطاء نباتي": r.get("veg_ratio"),
                })
                st.divider()
                st.write({
                    "GPS": (r.get("lat"), r.get("lon")),
                    "تقديري؟": r.get("gps_estimated"),
                    "رطوبة التربة%": r.get("soil_moisture"),
                    "حرارة (متوسّط)": r.get("thermal_avg"),
                    "كشوفات": r.get("n_detections"),
                    "خُزِّن؟": r.get("stored"),
                })
                if r.get("gps_estimated"):
                    st.caption("⚠ موقع تقديري/محاكاة — لا يُخزَّن (إلا بتفعيل وضع الاختبار).")
                st.caption("التحليل أعلاه = رؤية حاسوبية للون/صحة الأوراق (المرحلة 1). "
                           "«كشوفات» = YOLO للأعشاب (المرحلة 2، معطّل حالياً).")

# ════════════════ خريطة الجفاف ════════════════
with t_map:
    st.subheader("خريطة المناطق: 🟢 سليم · 🟠 يحتاج ري · 🔴 جاف")
    zones = db.zone_summary(db_path)
    # موقع الروبوت الحالي (حتى لو تقديري) — لتوسيط الخريطة وعرض علامة حيّة
    robot_pos = None
    if coll and isinstance(coll.last, dict) and coll.last.get("lat") is not None:
        robot_pos = (coll.last["lat"], coll.last["lon"], bool(coll.last.get("gps_estimated")))

    try:
        import folium
        from streamlit_folium import st_folium

        # تحديد مركز الخريطة: المناطق المخزّنة ← موقع الروبوت ← نقطة افتراضية
        if zones:
            lats = [z["lat"] for z in zones]; lons = [z["lon"] for z in zones]
            center = [sum(lats) / len(lats), sum(lons) / len(lons)]
        elif robot_pos:
            center = [robot_pos[0], robot_pos[1]]
        else:
            center = DEFAULT_CENTER

        m = folium.Map(location=center, zoom_start=18, max_zoom=22)

        # علامة موقع الروبوت الحالي
        if robot_pos:
            est = robot_pos[2]
            folium.Marker(
                location=[robot_pos[0], robot_pos[1]],
                tooltip="موقع الروبوت الحالي" + (" (تقديري)" if est else " (GPS حقيقي)"),
                icon=folium.Icon(color="blue", icon="screenshot" if not est else "info-sign"),
            ).add_to(m)

        # المناطق المخزّنة (دوائر ملوّنة بحجم بكسلي ثابت → واضحة بأي تكبير)
        for z in zones:
            status = grid.status_from_score(
                z["drought"], cfg["drought"]["irrigate_threshold"],
                cfg["drought"]["dry_threshold"])
            col = grid.STATUS_COLORS.get(status, "#888")
            folium.CircleMarker(
                location=[z["lat"], z["lon"]], radius=12,
                color="#000", weight=1, fill=True, fill_color=col, fill_opacity=0.85,
                tooltip=f"{status} · جفاف={round(z['drought'] or 0,2)}",
                popup=(f"الحالة: {status}<br>درجة الجفاف: {round(z['drought'] or 0,2)}<br>"
                       f"صحة الأوراق: {round(z['health'] or 0,2)}<br>عينات: {z['n']}"),
            ).add_to(m)

        if len(zones) > 1:
            m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

        st_folium(m, height=520, use_container_width=True, returned_objects=[])
        if zones:
            st.caption(f"عدد المناطق: {len(zones)} · حجم الخلية {cfg['grid']['cell_size_m']}م")
        else:
            st.caption("الخريطة معروضة — لا مناطق مخزّنة بعد. العلامات الملوّنة تظهر بعد "
                       "«حقن صور الاختبار» أو التقاط GPS حقيقي.")
    except Exception as e:
        st.warning(f"تعذّر رسم الخريطة التفاعلية ({e}).")
        if zones:
            df = pd.DataFrame(zones)[["lat", "lon", "drought", "health", "n"]]
            st.map(df.rename(columns={"lat": "latitude", "lon": "longitude"}))
            st.dataframe(df, use_container_width=True)

# ════════════════ قاعدة البيانات ════════════════
with t_db:
    st.subheader("العينات المسجّلة")
    st.json(db.counts(db_path))
    rows = db.recent_samples(db_path, limit=500)
    if rows:
        dfr = pd.DataFrame(rows)
        st.dataframe(dfr, use_container_width=True, height=420)
        cda, cdb = st.columns(2)
        cda.download_button("⬇ تنزيل CSV", dfr.to_csv(index=False).encode("utf-8-sig"),
                            "spider_ai_samples.csv", "text/csv", use_container_width=True)
        if cdb.button("📄 توليد تقرير PDF", use_container_width=True):
            from report import generate_report
            with st.spinner("جارٍ توليد التقرير…"):
                st.session_state["pdf_report"] = generate_report(db_path, cfg)
    else:
        st.info("لا عينات بعد.")

    if st.session_state.get("pdf_report"):
        st.download_button(
            "⬇ تنزيل تقرير PDF",
            st.session_state["pdf_report"],
            f"spider_ai_report_{time.strftime('%Y%m%d_%H%M')}.pdf",
            "application/pdf", use_container_width=True)

# ════════════════ الإعدادات ════════════════
with t_cfg:
    st.subheader("الإعدادات الفعّالة (config.yaml)")
    st.caption("عدّل config.yaml لتغيير الأوزان/العتبات/الشبكة، ثم أعد التشغيل.")
    st.json(cfg)

# ── التحديث التلقائي ──
if auto and coll and coll.running:
    time.sleep(2)
    st.rerun()
