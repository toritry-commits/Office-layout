import argparse
import logging

from catalog import FURNITURE
from geometry import Rect
from constants import DOOR_WIDTH, DOOR_BUFFER_DEPTH
from utils import parse_equipment, calc_desk_area, score_layout, get_ws_candidates
from patterns import (
    place_workstations_double_wall,
    place_workstations_double_wall_top_bottom,
    place_workstations_single_wall_tb,
    place_workstations_face_to_face_center,
    place_workstations_single_wall,
    place_equipment_along_wall,
)
from export_pdf import export_multi_layout_pdf
from export_data import export_layout_json, export_layout_csv

# ロギング設定(デバッグ時は logging.DEBUG に変更)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def build_blocks(room_w, room_d, door_w=850, door_d=900, door_side="T", door_offset=None, door_swing="in"):
    """
    ブロック（禁止エリア）
    - 入口バッファ：指定辺に沿って door_w x door_d
    """
    blocks = []
    door_rect = None

    door_side = (door_side or "T").upper()
    if door_side in ("T", "B"):
        max_offset = max(0, room_w - door_w)
        if door_offset is None:
            door_x = max_offset // 2
        else:
            door_x = max(0, min(int(door_offset), max_offset))
        door_y = 0 if door_side == "T" else (room_d - door_d)
    else:
        max_offset = max(0, room_d - door_w)
        if door_offset is None:
            door_y = max_offset // 2
        else:
            door_y = max(0, min(int(door_offset), max_offset))
        door_x = 0 if door_side == "L" else (room_w - door_d)

    if door_side in ("T", "B"):
        door_rect = Rect(x=door_x, y=door_y, w=door_w, d=door_d)
    else:
        door_rect = Rect(x=door_x, y=door_y, w=door_d, d=door_w)

    blocks.append(door_rect)

    # ドア先端（室内方向）座標
    if door_side in ("T", "B"):
        radius = door_rect.w
        cx = door_rect.x
        cy = 0 if door_side == "T" else room_d
        tip = (cx, cy + radius) if door_side == "T" else (cx, cy - radius)
    else:
        radius = door_rect.d
        cx = 0 if door_side == "L" else room_w
        cy = door_rect.y
        tip = (cx + radius, cy) if door_side == "L" else (cx - radius, cy)

    return blocks, door_rect, door_side, tip


# parse_equipment は utils.py に移動済み


def solve_one_plan(
    room_w,
    room_d,
    seats_required,
    ws_candidates,
    blocks,
    equipment,
    equipment_x_override=None,
    door_side=None,
    door_offset=None,
    priority="equipment",
    door_tip=None,
):
    """
    机パターン（両壁/片壁）を試して、席数最大の案を返す。
    その後、可能なら設備を壁付けで追加する。
    """
    best = None

    def _score(res):
        return score_layout(res, priority)

    for ws_type in ws_candidates:
        candidates = []
        door_side_u = (door_side or "").upper()
        if door_side_u in ("L", "R"):
            # 入口が左右壁の場合は上下壁（長辺）に両壁配置
            start_from = "R" if door_side_u == "L" else "L"
            tmp = place_workstations_double_wall_top_bottom(
                room_w=room_w,
                room_d=room_d,
                furniture=FURNITURE,
                ws_type=ws_type,
                seats_required=seats_required,
                blocks=blocks,
                gap_x=0,
                start_from=start_from,
                door_tip=door_tip,
            )
            logger.debug("try double TB: %s seats=%d ok=%s", ws_type, tmp["seats_placed"], tmp["ok"])
            candidates.append(tmp)
        elif door_side_u in ("T", "B"):
            side = "B" if door_side_u == "T" else "T"
            start_from = "L"
            if door_offset is not None:
                if door_offset < (room_w / 2):
                    start_from = "R"
            tmp = place_workstations_single_wall_tb(
                room_w=room_w,
                room_d=room_d,
                furniture=FURNITURE,
                ws_type=ws_type,
                seats_required=seats_required,
                blocks=blocks,
                side=side,
                gap_x=0,
                start_from=start_from,
                door_tip=door_tip,
            )
            logger.debug("try single %s: %s seats=%d ok=%s", side, ws_type, tmp["seats_placed"], tmp["ok"])
            candidates.append(tmp)
        else:
            # 1) 両壁（左右）
            tmp1 = place_workstations_double_wall(
                room_w=room_w,
                room_d=room_d,
                furniture=FURNITURE,
                ws_type=ws_type,
                seats_required=seats_required,
                blocks=blocks,
                gap_y=0,
                door_tip=door_tip,
            )
            logger.debug("try double: %s seats=%d ok=%s", ws_type, tmp1["seats_placed"], tmp1["ok"])

            # 2) 上下壁
            tmp_tb = place_workstations_double_wall_top_bottom(
                room_w=room_w,
                room_d=room_d,
                furniture=FURNITURE,
                ws_type=ws_type,
                seats_required=seats_required,
                blocks=blocks,
                gap_x=0,
                door_tip=door_tip,
            )
            print("--- try double TB:", ws_type, tmp_tb["seats_placed"], tmp_tb["ok"])

            # 3) 片壁（左）
            tmp2 = place_workstations_single_wall(
                room_w=room_w,
                room_d=room_d,
                furniture=FURNITURE,
                ws_type=ws_type,
                seats_required=seats_required,
                blocks=blocks,
                side="L",
                gap_y=0,
                door_tip=door_tip,
            )
            logger.debug("try single L: %s seats=%d ok=%s", ws_type, tmp2["seats_placed"], tmp2["ok"])

            # 4) 片壁（右）
            tmp3 = place_workstations_single_wall(
                room_w=room_w,
                room_d=room_d,
                furniture=FURNITURE,
                ws_type=ws_type,
                seats_required=seats_required,
                blocks=blocks,
                side="R",
                gap_y=0,
                door_tip=door_tip,
            )
            logger.debug("try single R: %s seats=%d ok=%s", ws_type, tmp3["seats_placed"], tmp3["ok"])

            candidates = [tmp1, tmp_tb, tmp2, tmp3]
        if equipment:
            candidates = [
                place_equipment_along_wall(
                    base_result=c,
                    room_w=room_w,
                    room_d=room_d,
                    furniture=FURNITURE,
                    equipment_list=equipment,
                    blocks=blocks,
                    equipment_x_override=equipment_x_override,
                    door_side=door_side,
                    door_offset=door_offset,
                    equipment_clearance_mm=0,
                )
                for c in candidates
            ]

        best_for_ws = sorted(candidates, key=_score, reverse=True)[0]
        if not any(c.get("ok") for c in candidates):
            best_for_ws = sorted(
                candidates,
                key=lambda r: (r.get("seats_placed", 0), r.get("equipment_placed", 0)),
                reverse=True,
            )[0]

        # ws_typeごとにベストを更新
        if best is None or _score(best_for_ws) > _score(best):
            best = best_for_ws

        # 目的席数に到達したら、そこから先は設備配置に進むためbreak
        if best_for_ws["ok"] and priority == "equipment":
            if (not equipment) or best_for_ws.get("equipment_placed", 0) >= len(equipment):
                best = best_for_ws
                break

    return best


def main():
    parser = argparse.ArgumentParser(description="Office layout engine (room size specified)")
    parser.add_argument("--w", type=int, required=True, help="room width in mm (e.g. 5000)")
    parser.add_argument("--d", type=int, required=True, help="room depth in mm (e.g. 4000)")
    parser.add_argument("--seats", type=int, default=8, help="required seats (default: 8)")
    parser.add_argument("--equip", type=str, default="", help='equipment csv e.g. "storage_M,storage_M,mfp"')
    parser.add_argument("--out", type=str, default="layout_3plans.pdf", help="output pdf filename")
    parser.add_argument("--xeq", type=int, default=None, help="equipment x override (mm), optional")
    parser.add_argument("--door-d", type=int, default=900, help="door buffer depth in mm (default: 900)")
    parser.add_argument("--door-side", type=str, default="T", help="door side: T/B/L/R (default: T)")
    parser.add_argument("--door-offset", type=int, default=None, help="door offset along side (mm), optional")
    parser.add_argument("--priority", type=str, default="equipment", choices=["equipment", "desk", "desk_1200"], help="selection priority (default: equipment)")
    args = parser.parse_args()

    room_w = args.w
    room_d = args.d
    room_w_actual = room_w + 10
    room_d_actual = room_d + 10
    seats_required = args.seats
    equipment = parse_equipment(args.equip)

    # 机候補（プランA/Bで順序を変える）
    if args.priority == "desk_1200":
        ws_candidates_wall = ["ws_1200x600", "ws_1200x700"]
        ws_candidates_face = ["ws_1200x600", "ws_1200x700"]
    else:
        ws_candidates_wall = ["ws_1200x600", "ws_1000x600", "ws_1200x700"]
        ws_candidates_face = ["ws_1000x600", "ws_1200x600", "ws_1200x700"]

    blocks, door_rect, door_side, door_tip = build_blocks(
        room_w_actual,
        room_d_actual,
        door_w=850,
        door_d=args.door_d,
        door_side=args.door_side,
        door_offset=args.door_offset,
    )

    # 2案を作る：壁付けパターンと対面パターン
    pages = []

    res_wall = solve_one_plan(
        room_w=room_w_actual,
        room_d=room_d_actual,
        seats_required=seats_required,
        ws_candidates=ws_candidates_wall,
        blocks=blocks,
        equipment=equipment,
        equipment_x_override=args.xeq,
        door_side=door_side,
        door_offset=args.door_offset,
        priority=args.priority,
        door_tip=door_tip,
    )

    def _score_face(res):
        return score_layout(res, args.priority)

    res_face = None
    for ws_type in ws_candidates_face:
        tmp = place_workstations_face_to_face_center(
            room_w=room_w_actual,
            room_d=room_d_actual,
            furniture=FURNITURE,
            ws_type=ws_type,
            seats_required=seats_required,
            blocks=blocks,
            gap_x=0,
            door_side=door_side,
            door_rect=door_rect,
            door_tip=door_tip,
        )
        if equipment:
            tmp = place_equipment_along_wall(
                base_result=tmp,
                room_w=room_w_actual,
                room_d=room_d_actual,
                furniture=FURNITURE,
                equipment_list=equipment,
                blocks=blocks,
                equipment_x_override=args.xeq,
                door_side=door_side,
                door_offset=args.door_offset,
                equipment_clearance_mm=0,
            )
        if res_face is None:
            res_face = tmp
        else:
            cur = _score_face(tmp)
            best = _score_face(res_face)
            if cur > best:
                res_face = tmp
            elif cur == best and res_wall.get("ws_type") and tmp.get("ws_type") != res_wall.get("ws_type"):
                res_face = tmp

    door_item = {"type": "door_arc", "rect": door_rect, "side": door_side, "flip_v": False, "flip_h": False}
    pages.append({"title": "Plan A (Wall)", "items": res_wall["items"] + [door_item]})
    pages.append({"title": "Plan B (Face-to-Face)", "items": res_face["items"] + [door_item]})

    export_multi_layout_pdf(args.out, room_w_actual, room_d_actual, pages, label_w=room_w, label_d=room_d)
    logger.info("PDF exported: %s", args.out)

    export_layout_json("layout_3plans.json", room_w_actual, room_d_actual, pages)
    export_layout_csv("layout_3plans.csv", pages)
    logger.info("Data exported: layout_3plans.json, layout_3plans.csv")

    # コンソールにも要約
    logger.info("=== RESULT (Plan A / Wall) ===")
    logger.info("pattern: %s", res_wall.get("pattern"))
    logger.info("ws_type: %s", res_wall.get("ws_type"))
    logger.info("seats_required: %d", seats_required)
    logger.info("seats_placed: %d", res_wall.get("seats_placed"))
    logger.info("ok: %s", res_wall.get("ok"))
    if "equipment_target" in res_wall:
        logger.info("equipment_target: %d", res_wall.get("equipment_target"))
        logger.info("equipment_placed: %d", res_wall.get("equipment_placed"))
    if "score" in res_wall:
        logger.info("score: %s", res_wall.get("score"))

    # 警告表示
    if res_wall.get("seats_placed", 0) < seats_required:
        logger.warning("Plan A does not meet required seats.")
    if res_face.get("seats_placed", 0) < seats_required:
        logger.warning("Plan B does not meet required seats.")
    if equipment:
        if res_wall.get("equipment_placed", 0) < len(equipment):
            logger.warning("Plan A cannot place all equipment.")
        if res_face.get("equipment_placed", 0) < len(equipment):
            logger.warning("Plan B cannot place all equipment.")


if __name__ == "__main__":
    main()
