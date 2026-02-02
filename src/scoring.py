# レイアウトスコアリングモジュール
# 複数のレイアウト候補を評価・比較するための機能を提供

import os
import yaml
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ScoreBreakdown:
    """スコアの内訳を保持するクラス"""
    seat_count: float = 0.0
    passage_width: float = 0.0
    natural_light: float = 0.0
    traffic_flow: float = 0.0
    face_to_face_bonus: float = 0.0
    space_efficiency: float = 0.0
    total: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "seat_count": self.seat_count,
            "passage_width": self.passage_width,
            "natural_light": self.natural_light,
            "traffic_flow": self.traffic_flow,
            "face_to_face_bonus": self.face_to_face_bonus,
            "space_efficiency": self.space_efficiency,
            "total": self.total,
        }


# デフォルトの重み (config.yamlが読めない場合のフォールバック)
DEFAULT_WEIGHTS = {
    "seat_count": 1.0,
    "passage_width": 0.5,
    "natural_light": 0.3,
    "traffic_flow": 0.4,
    "face_to_face_bonus": 0.2,
    "space_efficiency": 0.3,
}


def _find_config_path() -> Optional[str]:
    """config.yamlのパスを探す"""
    # srcディレクトリからの相対パス
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
        preset: プリセット名("max_seats", "comfort", "collaboration", "balanced")
                Noneの場合はデフォルトの重みを使用

    Returns:
        重みの辞書
    """
    config_path = _find_config_path()
    if not config_path:
        return DEFAULT_WEIGHTS.copy()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        scoring_config = config.get("scoring", {})

        if preset and preset in scoring_config.get("presets", {}):
            return scoring_config["presets"][preset].copy()

        return scoring_config.get("weights", DEFAULT_WEIGHTS).copy()
    except Exception:
        return DEFAULT_WEIGHTS.copy()


def _calc_seat_score(result: Dict, max_possible: int = 20) -> float:
    """
    席数スコアを計算 (0.0 - 1.0)

    Args:
        result: レイアウト結果
        max_possible: 想定最大席数(正規化用)
    """
    seats = result.get("seats_placed", 0)
    return min(seats / max_possible, 1.0) if max_possible > 0 else 0.0


def _calc_passage_score(result: Dict, room_w: int, room_d: int) -> float:
    """
    通路幅スコアを計算 (0.0 - 1.0)
    広い通路が確保されているほど高スコア

    Args:
        result: レイアウト結果
        room_w, room_d: 部屋サイズ
    """
    items = result.get("items", [])
    if not items:
        return 1.0  # アイテムがない場合は最高スコア

    # 簡易的な通路幅の推定
    # 部屋の中央付近の空きスペースを評価
    center_x = room_w / 2
    center_y = room_d / 2

    min_distance = float("inf")
    for item in items:
        rect = item.get("rect")
        if not rect:
            continue

        # アイテムの中心からの距離
        item_center_x = rect.x + rect.w / 2
        item_center_y = rect.y + rect.d / 2

        dx = abs(center_x - item_center_x)
        dy = abs(center_y - item_center_y)
        distance = min(dx, dy)  # 最も近い方向での距離
        min_distance = min(min_distance, distance)

    # 通路幅を正規化 (1000mm以上で満点)
    if min_distance == float("inf"):
        return 1.0
    return min(min_distance / 1000.0, 1.0)


def _calc_natural_light_score(result: Dict, room_w: int, room_d: int) -> float:
    """
    採光スコアを計算 (0.0 - 1.0)
    窓(壁際)に近い席が多いほど高スコア

    前提: 部屋の上辺(y=0)と右辺(x=room_w)に窓があると仮定
    """
    items = result.get("items", [])
    desks = [item for item in items if item.get("type") == "desk"]

    if not desks:
        return 0.5  # 机がない場合は中間値

    total_light_score = 0.0
    for desk in desks:
        rect = desk.get("rect")
        if not rect:
            continue

        # 窓からの距離を計算 (上辺と右辺)
        dist_top = rect.y
        dist_right = room_w - (rect.x + rect.w)

        # 近い方の窓との距離
        min_dist = min(dist_top, dist_right)

        # 距離を正規化 (2000mm以内で高スコア)
        light_score = max(0, 1.0 - min_dist / 2000.0)
        total_light_score += light_score

    return total_light_score / len(desks)


def _calc_traffic_flow_score(result: Dict, door_positions: List[Dict] = None) -> float:
    """
    動線効率スコアを計算 (0.0 - 1.0)
    ドアからのアクセスが良いほど高スコア

    Args:
        result: レイアウト結果
        door_positions: ドア位置のリスト [{"x": int, "y": int}, ...]
    """
    if not door_positions:
        # ドア位置が指定されていない場合はデフォルト値
        return 0.5

    items = result.get("items", [])
    desks = [item for item in items if item.get("type") == "desk"]

    if not desks:
        return 0.5

    total_flow_score = 0.0
    for desk in desks:
        rect = desk.get("rect")
        if not rect:
            continue

        desk_center_x = rect.x + rect.w / 2
        desk_center_y = rect.y + rect.d / 2

        # 最も近いドアからの距離
        min_door_dist = float("inf")
        for door in door_positions:
            dx = desk_center_x - door.get("x", 0)
            dy = desk_center_y - door.get("y", 0)
            dist = (dx ** 2 + dy ** 2) ** 0.5
            min_door_dist = min(min_door_dist, dist)

        # 距離を正規化 (5000mm以内で良好)
        flow_score = max(0, 1.0 - min_door_dist / 5000.0)
        total_flow_score += flow_score

    return total_flow_score / len(desks)


def _calc_face_to_face_bonus(result: Dict) -> float:
    """
    対面配置ボーナスを計算 (0.0 - 1.0)
    対面配置パターンが使われているほど高スコア
    """
    pattern = result.get("pattern", "")
    items = result.get("items", [])

    # パターン名から対面配置を判定
    if "face" in pattern.lower() or "対面" in pattern:
        return 1.0

    # アイテムから対面配置を検出
    desks = [item for item in items if item.get("type") == "desk"]
    if len(desks) < 2:
        return 0.0

    # 簡易的な対面検出: 向かい合っている机のペアをカウント
    face_pairs = 0
    for i, desk1 in enumerate(desks):
        for desk2 in desks[i + 1:]:
            rect1 = desk1.get("rect")
            rect2 = desk2.get("rect")
            if not rect1 or not rect2:
                continue

            # X座標が近く、Y座標が離れている = 縦方向の対面
            x_diff = abs(rect1.x - rect2.x)
            y_diff = abs(rect1.y - rect2.y)

            if x_diff < 100 and 1000 < y_diff < 3000:
                face_pairs += 1

    return min(face_pairs / max(len(desks) / 2, 1), 1.0)


def _calc_space_efficiency_score(result: Dict, room_w: int, room_d: int) -> float:
    """
    スペース効率スコアを計算 (0.0 - 1.0)
    デッドスペースが少ないほど高スコア
    """
    items = result.get("items", [])
    if not items:
        return 0.0

    # 使用面積を計算
    used_area = 0
    for item in items:
        rect = item.get("rect")
        if rect:
            used_area += rect.w * rect.d

    total_area = room_w * room_d
    if total_area == 0:
        return 0.0

    # 使用率を計算 (20-60%が適正範囲と仮定)
    usage_ratio = used_area / total_area

    # 使用率が低すぎても高すぎても減点
    if usage_ratio < 0.2:
        return usage_ratio / 0.2 * 0.5
    elif usage_ratio > 0.6:
        return max(0, 1.0 - (usage_ratio - 0.6) / 0.4)
    else:
        # 20-60%の範囲で正規化
        return 0.5 + (usage_ratio - 0.2) / 0.8

    return min(usage_ratio * 2.0, 1.0)


def calculate_layout_score(
    result: Dict,
    room_w: int,
    room_d: int,
    weights: Optional[Dict[str, float]] = None,
    preset: Optional[str] = None,
    door_positions: Optional[List[Dict]] = None,
    max_seats: int = 20,
) -> Tuple[float, ScoreBreakdown]:
    """
    レイアウトの総合スコアを計算する

    Args:
        result: レイアウト結果
        room_w, room_d: 部屋サイズ(mm)
        weights: 各評価項目の重み(Noneの場合はconfig.yamlから読み込み)
        preset: プリセット名("max_seats", "comfort", "collaboration", "balanced")
        door_positions: ドア位置のリスト
        max_seats: 想定最大席数(スコア正規化用)

    Returns:
        (総合スコア, スコア内訳)
    """
    if not result.get("ok"):
        return 0.0, ScoreBreakdown()

    # 重みを取得
    if weights is None:
        weights = load_scoring_weights(preset)

    # 各スコアを計算
    seat_score = _calc_seat_score(result, max_seats)
    passage_score = _calc_passage_score(result, room_w, room_d)
    light_score = _calc_natural_light_score(result, room_w, room_d)
    flow_score = _calc_traffic_flow_score(result, door_positions)
    face_bonus = _calc_face_to_face_bonus(result)
    efficiency_score = _calc_space_efficiency_score(result, room_w, room_d)

    # 重み付き合計
    breakdown = ScoreBreakdown(
        seat_count=seat_score * weights.get("seat_count", 1.0),
        passage_width=passage_score * weights.get("passage_width", 0.5),
        natural_light=light_score * weights.get("natural_light", 0.3),
        traffic_flow=flow_score * weights.get("traffic_flow", 0.4),
        face_to_face_bonus=face_bonus * weights.get("face_to_face_bonus", 0.2),
        space_efficiency=efficiency_score * weights.get("space_efficiency", 0.3),
    )

    breakdown.total = (
        breakdown.seat_count
        + breakdown.passage_width
        + breakdown.natural_light
        + breakdown.traffic_flow
        + breakdown.face_to_face_bonus
        + breakdown.space_efficiency
    )

    return breakdown.total, breakdown


def compare_layouts(
    results: List[Dict],
    room_w: int,
    room_d: int,
    preset: Optional[str] = None,
) -> List[Tuple[int, float, ScoreBreakdown]]:
    """
    複数のレイアウト候補を比較してランキングを返す

    Args:
        results: レイアウト結果のリスト
        room_w, room_d: 部屋サイズ
        preset: スコアリングプリセット

    Returns:
        [(元のインデックス, スコア, 内訳), ...] スコア降順
    """
    scored = []
    for i, result in enumerate(results):
        score, breakdown = calculate_layout_score(
            result, room_w, room_d, preset=preset
        )
        scored.append((i, score, breakdown))

    # スコア降順でソート
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def get_best_layout(
    results: List[Dict],
    room_w: int,
    room_d: int,
    preset: Optional[str] = None,
) -> Tuple[Optional[Dict], float, ScoreBreakdown]:
    """
    最高スコアのレイアウトを取得する

    Returns:
        (最良のレイアウト結果, スコア, 内訳)
    """
    if not results:
        return None, 0.0, ScoreBreakdown()

    ranking = compare_layouts(results, room_w, room_d, preset)
    best_idx, best_score, best_breakdown = ranking[0]
    return results[best_idx], best_score, best_breakdown
