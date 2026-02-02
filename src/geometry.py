# 四角形（家具や禁止エリア）を扱うための基本ツール

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Rect:
    """
    画面左上を (0,0) として扱う座標系
    x: 左からの位置(mm)
    y: 上からの位置(mm)
    w: 横幅(mm)
    d: 奥行(mm)
    """
    x: int
    y: int
    w: int
    d: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.d


def intersects(a: Rect, b: Rect) -> bool:
    """
    a と b が重なっていれば True
    端が接しているだけなら False
    """
    return not (
        a.x2 <= b.x or
        a.x >= b.x2 or
        a.y2 <= b.y or
        a.y >= b.y2
    )


def inside_room(r: Rect, room_w: int, room_d: int) -> bool:
    """
    部屋の中に完全に収まっていれば True
    """
    return (
        r.x >= 0 and
        r.y >= 0 and
        r.x2 <= room_w and
        r.y2 <= room_d
    )


def intersects_any(r: Rect, blocks: List[Rect]) -> bool:
    """
    blocks のどれかと重なれば True
    """
    for b in blocks:
        if intersects(r, b):
            return True
    return False


def can_place(r: Rect, room_w: int, room_d: int, blocks: List[Rect]) -> bool:
    """
    r を置いて良いなら True
    """
    if not inside_room(r, room_w, room_d):
        return False
    if intersects_any(r, blocks):
        return False
    return True


def check_desk_chair_collision(
    desk_rect: Rect,
    chair_rect: Rect,
    blocks: List[Rect],
    room_w: int,
    room_d: int,
) -> bool:
    """
    机と椅子が柱(blocks)と衝突していないかチェック
    衝突していなければ True (配置可能)
    """
    # 机が部屋内にあるか
    if not inside_room(desk_rect, room_w, room_d):
        return False
    # 椅子が部屋内にあるか
    if not inside_room(chair_rect, room_w, room_d):
        return False
    # 机が柱と衝突していないか
    if intersects_any(desk_rect, blocks):
        return False
    # 椅子が柱と衝突していないか
    if intersects_any(chair_rect, blocks):
        return False
    return True


def get_pillar_blocks(blocks: List[Rect]) -> List[Rect]:
    """
    blocksリストから柱(pillar)のみを抽出
    柱は配置済みアイテムと区別するため、最初に追加されたものとして扱う
    """
    return blocks


def calc_passage_widths(items: List[dict], room_w: int, room_d: int) -> dict:
    """
    配置されたアイテム間の通路幅を計算する
    通路とは「人が移動できるスペース」のこと。
    - デスク間、デスクと壁の間の距離を計算
    - 同じワークステーション内のデスク-椅子間隔は除外
    - 壁に密着 (0mm) の場合は通路としてカウントしない

    Returns:
        dict: {
            "min_horizontal": 最小横通路幅(mm) - デスク間の横方向距離,
            "min_vertical": 最小縦通路幅(mm) - デスク間の縦方向距離,
            "left_wall_gap": 左壁からの最小距離(mm),
            "right_wall_gap": 右壁からの最小距離(mm),
            "top_wall_gap": 上壁からの最小距離(mm),
            "bottom_wall_gap": 下壁からの最小距離(mm),
            "min_passage": 有効な最小通路幅(mm) - 100mm未満は除外,
            "main_aisle": メイン通路幅(mm) - 最大の通路幅,
        }
    """
    # デスクのみを抽出 (通路計算の主要対象)
    desk_rects = []
    for it in items:
        if "rect" in it and it.get("type") == "desk":
            desk_rects.append(it["rect"])

    # 設備 (収納、複合機) も含める
    furniture_rects = list(desk_rects)
    for it in items:
        if "rect" in it and it.get("type") in ("storage_M", "mfp", "block"):
            furniture_rects.append(it["rect"])

    if not furniture_rects:
        return {
            "min_horizontal": room_w,
            "min_vertical": room_d,
            "left_wall_gap": room_w,
            "right_wall_gap": room_w,
            "top_wall_gap": room_d,
            "bottom_wall_gap": room_d,
            "min_passage": min(room_w, room_d),
            "main_aisle": min(room_w, room_d),
        }

    # 壁からの距離
    left_gaps = [r.x for r in furniture_rects]
    right_gaps = [room_w - r.x2 for r in furniture_rects]
    top_gaps = [r.y for r in furniture_rects]
    bottom_gaps = [room_d - r.y2 for r in furniture_rects]

    left_wall_gap = min(left_gaps) if left_gaps else room_w
    right_wall_gap = min(right_gaps) if right_gaps else room_w
    top_wall_gap = min(top_gaps) if top_gaps else room_d
    bottom_wall_gap = min(bottom_gaps) if bottom_gaps else room_d

    # アイテム間の通路幅を計算
    horizontal_gaps = []
    vertical_gaps = []

    n = len(furniture_rects)
    for i in range(n):
        for j in range(i + 1, n):
            ri = furniture_rects[i]
            rj = furniture_rects[j]

            # 横方向 (X軸) の距離 - Y方向で重なっている場合のみ有効な通路
            y_overlap = not (ri.y2 <= rj.y or rj.y2 <= ri.y)
            if y_overlap:
                if ri.x2 <= rj.x:
                    horizontal_gaps.append(rj.x - ri.x2)
                elif rj.x2 <= ri.x:
                    horizontal_gaps.append(ri.x - rj.x2)

            # 縦方向 (Y軸) の距離 - X方向で重なっている場合のみ有効な通路
            x_overlap = not (ri.x2 <= rj.x or rj.x2 <= ri.x)
            if x_overlap:
                if ri.y2 <= rj.y:
                    vertical_gaps.append(rj.y - ri.y2)
                elif rj.y2 <= ri.y:
                    vertical_gaps.append(ri.y - rj.y2)

    min_horizontal = min(horizontal_gaps) if horizontal_gaps else room_w
    min_vertical = min(vertical_gaps) if vertical_gaps else room_d

    # 有効な通路幅のリスト (100mm以上のものだけ - 小さな隙間は通路ではない)
    min_threshold = 100  # 100mm未満は「通路」ではなく「隙間」
    valid_passages = []
    for gap in [left_wall_gap, right_wall_gap, top_wall_gap, bottom_wall_gap]:
        if gap >= min_threshold:
            valid_passages.append(gap)
    for gap in horizontal_gaps + vertical_gaps:
        if gap >= min_threshold:
            valid_passages.append(gap)

    # 最小通路幅 (100mm未満は除外)
    min_passage = min(valid_passages) if valid_passages else 0

    # メイン通路幅 (最大の通路)
    main_aisle = max(valid_passages) if valid_passages else 0

    return {
        "min_horizontal": min_horizontal,
        "min_vertical": min_vertical,
        "left_wall_gap": left_wall_gap,
        "right_wall_gap": right_wall_gap,
        "top_wall_gap": top_wall_gap,
        "bottom_wall_gap": bottom_wall_gap,
        "min_passage": min_passage,
        "main_aisle": main_aisle,
    }


def count_window_adjacent_seats(items: List[dict], windows: List[dict], room_w: int, room_d: int) -> int:
    """
    窓に隣接するデスク数をカウントする (自然光の恩恵を受ける席)

    Args:
        items: レイアウトアイテム
        windows: 窓リスト [{side, offset, width}, ...]
        room_w: 部屋幅
        room_d: 部屋奥行

    Returns:
        窓に隣接するデスク数
    """
    if not windows:
        return 0

    desk_rects = [it["rect"] for it in items if it.get("type") == "desk"]
    if not desk_rects:
        return 0

    window_adjacent = 0
    adjacency_threshold = 1500  # 窓から1500mm以内を「窓際」とみなす

    for desk in desk_rects:
        desk_cx = desk.x + desk.w / 2
        desk_cy = desk.y + desk.d / 2

        for win in windows:
            side = (win.get("side") or "T").upper()
            offset = win.get("offset", 0)
            width = win.get("width", 1000)

            is_adjacent = False

            if side == "T":
                # 上壁の窓: デスクが上壁近くで、窓の範囲内
                if desk.y <= adjacency_threshold and offset <= desk_cx <= offset + width:
                    is_adjacent = True
            elif side == "B":
                # 下壁の窓
                if room_d - desk.y2 <= adjacency_threshold and offset <= desk_cx <= offset + width:
                    is_adjacent = True
            elif side == "L":
                # 左壁の窓
                if desk.x <= adjacency_threshold and offset <= desk_cy <= offset + width:
                    is_adjacent = True
            elif side == "R":
                # 右壁の窓
                if room_w - desk.x2 <= adjacency_threshold and offset <= desk_cy <= offset + width:
                    is_adjacent = True

            if is_adjacent:
                window_adjacent += 1
                break  # 1つのデスクは1回だけカウント

    return window_adjacent
