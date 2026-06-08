# 🕷️ Spider-AI — مشروع التحليل الذكي (على اللابتوب)

يسحب بيانات الروبوت العنكبوتي (راسبيري) عبر الـ API على `ip:5000`، يحلّل صورة
الكاميرا (لون/صحة الأوراق + كشف أعشاب اختياري بـ YOLO)، يربطها بإحداثيات GPS،
يخزّنها في **SQLite**، ويرسم **خريطة الجفاف/الري** على شبكة جغرافية.

> اللابتوب = «العقل». الروبوت = مصدر القراءات والصور (لا نعدّل عليه شيئاً).

---

## ⚡ تشغيل سريع

```bash
# 1) التبعيات (المرحلة 1 بدون YOLO)
pip install -r requirements.txt

# 2) عدّل IP الروبوت في config.yaml  (أو من الشريط الجانبي بالداشبورد)
#    لمعرفة IP الراسبيري:  hostname -I   (على الراسبيري)

# 3) الداشبورد
streamlit run dashboard.py          # أو شغّل run_dashboard.bat على ويندوز

# (بديل) جمع بلا واجهة:
python collector.py
```

تغيير IP بسرعة بلا تعديل الملف:
```bash
set SPIDER_ROBOT_IP=192.168.1.77    # ويندوز (PowerShell: $env:SPIDER_ROBOT_IP="...")
```

---

## 🧩 المعمارية

```
الروبوت (راسبيري) ──/api/v1/readings + camera/rgb.jpg──► اللابتوب (هذا المشروع)
                                                          ├─ robot_client.py  سحب
                                                          ├─ vision/color_health.py  لون/صحة
                                                          ├─ vision/weeds_yolo.py     YOLO (مرحلة 2)
                                                          ├─ grid.py + db.py          شبكة + SQLite
                                                          ├─ collector.py             الـ pipeline
                                                          └─ dashboard.py             واجهة Streamlit
```

| الملف | الدور |
|------|------|
| `config.yaml` | كل الإعدادات (IP، عتبات، أوزان الجفاف، الشبكة) |
| `robot_client.py` | عميل API — قراءات + صور، يتحمّل انقطاع الشبكة |
| `vision/color_health.py` | ExG + HSV → نِسَب أخضر/أصفر/بنّي + `drought_score` |
| `vision/weeds_yolo.py` | خطّاف YOLO (يبقى خاملاً حتى تجهّز نموذجك) |
| `grid.py` | تجميع GPS في خلايا (يناسب دقّة 2–5م) |
| `db.py` | SQLite: جدولا `samples` و `detections` |
| `collector.py` | الحلقة: سحب → تحليل → دمج → تخزين |
| `dashboard.py` | بثّ حي + خريطة + قاعدة بيانات + إعدادات |

---

## 📷 صور الاختبار (بلا حقل حقيقي)

افتح `test_gallery.html` على **موبايلك**، انقر صورة لعرضها ملء الشاشة، ووجّه
كاميرا الروبوت عليها. الفئات: أوراق خضراء سليمة · أوراق مُجهَدة · أعشاب · تربة جافة.
الصور تُجلب من Wikimedia مباشرة (موثوقة)، وللاستخدام دون اتصال:
```bash
python download_test_images.py     # ينزّلها محلياً في test_images/
```

---

## 🗺️ منطق خريطة الجفاف (المرحلة 1 — حسب طلبك: اللون فقط)

- لكل لقطة: نعزل النبات (ExG)، نصنّف لونه (Hue)، فنحسب `drought_score` لونياً.
- نجمّع القراءات في خلايا شبكة (`cell_size_m`)، فكل خلية تأخذ متوسّط جفاف وحالة:
  **🟢 سليم · 🟠 يحتاج ري · 🔴 جاف** (عتبات في `config.yaml`).
- **العينات بموقع تقديري/محاكاة (`estimated=true`) لا تُخزَّن على الخريطة** — مهم
  حتى لا تتكدّس كل القراءات على نقطة وهمية واحدة.

### قابلية التوسّع (مجاناً لاحقاً)
درجة الجفاف **قابلة للدمج**: زِد وزن `soil` و `thermal` في `config.yaml` لتدمج
رطوبة التربة والكاميرا الحرارية (كلاهما جاهز بالـ API) — مؤشّران أقوى من اللون.

---

## 🚀 المرحلة 2 — كشف الأعشاب بـ YOLO

1. اجمع صوراً أثناء جولات المسح (الكاميرا + GPS).
2. رقّمها (Roboflow / LabelImg) لأصناف أعشابك/محصولك.
3. درّب `YOLOv8/v11`، وضع `weeds.pt` في `models/`.
4. في `config.yaml`: `vision.yolo.enabled: true` و `model_path: models/weeds.pt`.
5. `pip install ultralytics` — وستظهر الكشوفات في البثّ الحي وتُخزَّن في `detections`.

---

## 🗄️ قاعدة البيانات

`samples`: ts, lat, lon, gps_estimated, grid_i/j, soil_moisture, thermal_avg,
veg/green/yellow/brown ratios, leaf_health, drought_score, image_path …
`detections`: sample_id, label, conf, bbox. الصور تُحفظ كملفات في `data/frames/`.

تصدير CSV من تبويب «قاعدة البيانات» بالداشبورد.
