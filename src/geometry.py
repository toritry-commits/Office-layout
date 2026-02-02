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
