"""
レイアウトスコアリング機能のテストスクリプト
設計原則に基づく評価を実行
"""
import json
from geometry import Rect, calc_passage_widths
from utils import (
    score_layout_advanced,
    calculate_detailed_score,
    evaluate_space_per_person,
    evaluate_passage_width,
    calculate_space_per_person,
)


def load_layout_json(filepath: str) -> dict:
    """JSONファイルからレイアウトを読み込む"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def convert_items_to_rects(items: list) -> list:
    """JSON形式のitemsをRect形式に変換"""
    converted = []
    for it in items:
        if "x" in it and "y" in it and "w" in it and "d" in it:
            rect = Rect(x=it["x"], y=it["y"], w=it["w"], d=it["d"])
            converted.append({
                "type": it.get("type", ""),
                "label": it.get("label", ""),
                "rect": rect,
            })
    return converted


def evaluate_layout(page: dict, room_w: int, room_d: int) -> dict:
    """レイアウトページを評価"""
    items = convert_items_to_rects(page.get("items", []))

    # 基本情報
    desks = [it for it in items if it.get("type") == "desk"]
    chairs = [it for it in items if it.get("type") == "chair"]
    storage = [it for it in items if it.get("type") == "storage_M"]

    seats_placed = len(desks)
    equipment_placed = len(storage)

    # 通路幅計算
    passage_widths = calc_passage_widths(items, room_w, room_d)
    min_passage = passage_widths.get("min_passage", 0)

    # スペース効率
    space_per_person = calculate_space_per_person(room_w, room_d, seats_placed)
    space_score, space_label = evaluate_space_per_person(space_per_person)

    # 通路評価
    passage_score, passage_label = evaluate_passage_width(min_passage)

    return {
        "title": page.get("title", ""),
        "seats_placed": seats_placed,
        "equipment_placed": equipment_placed,
        "min_passage_mm": min_passage,
        "passage_label": passage_label,
        "passage_score": round(passage_score, 2),
        "space_per_person_sqm": round(space_per_person, 2),
        "space_label": space_label,
        "space_score": round(space_score, 2),
        "passage_widths": passage_widths,
    }


def main():
    print("=" * 60)
    print("オフィスレイアウト スコアリングテスト")
    print("=" * 60)

    # JSONファイル読み込み
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    json_path = os.path.join(project_root, "layout_3plans.json")
    layout = load_layout_json(json_path)
    meta = layout.get("meta", {})
    room_w = meta.get("room_w", 5010)
    room_d = meta.get("room_d", 4010)

    print(f"\n部屋サイズ: {room_w}mm x {room_d}mm")
    print(f"面積: {room_w * room_d / 1000000:.2f}㎡")
    print("-" * 60)

    # 各プランを評価
    for page in layout.get("pages", []):
        result = evaluate_layout(page, room_w, room_d)

        print(f"\n【{result['title']}】")
        print(f"  席数: {result['seats_placed']}")
        print(f"  設備数: {result['equipment_placed']}")
        print(f"  最小通路幅: {result['min_passage_mm']}mm ({result['passage_label']})")
        print(f"  通路スコア: {result['passage_score']}")
        print(f"  一人当たりスペース: {result['space_per_person_sqm']}㎡/人 ({result['space_label']})")
        print(f"  スペーススコア: {result['space_score']}")

        # 詳細な通路幅情報
        pw = result['passage_widths']
        print(f"  通路詳細:")
        print(f"    - 左壁からの距離: {pw.get('left_wall_gap', 0)}mm")
        print(f"    - 右壁からの距離: {pw.get('right_wall_gap', 0)}mm")
        print(f"    - 上壁からの距離: {pw.get('top_wall_gap', 0)}mm")
        print(f"    - 下壁からの距離: {pw.get('bottom_wall_gap', 0)}mm")
        print(f"    - 横方向最小間隔: {pw.get('min_horizontal', 0)}mm")
        print(f"    - 縦方向最小間隔: {pw.get('min_vertical', 0)}mm")

    # 設計原則との比較
    print("\n" + "=" * 60)
    print("設計原則チェック")
    print("=" * 60)
    print("\n基準値:")
    print("  - メイン通路幅: 1200mm以上 (すれ違い可能)")
    print("  - 最小通路幅: 600mm以上 (一人通行)")
    print("  - 一人当たりスペース: 6.7㎡/人以上 (推奨)")
    print("  - 避難経路: 1200mm以上 (建築基準法)")

    print("\n各プランの判定:")
    for page in layout.get("pages", []):
        result = evaluate_layout(page, room_w, room_d)
        title = result['title']

        # 通路幅チェック
        passage_ok = "OK" if result['min_passage_mm'] >= 1200 else "NG"
        passage_min_ok = "OK" if result['min_passage_mm'] >= 600 else "NG"

        # スペースチェック
        space_ok = "OK" if result['space_per_person_sqm'] >= 6.7 else "NG"

        print(f"\n  {title}:")
        print(f"    passage>=1200mm: {passage_ok} ({result['min_passage_mm']}mm)")
        print(f"    passage>=600mm: {passage_min_ok} ({result['min_passage_mm']}mm)")
        print(f"    space>=6.7sqm: {space_ok} ({result['space_per_person_sqm']}sqm)")


if __name__ == "__main__":
    main()
