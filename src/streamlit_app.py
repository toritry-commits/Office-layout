import io
import math
import tempfile
from pathlib import Path

import streamlit as st
from streamlit_drawable_canvas import st_canvas

from app import build_blocks, solve_one_plan
from geometry import Rect
from catalog import FURNITURE
from export_data import export_layout_csv, export_layout_json
from export_pdf import export_multi_layout_pdf
from export_svg import render_layout_svg
from patterns import place_workstations_face_to_face_center, place_equipment_along_wall, place_workstations_mixed
from utils import score_layout


st.set_page_config(page_title="Office Layout Engine", layout="wide")

st.title("Office Layout Engine")

if "step" not in st.session_state:
    st.session_state["step"] = 1

col1, col2 = st.columns(2)
with col1:
    room_d = st.number_input("縦 (mm)", min_value=2000, max_value=50000, value=3000, step=50)
    door_center = st.checkbox("入口を中央に配置", value=True)
    door_offset = st.number_input("入口位置オフセット (mm)", min_value=0, max_value=50000, value=0, step=50)
with col2:
    room_w = st.number_input("横 (mm)", min_value=2000, max_value=50000, value=4500, step=50)
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

# 柱/凹凸ブロック（数値入力 + ドラッグ配置）
st.subheader("平面図（柱・凹凸の配置）")

# キャンバスサイズ計算 (最大400pxの幅でアスペクト比を維持)
canvas_max_width = 400
canvas_scale = canvas_max_width / room_w_actual
canvas_width = int(room_w_actual * canvas_scale)
canvas_height = int(room_d_actual * canvas_scale)

col_canvas, col_input = st.columns([2, 1])

with col_canvas:
    st.caption("キャンバス上で矩形をドラッグして柱を配置 (または右の数値入力を使用)")

    # 背景画像 (グリッド付きの床) を生成
    bg_grid_lines = []
    step = 500 * canvas_scale
    x = step
    while x < canvas_width - 0.1:
        bg_grid_lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{canvas_height}" stroke="#BFBFBF" stroke-width="0.5"/>')
        x += step
    y = step
    while y < canvas_height - 0.1:
        bg_grid_lines.append(f'<line x1="0" y1="{y}" x2="{canvas_width}" y2="{y}" stroke="#BFBFBF" stroke-width="0.5"/>')
        y += step

    # 既存の柱を描画
    existing_blocks_svg = []
    for b in st.session_state.get("blocks", []):
        bx = b["x"] * canvas_scale
        by = b["y"] * canvas_scale
        bw = b["w"] * canvas_scale
        bd = b["d"] * canvas_scale
        existing_blocks_svg.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bd}" fill="rgba(128,128,128,0.5)" stroke="#666"/>')

    bg_svg = (
        f'<svg width="{canvas_width}" height="{canvas_height}" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{canvas_width}" height="{canvas_height}" fill="#D9D9D9"/>'
        + "".join(bg_grid_lines)
        + "".join(existing_blocks_svg)
        + "</svg>"
    )

    # SVGをPNG変換せずに描画用キャンバスを表示
    canvas_result = st_canvas(
        fill_color="rgba(128, 128, 128, 0.5)",
        stroke_width=2,
        stroke_color="#666666",
        background_color="#D9D9D9",
        height=canvas_height,
        width=canvas_width,
        drawing_mode="rect",
        key="pillar_canvas",
    )

    # キャンバスで描画された矩形を柱として追加
    if canvas_result.json_data is not None:
        objects = canvas_result.json_data.get("objects", [])
        if objects:
            st.caption("キャンバスで描画した柱を追加するには「描画を確定」ボタンを押してください")
            if st.button("描画を確定"):
                blocks = st.session_state.get("blocks", [])
                for obj in objects:
                    if obj.get("type") == "rect":
                        # キャンバス座標 (px) を部屋座標 (mm) に変換
                        px_x = obj.get("left", 0)
                        px_y = obj.get("top", 0)
                        px_w = obj.get("width", 100)
                        px_h = obj.get("height", 100)

                        mm_x = int(px_x / canvas_scale)
                        mm_y = int(px_y / canvas_scale)
                        mm_w = int(px_w / canvas_scale)
                        mm_h = int(px_h / canvas_scale)

                        # 最小サイズ制限
                        if mm_w >= 100 and mm_h >= 100:
                            if mm_x + mm_w <= room_w_actual and mm_y + mm_h <= room_d_actual:
                                blocks.append({"x": mm_x, "y": mm_y, "w": mm_w, "d": mm_h})
                st.session_state["blocks"] = blocks
                st.rerun()

with col_input:
    st.caption("数値入力で追加")
    block_x = st.number_input("柱/凹凸のX (mm)", min_value=0, max_value=50000, value=0, step=50)
    block_y = st.number_input("柱/凹凸のY (mm)", min_value=0, max_value=50000, value=0, step=50)
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

    st.caption("現在の柱/凹凸一覧")
    blocks_display = []
    for i, b in enumerate(st.session_state.get("blocks", [])):
        blocks_display.append({
            "#": i + 1,
            "X": f"{b['x']}mm",
            "Y": f"{b['y']}mm",
            "幅": f"{b['w']}mm",
            "奥行": f"{b['d']}mm"
        })
    if blocks_display:
        st.table(blocks_display)
    else:
        st.caption("柱はまだ追加されていません")

# 窓の入力
st.subheader("窓の配置")
col_win_a, col_win_b = st.columns([2, 1])
with col_win_b:
    window_side_label = st.selectbox("窓の位置 (壁)", ["上 (T)", "下 (B)", "左 (L)", "右 (R)"], key="window_side")
    window_offset = st.number_input("窓の位置オフセット (mm)", min_value=0, max_value=50000, value=500, step=50)
    window_width = st.number_input("窓の幅 (mm)", min_value=100, max_value=5000, value=1000, step=50)
    if st.button("窓を追加"):
        windows = st.session_state.get("windows", [])
        window_side = window_side_label.split("(")[1][0]
        windows.append({"side": window_side, "offset": int(window_offset), "width": int(window_width)})
        st.session_state["windows"] = windows
    if st.button("窓をクリア"):
        st.session_state["windows"] = []

with col_win_a:
    st.caption("現在の窓一覧")
    windows_display = []
    for w in st.session_state.get("windows", []):
        side_labels = {"T": "上", "B": "下", "L": "左", "R": "右"}
        windows_display.append({
            "壁": side_labels.get(w["side"], w["side"]),
            "オフセット": f"{w['offset']}mm",
            "幅": f"{w['width']}mm"
        })
    if windows_display:
        st.table(windows_display)
    else:
        st.caption("窓はまだ追加されていません")

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

    # 窓の描画 (プレビュー用)
    window_svgs = []
    for win in st.session_state.get("windows", []):
        side = win["side"]
        win_offset = win["offset"]
        win_width = win["width"]
        win_color = "#0080CC"
        gap = 2

        if side == "T":
            x1 = ox + win_offset * scale_preview
            x2 = ox + (win_offset + win_width) * scale_preview
            y_wall = oy
            window_svgs.append(f'<line x1="{x1}" y1="{y_wall}" x2="{x2}" y2="{y_wall}" stroke="{win_color}" stroke-width="2.5"/>')
            window_svgs.append(f'<line x1="{x1}" y1="{y_wall + gap}" x2="{x2}" y2="{y_wall + gap}" stroke="{win_color}" stroke-width="2.5"/>')
        elif side == "B":
            x1 = ox + win_offset * scale_preview
            x2 = ox + (win_offset + win_width) * scale_preview
            y_wall = oy + floor_d
            window_svgs.append(f'<line x1="{x1}" y1="{y_wall}" x2="{x2}" y2="{y_wall}" stroke="{win_color}" stroke-width="2.5"/>')
            window_svgs.append(f'<line x1="{x1}" y1="{y_wall - gap}" x2="{x2}" y2="{y_wall - gap}" stroke="{win_color}" stroke-width="2.5"/>')
        elif side == "L":
            y1 = oy + win_offset * scale_preview
            y2 = oy + (win_offset + win_width) * scale_preview
            x_wall = ox
            window_svgs.append(f'<line x1="{x_wall}" y1="{y1}" x2="{x_wall}" y2="{y2}" stroke="{win_color}" stroke-width="2.5"/>')
            window_svgs.append(f'<line x1="{x_wall + gap}" y1="{y1}" x2="{x_wall + gap}" y2="{y2}" stroke="{win_color}" stroke-width="2.5"/>')
        else:  # R
            y1 = oy + win_offset * scale_preview
            y2 = oy + (win_offset + win_width) * scale_preview
            x_wall = ox + floor_w
            window_svgs.append(f'<line x1="{x_wall}" y1="{y1}" x2="{x_wall}" y2="{y2}" stroke="{win_color}" stroke-width="2.5"/>')
            window_svgs.append(f'<line x1="{x_wall - gap}" y1="{y1}" x2="{x_wall - gap}" y2="{y2}" stroke="{win_color}" stroke-width="2.5"/>')

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
        + "".join(window_svgs)
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

    def _score_face(res):
        return score_layout(res, priority_value)

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

    # 混在パターン (壁面 + 対面)
    res_mixed = None
    # ドアと反対の壁に壁付け席を配置
    wall_for_mixed = "R" if door_side in ("L", "T") else "L"
    wall_seats_count = min(2, seats_required)  # 壁沿いは2席まで

    for ws_type in ws_candidates_face:
        tmp = place_workstations_mixed(
            room_w=room_w_actual,
            room_d=room_d_actual,
            furniture=FURNITURE,
            ws_type=ws_type,
            seats_required=seats_required,
            blocks=blocks,
            wall_seats=wall_seats_count,
            wall_side=wall_for_mixed,
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
        if res_mixed is None:
            res_mixed = tmp
        else:
            cur = _score_face(tmp)
            best = _score_face(res_mixed)
            if cur > best:
                res_mixed = tmp

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
    # 窓アイテムを追加
    window_items = [
        {"type": "window", "side": w["side"], "offset": w["offset"], "width": w["width"]}
        for w in st.session_state.get("windows", [])
    ]
    pages = [
        {"title": "Plan A (Wall)", "items": block_items + res_wall["items"] + [door_item] + window_items},
        {"title": "Plan B (Face-to-Face)", "items": block_items + res_face["items"] + [door_item] + window_items},
        {"title": "Plan C (Mixed)", "items": block_items + res_mixed["items"] + [door_item] + window_items},
    ]

    # 固定パスにJSONを自動保存 (Claude検証用)
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    latest_json_path = output_dir / "latest_layout.json"
    export_layout_json(str(latest_json_path), room_w_actual, room_d_actual, pages)

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
    st.info(f"JSON保存先: {latest_json_path}")

    # SVGで画面表示
    st.subheader("レイアウト結果")
    col_svg1, col_svg2, col_svg3 = st.columns(3)
    with col_svg1:
        svg_wall = render_layout_svg(room_w_actual, room_d_actual, pages[0]["items"], title="Plan A (Wall)")
        st.image(svg_wall)
        st.caption(f"席数: {res_wall.get('seats_placed', 0)} / 収納: {res_wall.get('equipment_placed', 0)}")
    with col_svg2:
        svg_face = render_layout_svg(room_w_actual, room_d_actual, pages[1]["items"], title="Plan B (Face-to-Face)")
        st.image(svg_face)
        st.caption(f"席数: {res_face.get('seats_placed', 0)} / 収納: {res_face.get('equipment_placed', 0)}")
    with col_svg3:
        svg_mixed = render_layout_svg(room_w_actual, room_d_actual, pages[2]["items"], title="Plan C (Mixed)")
        st.image(svg_mixed)
        st.caption(f"席数: {res_mixed.get('seats_placed', 0)} / 収納: {res_mixed.get('equipment_placed', 0)}")
    if res_wall.get("seats_placed", 0) < seats_required:
        st.warning("Plan A（壁付け）が希望席数を満たしていません。")
    if res_face.get("seats_placed", 0) < seats_required:
        st.warning("Plan B（対面）が希望席数を満たしていません。")
    if res_mixed.get("seats_placed", 0) < seats_required:
        st.warning("Plan C（混在）が希望席数を満たしていません。")
    if equipment:
        if res_wall.get("equipment_placed", 0) < len(equipment):
            st.warning("Plan A（壁付け）で収納が全数配置できていません。")
        if res_face.get("equipment_placed", 0) < len(equipment):
            st.warning("Plan B（対面）で収納が全数配置できていません。")
        if res_mixed.get("equipment_placed", 0) < len(equipment):
            st.warning("Plan C（混在）で収納が全数配置できていません。")
    pdf_bytes = st.session_state.get("layout_pdf")
    json_bytes = st.session_state.get("layout_json")
    csv_bytes = st.session_state.get("layout_csv")
    st.download_button("PDFをダウンロード", pdf_bytes or b"", file_name="layout.pdf", disabled=pdf_bytes is None)
    st.download_button("JSONをダウンロード", json_bytes or b"", file_name="layout.json", disabled=json_bytes is None)
    st.download_button("CSVをダウンロード", csv_bytes or b"", file_name="layout.csv", disabled=csv_bytes is None)
