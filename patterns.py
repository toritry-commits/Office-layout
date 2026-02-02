from typing import Dict, List, Tuple
from geometry import Rect, can_place


def _ws_size(furniture: Dict, ws_type: str) -> Tuple[int, int]:
    """
    ws furniture:
      w = 壁沿いの長さ（机長辺）
      d = 壁から必要奥行（机＋椅子＋引きしろ込みの想定）
    """
    f = furniture[ws_type]
    return int(f["w"]), int(f["d"])


def _parse_desk_depth(ws_type: str) -> int:
    # ws_1000x600 -> 600
    try:
        s = ws_type.replace("ws_", "")
        _, b = s.split("x")
        return int(b)
    except Exception:
        return 600


def _add_desk_and_chair_items_circle(
    items: list,
    label_prefix: str,
    room_w: int,
    ws_type: str,
    wall_side: str,     # "L" or "R"
    y: int,
    unit_w_along_wall: int,     # 壁沿い方向（=机長辺）
    unit_depth_from_wall: int,  # 壁から室内方向（=必要奥行）
):
    """
    見た目用：
      - desk: 壁にピタ付け（長辺が壁沿い）
      - chair: 直径550mmの円
        「机の室内側長辺の中心」に、円の端が机の端に“接触”するように配置
    当たり判定は席ユニットで確保済みなので、desk/chairは描画専用。
    """
    desk_depth = min(_parse_desk_depth(ws_type), unit_depth_from_wall)

    # desk（壁付け・長辺=壁沿い）
    if wall_side == "L":
        desk_x = 0
    else:
        desk_x = room_w - desk_depth

    desk_rect = Rect(x=desk_x, y=y, w=desk_depth, d=unit_w_along_wall)
    items.append({"type": "desk", "rect": desk_rect, "label": f"{label_prefix}_D"})

    # chair（650角）— desk_rectから50mm離す
    chair_size = 700
    gap = 5

    # 机の「室内側端」を desk_rect から厳密に取る
    if wall_side == "L":
        inner_edge_x = desk_rect.x + desk_rect.w
        chair_x = inner_edge_x + gap
        back_side = "R"
    else:
        inner_edge_x = desk_rect.x
        chair_x = inner_edge_x - gap - chair_size
        back_side = "L"

    # 机の長辺中心（壁沿い方向の中心）
    cy = desk_rect.y + (desk_rect.d / 2.0)
    chair_y = cy - chair_size / 2.0

    chair_box = Rect(
        x=int(chair_x),
        y=int(chair_y),
        w=int(chair_size),
        d=int(chair_size),
    )
    items.append(
        {
            "type": "chair",
            "rect": chair_box,
            "label": f"{label_prefix}_C",
            "chair_back": back_side,
        }
    )


def _add_desk_and_chair_items_circle_tb(
    items: list,
    label_prefix: str,
    room_d: int,
    ws_type: str,
    wall_side: str,     # "T" or "B"
    x: int,
    unit_w_along_wall: int,     # 壁沿い方向（=机長辺）
    unit_depth_from_wall: int,  # 壁から室内方向（=必要奥行）
):
    """
    見た目用（上/下壁）：
      - desk: 壁にピタ付け（長辺が壁沿い）
      - chair: 直径550mmの円
    """
    desk_depth = min(_parse_desk_depth(ws_type), unit_depth_from_wall)

    if wall_side == "T":
        desk_y = 0
    else:
        desk_y = room_d - desk_depth

    desk_rect = Rect(x=x, y=desk_y, w=unit_w_along_wall, d=desk_depth)
    items.append({"type": "desk", "rect": desk_rect, "label": f"{label_prefix}_D"})

    chair_size = 700
    gap = 5

    if wall_side == "T":
        inner_edge_y = desk_rect.y + desk_rect.d
        chair_y = inner_edge_y + gap
        back_side = "B"
    else:
        inner_edge_y = desk_rect.y
        chair_y = inner_edge_y - gap - chair_size
        back_side = "T"

    cx = desk_rect.x + (desk_rect.w / 2.0)
    chair_x = cx - chair_size / 2.0

    chair_box = Rect(
        x=int(chair_x),
        y=int(chair_y),
        w=int(chair_size),
        d=int(chair_size),
    )
    items.append(
        {
            "type": "chair",
            "rect": chair_box,
            "label": f"{label_prefix}_C",
            "chair_back": back_side,
        }
    )


def _add_desk_and_chair_items_circle_free(
    items: list,
    label_prefix: str,
    ws_type: str,
    x: int,
    y: int,
    desk_w: int,
    unit_depth_from_wall: int,
    chair_side: str,  # "up" or "down"
    desk_depth_override: int = None,
):
    """
    自由配置用：
      - desk: 指定座標
      - chair: desk の長辺中央、chair_side 方向に接触
    """
    if desk_depth_override is not None:
        desk_depth = min(int(desk_depth_override), unit_depth_from_wall)
    else:
        desk_depth = min(_parse_desk_depth(ws_type), unit_depth_from_wall)
    desk_rect = Rect(x=x, y=y, w=desk_w, d=desk_depth)
    items.append({"type": "desk", "rect": desk_rect, "label": f"{label_prefix}_D"})

    chair_size = 700
    gap = 5

    if chair_side == "down":
        inner_edge_y = desk_rect.y + desk_rect.d
        chair_y = inner_edge_y + gap
        back_side = "B"
    else:
        inner_edge_y = desk_rect.y
        chair_y = inner_edge_y - gap - chair_size
        back_side = "T"

    cx = desk_rect.x + (desk_rect.w / 2.0)
    chair_x = cx - chair_size / 2.0

    chair_box = Rect(
        x=int(chair_x),
        y=int(chair_y),
        w=int(chair_size),
        d=int(chair_size),
    )
    items.append(
        {
            "type": "chair",
            "rect": chair_box,
            "label": f"{label_prefix}_C",
            "chair_back": back_side,
        }
    )


def _add_desk_and_chair_items_circle_lr(
    items: list,
    label_prefix: str,
    ws_type: str,
    x: int,
    y: int,
    desk_w: int,
    desk_d: int,
    chair_side: str,  # "L" or "R"
    chair_rotate_deg: int = 0,
):
    """
    自由配置（左右向き）：
      - desk: 指定座標
      - chair: desk の短辺中央、chair_side 方向に接触
    """
    desk_rect = Rect(x=x, y=y, w=desk_w, d=desk_d)
    items.append({"type": "desk", "rect": desk_rect, "label": f"{label_prefix}_D"})

    chair_size = 700
    gap = 5

    if chair_side == "L":
        inner_edge_x = desk_rect.x
        chair_x = inner_edge_x - gap - chair_size
        back_side = "L"
    else:
        inner_edge_x = desk_rect.x + desk_rect.w
        chair_x = inner_edge_x + gap
        back_side = "R"

    cy = desk_rect.y + (desk_rect.d / 2.0)
    chair_y = cy - chair_size / 2.0

    chair_box = Rect(
        x=int(chair_x),
        y=int(chair_y),
        w=int(chair_size),
        d=int(chair_size),
    )
    items.append(
        {
            "type": "chair",
            "rect": chair_box,
            "label": f"{label_prefix}_C",
            "chair_back": back_side,
            "chair_rotate": chair_rotate_deg,
        }
    )


# =========================
# 両壁2列（席数最大）
# =========================
def place_workstations_double_wall(
    room_w: int,
    room_d: int,
    furniture: Dict,
    ws_type: str,
    seats_required: int,
    blocks: List[Rect],
    gap_y: int = 0,
    door_tip: Tuple[float, float] = None,
    door_clear_radius: int = 900,
):
    ws_w, ws_d = _ws_size(furniture, ws_type)

    # 当たり判定用：席ユニット（奥行=ws_d、壁沿い=ws_w）
    unit_w_x = ws_d
    unit_d_y = ws_w

    items = []
    placed = list(blocks)

    y = 0
    y_limit = room_d - unit_d_y
    seat_idx = 1

    while y <= y_limit and seat_idx <= seats_required:
        # 左壁
        left_unit = Rect(x=0, y=y, w=unit_w_x, d=unit_d_y)
        if can_place(left_unit, room_w, room_d, placed) and _clear_of_point(left_unit, door_tip, door_clear_radius) and seat_idx <= seats_required:
            placed.append(left_unit)
            _add_desk_and_chair_items_circle(
                items=items,
                label_prefix=f"WS{seat_idx}",
                room_w=room_w,
                ws_type=ws_type,
                wall_side="L",
                y=y,
                unit_w_along_wall=unit_d_y,
                unit_depth_from_wall=unit_w_x,
            )
            seat_idx += 1

        # 右壁
        right_unit = Rect(x=room_w - unit_w_x, y=y, w=unit_w_x, d=unit_d_y)
        if can_place(right_unit, room_w, room_d, placed) and _clear_of_point(right_unit, door_tip, door_clear_radius) and seat_idx <= seats_required:
            placed.append(right_unit)
            _add_desk_and_chair_items_circle(
                items=items,
                label_prefix=f"WS{seat_idx}",
                room_w=room_w,
                ws_type=ws_type,
                wall_side="R",
                y=y,
                unit_w_along_wall=unit_d_y,
                unit_depth_from_wall=unit_w_x,
            )
            seat_idx += 1

        y += unit_d_y + gap_y

    seats_placed = seat_idx - 1
    ok = seats_placed >= seats_required and _door_clearance_ok_for_items(items, door_tip)
    return {
        "ok": ok,
        "seats_placed": seats_placed,
        "seats_required": seats_required,
        "items": items,
        "ws_type": ws_type,
        "pattern": "double_wall",
    }


# =========================
# 上下壁2列（席数最大）
# =========================
def place_workstations_double_wall_top_bottom(
    room_w: int,
    room_d: int,
    furniture: Dict,
    ws_type: str,
    seats_required: int,
    blocks: List[Rect],
    gap_x: int = 0,
    start_from: str = "L",
    door_tip: Tuple[float, float] = None,
    door_clear_radius: int = 900,
):
    ws_w, ws_d = _ws_size(furniture, ws_type)

    unit_w_x = ws_w
    unit_d_y = ws_d

    items = []
    placed = list(blocks)

    x_limit = room_w - unit_w_x
    step = unit_w_x + gap_x
    if (start_from or "L").upper() == "R":
        x = x_limit
        step = -step
    else:
        x = 0
    seat_idx = 1

    def _in_range(xx: int) -> bool:
        return 0 <= xx <= x_limit

    while _in_range(x) and seat_idx <= seats_required:
        # 上壁
        top_unit = Rect(x=x, y=0, w=unit_w_x, d=unit_d_y)
        if can_place(top_unit, room_w, room_d, placed) and _clear_of_point(top_unit, door_tip, door_clear_radius) and seat_idx <= seats_required:
            placed.append(top_unit)
            _add_desk_and_chair_items_circle_tb(
                items=items,
                label_prefix=f"WS{seat_idx}",
                room_d=room_d,
                ws_type=ws_type,
                wall_side="T",
                x=x,
                unit_w_along_wall=unit_w_x,
                unit_depth_from_wall=unit_d_y,
            )
            seat_idx += 1

        # 下壁
        bottom_unit = Rect(x=x, y=room_d - unit_d_y, w=unit_w_x, d=unit_d_y)
        if can_place(bottom_unit, room_w, room_d, placed) and _clear_of_point(bottom_unit, door_tip, door_clear_radius) and seat_idx <= seats_required:
            placed.append(bottom_unit)
            _add_desk_and_chair_items_circle_tb(
                items=items,
                label_prefix=f"WS{seat_idx}",
                room_d=room_d,
                ws_type=ws_type,
                wall_side="B",
                x=x,
                unit_w_along_wall=unit_w_x,
                unit_depth_from_wall=unit_d_y,
            )
            seat_idx += 1

        x += step

    seats_placed = seat_idx - 1
    ok = seats_placed >= seats_required and _door_clearance_ok_for_items(items, door_tip)
    return {
        "ok": ok,
        "seats_placed": seats_placed,
        "seats_required": seats_required,
        "items": items,
        "ws_type": ws_type,
        "pattern": "double_wall_top_bottom",
    }


# =========================
# 対面2席セット（中央揃え・横並び）
# =========================
def place_workstations_face_to_face_center(
    room_w: int,
    room_d: int,
    furniture: Dict,
    ws_type: str,
    seats_required: int,
    blocks: List[Rect],
    gap_x: int = 0,
    door_side: str = None,
    door_rect: Rect = None,
    door_tip: Tuple[float, float] = None,
):
    """
    椅子側を外側にして、机の“椅子なし側（壁側）”同士を向かい合わせる。
    2席1セットを横並びにし、短辺方向の中央に揃えて配置する。
    """
    ws_w, ws_d = _ws_size(furniture, ws_type)

    if room_d < ws_d * 2:
        return {
            "ok": False,
            "seats_placed": 0,
            "seats_required": seats_required,
            "items": [],
            "ws_type": ws_type,
            "pattern": "face_to_face_center",
        }

    pairs = seats_required // 2
    has_single = (seats_required % 2) == 1
    seats_target = seats_required

    unit_w_x = ws_w
    unit_d_y = ws_d * 2

    total_units = pairs
    total_w = total_units * unit_w_x + max(0, total_units - 1) * gap_x
    if total_w > room_w:
        return {
            "ok": False,
            "seats_placed": 0,
            "seats_required": seats_required,
            "items": [],
            "ws_type": ws_type,
            "pattern": "face_to_face_center",
        }

    door_side = (door_side or "").upper()
    x_start = int((room_w - total_w) / 2)
    center_line = int(room_d / 2)
    y0 = int(center_line - (unit_d_y / 2))
    if door_side == "L":
        x_start = room_w - total_w
    elif door_side == "R":
        x_start = 0
    elif door_side == "T":
        y0 = room_d - unit_d_y
    elif door_side == "B":
        y0 = 0

    items = []
    placed = list(blocks)
    seat_idx = 1

    def _place_unit(x: int, y: int):
        r = Rect(x=x, y=y, w=unit_w_x, d=unit_d_y)
        if can_place(r, room_w, room_d, placed) and _clear_of_point(r, door_tip, 900):
            placed.append(r)
            return r
        return None

    desk_depth = min(_parse_desk_depth(ws_type), ws_d)
    if has_single:
        desk_depth = 600
        unit_d_y = desk_depth * 2
        y0 = int(center_line - (unit_d_y / 2))

    if door_rect is not None and door_side in ("L", "R"):
        if not (y0 + unit_d_y <= door_rect.y or y0 >= door_rect.y2):
            y0_down = door_rect.y2
            y0_up = door_rect.y - unit_d_y
            if 0 <= y0_down and (y0_down + unit_d_y) <= room_d:
                y0 = y0_down
            elif 0 <= y0_up and (y0_up + unit_d_y) <= room_d:
                y0 = y0_up
    x = x_start
    unit_rects = []
    for i in range(total_units):
        unit_rect = _place_unit(x, y0)
        if unit_rect is None:
            x += unit_w_x + gap_x
            continue
        unit_rects.append(unit_rect)

        if seat_idx <= seats_target:
            top_desk_y = center_line - desk_depth
            bottom_desk_y = center_line
            _add_desk_and_chair_items_circle_free(
                items=items,
                label_prefix=f"WS{seat_idx}",
                ws_type=ws_type,
                x=x,
                y=top_desk_y,
                desk_w=ws_w,
                unit_depth_from_wall=desk_depth,
                chair_side="up",
                desk_depth_override=desk_depth,
            )
            seat_idx += 1
        if seat_idx <= seats_target:
            _add_desk_and_chair_items_circle_free(
                items=items,
                label_prefix=f"WS{seat_idx}",
                ws_type=ws_type,
                x=x,
                y=bottom_desk_y,
                desk_w=ws_w,
                unit_depth_from_wall=desk_depth,
                chair_side="down",
                desk_depth_override=desk_depth,
            )
            seat_idx += 1

        x += unit_w_x + gap_x

    if has_single and seat_idx <= seats_target and unit_rects:
        rotated_w = 600
        rotated_d = 1200
        door_side_u = (door_side or "").upper()
        leftmost = unit_rects[0]
        rightmost = unit_rects[-1]
        if door_side_u == "L":
            candidates = [("R", rightmost), ("L", leftmost)]
        elif door_side_u == "R":
            candidates = [("L", leftmost), ("R", rightmost)]
        else:
            candidates = [("R", rightmost), ("L", leftmost)]

        placed_flag = False
        for attach_side, unit_rect in candidates:
            if attach_side == "R":
                desk_x = unit_rect.x + unit_rect.w
                if room_w - (desk_x + rotated_w) < 1000:
                    continue
            else:
                desk_x = unit_rect.x - rotated_w
                if desk_x < 1000:
                    continue

            desk_y = (room_d / 2.0) - (rotated_d / 2.0)
            rotated_rect = Rect(x=int(desk_x), y=int(desk_y), w=int(rotated_w), d=int(rotated_d))
            if not can_place(rotated_rect, room_w, room_d, placed) or not _clear_of_point(rotated_rect, door_tip, 900):
                continue

            _add_desk_and_chair_items_circle_lr(
                items=items,
                label_prefix=f"WS{seat_idx}",
                ws_type=ws_type,
                x=int(desk_x),
                y=int(desk_y),
                desk_w=int(rotated_w),
                desk_d=int(rotated_d),
                chair_side=attach_side,
                chair_rotate_deg=90,
            )
            seat_idx += 1
            placed_flag = True
            break

        if not placed_flag:
            return {
                "ok": False,
                "seats_placed": seat_idx - 1,
                "seats_required": seats_required,
                "items": items,
                "ws_type": ws_type,
                "pattern": "face_to_face_center",
            }

    seats_placed = seat_idx - 1

    # 机の長辺側（上/下）から壁までの寸法（左端ユニット中心に揃える）
    desk_items = [it for it in items if it.get("type") == "desk"]
    if desk_items:
        leftmost = min(desk_items, key=lambda it: it["rect"].x)
        dim_x = int(leftmost["rect"].x + (leftmost["rect"].w / 2.0))
        dim_x = max(60, min(room_w - 60, dim_x))

        wall_half = 5
        top_desk = center_line - desk_depth
        bottom_desk = center_line + desk_depth
        inner_top = wall_half
        inner_bottom = room_d - wall_half
        top_gap = max(0, int(top_desk - inner_top))
        bottom_gap = max(0, int(inner_bottom - bottom_desk))
        items.append(
            {
                "type": "dim_v",
                "rect": Rect(x=dim_x, y=inner_top, w=0, d=top_gap),
                "x0": dim_x,
                "y0": inner_top,
                "y1": inner_top + top_gap,
                "text": f"{int(top_gap)}",
            }
        )
        items.append(
            {
                "type": "dim_v",
                "rect": Rect(x=dim_x, y=inner_bottom - bottom_gap, w=0, d=bottom_gap),
                "x0": dim_x,
                "y0": inner_bottom - bottom_gap,
                "y1": inner_bottom,
                "text": f"{int(bottom_gap)}",
            }
        )

    ok = seats_placed >= seats_required and _door_clearance_ok_for_items(items, door_tip)
    return {
        "ok": ok,
        "seats_placed": seats_placed,
        "seats_required": seats_required,
        "items": items,
        "ws_type": ws_type,
        "pattern": "face_to_face_center",
    }


# =========================
# 片壁1列
# =========================
def place_workstations_single_wall(
    room_w: int,
    room_d: int,
    furniture: Dict,
    ws_type: str,
    seats_required: int,
    blocks: List[Rect],
    side: str = "L",
    gap_y: int = 0,
    door_tip: Tuple[float, float] = None,
    door_clear_radius: int = 900,
):
    ws_w, ws_d = _ws_size(furniture, ws_type)

    unit_w_x = ws_d
    unit_d_y = ws_w

    items = []
    placed = list(blocks)

    x = 0 if side == "L" else room_w - unit_w_x
    y = 0
    y_limit = room_d - unit_d_y
    seat_idx = 1

    while y <= y_limit and seat_idx <= seats_required:
        unit = Rect(x=x, y=y, w=unit_w_x, d=unit_d_y)
        if can_place(unit, room_w, room_d, placed) and _clear_of_point(unit, door_tip, door_clear_radius):
            placed.append(unit)
            _add_desk_and_chair_items_circle(
                items=items,
                label_prefix=f"WS{seat_idx}",
                room_w=room_w,
                ws_type=ws_type,
                wall_side=("L" if side == "L" else "R"),
                y=y,
                unit_w_along_wall=unit_d_y,
                unit_depth_from_wall=unit_w_x,
            )
            seat_idx += 1
        y += unit_d_y + gap_y

    seats_placed = seat_idx - 1
    ok = seats_placed >= seats_required and _door_clearance_ok_for_items(items, door_tip)
    return {
        "ok": ok,
        "seats_placed": seats_placed,
        "seats_required": seats_required,
        "items": items,
        "ws_type": ws_type,
        "pattern": f"single_wall_{side}",
    }


# =========================
# 片壁1列（上/下）
# =========================
def place_workstations_single_wall_tb(
    room_w: int,
    room_d: int,
    furniture: Dict,
    ws_type: str,
    seats_required: int,
    blocks: List[Rect],
    side: str = "T",
    gap_x: int = 0,
    start_from: str = "L",
    door_tip: Tuple[float, float] = None,
    door_clear_radius: int = 900,
):
    ws_w, ws_d = _ws_size(furniture, ws_type)

    unit_w_x = ws_w
    unit_d_y = ws_d

    items = []
    placed = list(blocks)

    y = 0 if side == "T" else room_d - unit_d_y
    x_limit = room_w - unit_w_x
    step = unit_w_x + gap_x
    if (start_from or "L").upper() == "R":
        x = x_limit
        step = -step
    else:
        x = 0
    seat_idx = 1

    def _in_range(xx: int) -> bool:
        return 0 <= xx <= x_limit

    while _in_range(x) and seat_idx <= seats_required:
        unit = Rect(x=x, y=y, w=unit_w_x, d=unit_d_y)
        if can_place(unit, room_w, room_d, placed) and _clear_of_point(unit, door_tip, door_clear_radius):
            placed.append(unit)
            _add_desk_and_chair_items_circle_tb(
                items=items,
                label_prefix=f"WS{seat_idx}",
                room_d=room_d,
                ws_type=ws_type,
                wall_side=("T" if side == "T" else "B"),
                x=x,
                unit_w_along_wall=unit_w_x,
                unit_depth_from_wall=unit_d_y,
            )
            seat_idx += 1
        x += step

    seats_placed = seat_idx - 1
    ok = seats_placed >= seats_required and _door_clearance_ok_for_items(items, door_tip)
    return {
        "ok": ok,
        "seats_placed": seats_placed,
        "seats_required": seats_required,
        "items": items,
        "ws_type": ws_type,
        "pattern": f"single_wall_{side}",
    }


# =========================
# 設備配置（壁付けのみ・長辺を壁に沿わせる）
# =========================
def place_equipment_wall_only(
    room_w: int,
    room_d: int,
    furniture: Dict,
    equipment: List[str],
    blocks: List[Rect],
    wall: str,          # "L" or "R" or "T" or "B"
    start_y: int = 0,
    gap_y: int = 50,
    avoid_centers: List[Tuple[float, float]] = None,
    avoid_radius_mm: int = None,
    desk_rects_same_wall: List[Rect] = None,
    desk_clearance_mm: int = 200,
    equipment_clearance_mm: int = 100,
    start_from: str = "start",
):
    """
    収納などの設備は「壁付けのみ」。
    壁面がデスクで埋まって置けない場合は無理に入れない（置けたものだけ）。
    壁付け時は “長辺が壁沿い” になるよう回転して配置する。
    """
    if wall not in ("L", "R", "T", "B"):
        raise ValueError("wall must be 'L' or 'R' or 'T' or 'B'")

    items = []
    placed = list(blocks)
    y = start_y
    idx = 1

    for eq in equipment:
        spec = furniture[eq]
        w0 = int(spec["w"])
        d0 = int(spec["d"])

        # 長辺を壁沿い（y方向）にする：along=max、depth=min
        along = max(w0, d0)   # 壁沿い（長辺）
        depth = min(w0, d0)   # 壁からの出（短辺）

        if wall in ("L", "R"):
            x = 0 if wall == "L" else (room_w - depth)
            max_pos = room_d - along
            pos = y
        else:
            y = 0 if wall == "T" else (room_d - depth)
            max_pos = room_w - along
            pos = start_y

        if (start_from or "start").lower() == "end":
            pos = max_pos
            step = -50
        else:
            step = 50

        placed_flag = False
        strict_chain = eq.startswith("storage_") and equipment_clearance_mm == 0
        while 0 <= pos <= max_pos:
            if wall in ("L", "R"):
                r = Rect(x=x, y=pos, w=depth, d=along)
            else:
                r = Rect(x=pos, y=y, w=along, d=depth)
            if avoid_centers and avoid_radius_mm:
                cx, cy = _item_center(r)
                too_close = False
                for ax, ay in avoid_centers:
                    dx = cx - ax
                    dy = cy - ay
                    if (dx * dx + dy * dy) ** 0.5 <= avoid_radius_mm:
                        too_close = True
                        break
                if too_close:
                    pos += step
                    continue

            if desk_rects_same_wall is not None:
                if not _clearance_ok_same_wall(r, desk_rects_same_wall, wall, desk_clearance_mm):
                    pos += step
                    continue

            if can_place(r, room_w, room_d, placed):
                items.append({"type": eq, "rect": r, "label": f"EQ{idx}"})
                placed.append(r)
                if equipment_clearance_mm > 0:
                    if wall in ("L", "R"):
                        buf = Rect(
                            x=r.x,
                            y=r.y - equipment_clearance_mm,
                            w=r.w,
                            d=r.d + equipment_clearance_mm * 2,
                        )
                    else:
                        buf = Rect(
                            x=r.x - equipment_clearance_mm,
                            y=r.y,
                            w=r.w + equipment_clearance_mm * 2,
                            d=r.d,
                        )
                    placed.append(buf)
                idx += 1
                if wall in ("L", "R"):
                    y = pos + along + gap_y
                else:
                    start_y = pos + along + gap_y
                placed_flag = True
                break
            if strict_chain:
                break
            pos += step

        # 壁付けで入らないなら無理に入れない
        if not placed_flag:
            if strict_chain:
                break
            continue

    return {"items": items, "placed_rects": placed}


def _remove_equipment_types(remaining: List[str], placed_items: List[dict]) -> List[str]:
    """
    remaining から placed_items の type を出現数分だけ差し引く。
    """
    rest = list(remaining)
    for it in placed_items:
        t = it.get("type")
        if not t:
            continue
        try:
            rest.remove(t)
        except ValueError:
            continue
    return rest


def _item_center(rect: Rect) -> Tuple[float, float]:
    return (rect.x + rect.w / 2.0, rect.y + rect.d / 2.0)


def _rect_wall_sides(r: Rect, room_w: int, room_d: int) -> List[str]:
    sides = []
    if r.x == 0:
        sides.append("L")
    if r.x + r.w == room_w:
        sides.append("R")
    if r.y == 0:
        sides.append("T")
    if r.y + r.d == room_d:
        sides.append("B")
    return sides


def _clearance_ok_same_wall(r: Rect, desk_rects: List[Rect], wall: str, clearance_mm: int) -> bool:
    if clearance_mm <= 0:
        return True
    if not desk_rects:
        return True

    if wall in ("L", "R"):
        for d in desk_rects:
            if r.y >= d.y2:
                gap = r.y - d.y2
            elif d.y >= r.y2:
                gap = d.y - r.y2
            else:
                gap = 0
            if gap < clearance_mm:
                return False
    else:
        for d in desk_rects:
            if r.x >= d.x2:
                gap = r.x - d.x2
            elif d.x >= r.x2:
                gap = d.x - r.x2
            else:
                gap = 0
            if gap < clearance_mm:
                return False
    return True


def _clear_of_point(r: Rect, pt: Tuple[float, float], radius_mm: int) -> bool:
    if pt is None:
        return True
    px, py = pt
    dx = 0
    if px < r.x:
        dx = r.x - px
    elif px > r.x2:
        dx = px - r.x2
    dy = 0
    if py < r.y:
        dy = r.y - py
    elif py > r.y2:
        dy = py - r.y2
    return (dx * dx + dy * dy) ** 0.5 >= radius_mm


def _rect_point_distance(r: Rect, pt: Tuple[float, float]) -> float:
    px, py = pt
    dx = 0
    if px < r.x:
        dx = r.x - px
    elif px > r.x2:
        dx = px - r.x2
    dy = 0
    if py < r.y:
        dy = r.y - py
    elif py > r.y2:
        dy = py - r.y2
    return (dx * dx + dy * dy) ** 0.5


def _door_clearance_ok_for_items(items: List[dict], door_tip: Tuple[float, float]) -> bool:
    if door_tip is None:
        return True
    desk_rects = [it["rect"] for it in items if it.get("type") == "desk"]
    if not desk_rects:
        return True

    def _side_length_facing(r: Rect) -> int:
        px, py = door_tip
        dx = 0
        if px < r.x:
            dx = r.x - px
        elif px > r.x2:
            dx = px - r.x2
        dy = 0
        if py < r.y:
            dy = r.y - py
        elif py > r.y2:
            dy = py - r.y2

        if dx == 0 and dy == 0:
            return min(r.w, r.d)
        # If both dx and dy, choose the dominant gap side.
        if dx >= dy:
            return r.d
        return r.w

    # Find nearest desk to door tip
    nearest = min(desk_rects, key=lambda r: _rect_point_distance(r, door_tip))
    nearest_dist = _rect_point_distance(nearest, door_tip)
    side_len = _side_length_facing(nearest)
    short_side = min(nearest.w, nearest.d)
    required = 200 if side_len == short_side else 900
    return nearest_dist >= required


def place_equipment_along_wall(
    base_result: Dict,
    room_w: int,
    room_d: int,
    furniture: Dict,
    equipment_list: List[str],
    blocks: List[Rect],
    equipment_x_override: int = None,
    desk_clear_radius_mm: int = 1225,
    desk_side_clearance_mm: int = 200,
    equipment_clearance_mm: int = 100,
    door_side: str = None,
    door_offset: int = None,
):
    """
    base_result の配置に対して、設備を壁付けで追加する。
    左壁→右壁の順で詰め、置けなかった設備はスキップする。
    equipment_x_override が指定されている場合、x位置から壁側を選ぶ。
    """
    if not equipment_list:
        return base_result

    base_items = list(base_result.get("items", []))
    placed_rects = list(blocks) + [it["rect"] for it in base_items]
    desk_rects = [it["rect"] for it in base_items if it.get("type") == "desk"]
    chair_rects = [it["rect"] for it in base_items if it.get("type") == "chair"]

    desk_walls = set()
    desk_rects_by_wall = {"L": [], "R": [], "T": [], "B": []}
    for r in desk_rects:
        for s in _rect_wall_sides(r, room_w, room_d):
            desk_walls.add(s)
            desk_rects_by_wall[s].append(r)

    avoid_centers = [_item_center(r) for r in desk_rects]

    long_walls = ["T", "B"] if room_w >= room_d else ["L", "R"]
    preferred_walls = [w for w in long_walls if w in desk_walls] or list(desk_walls)
    walls = preferred_walls

    if equipment_x_override is not None:
        walls = ["L"] if equipment_x_override <= room_w / 2 else ["R"]

    door_side_u = (door_side or "").upper()
    if door_side_u and door_side_u not in walls:
        walls = walls + [door_side_u]

    remaining = list(equipment_list)
    equipment_items = []

    for wall in walls:
        if not remaining:
            break
        side_by_side = wall in desk_walls
        desk_rects_same_wall = desk_rects_by_wall.get(wall, []) if side_by_side else None

        start_from = "start"
        if wall == door_side_u:
            if door_side_u in ("L", "R"):
                if door_offset is not None:
                    start_from = "end" if door_offset < (room_d / 2) else "start"
                else:
                    start_from = "end"
            elif door_side_u in ("T", "B"):
                if door_offset is not None:
                    start_from = "end" if door_offset < (room_w / 2) else "start"
                else:
                    start_from = "end"

        res = place_equipment_wall_only(
            room_w=room_w,
            room_d=room_d,
            furniture=furniture,
            equipment=remaining,
            blocks=placed_rects,
            wall=wall,
            gap_y=equipment_clearance_mm,
            avoid_centers=None if side_by_side else avoid_centers,
            avoid_radius_mm=None if side_by_side else desk_clear_radius_mm,
            desk_rects_same_wall=desk_rects_same_wall,
            desk_clearance_mm=desk_side_clearance_mm,
            equipment_clearance_mm=equipment_clearance_mm,
            start_from=start_from,
        )
        eq_items = res["items"]
        equipment_items.extend(eq_items)
        placed_rects = res["placed_rects"]
        remaining = _remove_equipment_types(remaining, eq_items)

    out = dict(base_result)
    out["items"] = base_items + equipment_items
    out["equipment_target"] = len(equipment_list)
    out["equipment_placed"] = len(equipment_items)
    return out
