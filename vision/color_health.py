"""تحليل لون/صحة الغطاء النباتي من صورة RGB — بدون أي نموذج مدرَّب.

الفكرة: نعزل بكسلات النبات (مؤشّر ExG المنوّن، مقاوم نسبياً للإضاءة)، ثم
نصنّف لونها (أخضر/أصفر/بنّي) عبر قناة Hue. الأوراق المصفرّة/البنّية = إجهاد/جفاف.

يرجّع قاموساً بنِسَب اللون + leaf_health + drought_score_color (0=سليم .. 1=جاف).
هذا المؤشّر اللوني هو مصدر خريطة الجفاف في المرحلة 1 (حسب طلب المستخدم)؛
يمكن دمجه لاحقاً مع رطوبة التربة والحرارة عبر الأوزان في config.yaml.
"""
import numpy as np


def analyze(bgr, exg_threshold=0.10):
    if bgr is None:
        return _empty()
    try:
        import cv2
    except ImportError:
        return _empty(error="cv2 missing")

    img = bgr.astype(np.float32)
    b, g, r = img[..., 0], img[..., 1], img[..., 2]
    s = b + g + r + 1e-6
    exg = (2 * g - r - b) / s                 # مؤشّر الخضرة الزائدة (منوّن)
    veg = exg > exg_threshold                  # قناع الغطاء النباتي
    total = veg.size
    veg_ratio = float(veg.mean())

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    H = hsv[..., 0].astype(np.int16)           # 0..179 في OpenCV
    S = hsv[..., 1]
    V = hsv[..., 2]

    # نضمّ للقناع البكسلات النباتية + ما له تشبّع/إضاءة كافية ضمن نطاق ألوان النبات
    plantish = veg | ((S > 60) & (V > 40) & (H >= 10) & (H <= 90))

    green = plantish & (H >= 36) & (H <= 85)
    yellow = plantish & (H >= 20) & (H < 36)
    brown = plantish & (((H >= 8) & (H < 20)) | ((S < 80) & (V < 140) & (H < 30)))
    brown = brown & ~green & ~yellow           # امنع التداخل

    gp, yp, bp = int(green.sum()), int(yellow.sum()), int(brown.sum())
    denom = max(1, gp + yp + bp)
    green_frac = gp / denom
    yellow_frac = yp / denom
    brown_frac = bp / denom
    leaf_health = green_frac                    # نسبة الأوراق الخضراء السليمة من النبات

    # درجة جفاف لونية: مشهد شبه قاحل → جفاف عالٍ؛ غير ذلك → كلما قلّ الأخضر زاد الجفاف
    if veg_ratio < 0.05:
        drought = 0.85
    else:
        drought = float(np.clip(1.0 - leaf_health, 0.0, 1.0))

    return {
        "veg_ratio": round(veg_ratio, 3),
        "green_ratio": round(gp / total, 3),
        "yellow_ratio": round(yp / total, 3),
        "brown_ratio": round(bp / total, 3),
        "green_frac": round(green_frac, 3),
        "yellow_frac": round(yellow_frac, 3),
        "brown_frac": round(brown_frac, 3),
        "leaf_health": round(leaf_health, 3),
        "drought_score_color": round(drought, 3),
        "leaf_health_label": health_label(drought),
        "error": None,
    }


def health_label(drought_score):
    if drought_score < 0.35:
        return "سليم"
    if drought_score < 0.60:
        return "مُجهَد"
    return "جاف"


def _empty(error="no frame"):
    return {
        "veg_ratio": 0.0, "green_ratio": 0.0, "yellow_ratio": 0.0, "brown_ratio": 0.0,
        "green_frac": 0.0, "yellow_frac": 0.0, "brown_frac": 0.0,
        "leaf_health": 0.0, "drought_score_color": 0.0,
        "leaf_health_label": "غير معروف", "error": error,
    }
