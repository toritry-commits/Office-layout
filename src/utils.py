# 共通ユーティリティ関数
# app.py と streamlit_app.py で重複していた関数を集約

from typing import Dict, List


def parse_desk_depth(ws_type: str) -> int:
    """
    机タイプから奥行を取得する
    例: ws_1000x600 -> 600
    """
    try:
        s = ws_type.replace("ws_", "")
        _, b = s.split("x")
        return int(b)
    except Exception:
        return 600


def calc_desk_area(ws_type: str) -> int:
    """
    机タイプから面積を計算する
    例: ws_1200x600 -> 720000
    """
    try:
        s = ws_type.replace("ws_", "")
        a, b = s.split("x")
        return int(a) * int(b)
    except Exception:
        return 0


def score_layout(result: Dict, priority: str) -> tuple:
    """
    レイアウト結果をスコア化する(比較用)

    Args:
        result: レイアウト結果(ok, seats_placed, equipment_placed, ws_typeを含む)
        priority: 優先項目("equipment", "desk", "desk_1200")

    Returns:
        比較用タプル(大きいほど良い)
    """
    ok = 1 if result.get("ok") else 0
    seats = result.get("seats_placed", 0)
    equip = result.get("equipment_placed", 0)
    desk_area = calc_desk_area(result.get("ws_type", ""))

    if priority in ("desk", "desk_1200"):
        return (ok, seats, desk_area, equip)
    return (ok, seats, equip, desk_area)


def parse_equipment(equip_str: str) -> List[str]:
    """
    設備文字列をリストに変換する
    例: "storage_M,storage_M,mfp" -> ["storage_M", "storage_M", "mfp"]
    """
    if not equip_str:
        return []
    parts = [p.strip() for p in equip_str.split(",")]
    return [p for p in parts if p]


def get_ws_candidates(priority: str) -> tuple:
    """
    優先項目に応じた机候補リストを返す

    Returns:
        (wall_candidates, face_candidates)
    """
    if priority == "desk_1200":
        wall = ["ws_1200x600", "ws_1200x700"]
        face = ["ws_1200x600", "ws_1200x700"]
    else:
        wall = ["ws_1200x600", "ws_1000x600", "ws_1200x700"]
        face = ["ws_1000x600", "ws_1200x600", "ws_1200x700"]
    return wall, face
