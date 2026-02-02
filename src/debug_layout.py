"""
レイアウトロジックのデバッグ用スクリプト
"""
from app import build_blocks, solve_one_plan
from geometry import Rect, can_place
from catalog import FURNITURE
from patterns import place_workstations_face_to_face_center, place_equipment_along_wall


def debug_face_to_face():
    """Plan B (対面配置) のデバッグ"""
    room_w = 4510
    room_d = 3010
    seats_required = 5
    door_side = "B"

    # ブロック・ドア情報を構築
    blocks, door_rect, door_side_out, door_tip = build_blocks(
        room_w, room_d,
        door_w=850, door_d=900,
        door_side=door_side,
        door_offset=None,
    )

    print("=" * 50)
    print("デバッグ: Plan B (対面配置)")
    print("=" * 50)
    print(f"部屋サイズ: {room_w} x {room_d} mm")
    print(f"必要席数: {seats_required}")
    print(f"ドア位置: {door_side_out}")
    print(f"ドアRect: {door_rect}")
    print(f"ドア先端: {door_tip}")
    print(f"ブロック数: {len(blocks)}")
    for i, b in enumerate(blocks):
        print(f"  Block {i}: x={b.x}, y={b.y}, w={b.w}, d={b.d}")

    # 家具サイズ確認
    ws_type = "ws_1000x600"
    ws_w = FURNITURE[ws_type]["w"]
    ws_d = FURNITURE[ws_type]["d"]
    print(f"\nデスクタイプ: {ws_type}")
    print(f"  ws_w (幅): {ws_w}")
    print(f"  ws_d (奥行): {ws_d}")
    print(f"  対面に必要な奥行: {ws_d * 2} = {ws_d * 2} mm")
    print(f"  部屋の奥行: {room_d} mm")
    print(f"  条件 (room_d >= ws_d * 2): {room_d >= ws_d * 2}")

    # 配置計算の詳細
    pairs = seats_required // 2
    total_units = pairs
    total_w = total_units * ws_w
    x_start = int((room_w - total_w) / 2)
    print(f"\n配置計算:")
    print(f"  pairs: {pairs}")
    print(f"  total_units: {total_units}")
    print(f"  total_w: {total_w}")
    print(f"  x_start (中央): {x_start}")
    print(f"  ドア範囲: x={door_rect.x}~{door_rect.x + door_rect.w}")

    # 対面配置を実行
    print("\n対面配置を実行中...")
    res = place_workstations_face_to_face_center(
        room_w=room_w,
        room_d=room_d,
        furniture=FURNITURE,
        ws_type=ws_type,
        seats_required=seats_required,
        blocks=blocks,
        gap_x=0,
        door_side=door_side_out,
        door_rect=door_rect,
        door_tip=door_tip,
    )

    print(f"\n結果:")
    print(f"  ok: {res['ok']}")
    print(f"  seats_placed: {res['seats_placed']}")
    print(f"  pattern: {res['pattern']}")
    print(f"  items数: {len(res['items'])}")

    # アイテム詳細
    for it in res["items"]:
        if it.get("type") in ("desk", "chair"):
            r = it["rect"]
            print(f"    {it['type']}: {it.get('label', '')} at ({r.x}, {r.y}) size ({r.w} x {r.d})")


def debug_equipment():
    """収納配置のデバッグ"""
    room_w = 4510
    room_d = 3010
    seats_required = 5
    storage_count = 2
    door_side = "B"

    blocks, door_rect, door_side_out, door_tip = build_blocks(
        room_w, room_d,
        door_w=850, door_d=900,
        door_side=door_side,
        door_offset=None,
    )

    # まずPlan A (壁付け) を実行
    res_wall = solve_one_plan(
        room_w=room_w,
        room_d=room_d,
        seats_required=seats_required,
        ws_candidates=["ws_1000x600", "ws_1200x600"],
        blocks=blocks,
        equipment=["storage_M"] * storage_count,
        equipment_x_override=None,
        door_side=door_side_out,
        door_offset=None,
        priority="desk",
        door_tip=door_tip,
    )

    print("\n" + "=" * 50)
    print("デバッグ: 収納配置")
    print("=" * 50)
    print(f"結果:")
    print(f"  seats_placed: {res_wall.get('seats_placed', 0)}")
    print(f"  equipment_placed: {res_wall.get('equipment_placed', 0)}")

    # デスクと収納の位置を表示
    for it in res_wall["items"]:
        if it.get("type") in ("desk", "storage_M"):
            r = it["rect"]
            print(f"  {it['type']}: {it.get('label', '')} at ({r.x}, {r.y}) size ({r.w} x {r.d})")


if __name__ == "__main__":
    debug_face_to_face()
    debug_equipment()
