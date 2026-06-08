"""توليد تقرير PDF عن حالة المسح الزراعي — مع دعم عربي صحيح (reshape + bidi)
وخريطة نقطية للمناطق ملوّنة حسب الحالة.

generate_report(db_path, cfg) → bytes (PDF) جاهزة لزر التنزيل في الداشبورد.
"""
import io
import os
import time
import tempfile
import datetime
from collections import Counter

import db
import grid


# ── تشكيل العربي للعرض الصحيح في PDF ──
def _ar(text):
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)


def _font():
    """يسجّل خطاً يدعم العربية (Tahoma/Arial على ويندوز)، وإلا يرجع Helvetica."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    name = "ArabicFont"
    if name in pdfmetrics.getRegisteredFontNames():
        return name
    for p in (r"C:\Windows\Fonts\tahoma.ttf", r"C:\Windows\Fonts\arial.ttf",
              r"C:\Windows\Fonts\segoeui.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont(name, p))
                return name
            except Exception:
                continue
    return "Helvetica"


def _scatter(zones, cfg, out_png):
    """خريطة نقطية: كل منطقة دائرة ملوّنة حسب حالتها (تسميات إنجليزية لتجنّب مشاكل الخط)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    fig, ax = plt.subplots(figsize=(6, 4), dpi=130)
    for z in zones:
        status = grid.status_from_score(
            z["drought"], cfg["drought"]["irrigate_threshold"],
            cfg["drought"]["dry_threshold"])
        ax.scatter(z["lon"], z["lat"], c=grid.STATUS_COLORS.get(status, "#888"),
                   s=200, edgecolors="black", linewidths=0.6, zorder=3)
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.set_title("Drought / Irrigation Zones")
    ax.grid(True, alpha=0.3)
    ax.ticklabel_format(useOffset=False, style="plain")
    handles = [
        mpatches.Patch(color=grid.STATUS_COLORS["سليم"], label="Healthy"),
        mpatches.Patch(color=grid.STATUS_COLORS["يحتاج ري"], label="Needs irrigation"),
        mpatches.Patch(color=grid.STATUS_COLORS["جاف"], label="Dry"),
    ]
    ax.legend(handles=handles, loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


def generate_report(db_path, cfg):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    font = _font()
    counts = db.counts(db_path)
    zones = db.zone_summary(db_path)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    rmargin = W - 20 * mm

    def rline(txt, y, size=11, x=None):
        c.setFont(font, size)
        c.drawRightString(x if x is not None else rmargin, y, _ar(txt))

    y = H - 22 * mm
    rline("تقرير مسح الأراضي الزراعية — Spider-AI", y, 16); y -= 9 * mm
    rline("التاريخ: " + datetime.datetime.now().strftime("%Y-%m-%d  %H:%M"), y, 10); y -= 5 * mm
    c.setStrokeColorRGB(0.7, 0.7, 0.7); c.line(20 * mm, y, rmargin, y); y -= 10 * mm

    # ── الملخّص ──
    rline("الملخّص العام", y, 13); y -= 8 * mm
    rline(f"عدد العينات المسجّلة:  {counts['samples']}", y, 11, rmargin - 5 * mm); y -= 6 * mm
    rline(f"عدد المناطق (خلايا الشبكة):  {counts['zones']}", y, 11, rmargin - 5 * mm); y -= 6 * mm
    rline(f"كشوفات الأعشاب (YOLO):  {counts['detections']}", y, 11, rmargin - 5 * mm); y -= 6 * mm
    rline(f"حجم خلية الشبكة:  {cfg['grid']['cell_size_m']} م", y, 11, rmargin - 5 * mm); y -= 10 * mm

    # ── توزيع الحالات ──
    cnt = Counter()
    for z in zones:
        cnt[grid.status_from_score(
            z["drought"], cfg["drought"]["irrigate_threshold"],
            cfg["drought"]["dry_threshold"])] += 1
    rline("توزيع حالة المناطق", y, 13); y -= 8 * mm
    rline(f"سليم: {cnt.get('سليم', 0)}      "
          f"يحتاج ري: {cnt.get('يحتاج ري', 0)}      "
          f"جاف: {cnt.get('جاف', 0)}", y, 11, rmargin - 5 * mm); y -= 12 * mm

    # ── الخريطة النقطية ──
    if zones:
        rline("خريطة المناطق", y, 13); y -= 4 * mm
        tmp = os.path.join(tempfile.gettempdir(), f"spider_map_{int(time.time()*1000)}.png")
        try:
            _scatter(zones, cfg, tmp)
            img_h = 85 * mm
            c.drawImage(tmp, 25 * mm, y - img_h, width=150 * mm, height=img_h,
                        preserveAspectRatio=True, anchor="n")
            y -= img_h + 6 * mm
        except Exception as e:
            rline(f"(تعذّر رسم الخريطة: {e})", y, 9, rmargin - 5 * mm); y -= 8 * mm
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass
    else:
        rline("لا توجد بيانات مخزّنة بعد — شغّل الجمع مع GPS حقيقي أو احقن صور الاختبار.",
              y, 11, rmargin - 5 * mm); y -= 8 * mm

    # ── جدول أعلى المناطق جفافاً ──
    if zones:
        if y < 60 * mm:
            c.showPage(); y = H - 22 * mm
        top = sorted(zones, key=lambda z: -(z["drought"] or 0))[:12]
        rline("أكثر المناطق احتياجاً للتدخّل", y, 13); y -= 8 * mm
        c.setFont(font, 9)
        c.drawRightString(rmargin, y, _ar("الحالة"))
        c.drawRightString(rmargin - 35 * mm, y, _ar("درجة الجفاف"))
        c.drawRightString(rmargin - 70 * mm, y, _ar("الإحداثيات (lat, lon)"))
        c.drawRightString(rmargin - 130 * mm, y, _ar("عينات"))
        y -= 5 * mm
        for z in top:
            status = grid.status_from_score(
                z["drought"], cfg["drought"]["irrigate_threshold"],
                cfg["drought"]["dry_threshold"])
            c.setFont(font, 9)
            c.drawRightString(rmargin, y, _ar(status))
            c.drawRightString(rmargin - 35 * mm, y, f"{(z['drought'] or 0):.2f}")
            c.drawRightString(rmargin - 70 * mm, y,
                              f"{z['lat']:.6f}, {z['lon']:.6f}")
            c.drawRightString(rmargin - 130 * mm, y, str(z["n"]))
            y -= 5 * mm
            if y < 20 * mm:
                c.showPage(); y = H - 22 * mm

    # ── تذييل ──
    c.setFont(font, 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawRightString(rmargin, 12 * mm,
                      _ar("Spider-AI · تقرير آلي · المرحلة 1 (تحليل لوني)"))

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
