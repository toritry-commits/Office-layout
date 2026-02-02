# 共通ユーティリティ関数
# app.py と streamlit_app.py で重複していた関数を集約
# スコアリング機能: JOIFA基準、建築基準法、人間工学に基づく評価

from typing import Dict, List, Tuple, Any
import math

# 設定ファイルから定数を読み込む
try:
    from constants import get_all_config
    _config = get_all_config()
except ImportError:
    _config = {}


def _get_scoring_config() -> Dict[str, Any]:
    """スコアリング設定を取得"""
    return _config.get("scoring", {})


def _get_passage_config() -> Dict[str, Any]:
    """通路設定を取得"""
    return _config.get("passage", {})


def _get_placement_config() -> Dict[str, Any]:
    """配置設定を取得"""
    return _config.get("placement", {})


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


# ===============================
# 高度なスコアリング機能
# JOIFA基準、建築基準法、人間工学に基づく
# ===============================

def calculate_space_per_person(room_w: int, room_d: int, seat_count: int) -> float:
    """
    一人当たりのスペースを計算 (㎡/人)

    基準:
    - 最小: 4㎡/人 (労働安全衛生法)
    - 推奨: 6.7㎡/人 (カナダ政府オフィス基準)
    - 優秀: 8㎡/人以上
    """
    if seat_count <= 0:
        return 0.0
    room_area_sqm = (room_w / 1000.0) * (room_d / 1000.0)
    return room_area_sqm / seat_count


def evaluate_space_per_person(space_sqm: float) -> Tuple[float, str]:
    """
    一人当たりスペースを評価

    Returns:
        (score 0-1, evaluation_label)
    """
    thresholds = _get_scoring_config().get("thresholds", {})
    excellent = thresholds.get("space_excellent", 8.0)
    good = thresholds.get("space_good", 6.7)
    acceptable = thresholds.get("space_acceptable", 4.0)
    poor = thresholds.get("space_poor", 3.0)

    if space_sqm >= excellent:
        return (1.0, "優秀")
    elif space_sqm >= good:
        score = 0.75 + 0.25 * (space_sqm - good) / (excellent - good)
        return (score, "良好")
    elif space_sqm >= acceptable:
        score = 0.5 + 0.25 * (space_sqm - acceptable) / (good - acceptable)
        return (score, "許容")
    elif space_sqm >= poor:
        score = 0.25 * (space_sqm - poor) / (acceptable - poor)
        return (score, "要改善")
    else:
        return (0.0, "不可")


def calculate_min_passage_width(items: List[Dict], room_w: int, room_d: int) -> int:
    """
    レイアウト内の最小通路幅を計算

    デスク間、デスクと壁の間の最小距離を計算
    注: デスクと椅子の間隔(5mm程度)は通路ではないため除外
    """
    desk_rects = [it["rect"] for it in items if it.get("type") == "desk"]
    chair_rects = [it["rect"] for it in items if it.get("type") == "chair"]

    if not desk_rects:
        return min(room_w, room_d)

    # 通路幅の計算では主にデスク間、デスク-壁、椅子-壁を見る
    # デスクと椅子の間の微小な間隔は通路ではないため除外
    MIN_PASSAGE_THRESHOLD = 100  # 100mm未満は通路とみなさない

    min_gap = float("inf")

    # デスクと壁の距離
    for r in desk_rects:
        left_gap = r.x
        right_gap = room_w - (r.x + r.w)
        top_gap = r.y
        bottom_gap = room_d - (r.y + r.d)
        for gap in [left_gap, right_gap, top_gap, bottom_gap]:
            if gap >= MIN_PASSAGE_THRESHOLD:
                min_gap = min(min_gap, gap)

    # 椅子と壁の距離（椅子の背面スペース）
    for r in chair_rects:
        left_gap = r.x
        right_gap = room_w - (r.x + r.w)
        top_gap = r.y
        bottom_gap = room_d - (r.y + r.d)
        for gap in [left_gap, right_gap, top_gap, bottom_gap]:
            if gap >= MIN_PASSAGE_THRESHOLD:
                min_gap = min(min_gap, gap)

    # デスク間の距離
    for i, r1 in enumerate(desk_rects):
        for j, r2 in enumerate(desk_rects):
            if i >= j:
                continue
            # X方向のギャップ
            if r1.x + r1.w <= r2.x:
                gap_x = r2.x - (r1.x + r1.w)
            elif r2.x + r2.w <= r1.x:
                gap_x = r1.x - (r2.x + r2.w)
            else:
                gap_x = 0
            # Y方向のギャップ
            if r1.y + r1.d <= r2.y:
                gap_y = r2.y - (r1.y + r1.d)
            elif r2.y + r2.d <= r1.y:
                gap_y = r1.y - (r2.y + r2.d)
            else:
                gap_y = 0
            # 通路としてカウント
            if gap_x >= MIN_PASSAGE_THRESHOLD:
                min_gap = min(min_gap, gap_x)
            if gap_y >= MIN_PASSAGE_THRESHOLD:
                min_gap = min(min_gap, gap_y)

    # 椅子間の距離（背中合わせの場合など）
    for i, r1 in enumerate(chair_rects):
        for j, r2 in enumerate(chair_rects):
            if i >= j:
                continue
            if r1.x + r1.w <= r2.x:
                gap_x = r2.x - (r1.x + r1.w)
            elif r2.x + r2.w <= r1.x:
                gap_x = r1.x - (r2.x + r2.w)
            else:
                gap_x = 0
            if r1.y + r1.d <= r2.y:
                gap_y = r2.y - (r1.y + r1.d)
            elif r2.y + r2.d <= r1.y:
                gap_y = r1.y - (r2.y + r2.d)
            else:
                gap_y = 0
            if gap_x >= MIN_PASSAGE_THRESHOLD:
                min_gap = min(min_gap, gap_x)
            if gap_y >= MIN_PASSAGE_THRESHOLD:
                min_gap = min(min_gap, gap_y)

    return int(min_gap) if min_gap != float("inf") else min(room_w, room_d)


def evaluate_passage_width(passage_mm: int) -> Tuple[float, str]:
    """
    通路幅を評価

    基準 (JOIFA/建築基準法):
    - 優秀: 1600mm以上 (メイン通路・すれ違い余裕あり)
    - 良好: 1200mm以上 (2人すれ違い可能・避難経路基準)
    - 許容: 900mm以上 (1人通行・推奨最小値)
    - 不可: 600mm未満 (人体寸法の限界)

    Returns:
        (score 0-1, evaluation_label)
    """
    thresholds = _get_scoring_config().get("thresholds", {})
    excellent = thresholds.get("passage_excellent", 1600)
    good = thresholds.get("passage_good", 1200)
    acceptable = thresholds.get("passage_acceptable", 900)
    poor = thresholds.get("passage_poor", 600)

    if passage_mm >= excellent:
        return (1.0, "優秀")
    elif passage_mm >= good:
        score = 0.75 + 0.25 * (passage_mm - good) / (excellent - good)
        return (score, "良好")
    elif passage_mm >= acceptable:
        score = 0.5 + 0.25 * (passage_mm - acceptable) / (good - acceptable)
        return (score, "許容")
    elif passage_mm >= poor:
        score = 0.25 * (passage_mm - poor) / (acceptable - poor)
        return (score, "要改善")
    else:
        return (0.0, "不可")


def calculate_door_accessibility(
    items: List[Dict],
    door_tip: Tuple[float, float],
    room_w: int,
    room_d: int
) -> float:
    """
    ドアからの動線効率を計算

    全デスクへのドアからの平均距離を正規化して返す
    値が小さいほど動線効率が良い (0-1に正規化、1が最良)
    """
    if door_tip is None:
        return 0.5  # ドア情報がない場合は中間値

    desk_rects = [it["rect"] for it in items if it.get("type") == "desk"]
    if not desk_rects:
        return 1.0

    px, py = door_tip
    total_dist = 0
    for r in desk_rects:
        # デスク中心までの距離
        cx = r.x + r.w / 2
        cy = r.y + r.d / 2
        dist = math.sqrt((cx - px) ** 2 + (cy - py) ** 2)
        total_dist += dist

    avg_dist = total_dist / len(desk_rects)
    # 部屋の対角線で正規化
    max_dist = math.sqrt(room_w ** 2 + room_d ** 2)
    normalized = avg_dist / max_dist if max_dist > 0 else 0

    # 距離が短いほどスコアが高い (反転)
    return max(0, 1 - normalized)


def check_evacuation_compliance(
    items: List[Dict],
    room_w: int,
    room_d: int,
    min_evacuation_width: int = 1200
) -> Tuple[bool, int]:
    """
    避難経路の法的要件をチェック

    建築基準法施行令第119条:
    - 片側居室: 1200mm以上
    - 両側居室: 1600mm以上

    Returns:
        (is_compliant, actual_min_width)
    """
    min_passage = calculate_min_passage_width(items, room_w, room_d)
    passage_config = _get_passage_config()
    required = passage_config.get("evacuation_route", min_evacuation_width)
    return (min_passage >= required, min_passage)


def calculate_detailed_score(
    result: Dict,
    room_w: int,
    room_d: int,
    door_tip: Tuple[float, float] = None,
    preset: str = "balanced"
) -> Dict[str, Any]:
    """
    詳細なスコアリングを実行

    Args:
        result: レイアウト結果
        room_w: 部屋の幅(mm)
        room_d: 部屋の奥行(mm)
        door_tip: ドア先端座標
        preset: スコアリングプリセット名

    Returns:
        詳細スコア情報を含む辞書
    """
    items = result.get("items", [])
    seats_placed = result.get("seats_placed", 0)
    pattern = result.get("pattern", "")

    # 設定から重みを取得
    scoring_config = _get_scoring_config()
    presets = scoring_config.get("presets", {})
    weights = presets.get(preset, scoring_config.get("weights", {}))

    # 各指標を計算
    space_per_person = calculate_space_per_person(room_w, room_d, seats_placed)
    space_score, space_label = evaluate_space_per_person(space_per_person)

    min_passage = calculate_min_passage_width(items, room_w, room_d)
    passage_score, passage_label = evaluate_passage_width(min_passage)

    door_score = calculate_door_accessibility(items, door_tip, room_w, room_d)

    is_compliant, actual_min = check_evacuation_compliance(items, room_w, room_d)
    compliance_score = 1.0 if is_compliant else 0.5

    # 対面配置ボーナス
    face_to_face = 1.0 if "face_to_face" in pattern else 0.0

    # 席数スコア (要求席数に対する達成率)
    seats_required = result.get("seats_required", seats_placed)
    seat_ratio = seats_placed / seats_required if seats_required > 0 else 1.0
    seat_score = min(1.0, seat_ratio)

    # スペース効率 (配置面積 / 部屋面積)
    desk_rects = [it["rect"] for it in items if it.get("type") == "desk"]
    used_area = sum(r.w * r.d for r in desk_rects)
    room_area = room_w * room_d
    efficiency = used_area / room_area if room_area > 0 else 0
    efficiency_score = min(1.0, efficiency * 5)  # 20%使用で満点

    # 総合スコアを計算
    total_score = 0
    weight_sum = 0

    score_components = {
        "seat_count": seat_score,
        "passage_width": passage_score,
        "traffic_flow": door_score,
        "space_per_person": space_score,
        "evacuation_compliance": compliance_score,
        "face_to_face_bonus": face_to_face,
        "space_efficiency": efficiency_score,
    }

    for key, score in score_components.items():
        w = weights.get(key, 0)
        total_score += score * w
        weight_sum += w

    final_score = total_score / weight_sum if weight_sum > 0 else 0

    return {
        "total_score": round(final_score, 3),
        "seat_count": seats_placed,
        "seat_score": round(seat_score, 3),
        "space_per_person_sqm": round(space_per_person, 2),
        "space_per_person_label": space_label,
        "space_per_person_score": round(space_score, 3),
        "min_passage_mm": min_passage,
        "passage_label": passage_label,
        "passage_score": round(passage_score, 3),
        "door_accessibility_score": round(door_score, 3),
        "evacuation_compliant": is_compliant,
        "evacuation_score": round(compliance_score, 3),
        "face_to_face_bonus": face_to_face,
        "space_efficiency_score": round(efficiency_score, 3),
        "pattern": pattern,
        "preset_used": preset,
    }


def score_layout_advanced(
    result: Dict,
    room_w: int,
    room_d: int,
    door_tip: Tuple[float, float] = None,
    preset: str = "balanced"
) -> Tuple[float, Dict[str, Any]]:
    """
    高度なレイアウトスコアリング

    Returns:
        (total_score, detailed_scores)
    """
    detailed = calculate_detailed_score(result, room_w, room_d, door_tip, preset)
    return (detailed["total_score"], detailed)
