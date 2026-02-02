# レイアウトスコアリングモジュール
# オフィスレイアウト設計原則に基づく評価機能
#
# 参考基準:
# - JOIFA (日本オフィス家具協会) ガイドライン
# - 事務所衛生基準規則
# - BIFMA G1-2013, ISO 9241-5:2024
# - 消防法・建築基準法

import os
import math
import yaml
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# ========== 設計基準定数 (mm) ==========

# 通路幅基準
MAIN_AISLE_MIN = 1200       # メイン通路最小幅 (すれ違い可能)
MAIN_AISLE_OPTIMAL = 1500   # メイン通路推奨幅
SUB_AISLE_MIN = 900         # サブ通路最小幅
SUB_AISLE_OPTIMAL = 1200    # サブ通路推奨幅
ONE_PERSON_MIN = 600        # 1人通行最小幅
EMERGENCY_EXIT_MIN = 860    # 非常口通路最小幅 (消防法)

# 椅子・デスク間隔基準
CHAIR_CLEARANCE_MIN = 800   # 椅子後ろの最小クリアランス
CHAIR_CLEARANCE_OPTIMAL = 1100  # 椅子後ろの推奨クリアランス
DESK_ROW_SPACING_MIN = 900  # デスク列間の最小間隔
DESK_ROW_SPACING_OPTIMAL = 1200  # デスク列間の推奨間隔

# 一人当たり面積基準 (mm²)
AREA_PER_PERSON_MIN = 4_000_000      # 最小 4㎡ (法令基準相当)
AREA_PER_PERSON_OPTIMAL = 10_000_000  # 推奨 10㎡
AREA_PER_PERSON_MAX = 15_000_000     # 最大 15㎡ (広すぎは非効率)

# 採光基準 (窓からの距離)
WINDOW_PROXIMITY_OPTIMAL = 2000   # 最適距離 2m以内
WINDOW_PROXIMITY_MAX = 5000       # 効果がある最大距離 5m

# 動線基準
TRAFFIC_FLOW_OPTIMAL = 3000   # ドアから3m以内が最適
TRAFFIC_FLOW_MAX = 8000       # 動線の最大距離


@dataclass
class ScoreBreakdown:
    """スコアの内訳を保持するクラス"""
    seat_count: float = 0.0           # 席数スコア
    passage_width: float = 0.0         # 通路幅スコア
    natural_light: float = 0.0         # 採光スコア
    traffic_flow: float = 0.0          # 動線効率スコア
    face_to_face_bonus: float = 0.0    # 対面配置ボーナス
    space_efficiency: float = 0.0      # スペース効率スコア
    desk_spacing: float = 0.0          # デスク間隔スコア (新規)
    area_per_person: float = 0.0       # 一人当たり面積スコア (新規)
    total: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "seat_count": round(self.seat_count, 3),
            "passage_width": round(self.passage_width, 3),
            "natural_light": round(self.natural_light, 3),
            "traffic_flow": round(self.traffic_flow, 3),
            "face_to_face_bonus": round(self.face_to_face_bonus, 3),
            "space_efficiency": round(self.space_efficiency, 3),
            "desk_spacing": round(self.desk_spacing, 3),
            "area_per_person": round(self.area_per_person, 3),
            "total": round(self.total, 3),
        }


# デフォルトの重み (config.yamlが読めない場合のフォールバック)
DEFAULT_WEIGHTS = {
    "seat_count": 1.0,
    "passage_width": 0.8,       # 通路幅の重要性を上げた
    "natural_light": 0.5,       # 採光の重要性を上げた
    "traffic_flow": 0.6,        # 動線効率の重要性を上げた
    "face_to_face_bonus": 0.3,
    "space_efficiency": 0.4,
    "desk_spacing": 0.7,        # 新規: デスク間隔
    "area_per_person": 0.6,     # 新規: 一人当たり面積
}


def _find_config_path() -> Optional[str]:
    """config.yamlのパスを探す"""
    src_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(src_dir)
    config_path = os.path.join(project_root, "config.yaml")
    if os.path.exists(config_path):
        return config_path
    return None


def load_scoring_weights(preset: Optional[str] = None) -> Dict[str, float]:
    """
    config.yamlからスコアリングの重みを読み込む

    Args:
        preset: プリセット名 ("max_seats", "comfort", "collaboration", "balanced", "ergonomic")
    """
    config_path = _find_config_path()
    if not config_path:
        return DEFAULT_WEIGHTS.copy()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        scoring_config = config.get("scoring", {})

        if preset and preset in scoring_config.get("presets", {}):
            weights = DEFAULT_WEIGHTS.copy()
            weights.update(scoring_config["presets"][preset])
            return weights

        weights = DEFAULT_WEIGHTS.copy()
        weights.update(scoring_config.get("weights", {}))
        return weights
    except Exception:
        return DEFAULT_WEIGHTS.copy()


def _get_desks_and_chairs(items: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """アイテムリストから机と椅子を抽出"""
    desks = [item for item in items if item.get("type") == "desk"]
    chairs = [item for item in items if item.get("type") == "chair"]
    return desks, chairs


def _calc_seat_score(result: Dict, room_w: int, room_d: int) -> float:
    """
    席数スコアを計算 (0.0 - 1.0)

    部屋面積から理論的な最大席数を推定し、達成率を計算
    推奨一人当たり面積 10㎡ を基準にする
    """
    seats = result.get("seats_placed", 0)
    if seats == 0:
        return 0.0

    # 理論的最大席数 (一人当たり10㎡として)
    total_area = room_w * room_d
    theoretical_max = max(1, total_area // AREA_PER_PERSON_OPTIMAL)

    # 達成率を計算 (最大1.0)
    return min(seats / theoretical_max, 1.0)


def _calc_passage_score(result: Dict, room_w: int, room_d: int) -> float:
    """
    通路幅スコアを計算 (0.0 - 1.0)

    設計基準:
    - メイン通路: 1200mm以上 (すれ違い可能)
    - サブ通路: 900mm以上
    - 最低: 600mm (1人通行)
    """
    items = result.get("items", [])
    desks, chairs = _get_desks_and_chairs(items)

    if not desks:
        return 1.0

    # 中央の通路幅を推定
    # 左右の壁から最も近いデスクまでの距離を計算
    left_items = [d for d in desks if d.get("rect") and d["rect"].x < room_w / 2]
    right_items = [d for d in desks if d.get("rect") and d["rect"].x >= room_w / 2]

    center_gap = room_w  # 初期値は部屋幅

    if left_items and right_items:
        # 左側の最も右端
        left_edge = max(d["rect"].x + d["rect"].w for d in left_items if d.get("rect"))
        # 右側の最も左端
        right_edge = min(d["rect"].x for d in right_items if d.get("rect"))
        center_gap = right_edge - left_edge

    # 椅子のクリアランスも考慮
    chair_gaps = []
    for chair in chairs:
        rect = chair.get("rect")
        if not rect:
            continue
        # 椅子の後ろのスペースを計算 (簡易的に壁との距離)
        back_side = chair.get("chair_back", "B")
        if back_side == "T":
            gap = rect.y
        elif back_side == "B":
            gap = room_d - (rect.y + rect.d)
        elif back_side == "L":
            gap = rect.x
        else:  # R
            gap = room_w - (rect.x + rect.w)
        chair_gaps.append(gap)

    # スコア計算
    scores = []

    # メイン通路スコア
    if center_gap >= MAIN_AISLE_OPTIMAL:
        scores.append(1.0)
    elif center_gap >= MAIN_AISLE_MIN:
        scores.append(0.7 + 0.3 * (center_gap - MAIN_AISLE_MIN) / (MAIN_AISLE_OPTIMAL - MAIN_AISLE_MIN))
    elif center_gap >= SUB_AISLE_MIN:
        scores.append(0.4 + 0.3 * (center_gap - SUB_AISLE_MIN) / (MAIN_AISLE_MIN - SUB_AISLE_MIN))
    elif center_gap >= ONE_PERSON_MIN:
        scores.append(0.2 + 0.2 * (center_gap - ONE_PERSON_MIN) / (SUB_AISLE_MIN - ONE_PERSON_MIN))
    else:
        scores.append(0.0)

    # 椅子クリアランススコア
    if chair_gaps:
        avg_chair_gap = sum(chair_gaps) / len(chair_gaps)
        if avg_chair_gap >= CHAIR_CLEARANCE_OPTIMAL:
            scores.append(1.0)
        elif avg_chair_gap >= CHAIR_CLEARANCE_MIN:
            scores.append(0.5 + 0.5 * (avg_chair_gap - CHAIR_CLEARANCE_MIN) / (CHAIR_CLEARANCE_OPTIMAL - CHAIR_CLEARANCE_MIN))
        else:
            scores.append(max(0, avg_chair_gap / CHAIR_CLEARANCE_MIN * 0.5))

    return sum(scores) / len(scores) if scores else 0.5


def _calc_natural_light_score(
    result: Dict,
    room_w: int,
    room_d: int,
    window_sides: List[str] = None
) -> float:
    """
    採光スコアを計算 (0.0 - 1.0)

    設計基準:
    - 窓から2m以内: 最適
    - 窓から5m以内: 効果あり
    - 窓に対して垂直に配置: ボーナス

    Args:
        window_sides: 窓がある壁 ["T", "R"] など。Noneの場合は上と右に窓があると仮定
    """
    items = result.get("items", [])
    desks, _ = _get_desks_and_chairs(items)

    if not desks:
        return 0.5

    if window_sides is None:
        window_sides = ["T", "R"]  # デフォルト: 上辺と右辺に窓

    total_score = 0.0

    for desk in desks:
        rect = desk.get("rect")
        if not rect:
            continue

        desk_center_x = rect.x + rect.w / 2
        desk_center_y = rect.y + rect.d / 2

        # 各窓からの距離を計算
        distances = []
        if "T" in window_sides:
            distances.append(desk_center_y)
        if "B" in window_sides:
            distances.append(room_d - desk_center_y)
        if "L" in window_sides:
            distances.append(desk_center_x)
        if "R" in window_sides:
            distances.append(room_w - desk_center_x)

        if not distances:
            total_score += 0.5
            continue

        min_dist = min(distances)

        # 距離に基づくスコア
        if min_dist <= WINDOW_PROXIMITY_OPTIMAL:
            base_score = 1.0
        elif min_dist <= WINDOW_PROXIMITY_MAX:
            base_score = 0.3 + 0.7 * (WINDOW_PROXIMITY_MAX - min_dist) / (WINDOW_PROXIMITY_MAX - WINDOW_PROXIMITY_OPTIMAL)
        else:
            base_score = max(0, 0.3 * (1.0 - (min_dist - WINDOW_PROXIMITY_MAX) / WINDOW_PROXIMITY_MAX))

        total_score += base_score

    return total_score / len(desks)


def _calc_traffic_flow_score(
    result: Dict,
    room_w: int,
    room_d: int,
    door_positions: List[Dict] = None
) -> float:
    """
    動線効率スコアを計算 (0.0 - 1.0)

    設計基準:
    - ドアから3m以内: 最適
    - 動線はシンプルで最短距離が望ましい
    - 全席がメイン通路にアクセス可能であること
    """
    items = result.get("items", [])
    desks, _ = _get_desks_and_chairs(items)

    if not desks:
        return 0.5

    # ドア位置が指定されていない場合、結果から推測または中央下に仮定
    if not door_positions:
        # door_arc アイテムを探す
        door_items = [item for item in items if item.get("type") == "door_arc"]
        if door_items:
            door_positions = []
            for door in door_items:
                rect = door.get("rect")
                if rect:
                    door_positions.append({
                        "x": rect.x + rect.w / 2,
                        "y": rect.y + rect.d / 2
                    })
        else:
            # デフォルト: 下辺中央
            door_positions = [{"x": room_w / 2, "y": room_d}]

    total_score = 0.0

    for desk in desks:
        rect = desk.get("rect")
        if not rect:
            continue

        desk_center_x = rect.x + rect.w / 2
        desk_center_y = rect.y + rect.d / 2

        # 最も近いドアからの距離
        min_door_dist = float("inf")
        for door in door_positions:
            dx = desk_center_x - door.get("x", room_w / 2)
            dy = desk_center_y - door.get("y", room_d)
            dist = math.sqrt(dx ** 2 + dy ** 2)
            min_door_dist = min(min_door_dist, dist)

        # 距離に基づくスコア
        if min_door_dist <= TRAFFIC_FLOW_OPTIMAL:
            score = 1.0
        elif min_door_dist <= TRAFFIC_FLOW_MAX:
            score = 0.3 + 0.7 * (TRAFFIC_FLOW_MAX - min_door_dist) / (TRAFFIC_FLOW_MAX - TRAFFIC_FLOW_OPTIMAL)
        else:
            score = max(0, 0.3 * (1.0 - (min_door_dist - TRAFFIC_FLOW_MAX) / TRAFFIC_FLOW_MAX))

        total_score += score

    return total_score / len(desks)


def _calc_face_to_face_bonus(result: Dict) -> float:
    """
    対面配置ボーナスを計算 (0.0 - 1.0)

    対面配置はコミュニケーションを促進し、チームワークを向上させる
    """
    pattern = result.get("pattern", "")
    items = result.get("items", [])

    # パターン名から対面配置を判定
    if "face" in pattern.lower() or "対面" in pattern or "mixed" in pattern.lower():
        return 1.0

    # アイテムから対面配置を検出
    desks, _ = _get_desks_and_chairs(items)
    if len(desks) < 2:
        return 0.0

    # 対面ペアをカウント
    face_pairs = 0
    used = set()

    for i, desk1 in enumerate(desks):
        if i in used:
            continue
        rect1 = desk1.get("rect")
        if not rect1:
            continue

        for j, desk2 in enumerate(desks[i + 1:], i + 1):
            if j in used:
                continue
            rect2 = desk2.get("rect")
            if not rect2:
                continue

            # 対面の判定: X座標が近く、Y座標が一定距離離れている
            x_diff = abs(rect1.x - rect2.x)
            y_diff = abs(rect1.y - rect2.y)

            # 縦方向の対面
            if x_diff < 200 and 800 < y_diff < 3000:
                face_pairs += 1
                used.add(i)
                used.add(j)
                break

            # 横方向の対面
            if y_diff < 200 and 800 < x_diff < 3000:
                face_pairs += 1
                used.add(i)
                used.add(j)
                break

    max_pairs = len(desks) // 2
    if max_pairs == 0:
        return 0.0

    return min(face_pairs / max_pairs, 1.0)


def _calc_desk_spacing_score(result: Dict, room_w: int, room_d: int) -> float:
    """
    デスク間隔スコアを計算 (0.0 - 1.0)

    設計基準:
    - デスク列間: 900mm以上
    - 推奨: 1200mm
    """
    items = result.get("items", [])
    desks, _ = _get_desks_and_chairs(items)

    if len(desks) < 2:
        return 1.0  # 1台以下なら問題なし

    # デスク間の最小距離を計算
    min_distances = []

    for i, desk1 in enumerate(desks):
        rect1 = desk1.get("rect")
        if not rect1:
            continue

        for desk2 in desks[i + 1:]:
            rect2 = desk2.get("rect")
            if not rect2:
                continue

            # 2つのデスク間の距離を計算
            # X方向の距離
            if rect1.x + rect1.w <= rect2.x:
                dx = rect2.x - (rect1.x + rect1.w)
            elif rect2.x + rect2.w <= rect1.x:
                dx = rect1.x - (rect2.x + rect2.w)
            else:
                dx = 0  # X方向で重なっている

            # Y方向の距離
            if rect1.y + rect1.d <= rect2.y:
                dy = rect2.y - (rect1.y + rect1.d)
            elif rect2.y + rect2.d <= rect1.y:
                dy = rect1.y - (rect2.y + rect2.d)
            else:
                dy = 0  # Y方向で重なっている

            # 隣接している場合のみ距離を記録
            if dx == 0 or dy == 0:
                distance = max(dx, dy)
                if distance > 0:
                    min_distances.append(distance)

    if not min_distances:
        return 1.0

    avg_distance = sum(min_distances) / len(min_distances)
    min_distance = min(min_distances)

    # 最小距離に基づくスコア
    if min_distance >= DESK_ROW_SPACING_OPTIMAL:
        return 1.0
    elif min_distance >= DESK_ROW_SPACING_MIN:
        return 0.6 + 0.4 * (min_distance - DESK_ROW_SPACING_MIN) / (DESK_ROW_SPACING_OPTIMAL - DESK_ROW_SPACING_MIN)
    elif min_distance >= ONE_PERSON_MIN:
        return 0.3 + 0.3 * (min_distance - ONE_PERSON_MIN) / (DESK_ROW_SPACING_MIN - ONE_PERSON_MIN)
    else:
        return max(0, min_distance / ONE_PERSON_MIN * 0.3)


def _calc_area_per_person_score(result: Dict, room_w: int, room_d: int) -> float:
    """
    一人当たり面積スコアを計算 (0.0 - 1.0)

    設計基準:
    - 最低: 4㎡ (事務所衛生基準規則)
    - 推奨: 8-13㎡
    - 最大: 15㎡ (広すぎは非効率)
    """
    seats = result.get("seats_placed", 0)
    if seats == 0:
        return 0.0

    total_area = room_w * room_d
    area_per_person = total_area / seats

    # スコア計算
    if AREA_PER_PERSON_OPTIMAL <= area_per_person <= AREA_PER_PERSON_MAX:
        return 1.0
    elif area_per_person < AREA_PER_PERSON_MIN:
        # 最低基準以下: 低スコア
        return max(0, area_per_person / AREA_PER_PERSON_MIN * 0.3)
    elif area_per_person < AREA_PER_PERSON_OPTIMAL:
        # 最低〜推奨の間
        return 0.3 + 0.7 * (area_per_person - AREA_PER_PERSON_MIN) / (AREA_PER_PERSON_OPTIMAL - AREA_PER_PERSON_MIN)
    else:
        # 最大以上: 徐々に減点
        excess = area_per_person - AREA_PER_PERSON_MAX
        return max(0.5, 1.0 - excess / AREA_PER_PERSON_MAX * 0.5)


def _calc_space_efficiency_score(result: Dict, room_w: int, room_d: int) -> float:
    """
    スペース効率スコアを計算 (0.0 - 1.0)

    家具の配置効率と通路のバランスを評価
    """
    items = result.get("items", [])
    if not items:
        return 0.0

    # 使用面積を計算 (家具のみ)
    furniture_area = 0
    for item in items:
        item_type = item.get("type", "")
        if item_type in ("desk", "chair", "storage_M", "storage_S", "storage_D", "mfp"):
            rect = item.get("rect")
            if rect:
                furniture_area += rect.w * rect.d

    total_area = room_w * room_d
    if total_area == 0:
        return 0.0

    usage_ratio = furniture_area / total_area

    # 理想的な使用率: 25-45%
    # (残りは通路・余白)
    if 0.25 <= usage_ratio <= 0.45:
        return 1.0
    elif usage_ratio < 0.15:
        # 使用率が低すぎる (無駄が多い)
        return usage_ratio / 0.15 * 0.5
    elif usage_ratio < 0.25:
        return 0.5 + (usage_ratio - 0.15) / 0.10 * 0.5
    elif usage_ratio <= 0.55:
        return 1.0 - (usage_ratio - 0.45) / 0.10 * 0.3
    else:
        # 使用率が高すぎる (窮屈)
        return max(0.3, 0.7 - (usage_ratio - 0.55) / 0.20 * 0.4)


def calculate_layout_score(
    result: Dict,
    room_w: int,
    room_d: int,
    weights: Optional[Dict[str, float]] = None,
    preset: Optional[str] = None,
    door_positions: Optional[List[Dict]] = None,
    window_sides: Optional[List[str]] = None,
    max_seats: int = None,  # 互換性のため残す (未使用)
) -> Tuple[float, ScoreBreakdown]:
    """
    レイアウトの総合スコアを計算する

    Args:
        result: レイアウト結果
        room_w, room_d: 部屋サイズ (mm)
        weights: 各評価項目の重み (Noneの場合はconfig.yamlから読み込み)
        preset: プリセット名 ("max_seats", "comfort", "collaboration", "balanced", "ergonomic")
        door_positions: ドア位置のリスト [{"x": int, "y": int}, ...]
        window_sides: 窓がある壁のリスト ["T", "R", "B", "L"]

    Returns:
        (総合スコア, スコア内訳)
    """
    if not result.get("ok"):
        return 0.0, ScoreBreakdown()

    # 重みを取得
    if weights is None:
        weights = load_scoring_weights(preset)

    # 各スコアを計算
    seat_score = _calc_seat_score(result, room_w, room_d)
    passage_score = _calc_passage_score(result, room_w, room_d)
    light_score = _calc_natural_light_score(result, room_w, room_d, window_sides)
    flow_score = _calc_traffic_flow_score(result, room_w, room_d, door_positions)
    face_bonus = _calc_face_to_face_bonus(result)
    efficiency_score = _calc_space_efficiency_score(result, room_w, room_d)
    desk_spacing_score = _calc_desk_spacing_score(result, room_w, room_d)
    area_per_person_score = _calc_area_per_person_score(result, room_w, room_d)

    # 重み付きスコア
    breakdown = ScoreBreakdown(
        seat_count=seat_score * weights.get("seat_count", 1.0),
        passage_width=passage_score * weights.get("passage_width", 0.8),
        natural_light=light_score * weights.get("natural_light", 0.5),
        traffic_flow=flow_score * weights.get("traffic_flow", 0.6),
        face_to_face_bonus=face_bonus * weights.get("face_to_face_bonus", 0.3),
        space_efficiency=efficiency_score * weights.get("space_efficiency", 0.4),
        desk_spacing=desk_spacing_score * weights.get("desk_spacing", 0.7),
        area_per_person=area_per_person_score * weights.get("area_per_person", 0.6),
    )

    breakdown.total = (
        breakdown.seat_count
        + breakdown.passage_width
        + breakdown.natural_light
        + breakdown.traffic_flow
        + breakdown.face_to_face_bonus
        + breakdown.space_efficiency
        + breakdown.desk_spacing
        + breakdown.area_per_person
    )

    return breakdown.total, breakdown


def compare_layouts(
    results: List[Dict],
    room_w: int,
    room_d: int,
    preset: Optional[str] = None,
    door_positions: Optional[List[Dict]] = None,
    window_sides: Optional[List[str]] = None,
) -> List[Tuple[int, float, ScoreBreakdown]]:
    """
    複数のレイアウト候補を比較してランキングを返す

    Returns:
        [(元のインデックス, スコア, 内訳), ...] スコア降順
    """
    scored = []
    for i, result in enumerate(results):
        score, breakdown = calculate_layout_score(
            result, room_w, room_d,
            preset=preset,
            door_positions=door_positions,
            window_sides=window_sides,
        )
        scored.append((i, score, breakdown))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def get_best_layout(
    results: List[Dict],
    room_w: int,
    room_d: int,
    preset: Optional[str] = None,
    door_positions: Optional[List[Dict]] = None,
    window_sides: Optional[List[str]] = None,
) -> Tuple[Optional[Dict], float, ScoreBreakdown]:
    """
    最高スコアのレイアウトを取得する

    Returns:
        (最良のレイアウト結果, スコア, 内訳)
    """
    if not results:
        return None, 0.0, ScoreBreakdown()

    ranking = compare_layouts(
        results, room_w, room_d,
        preset=preset,
        door_positions=door_positions,
        window_sides=window_sides,
    )
    best_idx, best_score, best_breakdown = ranking[0]
    return results[best_idx], best_score, best_breakdown


def analyze_layout(
    result: Dict,
    room_w: int,
    room_d: int,
    door_positions: Optional[List[Dict]] = None,
    window_sides: Optional[List[str]] = None,
) -> Dict:
    """
    レイアウトを分析して詳細レポートを生成

    Returns:
        分析レポート (スコア、改善提案など)
    """
    score, breakdown = calculate_layout_score(
        result, room_w, room_d,
        door_positions=door_positions,
        window_sides=window_sides,
    )

    seats = result.get("seats_placed", 0)
    total_area = room_w * room_d
    area_per_person = total_area / seats if seats > 0 else 0

    # 改善提案を生成
    suggestions = []

    if breakdown.passage_width < 0.5 * DEFAULT_WEIGHTS["passage_width"]:
        suggestions.append("通路幅が狭いです。メイン通路は1200mm以上を確保してください。")

    if breakdown.natural_light < 0.3 * DEFAULT_WEIGHTS["natural_light"]:
        suggestions.append("採光が不十分です。窓際に席を配置することを検討してください。")

    if breakdown.desk_spacing < 0.5 * DEFAULT_WEIGHTS["desk_spacing"]:
        suggestions.append("デスク間隔が狭いです。900mm以上の間隔を確保してください。")

    if area_per_person < AREA_PER_PERSON_MIN:
        suggestions.append(f"一人当たり面積が{area_per_person/1_000_000:.1f}㎡と狭すぎます。最低4㎡を確保してください。")

    if breakdown.face_to_face_bonus < 0.3 * DEFAULT_WEIGHTS["face_to_face_bonus"]:
        suggestions.append("対面配置を取り入れるとコミュニケーションが活性化します。")

    return {
        "total_score": round(score, 3),
        "breakdown": breakdown.to_dict(),
        "seats_placed": seats,
        "area_per_person_m2": round(area_per_person / 1_000_000, 2),
        "room_area_m2": round(total_area / 1_000_000, 2),
        "suggestions": suggestions,
        "grade": _score_to_grade(score),
    }


def _score_to_grade(score: float) -> str:
    """スコアをグレード (A-F) に変換"""
    max_possible = sum(DEFAULT_WEIGHTS.values())
    ratio = score / max_possible if max_possible > 0 else 0

    if ratio >= 0.9:
        return "A"
    elif ratio >= 0.8:
        return "B"
    elif ratio >= 0.7:
        return "C"
    elif ratio >= 0.6:
        return "D"
    elif ratio >= 0.5:
        return "E"
    else:
        return "F"
