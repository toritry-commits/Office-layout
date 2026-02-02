import math

from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics

# 日本語フォント（CID）
try:
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    _JP_FONT = "HeiseiKakuGo-W5"  # ゴシック系（日本語OK）
    pdfmetrics.registerFont(UnicodeCIDFont(_JP_FONT))
except Exception:
    _JP_FONT = "Helvetica"  # 最終フォールバック（※日本語は□になる）


_PT_PER_MM = 72.0 / 25.4  # 1mm = 72/25.4 pt
_WALL_LINE_WIDTH = 2
_OUTER_OFFSET_MM = 10
_OUTER_LINE_WIDTH = 4


# 文字色（デスクに合わせる：薄グレー）
_TEXT_GRAY = (0.55, 0.55, 0.55)


def _draw_dim_h(c, x0, y0, x1, text, text_y_offset=8, color=None):
    if color:
        c.setStrokeColorRGB(*color)
        c.setFillColorRGB(*color)
    c.line(x0, y0, x1, y0)
    tick = 6
    c.line(x0, y0 - tick, x0, y0 + tick)
    c.line(x1, y0 - tick, x1, y0 + tick)
    c.setFont("Helvetica", 8)
    c.drawCentredString((x0 + x1) / 2, y0 + text_y_offset, text)
    if color:
        c.setStrokeColorRGB(0, 0, 0)
        c.setFillColorRGB(0, 0, 0)


def _draw_dim_v(c, x0, y0, y1, text, text_x_offset=6, color=None):
    if color:
        c.setStrokeColorRGB(*color)
        c.setFillColorRGB(*color)
    c.line(x0, y0, x0, y1)
    tick = 6
    c.line(x0 - tick, y0, x0 + tick, y0)
    c.line(x0 - tick, y1, x0 + tick, y1)
    c.setFont("Helvetica", 8)
    c.drawString(x0 + text_x_offset, (y0 + y1) / 2, text)
    if color:
        c.setStrokeColorRGB(0, 0, 0)
        c.setFillColorRGB(0, 0, 0)


def _calc_scale(room_w_mm, room_d_mm, draw_w_pt, draw_h_pt):
    fit_s = min(draw_w_pt / room_w_mm, draw_h_pt / room_d_mm)

    s_1_20 = _PT_PER_MM / 20.0  # 1:20
    if s_1_20 * room_w_mm <= draw_w_pt and s_1_20 * room_d_mm <= draw_h_pt:
        return s_1_20, "Scale 1:20"

    s_1_30 = _PT_PER_MM / 30.0  # 1:30
    if s_1_30 * room_w_mm <= draw_w_pt and s_1_30 * room_d_mm <= draw_h_pt:
        return s_1_30, "Scale 1:30"

    actual_ratio = round(_PT_PER_MM / fit_s)
    return fit_s, f"Scale FIT (approx 1:{actual_ratio})"


def _string_width(font_name, font_size, text):
    try:
        return pdfmetrics.stringWidth(text, font_name, font_size)
    except Exception:
        return font_size * len(text) * 0.6


def _fit_font_sizes_in_rect(rect_w_pt, line1, line2, font1, size1, font2, size2, pad=6, min_size=6):
    max_w = rect_w_pt - pad * 2
    s1, s2 = size1, size2

    while s1 >= min_size and s2 >= min_size:
        w1 = _string_width(font1, s1, line1)
        w2 = _string_width(font2, s2, line2)
        if max(w1, w2) <= max_w:
            return s1, s2

        if w1 >= w2 and s1 > min_size:
            s1 -= 1
        elif s2 > min_size:
            s2 -= 1
        else:
            break

    return max(s1, min_size), max(s2, min_size)


def _draw_centered_two_lines_in_rect(
    c,
    rect_x,
    rect_y,
    rect_w,
    rect_h,
    cx,
    cy,
    line1,
    line2,
    font1,
    size1,
    font2,
    size2,
    gap=14,
    pad=7,
    auto_adjust=True,
):
    s1, s2 = _fit_font_sizes_in_rect(rect_w, line1, line2, font1, size1, font2, size2, pad=pad)

    block_h = (s1 + s2) * 0.9 + gap
    half_h = block_h / 2.0

    w1 = _string_width(font1, s1, line1)
    w2 = _string_width(font2, s2, line2)
    half_w = max(w1, w2) / 2.0

    if auto_adjust:
        min_cx = rect_x + pad + half_w
        max_cx = rect_x + rect_w - pad - half_w
        min_cy = rect_y + pad + half_h
        max_cy = rect_y + rect_h - pad - half_h

        if cx < min_cx:
            cx = min_cx
        elif cx > max_cx:
            cx = max_cx

        if cy < min_cy:
            cy = min_cy
        elif cy > max_cy:
            cy = max_cy

    c.setFont(font1, s1)
    c.drawCentredString(cx, cy + gap / 2.0, line1)
    c.setFont(font2, s2)
    c.drawCentredString(cx, cy - gap / 2.0, line2)


def _draw_legend(c, x, y, desk_size_counts):
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, "Legend")
    y -= 14

    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "Desk sizes")
    y -= 12

    c.setFont("Helvetica", 9)
    if not desk_size_counts:
        c.drawString(x, y, "- (none)")
        return

    items = sorted(desk_size_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    for size, cnt in items[:20]:
        c.drawString(x, y, f"- {size} : {cnt}")
        y -= 12


def _draw_chair_icon(c, x, y, w, d, back_side: str = "B", rotate_deg: int = 0):
    # Chair glyph: seat + backrest + armrests.
    seat_size = min(w, d) * 0.55
    seat_x = x + (w - seat_size) / 2.0
    seat_y = y + (d - seat_size) / 2.0
    c.rect(seat_x, seat_y, seat_size, seat_size, stroke=1, fill=1)

    back_thickness = max(seat_size * 0.18, 2.0)
    back_w = seat_size * 0.9
    back_h = back_thickness
    back_side = (back_side or "B").upper()
    if back_side == "T":
        back_x = seat_x + (seat_size - back_w) / 2.0
        back_y = seat_y + seat_size - back_thickness / 2.0
        c.rect(back_x, back_y, back_w, back_h, stroke=1, fill=1)
    elif back_side == "B":
        back_x = seat_x + (seat_size - back_w) / 2.0
        back_y = seat_y - back_thickness / 2.0
        c.rect(back_x, back_y, back_w, back_h, stroke=1, fill=1)
    elif back_side == "L":
        back_x = seat_x - back_thickness / 2.0
        back_y = seat_y + (seat_size - back_w) / 2.0
        c.rect(back_x, back_y, back_h, back_w, stroke=1, fill=1)
    else:  # "R"
        back_x = seat_x + seat_size - back_thickness / 2.0
        back_y = seat_y + (seat_size - back_w) / 2.0
        c.rect(back_x, back_y, back_h, back_w, stroke=1, fill=1)

    arm_thickness = max(seat_size * 0.12, 2.0)
    arm_len = seat_size * 0.7
    arm_gap = (seat_size - arm_len) / 2.0
    if rotate_deg % 180 == 90:
        top_arm_y = seat_y + seat_size - arm_thickness / 2.0
        bottom_arm_y = seat_y - arm_thickness / 2.0
        arm_x = seat_x + arm_gap
        c.rect(arm_x, top_arm_y, arm_len, arm_thickness, stroke=1, fill=1)
        c.rect(arm_x, bottom_arm_y, arm_len, arm_thickness, stroke=1, fill=1)
    else:
        left_arm_x = seat_x - arm_thickness / 2.0
        right_arm_x = seat_x + seat_size - arm_thickness / 2.0
        arm_y = seat_y + arm_gap
        c.rect(left_arm_x, arm_y, arm_thickness, arm_len, stroke=1, fill=1)
        c.rect(right_arm_x, arm_y, arm_thickness, arm_len, stroke=1, fill=1)


def _draw_one_page(c, room_w, room_d, items, title, label_w=None, label_d=None):
    page_w, page_h = landscape(A3)

    margin = 30
    header_h = 60
    dim_offset = 18
    dim_pad = dim_offset + 28
    dim_color = (0.5, 0.5, 0.5)
    floor_base = (0.85, 0.85, 0.85)
    floor_grid = (0.75, 0.75, 0.75)

    avail_w = page_w - margin * 2
    avail_h = page_h - margin * 2 - header_h

    draw_w = avail_w - dim_pad
    draw_h = avail_h - dim_pad

    s, scale_label = _calc_scale(room_w, room_d, draw_w, draw_h)

    rw = room_w * s
    rd = room_d * s

    total_w = rw + dim_pad
    total_h = rd + dim_pad

    origin_x = margin + (avail_w - total_w) / 2.0
    origin_y = margin + (avail_h - total_h) / 2.0

    ox = origin_x
    oy = origin_y

    # タイトル
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, page_h - margin - 22, title)
    c.setFont("Helvetica", 11)
    c.drawString(margin, page_h - margin - 44, scale_label + "  (unit: mm)")

    desk_size_counts = {}

    # 床ベース
    c.setFillColorRGB(*floor_base)
    c.setStrokeColorRGB(*floor_base)
    c.rect(ox, oy, rw, rd, stroke=0, fill=1)

    # 床グリッド（500mm）
    c.setStrokeColorRGB(*floor_grid)
    c.setLineWidth(0.5)
    step = 500 * s
    x = ox + step
    while x < ox + rw - 0.1:
        c.line(x, oy, x, oy + rd)
        x += step
    y = oy + step
    while y < oy + rd - 0.1:
        c.line(ox, y, ox + rw, y)
        y += step

    # 床枠
    c.setStrokeColorRGB(*dim_color)
    c.setLineWidth(_WALL_LINE_WIDTH)
    c.rect(ox, oy, rw, rd)

    # 床外側の囲い（10mm外側）
    off = _OUTER_OFFSET_MM * s
    c.setLineWidth(_OUTER_LINE_WIDTH)
    c.rect(ox - off, oy - off, rw + off * 2, rd + off * 2)
    c.setStrokeColorRGB(0, 0, 0)

    # 寸法線（外側）
    c.setLineWidth(1)
    dim_w = int(room_w if label_w is None else label_w)
    dim_d = int(room_d if label_d is None else label_d)
    _draw_dim_h(
        c,
        ox,
        oy + rd + dim_offset,
        ox + rw,
        f"W {dim_w}",
        text_y_offset=8,
        color=dim_color,
    )
    _draw_dim_v(
        c,
        ox + rw + dim_offset,
        oy,
        oy + rd,
        f"D {dim_d}",
        text_x_offset=6,
        color=dim_color,
    )

    # アイテム描画
    for it in items:
        if it.get("type") == "dim_h":
            x0 = it.get("x0", 0)
            y0 = it.get("y0", 0)
            x1 = it.get("x1", 0)
            text = it.get("text", "")
            _draw_dim_h(
                c,
                ox + x0 * s,
                oy + (room_d - y0) * s,
                ox + x1 * s,
                text,
                text_y_offset=8,
                color=dim_color,
            )
            continue
        if it.get("type") == "dim_v":
            x0 = it.get("x0", 0)
            y0 = it.get("y0", 0)
            y1 = it.get("y1", 0)
            text = it.get("text", "")
            _draw_dim_v(
                c,
                ox + x0 * s,
                oy + (room_d - y0) * s,
                oy + (room_d - y1) * s,
                text,
                text_x_offset=6,
                color=dim_color,
            )
            continue
        if it.get("type") == "door_arc":
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

            if swing == "out":
                if side == "T":
                    start_ang = 90
                    extent = 90
                    line_angs = (90, 180)
                elif side == "B":
                    start_ang = 270
                    extent = 90
                    line_angs = (270, 360)
                elif side == "L":
                    start_ang = 0
                    extent = 90
                    line_angs = (0, 90)
                else:  # "R"
                    start_ang = 180
                    extent = 90
                    line_angs = (180, 270)
            else:
                if side == "T":
                    start_ang = 270
                    extent = 90
                    line_angs = (270, 0)
                elif side == "B":
                    start_ang = 0
                    extent = 90
                    line_angs = (0, 90)
                elif side == "L":
                    start_ang = 270
                    extent = 90
                    line_angs = (270, 0)
                else:  # "R"
                    start_ang = 180
                    extent = 90
                    line_angs = (180, 270)

            flip_v_eff = flip_v if side in ("L", "R") else False
            flip_h_eff = flip_h if side in ("T", "B") else False
            # Keep door opening span fixed; move hinge to opposite edge on flip
            if side in ("T", "B") and flip_h_eff:
                cx = r.x + r.w
            if side in ("L", "R") and flip_v_eff:
                cy = r.y + r.d

            def _flip_angle(a):
                a = a % 360
                if flip_v_eff:
                    a = (360 - a) % 360
                if flip_h_eff:
                    a = (180 - a) % 360
                return a

            a1 = _flip_angle(line_angs[0])
            a2 = _flip_angle(line_angs[1])
            start_ang = _flip_angle(start_ang)
            extent = (a2 - a1) % 360
            if extent > 180:
                extent = 360 - extent
                start_ang = a2
            else:
                start_ang = a1

            cxp = ox + cx * s
            cyp = oy + (room_d - cy) * s
            rp = radius * s

            c.setStrokeColorRGB(*dim_color)
            c.setLineWidth(1.2)
            c.arc(cxp - rp, cyp - rp, cxp + rp, cyp + rp, start_ang, extent)

            line_angs_draw = [a1, a2] if (flip_v_eff or flip_h_eff) else list(line_angs)
            for ang in line_angs_draw:
                rad = math.radians(ang)
                ex = cxp + rp * math.cos(rad)
                ey = cyp + rp * math.sin(rad)
                c.line(cxp, cyp, ex, ey)
            c.setStrokeColorRGB(0, 0, 0)
            continue
        if it.get("type") == "block":
            r = it["rect"]
            x = ox + r.x * s
            y = oy + (room_d - (r.y + r.d)) * s
            w = r.w * s
            d = r.d * s
            c.setFillColorRGB(0.5, 0.5, 0.5)
            c.setStrokeColorRGB(0.5, 0.5, 0.5)
            c.setLineWidth(1.0)
            c.rect(x, y, w, d, stroke=1, fill=1)
            c.setFillColorRGB(0, 0, 0)
            c.setStrokeColorRGB(0, 0, 0)
            continue

        r = it["rect"]

        x = ox + r.x * s
        y = oy + (room_d - (r.y + r.d)) * s
        w = r.w * s
        d = r.d * s

        t = it.get("type", "")

        # 枠線
        if t == "desk":
            c.setLineWidth(0.8)
        elif t == "chair":
            c.setLineWidth(0.8)
        else:
            c.setLineWidth(1.2)

        # 図形
        if t == "chair":
            c.setFillColorRGB(1, 1, 1)
            _draw_chair_icon(c, x, y, w, d, it.get("chair_back", "B"), it.get("chair_rotate", 0))
            c.setFillColorRGB(0, 0, 0)
            continue
        else:
            c.setFillColorRGB(1, 1, 1)
            c.rect(x, y, w, d, stroke=1, fill=1)
            c.setFillColorRGB(0, 0, 0)

        cx = x + w / 2.0
        cy = y + d / 2.0

        # ===== デスク：薄グレー文字＋室内側寄せ＋2行 =====
        if t == "desk":
            long_mm = int(max(r.w, r.d))
            short_mm = int(min(r.w, r.d))
            size_text = f"{long_mm}×{short_mm}"
            desk_size_counts[size_text] = desk_size_counts.get(size_text, 0) + 1

            # 文字色：薄グレー
            c.setFillColorRGB(*_TEXT_GRAY)
            _draw_centered_two_lines_in_rect(
                c, x, y, w, d, cx, cy,
                "デスク", size_text,
                _JP_FONT, 9,
                "Helvetica", 8,
                gap=14, pad=7, auto_adjust=True
            )
            c.setFillColorRGB(0, 0, 0)
            continue

        # ===== 収納：薄グレー文字＋2行中央 =====
        if t == "storage_M":
            w_mm = int(r.w)
            d_mm = int(r.d)
            c.setFillColorRGB(*_TEXT_GRAY)
            _draw_centered_two_lines_in_rect(
                c, x, y, w, d, cx, cy,
                "収納", f"{w_mm}×{d_mm}",
                _JP_FONT, 9,
                "Helvetica", 8,
                gap=14, pad=7, auto_adjust=True
            )
            c.setFillColorRGB(0, 0, 0)
            continue

        # ===== 複合機：薄グレー文字＋2行中央 =====
        if t == "mfp":
            w_mm = int(r.w)
            d_mm = int(r.d)
            c.setFillColorRGB(*_TEXT_GRAY)
            _draw_centered_two_lines_in_rect(
                c, x, y, w, d, cx, cy,
                "複合機", f"{w_mm}×{d_mm}",
                _JP_FONT, 9,
                "Helvetica", 8,
                gap=14, pad=7, auto_adjust=True
            )
            c.setFillColorRGB(0, 0, 0)
            continue

        # その他設備：薄グレーで左上（必要なら後で中央2行化）
        w_mm = int(r.w)
        d_mm = int(r.d)
        base = it.get("label", "")
        label = f"{base} {w_mm}×{d_mm}".strip()
        c.setFillColorRGB(*_TEXT_GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(x + 2, y + d - 12, label)
        c.setFillColorRGB(0, 0, 0)

    # 凡例（デスクサイズ集約）※凡例は読みやすさ優先で黒
    legend_x = page_w - margin - 220
    legend_y = page_h - margin - 24
    _draw_legend(c, legend_x, legend_y, desk_size_counts)


def export_multi_layout_pdf(out_path: str, room_w: int, room_d: int, pages: list, label_w: int = None, label_d: int = None):
    page_w, page_h = landscape(A3)
    c = canvas.Canvas(out_path, pagesize=(page_w, page_h))

    for p in pages:
        _draw_one_page(c, room_w, room_d, p["items"], p["title"], label_w=label_w, label_d=label_d)
        c.showPage()

    c.save()
