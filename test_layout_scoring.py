# -*- coding: utf-8 -*-
"""
レイアウト生成とスコアリングのテストスクリプト
業界標準に基づいた評価を確認する
"""
import sys
import json
from pathlib import Path

# srcディレクトリをパスに追加
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from catalog import FURNITURE
from patterns import (
    place_workstations_face_to_face_center,
    place_workstations_double_wall,
    place_equipment_along_wall,
)
from geometry import Rect
from utils import (
    score_layout,
    calculate_detailed_score,
    calculate_space_per_person,
    evaluate_space_per_person,
    calculate_min_passage_width,
    evaluate_passage_width,
    check_evacuation_compliance,
)


def test_layout(room_w: int, room_d: int, seats: int, pattern: str = "face_to_face"):
    """
    指定した部屋サイズと席数でレイアウトを生成し、スコアリングする
    """
    print(f"\n{'='*60}")
    print(f"部屋サイズ: {room_w}mm x {room_d}mm ({room_w/1000:.1f}m x {room_d/1000:.1f}m)")
    print(f"面積: {(room_w/1000)*(room_d/1000):.1f}㎡")
    print(f"要求席数: {seats}席")
    print(f"パターン: {pattern}")
    print(f"{'='*60}")

    # ドア位置 (下辺中央)
    door_tip = (room_w / 2, room_d)

    # レイアウト生成
    if pattern == "face_to_face":
        result = place_workstations_face_to_face_center(
            room_w=room_w,
            room_d=room_d,
            furniture=FURNITURE,
            ws_type="ws_1200x600",
            seats_required=seats,
            blocks=[],
            door_side="B",
            door_rect=None,
            door_tip=door_tip,
        )
    else:  # double_wall
        result = place_workstations_double_wall(
            room_w=room_w,
            room_d=room_d,
            furniture=FURNITURE,
            ws_type="ws_1200x600",
            seats_required=seats,
            blocks=[],
            door_tip=door_tip,
        )

    # 設備を追加
    equipment = ["storage_M", "mfp"]
    result = place_equipment_along_wall(
        base_result=result,
        room_w=room_w,
        room_d=room_d,
        furniture=FURNITURE,
        equipment_list=equipment,
        blocks=[],
        door_side="B",
    )

    # 基本情報
    print(f"\n[配置結果]")
    print(f"  配置成功: {result.get('ok')}")
    print(f"  配置席数: {result.get('seats_placed')}席")
    print(f"  設備配置: {result.get('equipment_placed', 0)}個")

    # 詳細スコアリング
    items = result.get("items", [])

    # 一人当たりスペース
    space = calculate_space_per_person(room_w, room_d, result.get("seats_placed", 0))
    space_score, space_label = evaluate_space_per_person(space)
    print(f"\n[一人当たりスペース]")
    print(f"  面積: {space:.2f}㎡/人")
    print(f"  評価: {space_label} (スコア: {space_score:.2f})")
    print(f"  基準: 最小4㎡/人、推奨6.7㎡/人")

    # 通路幅
    min_passage = calculate_min_passage_width(items, room_w, room_d)
    passage_score, passage_label = evaluate_passage_width(min_passage)
    print(f"\n[最小通路幅]")
    print(f"  幅: {min_passage}mm")
    print(f"  評価: {passage_label} (スコア: {passage_score:.2f})")
    print(f"  基準: 許容900mm、良好1200mm、優秀1600mm")

    # 避難経路
    is_compliant, actual_min = check_evacuation_compliance(items, room_w, room_d)
    print(f"\n[避難経路]")
    print(f"  法規準拠: {'OK' if is_compliant else 'NG'}")
    print(f"  最小幅: {actual_min}mm (基準: 1200mm以上)")

    # 詳細スコア
    detailed = calculate_detailed_score(result, room_w, room_d, door_tip, "balanced")
    print(f"\n[総合スコア]")
    print(f"  スコア: {detailed['total_score']:.3f}")
    print(f"  プリセット: {detailed['preset_used']}")

    # JSON出力用データ
    output_data = {
        "room": {
            "width_mm": room_w,
            "depth_mm": room_d,
            "area_sqm": round((room_w/1000)*(room_d/1000), 2),
        },
        "layout": {
            "pattern": result.get("pattern"),
            "seats_placed": result.get("seats_placed"),
            "equipment_placed": result.get("equipment_placed", 0),
            "ok": result.get("ok"),
        },
        "scoring": {
            "total_score": detailed["total_score"],
            "space_per_person_sqm": detailed["space_per_person_sqm"],
            "space_per_person_label": detailed["space_per_person_label"],
            "min_passage_mm": detailed["min_passage_mm"],
            "passage_label": detailed["passage_label"],
            "evacuation_compliant": detailed["evacuation_compliant"],
        },
        "items": [
            {
                "type": it.get("type"),
                "label": it.get("label"),
                "x": it["rect"].x,
                "y": it["rect"].y,
                "w": it["rect"].w,
                "d": it["rect"].d,
            }
            for it in items
            if it.get("type") in ("desk", "chair", "storage_M", "mfp")
        ]
    }

    return output_data


def main():
    """複数のテストケースを実行"""
    print("=" * 60)
    print("オフィスレイアウト スコアリングテスト")
    print("業界標準: JOIFA基準、建築基準法施行令第119条")
    print("=" * 60)

    test_cases = [
        # (幅mm, 奥行mm, 席数, パターン)
        # 対面配置は奥行3600mm以上必要 (机600mm x 2 + 椅子700mm x 2 + 通路)
        (5000, 4000, 4, "face_to_face"),   # 小規模オフィス (20㎡)
        (6000, 5000, 6, "face_to_face"),   # 中規模オフィス (30㎡)
        (8000, 6000, 10, "double_wall"),   # 大規模オフィス (48㎡)
        (4000, 4000, 2, "face_to_face"),   # 最小構成 (16㎡)
    ]

    all_results = []
    for room_w, room_d, seats, pattern in test_cases:
        result = test_layout(room_w, room_d, seats, pattern)
        all_results.append(result)

    # JSON出力
    output_path = Path(__file__).parent / "output" / "test_scoring_results.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"結果をJSONファイルに出力しました: {output_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
