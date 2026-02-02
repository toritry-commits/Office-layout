import csv
import json
from datetime import datetime


def export_layout_json(out_path: str, room_w: int, room_d: int, pages: list):
    """
    pages: [{"title": str, "items": [ {type, label, rect, ...}, ... ]}, ...]
    rect: Rect(x,y,w,d) in mm
    """
    data = {
        "meta": {
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "unit": "mm",
            "room_w": room_w,
            "room_d": room_d,
        },
        "pages": [],
    }

    for p in pages:
        page_obj = {"title": p.get("title", ""), "items": []}
        for it in p.get("items", []):
            r = it["rect"]
            page_obj["items"].append(
                {
                    "type": it.get("type", ""),
                    "label": it.get("label", ""),
                    "shape": it.get("shape", ""),
                    "x": int(r.x),
                    "y": int(r.y),
                    "w": int(r.w),
                    "d": int(r.d),
                }
            )
        data["pages"].append(page_obj)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def export_layout_csv(out_path: str, pages: list):
    """
    1行=1アイテム
    """
    fieldnames = ["plan_title", "type", "label", "shape", "x", "y", "w", "d", "note"]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for p in pages:
            title = p.get("title", "")
            for it in p.get("items", []):
                r = it["rect"]
                w.writerow(
                    {
                        "plan_title": title,
                        "type": it.get("type", ""),
                        "label": it.get("label", ""),
                        "shape": it.get("shape", ""),
                        "x": int(r.x),
                        "y": int(r.y),
                        "w": int(r.w),
                        "d": int(r.d),
                        "note": "",
                    }
                )
