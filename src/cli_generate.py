"""
CLIからレイアウト生成を実行するスクリプト
UIを介さずに条件指定→生成→JSON保存を一気通貫で行う
"""
import json
from pathlib import Path

from app import build_blocks, solve_one_plan
from geometry import Rect
from catalog import FURNITURE
from export_data import export_layout_json
from patterns import place_workstations_face_to_face_center, place_equipment_along_wall
from utils import calc_desk_area, score_layout


def generate_layout(
    room_w: int,
    room_d: int,
    seats_required: int,
    storage_count: int = 0,
    door_side: str = "B",
    priority: str = "desk",
) -> dict:
    """
    レイアウトを生成してJSONに保存する

    Args:
        room_w: 部屋の幅 (mm)
        room_d: 部屋の奥行き (mm)
        seats_required: 必要席数
        storage_count: 収納数
        door_side: ドア位置 (T=上, B=下, L=左, R=右)
        priority: 優先順位 (desk=席数優先, desk_1200=デスク幅1200優先, equipment=収納優先)

    Returns:
        生成結果の辞書
    """
    # 実寸 (+10mm)
    room_w_actual = room_w + 10
    room_d_actual = room_d + 10

    # 設備リスト
    equipment = ["storage_M"] * storage_count

    # ブロック・ドア情報を構築
    blocks, door_rect, door_side_out, door_tip = build_blocks(
        room_w_actual,
        room_d_actual,
        door_w=850,
        door_d=900,
        door_side=door_side,
        door_offset=None,
    )

    # デスク候補
    if priority == "desk_1200":
        ws_candidates_wall = ["ws_1200x600", "ws_1200x700"]
        ws_candidates_face = ["ws_1200x600", "ws_1200x700"]
    else:
        ws_candidates_wall = ["ws_1200x600", "ws_1000x600", "ws_1200x700"]
        ws_candidates_face = ["ws_1000x600", "ws_1200x600", "ws_1200x700"]

    # Plan A: 壁付け
    res_wall = solve_one_plan(
        room_w=room_w_actual,
        room_d=room_d_actual,
        seats_required=seats_required,
        ws_candidates=ws_candidates_wall,
        blocks=blocks,
        equipment=equipment,
        equipment_x_override=None,
        door_side=door_side_out,
        door_offset=None,
        priority=priority,
        door_tip=door_tip,
    )

    # Plan B: 対面
    res_face = None
    for ws_type in ws_candidates_face:
        tmp = place_workstations_face_to_face_center(
            room_w=room_w_actual,
            room_d=room_d_actual,
            furniture=FURNITURE,
            ws_type=ws_type,
            seats_required=seats_required,
            blocks=blocks,
            gap_x=0,
            door_side=door_side_out,
            door_rect=door_rect,
            door_tip=door_tip,
        )
        if equipment:
            tmp = place_equipment_along_wall(
                base_result=tmp,
                room_w=room_w_actual,
                room_d=room_d_actual,
                furniture=FURNITURE,
                equipment_list=equipment,
                blocks=blocks,
                equipment_x_override=None,
                door_side=door_side_out,
                door_offset=None,
                equipment_clearance_mm=0,
            )
        if res_face is None:
            res_face = tmp
        else:
            if score_layout(tmp, priority) > score_layout(res_face, priority):
                res_face = tmp

    # ドアアイテム
    door_item = {
        "type": "door_arc",
        "rect": door_rect,
        "side": door_side_out,
        "swing": "in",
        "flip_v": False,
        "flip_h": False,
    }

    # ページ構成
    pages = [
        {"title": "Plan A (Wall)", "items": res_wall["items"] + [door_item]},
        {"title": "Plan B (Face-to-Face)", "items": res_face["items"] + [door_item]},
    ]

    # JSON保存
    output_path = Path(__file__).parent.parent / "output" / "latest_layout.json"
    output_path.parent.mkdir(exist_ok=True)
    export_layout_json(str(output_path), room_w_actual, room_d_actual, pages)

    return {
        "output_path": str(output_path),
        "room_w": room_w_actual,
        "room_d": room_d_actual,
        "plan_a": {
            "seats_placed": res_wall.get("seats_placed", 0),
            "equipment_placed": res_wall.get("equipment_placed", 0),
            "ok": res_wall.get("ok", False),
        },
        "plan_b": {
            "seats_placed": res_face.get("seats_placed", 0),
            "equipment_placed": res_face.get("equipment_placed", 0),
            "ok": res_face.get("ok", False),
        },
    }


if __name__ == "__main__":
    import sys

    # テストケース定義
    test_cases = [
        {
            "name": "Test 1: 大部屋 (6000x4000, 10席, 収納3, ドア左)",
            "room_w": 6000,
            "room_d": 4000,
            "seats_required": 10,
            "storage_count": 3,
            "door_side": "L",
            "priority": "desk",
        },
        {
            "name": "Test 2: 小部屋 (3500x2500, 3席, 収納1, ドア上)",
            "room_w": 3500,
            "room_d": 2500,
            "seats_required": 3,
            "storage_count": 1,
            "door_side": "T",
            "priority": "desk",
        },
    ]

    for tc in test_cases:
        print("=" * 60)
        print(tc["name"])
        print("=" * 60)
        result = generate_layout(
            room_w=tc["room_w"],
            room_d=tc["room_d"],
            seats_required=tc["seats_required"],
            storage_count=tc["storage_count"],
            door_side=tc["door_side"],
            priority=tc["priority"],
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
