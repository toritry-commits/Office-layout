"""
レイアウト結果をSVG形式で出力するモジュール
Streamlitでの画面表示用
"""
import math


def render_layout_svg(room_w: int, room_d: int, items: list, title: str = "", width_px: int = 600) -> str:
    """
    レイアウト結果をSVG文字列として返す

    Args:
        room_w: 部屋の幅 (mm)
        room_d: 部屋の奥行き (mm)
        items: レイアウトアイテムのリスト
        title: タイトル (省略可)
        width_px: SVGの幅 (ピクセル)

    Returns:
        SVG文字列
    """
    # マージンとスケール計算
    margin = 40
    title_height = 30 if title else 0

    # アスペクト比を維持してスケール計算
    available_width = width_px - margin * 2
    scale = available_width / room_w
    height_px = int(room_d * scale + margin * 2 + title_height)

    # 原点オフセット
    ox = margin
    oy = margin + title_height

    # 色定義
    floor_base = "#D9D9D9"
    floor_grid = "#BFBFBF"
    outline = "#808080"
    text_gray = "#8C8C8C"

    # SVG開始
    svg_parts = [
        f'<svg width="{width_px}" height="{height_px}" viewBox="0 0 {width_px} {height_px}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect x="0" y="0" width="{width_px}" height="{height_px}" fill="#FFFFFF"/>',
    ]

    # タイトル
    if title:
        svg_parts.append(f'<text x="{margin}" y="24" font-family="sans-serif" font-size="16" font-weight="bold" fill="#333">{title}</text>')

    # 床描画
    floor_w = room_w * scale
    floor_d = room_d * scale
    svg_parts.append(f'<rect x="{ox}" y="{oy}" width="{floor_w}" height="{floor_d}" fill="{floor_base}"/>')

    # グリッド線 (500mm間隔)
    step = 500 * scale
    x = ox + step
    while x < ox + floor_w - 0.1:
        svg_parts.append(f'<line x1="{x}" y1="{oy}" x2="{x}" y2="{oy + floor_d}" stroke="{floor_grid}" stroke-width="0.5"/>')
        x += step
    y = oy + step
    while y < oy + floor_d - 0.1:
        svg_parts.append(f'<line x1="{ox}" y1="{y}" x2="{ox + floor_w}" y2="{y}" stroke="{floor_grid}" stroke-width="0.5"/>')
        y += step

    # 床枠
    svg_parts.append(f'<rect x="{ox}" y="{oy}" width="{floor_w}" height="{floor_d}" fill="none" stroke="{outline}" stroke-width="2"/>')

    # 外枠 (10mm外側)
    off = 10 * scale
    svg_parts.append(f'<rect x="{ox - off}" y="{oy - off}" width="{floor_w + off * 2}" height="{floor_d + off * 2}" fill="none" stroke="{outline}" stroke-width="4"/>')

    # アイテム描画
    for it in items:
        item_type = it.get("type", "")

        # ドアアーク
        if item_type == "door_arc":
            svg_parts.append(_render_door_arc(it, room_w, room_d, ox, oy, scale, outline))
            continue

        # 柱/ブロック
        if item_type == "block":
            r = it["rect"]
            x = ox + r.x * scale
            y = oy + r.y * scale
            w = r.w * scale
            d = r.d * scale
            svg_parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{d}" fill="rgba(128,128,128,0.5)" stroke="{outline}"/>')
            continue

        # 窓 (壁上に二重線で表示)
        if item_type == "window":
            side = (it.get("side") or "T").upper()
            win_offset = it.get("offset", 0)
            win_width = it.get("width", 1000)
            win_color = "#0080CC"  # 青みがかった色
            gap = 2  # 二重線の間隔 (px)

            if side == "T":
                x1 = ox + win_offset * scale
                x2 = ox + (win_offset + win_width) * scale
                y_wall = oy
                svg_parts.append(f'<line x1="{x1}" y1="{y_wall}" x2="{x2}" y2="{y_wall}" stroke="{win_color}" stroke-width="2.5"/>')
                svg_parts.append(f'<line x1="{x1}" y1="{y_wall + gap}" x2="{x2}" y2="{y_wall + gap}" stroke="{win_color}" stroke-width="2.5"/>')
            elif side == "B":
                x1 = ox + win_offset * scale
                x2 = ox + (win_offset + win_width) * scale
                y_wall = oy + floor_d
                svg_parts.append(f'<line x1="{x1}" y1="{y_wall}" x2="{x2}" y2="{y_wall}" stroke="{win_color}" stroke-width="2.5"/>')
                svg_parts.append(f'<line x1="{x1}" y1="{y_wall - gap}" x2="{x2}" y2="{y_wall - gap}" stroke="{win_color}" stroke-width="2.5"/>')
            elif side == "L":
                y1 = oy + win_offset * scale
                y2 = oy + (win_offset + win_width) * scale
                x_wall = ox
                svg_parts.append(f'<line x1="{x_wall}" y1="{y1}" x2="{x_wall}" y2="{y2}" stroke="{win_color}" stroke-width="2.5"/>')
                svg_parts.append(f'<line x1="{x_wall + gap}" y1="{y1}" x2="{x_wall + gap}" y2="{y2}" stroke="{win_color}" stroke-width="2.5"/>')
            else:  # R
                y1 = oy + win_offset * scale
                y2 = oy + (win_offset + win_width) * scale
                x_wall = ox + floor_w
                svg_parts.append(f'<line x1="{x_wall}" y1="{y1}" x2="{x_wall}" y2="{y2}" stroke="{win_color}" stroke-width="2.5"/>')
                svg_parts.append(f'<line x1="{x_wall - gap}" y1="{y1}" x2="{x_wall - gap}" y2="{y2}" stroke="{win_color}" stroke-width="2.5"/>')
            continue

        # 家具類
        if "rect" not in it:
            continue

        r = it["rect"]
        x = ox + r.x * scale
        y = oy + r.y * scale
        w = r.w * scale
        d = r.d * scale

        # 椅子
        if item_type == "chair":
            svg_parts.append(_render_chair(x, y, w, d, it.get("chair_back", "B")))
            continue

        # デスク
        if item_type == "desk":
            long_mm = int(max(r.w, r.d))
            short_mm = int(min(r.w, r.d))
            size_text = f"{long_mm}x{short_mm}"
            svg_parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{d}" fill="white" stroke="#333" stroke-width="0.8"/>')
            svg_parts.append(f'<text x="{x + w/2}" y="{y + d/2 - 4}" font-family="sans-serif" font-size="8" fill="{text_gray}" text-anchor="middle">desk</text>')
            svg_parts.append(f'<text x="{x + w/2}" y="{y + d/2 + 8}" font-family="sans-serif" font-size="7" fill="{text_gray}" text-anchor="middle">{size_text}</text>')
            continue

        # 収納
        if item_type == "storage_M":
            svg_parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{d}" fill="white" stroke="#333" stroke-width="1"/>')
            svg_parts.append(f'<text x="{x + w/2}" y="{y + d/2 - 4}" font-family="sans-serif" font-size="8" fill="{text_gray}" text-anchor="middle">storage</text>')
            svg_parts.append(f'<text x="{x + w/2}" y="{y + d/2 + 8}" font-family="sans-serif" font-size="7" fill="{text_gray}" text-anchor="middle">{int(r.w)}x{int(r.d)}</text>')
            continue

        # 複合機
        if item_type == "mfp":
            svg_parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{d}" fill="white" stroke="#333" stroke-width="1"/>')
            svg_parts.append(f'<text x="{x + w/2}" y="{y + d/2}" font-family="sans-serif" font-size="8" fill="{text_gray}" text-anchor="middle">MFP</text>')
            continue

        # その他
        label = it.get("label", item_type)
        svg_parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{d}" fill="white" stroke="#333" stroke-width="1"/>')
        if label:
            svg_parts.append(f'<text x="{x + 2}" y="{y + 12}" font-family="sans-serif" font-size="8" fill="{text_gray}">{label}</text>')

    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


def _render_chair(x: float, y: float, w: float, d: float, back_side: str = "B") -> str:
    """椅子アイコンをSVGで描画"""
    parts = []

    # 座面
    seat_size = min(w, d) * 0.55
    seat_x = x + (w - seat_size) / 2
    seat_y = y + (d - seat_size) / 2
    parts.append(f'<rect x="{seat_x}" y="{seat_y}" width="{seat_size}" height="{seat_size}" fill="white" stroke="#333" stroke-width="0.8"/>')

    # 背もたれ
    back_thickness = max(seat_size * 0.18, 2.0)
    back_w = seat_size * 0.9
    back_side = (back_side or "B").upper()

    if back_side == "T":
        back_x = seat_x + (seat_size - back_w) / 2
        back_y = seat_y - back_thickness / 2
        parts.append(f'<rect x="{back_x}" y="{back_y}" width="{back_w}" height="{back_thickness}" fill="white" stroke="#333" stroke-width="0.8"/>')
    elif back_side == "B":
        back_x = seat_x + (seat_size - back_w) / 2
        back_y = seat_y + seat_size - back_thickness / 2
        parts.append(f'<rect x="{back_x}" y="{back_y}" width="{back_w}" height="{back_thickness}" fill="white" stroke="#333" stroke-width="0.8"/>')
    elif back_side == "L":
        back_x = seat_x - back_thickness / 2
        back_y = seat_y + (seat_size - back_w) / 2
        parts.append(f'<rect x="{back_x}" y="{back_y}" width="{back_thickness}" height="{back_w}" fill="white" stroke="#333" stroke-width="0.8"/>')
    else:  # R
        back_x = seat_x + seat_size - back_thickness / 2
        back_y = seat_y + (seat_size - back_w) / 2
        parts.append(f'<rect x="{back_x}" y="{back_y}" width="{back_thickness}" height="{back_w}" fill="white" stroke="#333" stroke-width="0.8"/>')

    return '\n'.join(parts)


def _render_door_arc(it: dict, room_w: int, room_d: int, ox: float, oy: float, scale: float, color: str) -> str:
    """ドアアークをSVGで描画"""
    r = it["rect"]
    side = (it.get("side") or "T").upper()
    swing = (it.get("swing") or "in").lower()
    flip_v = bool(it.get("flip_v"))
    flip_h = bool(it.get("flip_h"))

    if side in ("T", "B"):
        radius = r.w
        cx = r.x
        cy = 0 if side == "T" else room_d
    else:
        radius = r.d
        cx = 0 if side == "L" else room_w
        cy = r.y

    # 角度計算
    if swing == "out":
        if side == "T":
            line_angs = (90, 180)
        elif side == "B":
            line_angs = (270, 360)
        elif side == "L":
            line_angs = (0, 90)
        else:
            line_angs = (180, 270)
    else:
        if side == "T":
            line_angs = (270, 0)
        elif side == "B":
            line_angs = (0, 90)
        elif side == "L":
            line_angs = (270, 0)
        else:
            line_angs = (180, 270)

    flip_v_eff = flip_v if side in ("L", "R") else False
    flip_h_eff = flip_h if side in ("T", "B") else False

    if side in ("T", "B") and flip_h_eff:
        cx = r.x + r.w
    if side in ("L", "R") and flip_v_eff:
        cy = r.y + r.d

    def flip_angle(a):
        a = a % 360
        if flip_v_eff:
            a = (360 - a) % 360
        if flip_h_eff:
            a = (180 - a) % 360
        return a

    a1 = flip_angle(line_angs[0])
    a2 = flip_angle(line_angs[1])

    # SVG座標に変換 (Y軸反転なし)
    cxp = ox + cx * scale
    cyp = oy + cy * scale
    rp = radius * scale

    # アーク描画用の座標計算
    def point_at_angle(ang):
        rad = math.radians(ang)
        return (cxp + rp * math.cos(rad), cyp - rp * math.sin(rad))

    start = point_at_angle(a1)
    end = point_at_angle(a2)

    # アークのsweepフラグ
    delta = (a2 - a1) % 360
    large_arc = 1 if delta > 180 else 0
    sweep = 0  # 反時計回り

    parts = []
    # アーク
    parts.append(f'<path d="M {start[0]} {start[1]} A {rp} {rp} 0 {large_arc} {sweep} {end[0]} {end[1]}" stroke="{color}" fill="none" stroke-width="1.5"/>')
    # 半径線
    parts.append(f'<line x1="{cxp}" y1="{cyp}" x2="{start[0]}" y2="{start[1]}" stroke="{color}" stroke-width="1"/>')
    parts.append(f'<line x1="{cxp}" y1="{cyp}" x2="{end[0]}" y2="{end[1]}" stroke="{color}" stroke-width="1"/>')

    return '\n'.join(parts)
