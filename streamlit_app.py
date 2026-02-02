import io
import math
import tempfile
from pathlib import Path

import streamlit as st

from app import build_blocks, solve_one_plan
from geometry import Rect
from catalog import FURNITURE
from export_data import export_layout_csv, export_layout_json
from export_pdf import export_multi_layout_pdf
from patterns import place_workstations_face_to_face_center, place_equipment_along_wall


st.set_page_config(page_title="Office Layout Engine", layout="wide")

st.title("Office Layout Engine")

if "step" not in st.session_state:
    st.session_state["step"] = 1

col1, col2 = st.columns(2)
with col1:
    room_d = st.number_input("縦 (mm)", min_value=2000, max_value=20000, value=3000, step=50)
    door_center = st.checkbox("入口を中央に配置", value=True)
    door_offset = st.number_input("入口位置オフセット (mm)", min_value=0, max_value=20000, value=0, step=50)
with col2:
    room_w = st.number_input("横 (mm)", min_value=2000, max_value=20000, value=4500, step=50)
    door_side_label = st.selectbox("入口位置 (壁)", ["上 (T)", "下 (B)", "左 (L)", "右 (R)"])
    door_swing = st.selectbox("ドア開き方向", ["室内側", "室外側"])
    flip_v = st.checkbox("ドア上下反転", value=False)
    flip_h = st.checkbox("ドア左右反転", value=False)


def _priority_value(label: str) -> str:
    if label == "席数優先":
        return "desk"
    if label == "デスクの大きさ優先（デスクの幅1200優先）":
        return "desk_1200"
    return "equipment"


room_w = int(room_w)
room_d = int(room_d)

# 仕様に合わせて実寸を +10mm
room_w_actual = room_w + 10
room_d_actual = room_d + 10

# 柱/凹凸ブロック（数値入力）
st.subheader("平面図（柱・凹凸の配置）")
col_a, col_b = st.columns([2, 1])
with col_b:
    block_x = st.number_input("柱/凹凸のX (mm)", min_value=0, max_value=20000, value=0, step=50)
    block_y = st.number_input("柱/凹凸のY (mm)", min_value=0, max_value=20000, value=0, step=50)
    block_w = st.number_input("柱/凹凸の幅 (mm)", min_value=100, max_value=5000, value=600, step=50)
    block_d = st.number_input("柱/凹凸の奥行 (mm)", min_value=100, max_value=5000, value=600, step=50)
    if st.button("柱/凹凸を追加"):
        blocks = st.session_state.get("blocks", [])
        if block_x + block_w <= room_w_actual and block_y + block_d <= room_d_actual:
            blocks.append({"x": int(block_x), "y": int(block_y), "w": int(block_w), "d": int(block_d)})
            st.session_state["blocks"] = blocks
        else:
            st.warning("柱/凹凸が床枠外です。")
    if st.button("柱/凹凸をクリア"):
        st.session_state["blocks"] = []

with col_a:
    st.caption("現在の柱/凹凸一覧")
    st.table(st.session_state.get("blocks", []))

# 「平面図の作成へ」ボタンは柱型入力の下に配置
save_room = st.button("平面図の作成へ")
if save_room:
    st.session_state["step"] = 2
    st.session_state["preview_ready"] = True

# 平面図プレビュー（床と同じ仕様 + 周囲余白1000mm）
if st.session_state.get("preview_ready"):
    door_side = door_side_label.split("(")[1][0]
    _, door_rect_preview, door_side_preview, _ = build_blocks(
        room_w_actual,
        room_d_actual,
        door_w=850,
        door_d=900,
        door_side=door_side,
        door_offset=None if door_center else door_offset,
    )
    st.subheader("平面図プレビュー")
    margin = 1000
    preview_w = room_w_actual + margin * 2
    preview_d = room_d_actual + margin * 2
    scale_preview = min(600 / preview_w, 400 / preview_d)
    w_px = int(preview_w * scale_preview)
    h_px = int(preview_d * scale_preview)
    ox = margin * scale_preview
    oy = margin * scale_preview
    floor_w = room_w_actual * scale_preview
    floor_d = room_d_actual * scale_preview

    base = "#D9D9D9"  # K:15
    grid = "#BFBFBF"  # K:25
    outline = "#808080"  # K:50

    # grid lines
    grid_lines = []
    step = 500 * scale_preview
    x = ox + step
    while x < ox + floor_w - 0.1:
        grid_lines.append(f'<line x1="{x}" y1="{oy}" x2="{x}" y2="{oy + floor_d}" stroke="{grid}" stroke-width="0.5"/>')
        x += step
    y = oy + step
    while y < oy + floor_d - 0.1:
        grid_lines.append(f'<line x1="{ox}" y1="{y}" x2="{ox + floor_w}" y2="{y}" stroke="{grid}" stroke-width="0.5"/>')
        y += step

    rects = []
    for b in st.session_state.get("blocks", []):
        x = ox + b["x"] * scale_preview
        y = oy + b["y"] * scale_preview
        w = b["w"] * scale_preview
        d = b["d"] * scale_preview
        rects.append(f'<rect x="{x}" y="{y}" width="{w}" height="{d}" fill="rgba(128,128,128,0.2)" stroke="{outline}" />')

    # door arc (preview) + radius lines
    door_items = []
    if door_rect_preview is not None:
        dr = door_rect_preview
        ds = door_side_preview
        if ds in ("T", "B"):
            radius = dr.w * scale_preview
            cx = ox + dr.x * scale_preview
            cy = oy + (0 if ds == "T" else room_d_actual) * scale_preview
        else:
            radius = dr.d * scale_preview
            cx = ox + (0 if ds == "L" else room_w_actual) * scale_preview
            cy = oy + dr.y * scale_preview

        flip_v_eff = flip_v if ds in ("L", "R") else False
        flip_h_eff = flip_h if ds in ("T", "B") else False
        # Keep door opening span fixed; move hinge to opposite edge on flip
        if ds in ("T", "B") and flip_h_eff:
            cx = ox + (dr.x + dr.w) * scale_preview
        if ds in ("L", "R") and flip_v_eff:
            cy = oy + (dr.y + dr.d) * scale_preview

        swing_out = door_swing == "室外側"
        if swing_out:
            if ds == "T":
                line_angs = (90, 180)
            elif ds == "B":
                line_angs = (270, 360)
            elif ds == "L":
                line_angs = (0, 90)
            else:  # "R"
                line_angs = (180, 270)
        else:
            if ds == "T":
                line_angs = (270, 0)
            elif ds == "B":
                line_angs = (0, 90)
            elif ds == "L":
                line_angs = (270, 0)
            else:  # "R"
                line_angs = (180, 270)

        def _flip_angle(a):
            a = a % 360
            if flip_v_eff:
                a = (360 - a) % 360
            if flip_h_eff:
                a = (180 - a) % 360
            return a

        a1 = _flip_angle(line_angs[0])
        a2 = _flip_angle(line_angs[1])

        def _svg_angle(a):
            return (360 - a) % 360

        a1 = _svg_angle(a1)
        a2 = _svg_angle(a2)

        def _pt(ang):
            rad = ang * 3.1415926535 / 180.0
            return (cx + radius * math.cos(rad), cy + radius * math.sin(rad))

        start = _pt(a1)
        end = _pt(a2)
        line1 = (cx, cy, start[0], start[1])
        line2 = (cx, cy, end[0], end[1])
        delta = (a2 - a1) % 360
        sweep = 1 if delta <= 180 else 0

        door_group = []
        door_group.append(
            f'<path d="M {start[0]} {start[1]} A {radius} {radius} 0 0 {sweep} {end[0]} {end[1]}" '
            f'stroke="{outline}" fill="none" stroke-width="1.5"/>'
        )
        door_group.append(
            f'<line x1="{line1[0]}" y1="{line1[1]}" x2="{line1[2]}" y2="{line1[3]}" stroke="{outline}" stroke-width="1"/>'
        )
        door_group.append(
            f'<line x1="{line2[0]}" y1="{line2[1]}" x2="{line2[2]}" y2="{line2[3]}" stroke="{outline}" stroke-width="1"/>'
        )

        door_items.extend(door_group)

    # outer frame 10mm
    off = 10 * scale_preview
    svg = (
        f'<svg width="{w_px}" height="{h_px}" viewBox="0 0 {w_px} {h_px}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<rect x="0" y="0" width="{w_px}" height="{h_px}" fill="#FFFFFF" />'
        f'<rect x="{ox}" y="{oy}" width="{floor_w}" height="{floor_d}" fill="{base}" stroke="none"/>'
        + "".join(grid_lines)
        + f'<rect x="{ox}" y="{oy}" width="{floor_w}" height="{floor_d}" fill="none" stroke="{outline}" stroke-width="2"/>'
        + f'<rect x="{ox - off}" y="{oy - off}" width="{floor_w + off*2}" height="{floor_d + off*2}" fill="none" stroke="{outline}" stroke-width="4"/>'
        + "".join(rects)
        + "".join(door_items)
        + "</svg>"
    )
    st.image(svg)

if st.session_state["step"] >= 2:
    with st.form("layout_inputs"):
        col3, col4 = st.columns(2)
        with col3:
            seats = st.number_input("席数", min_value=1, max_value=200, value=5, step=1)
            storage_count = st.number_input("収納数 (M)", min_value=0, max_value=20, value=2, step=1)
        with col4:
            priority = st.selectbox("優先順位", ["席数優先", "収納優先", "デスクの大きさ優先（デスクの幅1200優先）"])
        submitted = st.form_submit_button("レイアウト生成")
else:
    submitted = False

if submitted:
    seats_required = int(seats)
    equipment = ["storage_M"] * int(storage_count)
    priority_value = _priority_value(priority)
    door_side = door_side_label.split("(")[1][0]
    blocks, door_rect, door_side, door_tip = build_blocks(
        room_w_actual,
        room_d_actual,
        door_w=850,
        door_d=900,
        door_side=door_side,
        door_offset=None if door_center else door_offset,
    )
    # 追加ブロック
    for b in st.session_state.get("blocks", []):
        blocks.append(Rect(x=b["x"], y=b["y"], w=b["w"], d=b["d"]))

    if priority_value == "desk_1200":
        ws_candidates_wall = ["ws_1200x600", "ws_1200x700"]
        ws_candidates_face = ["ws_1200x600", "ws_1200x700"]
    else:
        ws_candidates_wall = ["ws_1200x600", "ws_1000x600", "ws_1200x700"]
        ws_candidates_face = ["ws_1000x600", "ws_1200x600", "ws_1200x700"]

    res_wall = solve_one_plan(
        room_w=room_w_actual,
        room_d=room_d_actual,
        seats_required=seats_required,
        ws_candidates=ws_candidates_wall,
        blocks=blocks,
        equipment=equipment,
        equipment_x_override=None,
        door_side=door_side,
        door_offset=None,
        priority=priority_value,
        door_tip=door_tip,
    )

    def _desk_area(ws_type: str) -> int:
        try:
            s = ws_type.replace("ws_", "")
            a, b = s.split("x")
            return int(a) * int(b)
        except Exception:
            return 0

    def _score_face(res):
        ok = 1 if res.get("ok") else 0
        seats = res.get("seats_placed", 0)
        equip = res.get("equipment_placed", 0)
        desk_area = _desk_area(res.get("ws_type", ""))
        if priority_value == "desk":
            return (ok, seats, desk_area, equip)
        return (ok, seats, equip, desk_area)

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
                equipment_x_override=None,
                door_side=door_side,
                door_offset=None,
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

    door_item = {
        "type": "door_arc",
        "rect": door_rect,
        "side": door_side,
        "swing": "in" if door_swing == "室内側" else "out",
        "flip_v": flip_v,
        "flip_h": flip_h,
    }
    block_items = [
        {"type": "block", "rect": Rect(x=b["x"], y=b["y"], w=b["w"], d=b["d"])}
        for b in st.session_state.get("blocks", [])
    ]
    pages = [
        {"title": "Plan A (Wall)", "items": block_items + res_wall["items"] + [door_item]},
        {"title": "Plan B (Face-to-Face)", "items": block_items + res_face["items"] + [door_item]},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        pdf_path = tmpdir / "layout.pdf"
        json_path = tmpdir / "layout.json"
        csv_path = tmpdir / "layout.csv"

        export_multi_layout_pdf(
            str(pdf_path),
            room_w_actual,
            room_d_actual,
            pages,
            label_w=room_w,
            label_d=room_d,
        )
        export_layout_json(str(json_path), room_w_actual, room_d_actual, pages)
        export_layout_csv(str(csv_path), pages)

        st.session_state["layout_pdf"] = pdf_path.read_bytes()
        st.session_state["layout_json"] = json_path.read_bytes()
        st.session_state["layout_csv"] = csv_path.read_bytes()

    st.success("レイアウトを生成しました。")
    if res_wall.get("seats_placed", 0) < seats_required:
        st.warning("Plan A（壁付け）が希望席数を満たしていません。")
    if res_face.get("seats_placed", 0) < seats_required:
        st.warning("Plan B（対面）が希望席数を満たしていません。")
    if equipment:
        if res_wall.get("equipment_placed", 0) < len(equipment):
            st.warning("Plan A（壁付け）で収納が全数配置できていません。")
        if res_face.get("equipment_placed", 0) < len(equipment):
            st.warning("Plan B（対面）で収納が全数配置できていません。")
    pdf_bytes = st.session_state.get("layout_pdf")
    json_bytes = st.session_state.get("layout_json")
    csv_bytes = st.session_state.get("layout_csv")
    st.download_button("PDFをダウンロード", pdf_bytes or b"", file_name="layout.pdf", disabled=pdf_bytes is None)
    st.download_button("JSONをダウンロード", json_bytes or b"", file_name="layout.json", disabled=json_bytes is None)
    st.download_button("CSVをダウンロード", csv_bytes or b"", file_name="layout.csv", disabled=csv_bytes is None)
