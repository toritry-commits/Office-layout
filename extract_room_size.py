import re
import sys
import argparse

import pdfplumber
import fitz  # PyMuPDF


def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.replace("：", ":").replace("×", "x").replace("㎜", "mm").replace("ｍｍ", "mm")
    return s


def _extract_text_first_page(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        txt = page.extract_text() or ""
    return _norm(txt)


def _find_candidates_from_text(txt: str):
    cands = []

    # W/D or 幅/奥行
    w_list = [int(x) for x in re.findall(r"\bW\s*[:=]?\s*(\d{3,6})\s*mm?\b", txt, flags=re.IGNORECASE)]
    d_list = [int(x) for x in re.findall(r"\bD\s*[:=]?\s*(\d{3,6})\s*mm?\b", txt, flags=re.IGNORECASE)]
    w_list += [int(x) for x in re.findall(r"(?:幅|間口)\s*[:=]?\s*(\d{3,6})\s*mm?\b", txt)]
    d_list += [int(x) for x in re.findall(r"(?:奥行|奥行き|行き)\s*[:=]?\s*(\d{3,6})\s*mm?\b", txt)]

    if w_list and d_list:
        cands.append(("explicit_WD", max(w_list), max(d_list), 0.95))

    # 5000x4000 形式
    for a, b in re.findall(r"\b(\d{3,6})\s*[xX]\s*(\d{3,6})\b", txt):
        a, b = int(a), int(b)
        if 2000 <= a <= 20000 and 2000 <= b <= 20000:
            cands.append(("AxB", a, b, 0.80))

    return cands


def _page_has_images(pdf_path: str) -> bool:
    doc = fitz.open(pdf_path)
    page = doc[0]
    has = len(page.get_images(full=True)) > 0
    doc.close()
    return has


def _largest_rect_ratio_from_vectors(pdf_path: str):
    """
    ベクタ図形から最大矩形を探して比率(w/h)を返す（補助）
    """
    doc = fitz.open(pdf_path)
    page = doc[0]
    drawings = page.get_drawings()

    best = None  # (area, w, h)
    for d in drawings:
        for it in d.get("items", []):
            if it and it[0] == "re":
                rect = it[1]
                w = abs(rect.x1 - rect.x0)
                h = abs(rect.y1 - rect.y0)
                area = w * h
                if area <= 0:
                    continue
                if best is None or area > best[0]:
                    best = (area, w, h)

    doc.close()

    if not best:
        return None
    _, w, h = best
    if h == 0:
        return None
    return w / h


def _ocr_first_page_text(pdf_path: str, dpi: int = 300) -> str:
    """
    画像PDF向け：1ページ目を画像化→OCRして文字列を得る
    事前に tesseract + pytesseract が必要
    """
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        raise RuntimeError("pytesseract / Pillow がありません。OCR手順のインストールを先に実行してください。")

    doc = fitz.open(pdf_path)
    page = doc[0]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    doc.close()

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    txt = pytesseract.image_to_string(img, lang="jpn+eng")
    return _norm(txt)


def decide_room_size(pdf_path: str, use_ocr: bool = False, debug: bool = False):
    txt = _extract_text_first_page(pdf_path)

    if debug:
        print("[debug] extracted_text_len =", len(txt))
        print("[debug] has_images =", _page_has_images(pdf_path))

    cands = _find_candidates_from_text(txt)
    ratio = _largest_rect_ratio_from_vectors(pdf_path)

    if debug:
        print("[debug] vector_ratio =", ratio)
        print("[debug] text_candidates =", cands[:10])

    # 文字抽出で候補がない & OCR指定ならOCRして再挑戦
    if (not cands) and use_ocr:
        if debug:
            print("[debug] running OCR...")
        ocr_txt = _ocr_first_page_text(pdf_path)
        if debug:
            print("[debug] ocr_text_len =", len(ocr_txt))
        cands = _find_candidates_from_text(ocr_txt)
        txt = ocr_txt  # デバッグ表示用に置き換え

    best = None  # (score, src, w, d, note)
    for src, a, b, base_conf in cands:
        for w, d in [(a, b), (b, a)]:
            if not (2000 <= w <= 20000 and 2000 <= d <= 20000):
                continue

            score = base_conf
            if ratio:
                r = w / d
                diff = abs(r - ratio)
                score += max(0.0, 0.15 - min(0.15, diff * 0.10))

            note = f"src={src}, base={base_conf:.2f}, ratio={'%.2f'%ratio if ratio else 'n/a'}"
            if best is None or score > best[0]:
                best = (score, src, w, d, note)

    return best, txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, help="input pdf path")
    ap.add_argument("--ocr", action="store_true", help="use OCR if text extraction fails")
    ap.add_argument("--debug", action="store_true", help="print debug info")
    args = ap.parse_args()

    best, txt = decide_room_size(args.pdf, use_ocr=args.ocr, debug=args.debug)

    if best is None:
        print("FAILED: room size not detected.")
        print("Next:")
        print("  1) --debug を付けて状況確認")
        print("  2) 画像PDFなら --ocr を使う（OCR環境が必要）")
        sys.exit(1)

    score, src, w, d, note = best
    print("OK: room_w =", w, "room_d =", d)
    print("confidence:", round(score, 3), "(", note, ")")

    head = (txt[:400] + "...") if len(txt) > 400 else txt
    print("\n--- extracted text head ---\n" + head)


if __name__ == "__main__":
    main()
