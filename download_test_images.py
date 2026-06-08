"""تنزيل صور اختبار موثوقة من Wikimedia (محلياً) — للعرض على الموبايل بلا نت.

يتعامل مع تحديد المعدّل (429) بإعادة محاولة بطيئة. شغّله مرة واحدة:
    python download_test_images.py
الصور المنزّلة سابقاً تُتخطّى. صفحة test_gallery.html تعمل أصلاً من روابط
Wikimedia المباشرة (موثوقة)، وهذه النسخ المحلية احتياط للاستخدام دون اتصال.
"""
import os
import time
import urllib.request

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_images")

IMAGES = {
    "healthy/green_crop_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Crop_field%2C_Leyland_Green_-_geograph.org.uk_-_4015548.jpg",
    "healthy/green_crop_2.jpg": "https://upload.wikimedia.org/wikipedia/commons/5/5b/Young_crop_field_near_Cross_Green_-_geograph.org.uk_-_5400543.jpg",
    "healthy/green_leaves_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Ivy_leaves%2C_Clandeboye_Wood_-_geograph.org.uk_-_1995558.jpg",
    "drought/drought_leaves_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/2/24/Starr-101006-9340-Vaccinium_reticulatum-drought_stressed_leaves-Polipoli-Maui_%2824759265360%29.jpg",
    "drought/drought_leaves_2.jpg": "https://upload.wikimedia.org/wikipedia/commons/4/49/Starr-110926-8574-Santalum_haleakalae_var_haleakalae-drought_stressed_leaves-Front_Country_HNP-Maui_%2825022170091%29.jpg",
    "drought/drought_field_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Degraded_plant_condition%2C_overgrazing_and_drought%2C_South_Dakota.jpg",
    "weeds/weeds_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/1/17/Field_margin_with_weeds_-_geograph.org.uk_-_5539082.jpg",
    "weeds/weeds_2.jpg": "https://upload.wikimedia.org/wikipedia/commons/9/95/Weeds_by_the_edge_of_field_-_geograph.org.uk_-_6890199.jpg",
    "weeds/weeds_3.jpg": "https://upload.wikimedia.org/wikipedia/commons/a/ae/Weeds_of_agricultural_land_-_geograph.org.uk_-_4049111.jpg",
    "dry_soil/dry_soil_1.jpg": "https://upload.wikimedia.org/wikipedia/commons/e/e1/Drought.jpg",
    "dry_soil/dry_soil_2.jpg": "https://upload.wikimedia.org/wikipedia/commons/0/07/Dry_and_cracked_soil_-_geograph.org.uk_-_8131059.jpg",
}


def fetch(url, dest, retries=4):
    req = urllib.request.Request(url, headers={"User-Agent": "SpiderAI-Testbed/1.0 (educational)"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) > 15000:
                with open(dest, "wb") as f:
                    f.write(data)
                return True, len(data)
            return False, len(data)
        except Exception as e:
            wait = 5 * (attempt + 1)
            print(f"    … محاولة {attempt+1} فشلت ({e}); انتظار {wait}ث")
            time.sleep(wait)
    return False, 0


def main():
    ok = skip = fail = 0
    for rel, url in IMAGES.items():
        dest = os.path.join(BASE, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest) and os.path.getsize(dest) > 15000:
            print(f"⏭  موجود: {rel}")
            skip += 1
            continue
        print(f"⬇  {rel}")
        good, size = fetch(url, dest)
        if good:
            print(f"   ✓ {size} بايت")
            ok += 1
        else:
            print(f"   ✗ فشل")
            fail += 1
        time.sleep(2)   # تهدئة لتجنّب 429
    print(f"\nتمّ: نزّل {ok} · موجود {skip} · فشل {fail}")


if __name__ == "__main__":
    main()
