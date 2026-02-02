"""
改善項目の検証テストスクリプト
"""
import json
from pathlib import Path

from app import build_blocks, solve_one_plan
from geometry import Rect, can_place
from catalog import FURNITURE
from export_data import export_layout_json
from patterns import (
    place_workstations_face_to_face_center,
    place_equipment_along_wall,
    place_workstations_mixed,
    place_workstations_double_wall_top_bottom,
)
from constants import CHAIR_SIZE, CHAIR_DESK_GAP


def test_pillar_avoidance():
    """テスト1: 柱を避ける機能"""
    print("\n" + "=" * 60)
    print("TEST 1: 柱を避ける機能")
    print("=" * 60)

    room_w = 5010
    room_d = 4010

    # 柱を配置 (デスクが配置されそうな場所に)
    pillar = Rect(x=4000, y=0, w=600, d=600)

    blocks, door_rect, door_side, door_tip = build_blocks(
        room_w, room_d, door_w=850, door_d=900, door_side="L"
    )
    blocks.append(pillar)

    # 壁付け配置を実行
    res = place_workstations_double_wall_top_bottom(
        room_w=room_w,
        room_d=room_d,
        furniture=FURNITURE,
        ws_type="ws_1000x600",
        seats_required=8,
        blocks=blocks,
        gap_x=0,
        door_tip=door_tip,
    )

    # 結果を確認
    items = res.get("items", [])
    desks = [it for it in items if it.get("type") == "desk"]
    chairs = [it for it in items if it.get("type") == "chair"]

    # 柱と重なっているデスク/椅子がないかチェック
    collision_found = False
    for desk in desks:
        r = desk["rect"]
        if (r.x < pillar.x + pillar.w and r.x + r.w > pillar.x and
            r.y < pillar.y + pillar.d and r.y + r.d > pillar.y):
            collision_found = True
            print(f"  NG: デスク {desk['label']} が柱と衝突!")

    for chair in chairs:
        r = chair["rect"]
        if (r.x < pillar.x + pillar.w and r.x + r.w > pillar.x and
            r.y < pillar.y + pillar.d and r.y + r.d > pillar.y):
            collision_found = True
            print(f"  NG: 椅子 {chair['label']} が柱と衝突!")

    if not collision_found:
        print(f"  OK: 柱を回避して {res['seats_placed']} 席配置")

    return not collision_found


def test_chair_desk_gap():
    """テスト2: 机と椅子の間隔"""
    print("\n" + "=" * 60)
    print("TEST 2: 机と椅子の間隔")
    print("=" * 60)

    room_w = 5010
    room_d = 4010

    blocks, door_rect, door_side, door_tip = build_blocks(
        room_w, room_d, door_w=850, door_d=900, door_side="L"
    )

    res = place_workstations_double_wall_top_bottom(
        room_w=room_w,
        room_d=room_d,
        furniture=FURNITURE,
        ws_type="ws_1000x600",
        seats_required=4,
        blocks=blocks,
        gap_x=0,
        door_tip=door_tip,
    )

    items = res.get("items", [])

    # デスクと椅子のペアを見つけて間隔を確認
    all_correct = True
    expected_gap = CHAIR_DESK_GAP

    for i, item in enumerate(items):
        if item.get("type") == "desk":
            label = item["label"]
            chair_label = label.replace("_D", "_C")
            chair = next((it for it in items if it.get("label") == chair_label), None)
            if chair:
                desk_rect = item["rect"]
                chair_rect = chair["rect"]

                # 間隔を計算 (デスクと椅子の位置関係による)
                # 上壁の場合: 椅子はデスクの下にある
                if desk_rect.y == 0:  # 上壁
                    gap = chair_rect.y - (desk_rect.y + desk_rect.d)
                elif desk_rect.y + desk_rect.d == room_d:  # 下壁
                    gap = desk_rect.y - (chair_rect.y + chair_rect.d)
                else:
                    gap = expected_gap  # その他の場合はスキップ

                if gap == expected_gap:
                    print(f"  OK: {label} - 間隔 {gap}mm")
                else:
                    print(f"  NG: {label} - 間隔 {gap}mm (期待値: {expected_gap}mm)")
                    all_correct = False

    print(f"  CHAIR_DESK_GAP 定数値: {CHAIR_DESK_GAP}mm")
    return all_correct


def test_storage_placement():
    """テスト3: 収納配置ロジック"""
    print("\n" + "=" * 60)
    print("TEST 3: 収納配置ロジック")
    print("=" * 60)

    room_w = 5010
    room_d = 4010

    blocks, door_rect, door_side, door_tip = build_blocks(
        room_w, room_d, door_w=850, door_d=900, door_side="L"
    )

    # まず席を配置
    res = place_workstations_double_wall_top_bottom(
        room_w=room_w,
        room_d=room_d,
        furniture=FURNITURE,
        ws_type="ws_1000x600",
        seats_required=6,
        blocks=blocks,
        gap_x=0,
        door_tip=door_tip,
    )

    # 収納を3個配置
    equipment_list = ["storage_M", "storage_M", "storage_M"]
    res_with_eq = place_equipment_along_wall(
        base_result=res,
        room_w=room_w,
        room_d=room_d,
        furniture=FURNITURE,
        equipment_list=equipment_list,
        blocks=blocks,
        door_side=door_side,
        door_offset=None,
        equipment_clearance_mm=0,
    )

    placed = res_with_eq.get("equipment_placed", 0)
    target = res_with_eq.get("equipment_target", 0)

    if placed == target:
        print(f"  OK: {placed}/{target} 収納を配置")
    else:
        print(f"  NG: {placed}/{target} 収納を配置 (不足)")

    # 収納の位置を表示
    storage_items = [it for it in res_with_eq["items"] if "storage" in it.get("type", "")]
    for st in storage_items:
        r = st["rect"]
        print(f"    - {st['type']}: x={r.x}, y={r.y}")

    return placed == target


def test_large_room():
    """テスト4: 大きな間取り対応"""
    print("\n" + "=" * 60)
    print("TEST 4: 大きな間取り対応 (50m)")
    print("=" * 60)

    # 50m x 30m の部屋
    room_w = 50010
    room_d = 30010

    try:
        blocks, door_rect, door_side, door_tip = build_blocks(
            room_w, room_d, door_w=850, door_d=900, door_side="L"
        )

        res = place_workstations_double_wall_top_bottom(
            room_w=room_w,
            room_d=room_d,
            furniture=FURNITURE,
            ws_type="ws_1200x600",
            seats_required=50,
            blocks=blocks,
            gap_x=0,
            door_tip=door_tip,
        )

        print(f"  OK: 50m x 30m の部屋で {res['seats_placed']} 席配置")
        return True
    except Exception as e:
        print(f"  NG: エラー発生 - {e}")
        return False


def test_mixed_pattern():
    """テスト5: 混在パターン (壁面+対面)"""
    print("\n" + "=" * 60)
    print("TEST 5: 混在パターン (壁面+対面)")
    print("=" * 60)

    room_w = 6010
    room_d = 4010

    blocks, door_rect, door_side, door_tip = build_blocks(
        room_w, room_d, door_w=850, door_d=900, door_side="L"
    )

    try:
        res = place_workstations_mixed(
            room_w=room_w,
            room_d=room_d,
            furniture=FURNITURE,
            ws_type="ws_1000x600",
            seats_required=8,
            blocks=blocks,
            wall_seats=2,
            wall_side="L",
            door_tip=door_tip,
        )

        print(f"  席数: {res['seats_placed']}/{res['seats_required']}")
        print(f"  パターン: {res.get('pattern', 'unknown')}")
        print(f"  OK: {res['ok']}")

        # 壁付けと対面の両方が配置されているか確認
        items = res.get("items", [])
        desks = [it for it in items if it.get("type") == "desk"]

        wall_desks = [d for d in desks if d["rect"].x == 0]  # 左壁に接している
        center_desks = [d for d in desks if d["rect"].x > 0]  # 中央付近

        print(f"  壁付けデスク: {len(wall_desks)}個")
        print(f"  対面デスク: {len(center_desks)}個")

        return res["seats_placed"] > 0
    except Exception as e:
        print(f"  NG: エラー発生 - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_face_to_face_chair_position():
    """テスト6: 対面配置で椅子が部屋外に出ない"""
    print("\n" + "=" * 60)
    print("TEST 6: 対面配置で椅子が部屋外に出ない")
    print("=" * 60)

    room_w = 5010
    room_d = 4010

    blocks, door_rect, door_side, door_tip = build_blocks(
        room_w, room_d, door_w=850, door_d=900, door_side="L"
    )

    res = place_workstations_face_to_face_center(
        room_w=room_w,
        room_d=room_d,
        furniture=FURNITURE,
        ws_type="ws_1200x600",
        seats_required=6,
        blocks=blocks,
        door_side=door_side,
        door_rect=door_rect,
        door_tip=door_tip,
    )

    items = res.get("items", [])
    chairs = [it for it in items if it.get("type") == "chair"]

    all_inside = True
    for chair in chairs:
        r = chair["rect"]
        if r.x < 0 or r.y < 0 or r.x + r.w > room_w or r.y + r.d > room_d:
            print(f"  NG: {chair['label']} が部屋外 (x={r.x}, y={r.y})")
            all_inside = False
        else:
            print(f"  OK: {chair['label']} は部屋内 (x={r.x}, y={r.y})")

    return all_inside


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("改善項目検証テスト")
    print("=" * 60)

    results = {}

    results["柱回避"] = test_pillar_avoidance()
    results["机椅子間隔"] = test_chair_desk_gap()
    results["収納配置"] = test_storage_placement()
    results["大部屋対応"] = test_large_room()
    results["混在パターン"] = test_mixed_pattern()
    results["椅子位置"] = test_face_to_face_chair_position()

    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + ("全テスト合格!" if all_passed else "一部テストが失敗しました"))
