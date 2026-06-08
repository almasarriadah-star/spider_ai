"""تجميع شبكي (grid binning) لإحداثيات GPS.

GPS العادي دقّته 2–5م، فلا نربط القراءة بشجرة بعينها، بل نجمّع القراءات في
خلايا مربّعة بحجم cell_size_m ونلوّن كل خلية حسب متوسّط درجة الجفاف.
"""
import math


def cell_indices(lat, lon, cell_m):
    """يرجّع (gi, gj) — رقم الخلية التي يقع فيها الإحداثي."""
    dlat = cell_m / 111111.0
    dlon = cell_m / (111111.0 * max(0.1, math.cos(math.radians(lat))))
    return math.floor(lat / dlat), math.floor(lon / dlon)


def cell_center(gi, gj, ref_lat, cell_m):
    """مركز الخلية (lat, lon) — للرسم على الخريطة."""
    dlat = cell_m / 111111.0
    dlon = cell_m / (111111.0 * max(0.1, math.cos(math.radians(ref_lat))))
    return (gi + 0.5) * dlat, (gj + 0.5) * dlon


def status_from_score(score, irrigate_thr, dry_thr):
    """يحوّل drought_score إلى حالة منطقة."""
    if score is None:
        return "غير معروف"
    if score >= dry_thr:
        return "جاف"
    if score >= irrigate_thr:
        return "يحتاج ري"
    return "سليم"


STATUS_COLORS = {
    "جاف": "#d62728",        # أحمر
    "يحتاج ري": "#ff7f0e",   # برتقالي
    "سليم": "#2ca02c",       # أخضر
    "غير معروف": "#7f7f7f",  # رمادي
}
