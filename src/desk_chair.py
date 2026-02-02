# 机と椅子の配置ロジック
# patterns.py にあった重複関数を統合

from geometry import Rect, check_desk_chair_collision
from constants import CHAIR_SIZE, CHAIR_DESK_GAP, DEFAULT_DESK_DEPTH
from typing import List, Tuple, Optional


def _parse_desk_depth(ws_type: str) -> int:
    """机タイプから奥行を取得"""
    try:
        s = ws_type.replace("ws_", "")
        _, b = s.split("x")
        return int(b)
    except Exception:
        return DEFAULT_DESK_DEPTH


def calc_chair_rect(
    desk_x: int,
    desk_y: int,
    desk_w: int,
    desk_d: int,
    chair_direction: str,
) -> Rect:
    """
    机の位置から椅子のRectを計算する

    Args:
        desk_x, desk_y: 机の座標
        desk_w, desk_d: 机のサイズ
        chair_direction: 椅子の方向("T", "B", "L", "R")

    Returns:
        椅子のRect
    """
    chair_size = CHAIR_SIZE
    gap = CHAIR_DESK_GAP

    if chair_direction == "T":
        chair_x = int(desk_x + (desk_w / 2.0) - (chair_size / 2.0))
        chair_y = int(desk_y - gap - chair_size)
    elif chair_direction == "B":
        chair_x = int(desk_x + (desk_w / 2.0) - (chair_size / 2.0))
        chair_y = int(desk_y + desk_d + gap)
    elif chair_direction == "L":
        chair_x = int(desk_x - gap - chair_size)
        chair_y = int(desk_y + (desk_d / 2.0) - (chair_size / 2.0))
    else:  # "R"
        chair_x = int(desk_x + desk_w + gap)
        chair_y = int(desk_y + (desk_d / 2.0) - (chair_size / 2.0))

    return Rect(x=chair_x, y=chair_y, w=chair_size, d=chair_size)


def calc_wall_desk_chair_rects(
    room_size: int,
    ws_type: str,
    wall_side: str,
    position: int,
    unit_along_wall: int,
    unit_depth: int,
    is_horizontal: bool = False,
) -> Tuple[Rect, Rect, str]:
    """
    壁付け机と椅子のRectを計算する (配置前の衝突判定用)

    Returns:
        (desk_rect, chair_rect, chair_direction)
    """
    desk_depth = min(_parse_desk_depth(ws_type), unit_depth)

    if is_horizontal:
        # 上下壁(T/B)の場合
        if wall_side == "T":
            desk_x = position
            desk_y = 0
            chair_dir = "B"
        else:  # "B"
            desk_x = position
            desk_y = room_size - desk_depth
            chair_dir = "T"
        desk_w = unit_along_wall
        desk_d = desk_depth
    else:
        # 左右壁(L/R)の場合
        if wall_side == "L":
            desk_x = 0
            desk_y = position
            chair_dir = "R"
        else:  # "R"
            desk_x = room_size - desk_depth
            desk_y = position
            chair_dir = "L"
        desk_w = desk_depth
        desk_d = unit_along_wall

    desk_rect = Rect(x=desk_x, y=desk_y, w=desk_w, d=desk_d)
    chair_rect = calc_chair_rect(desk_x, desk_y, desk_w, desk_d, chair_dir)

    return desk_rect, chair_rect, chair_dir


def can_place_desk_chair(
    room_size: int,
    room_w: int,
    room_d: int,
    ws_type: str,
    wall_side: str,
    position: int,
    unit_along_wall: int,
    unit_depth: int,
    is_horizontal: bool,
    pillar_blocks: List[Rect],
) -> bool:
    """
    壁付け机と椅子が柱と衝突せずに配置できるかチェック

    Returns:
        配置可能なら True
    """
    desk_rect, chair_rect, _ = calc_wall_desk_chair_rects(
        room_size=room_size,
        ws_type=ws_type,
        wall_side=wall_side,
        position=position,
        unit_along_wall=unit_along_wall,
        unit_depth=unit_depth,
        is_horizontal=is_horizontal,
    )

    return check_desk_chair_collision(
        desk_rect=desk_rect,
        chair_rect=chair_rect,
        blocks=pillar_blocks,
        room_w=room_w,
        room_d=room_d,
    )


def add_desk_and_chair(
    items: list,
    label_prefix: str,
    ws_type: str,
    desk_x: int,
    desk_y: int,
    desk_w: int,
    desk_d: int,
    chair_direction: str,
    chair_rotate_deg: int = 0,
):
    """
    机と椅子を配置する統合関数

    Args:
        items: アイテムリスト(追加先)
        label_prefix: ラベル接頭辞(例: "WS1")
        ws_type: 机タイプ
        desk_x, desk_y: 机の座標
        desk_w, desk_d: 机のサイズ(幅、奥行)
        chair_direction: 椅子の方向("T", "B", "L", "R")
            T=上(机の上側に椅子)、B=下、L=左、R=右
        chair_rotate_deg: 椅子の回転角度(0 or 90)
    """
    # 机を追加
    desk_rect = Rect(x=desk_x, y=desk_y, w=desk_w, d=desk_d)
    items.append({"type": "desk", "rect": desk_rect, "label": f"{label_prefix}_D"})

    # 椅子を追加
    chair_size = CHAIR_SIZE
    gap = CHAIR_DESK_GAP

    # 椅子の位置を計算
    if chair_direction == "T":
        # 机の上側に椅子
        chair_x = int(desk_x + (desk_w / 2.0) - (chair_size / 2.0))
        chair_y = int(desk_y - gap - chair_size)
        back_side = "T"
    elif chair_direction == "B":
        # 机の下側に椅子
        chair_x = int(desk_x + (desk_w / 2.0) - (chair_size / 2.0))
        chair_y = int(desk_y + desk_d + gap)
        back_side = "B"
    elif chair_direction == "L":
        # 机の左側に椅子
        chair_x = int(desk_x - gap - chair_size)
        chair_y = int(desk_y + (desk_d / 2.0) - (chair_size / 2.0))
        back_side = "L"
    else:  # "R"
        # 机の右側に椅子
        chair_x = int(desk_x + desk_w + gap)
        chair_y = int(desk_y + (desk_d / 2.0) - (chair_size / 2.0))
        back_side = "R"

    chair_rect = Rect(x=chair_x, y=chair_y, w=chair_size, d=chair_size)
    items.append({
        "type": "chair",
        "rect": chair_rect,
        "label": f"{label_prefix}_C",
        "chair_back": back_side,
        "chair_rotate": chair_rotate_deg,
    })


def add_wall_desk_and_chair(
    items: list,
    label_prefix: str,
    room_size: int,
    ws_type: str,
    wall_side: str,
    position: int,
    unit_along_wall: int,
    unit_depth: int,
    is_horizontal: bool = False,
):
    """
    壁付け机と椅子を配置する

    Args:
        items: アイテムリスト
        label_prefix: ラベル接頭辞
        room_size: 部屋サイズ(壁からの計算用、room_w or room_d)
        ws_type: 机タイプ
        wall_side: 壁の位置("L", "R", "T", "B")
        position: 壁沿い方向の位置
        unit_along_wall: 壁沿い方向のサイズ
        unit_depth: 壁からの奥行
        is_horizontal: 水平配置かどうか(T/Bの場合True)
    """
    desk_depth = min(_parse_desk_depth(ws_type), unit_depth)

    if is_horizontal:
        # 上下壁(T/B)の場合
        if wall_side == "T":
            desk_x = position
            desk_y = 0
            chair_dir = "B"
        else:  # "B"
            desk_x = position
            desk_y = room_size - desk_depth
            chair_dir = "T"
        desk_w = unit_along_wall
        desk_d = desk_depth
    else:
        # 左右壁(L/R)の場合
        if wall_side == "L":
            desk_x = 0
            desk_y = position
            chair_dir = "R"
        else:  # "R"
            desk_x = room_size - desk_depth
            desk_y = position
            chair_dir = "L"
        desk_w = desk_depth
        desk_d = unit_along_wall

    add_desk_and_chair(
        items=items,
        label_prefix=label_prefix,
        ws_type=ws_type,
        desk_x=desk_x,
        desk_y=desk_y,
        desk_w=desk_w,
        desk_d=desk_d,
        chair_direction=chair_dir,
    )


def add_free_desk_and_chair(
    items: list,
    label_prefix: str,
    ws_type: str,
    x: int,
    y: int,
    desk_w: int,
    unit_depth: int,
    chair_side: str,
    desk_depth_override: int = None,
):
    """
    自由配置用の机と椅子を配置する

    Args:
        items: アイテムリスト
        label_prefix: ラベル接頭辞
        ws_type: 机タイプ
        x, y: 机の座標
        desk_w: 机の幅
        unit_depth: 最大奥行
        chair_side: 椅子の方向("up" or "down")
        desk_depth_override: 机奥行の上書き値(Noneの場合はws_typeから取得)
    """
    if desk_depth_override is not None:
        desk_depth = min(int(desk_depth_override), unit_depth)
    else:
        desk_depth = min(_parse_desk_depth(ws_type), unit_depth)

    # chair_sideを方向に変換
    if chair_side == "down":
        chair_dir = "B"
    else:  # "up"
        chair_dir = "T"

    add_desk_and_chair(
        items=items,
        label_prefix=label_prefix,
        ws_type=ws_type,
        desk_x=x,
        desk_y=y,
        desk_w=desk_w,
        desk_d=desk_depth,
        chair_direction=chair_dir,
    )


def add_lr_desk_and_chair(
    items: list,
    label_prefix: str,
    ws_type: str,
    x: int,
    y: int,
    desk_w: int,
    desk_d: int,
    chair_side: str,
    chair_rotate_deg: int = 0,
):
    """
    左右向き自由配置用の机と椅子を配置する

    Args:
        items: アイテムリスト
        label_prefix: ラベル接頭辞
        ws_type: 机タイプ
        x, y: 机の座標
        desk_w, desk_d: 机のサイズ
        chair_side: 椅子の方向("L" or "R")
        chair_rotate_deg: 椅子の回転角度
    """
    add_desk_and_chair(
        items=items,
        label_prefix=label_prefix,
        ws_type=ws_type,
        desk_x=x,
        desk_y=y,
        desk_w=desk_w,
        desk_d=desk_d,
        chair_direction=chair_side,
        chair_rotate_deg=chair_rotate_deg,
    )
