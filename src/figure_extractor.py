# src/figure_extractor.py
import re
from pathlib import Path
from typing import Optional, Tuple, List, Any, Dict

import fitz
import pandas as pd


CAPTION_RE = re.compile(
    r"^\s*Рис(?:\.|унок)?\s*(?:№\s*)?(\d+)\s*(?:[—–\-:\.])?.*",
    re.IGNORECASE
)
STAR_ONLY_LINE = re.compile(r"^\s*\*+\s*$")


# ---------------- utils ----------------

def _safe_bbox(b: Any) -> Optional[fitz.Rect]:
    if not b:
        return None
    if isinstance(b, (list, tuple)) and len(b) == 4:
        return fitz.Rect(b)
    if isinstance(b, str):
        try:
            tup = eval(b, {}, {})
            if isinstance(tup, (list, tuple)) and len(tup) == 4:
                return fitz.Rect(tup)
        except Exception:
            return None
    return None


def _sanitize_star_text(spans: List[dict]) -> List[dict]:
    """Убираем строки '*' (чтобы не мешали подписи)."""
    cleaned = []
    for sp in spans:
        t = sp.get("text", "")
        if t and STAR_ONLY_LINE.match(t):
            continue
        cleaned.append(sp)
    return cleaned


def _line_text_and_bbox(line: dict) -> Tuple[str, Optional[fitz.Rect]]:
    spans = _sanitize_star_text(line.get("spans", []) or [])
    txt = "".join(sp.get("text", "") for sp in spans if sp.get("text"))
    rect: Optional[fitz.Rect] = None
    for sp in spans:
        bb = sp.get("bbox")
        if bb and len(bb) == 4:
            r = fitz.Rect(bb)
            rect = r if rect is None else rect | r
    return (txt, rect)


def _closest_nonstar_line_above(page: fitz.Page, y0: float) -> Optional[fitz.Rect]:
    raw = page.get_text("rawdict")
    best: Optional[fitz.Rect] = None
    best_dist = float("inf")
    for blk in raw.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for line in blk.get("lines", []) or []:
            txt, rect = _line_text_and_bbox(line)
            if not rect or rect.y1 > y0:
                continue
            if not txt.strip():
                continue
            dist = y0 - rect.y1
            if 0 <= dist < best_dist:
                best_dist = dist
                best = rect
    return best


def _pick_image_candidate(raw_blocks: List[dict],
                          caption_y0: float,
                          *,
                          min_size: int,
                          min_area: int,
                          max_aspect: float,
                          below_tol: float = 8.0
                          ) -> Optional[Tuple[dict, fitz.Rect, float, float]]:
    candidate = None
    min_distance = float("inf")
    for block in raw_blocks:
        if block.get("type") != 1:
            continue
        bb = block.get("bbox")
        if not bb or len(bb) != 4:
            continue
        bbox = fitz.Rect(bb)
        w, h = bbox.width, bbox.height
        area = w * h
        if w < min_size or h < min_size:
            continue
        if area < min_area:
            continue
        aspect = w / h if h > 0 else 999.0
        if aspect > max_aspect or aspect < 1.0 / max_aspect:
            continue

        if bbox.y1 > caption_y0 + below_tol:
            continue

        dist = max(0.0, caption_y0 - bbox.y1)
        if dist < min_distance:
            min_distance = dist
            candidate = (block, bbox, w, h)
    return candidate


# -------- special caption finder --------

def _find_caption_by_spans(page: fitz.Page) -> Optional[Tuple[int, fitz.Rect, str]]:
    """Ищем подпись 'Рисунок N' по спанам, даже если текст порезан."""
    raw = page.get_text("rawdict")
    spans_all: List[Tuple[str, fitz.Rect]] = []
    for blk in raw.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for line in blk.get("lines", []):
            spans = _sanitize_star_text(line.get("spans", []) or [])
            for sp in spans:
                t = sp.get("text", "")
                if not t:
                    continue
                bb = sp.get("bbox")
                rect = fitz.Rect(bb) if bb and len(bb) == 4 else None
                if rect:
                    spans_all.append((t, rect))
    if not spans_all:
        return None

    full_text = "".join(t for t, _ in spans_all)
    m = CAPTION_RE.search(full_text)
    if not m:
        return None
    try:
        fig_num = int(m.group(1))
    except Exception:
        return None

    start, end = m.span(1)
    taken: List[fitz.Rect] = []
    pos = 0
    for t, r in spans_all:
        nxt = pos + len(t)
        if nxt > start and pos < end:
            taken.append(r)
        pos = nxt
    if not taken:
        return None
    bbox = taken[0]
    for r in taken[1:]:
        bbox |= r
    return fig_num, bbox, m.group(0)


# ---------------- main ----------------

def extract_figures(
    pdf_path: Path,
    chunks_csv: Path,
    output_dir: Path,
    figures_csv: Path,
    *,
    min_size: int = 50,
    min_area: int = 10_000,
    max_aspect: float = 10.0,
    render_scale: float = 4.1667,
    band_side_margin: float = 20.0,
    fallback_min_h: float = 120.0
) -> None:
    print("🖼 Извлекаем рисунки из PDF...")
    doc = fitz.open(pdf_path)
    chunks = pd.read_csv(chunks_csv)
    output_dir.mkdir(parents=True, exist_ok=True)

    figures = []
    seen_ids = set()

    # подписи из chunks
    captions: Dict[int, dict] = {}
    for _, row in chunks.iterrows():
        text = str(row.get("text", "") or "")
        m = CAPTION_RE.match(text)
        if not m:
            continue
        fig_num = int(m.group(1))
        if fig_num in captions:
            continue
        page_num1 = int(row["page_start"])
        bbox = _safe_bbox(row.get("bbox"))
        if not bbox:
            continue
        captions[fig_num] = {
            "page": page_num1,
            "bbox": bbox,
            "text": text,
            "chunk_id": row.get("chunk_id"),
            "source": "chunks"
        }

    # fallback поиск подписи по спанам
    for special in (165, 207):
        if special in captions:
            continue
        for page_idx in range(len(doc)):
            res = _find_caption_by_spans(doc[page_idx])
            if res and res[0] == special:
                captions[special] = {
                    "page": page_idx + 1,
                    "bbox": res[1],
                    "text": res[2],
                    "chunk_id": None,
                    "source": "spans"
                }
                print(f"🔍 Нашёл подпись для {special} через спаны (стр. {page_idx+1})")
                break

    # обрабатываем подписи
    for fig_num, cap in sorted(captions.items()):
        figure_id = f"fig_{fig_num:04d}"
        if figure_id in seen_ids:
            continue

        page_num1 = cap["page"]
        page = doc[page_num1 - 1]
        caption_bbox = cap["bbox"]
        caption_y0 = caption_bbox.y0

        base_path = output_dir / figure_id
        saved_path = None
        saved_ext = None
        saved_w = None
        saved_h = None
        used_bbox = None

        raw = page.get_text("rawdict")

        # особые фигуры: сразу fallback широкой полосой
        if fig_num in (165, 207):
            y_top = max(page.rect.y0, caption_y0 - 500)  # фикс. высота 500 px
            clip = fitz.Rect(
                page.rect.x0 + band_side_margin,
                y_top,
                page.rect.x1 - band_side_margin,
                caption_y0
            )
            try:
                matrix = fitz.Matrix(render_scale, render_scale)
                pix = page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
                out_path = base_path.with_suffix(".png")
                pix.save(out_path)
                saved_path, saved_ext = out_path, "png"
                saved_w, saved_h = pix.width, pix.height
                used_bbox = clip
                print(f"🖼 {figure_id}: force-fallback (стр. {page_num1})")
            except Exception as e:
                print(f"❌ {figure_id}: ошибка force-fallback на стр. {page_num1}: {e}")
                continue
        else:
            # обычная логика
            cand = _pick_image_candidate(
                raw.get("blocks", []),
                caption_y0,
                min_size=min_size,
                min_area=min_area,
                max_aspect=max_aspect
            )

            if cand:
                block, bbox, w, h = cand
                used_bbox = bbox
                xref = block.get("xref")
                try:
                    if xref:
                        info = doc.extract_image(xref)
                        img_bytes = info["image"]
                        ext = (info.get("ext") or "png").lower()
                        saved_w = int(info.get("width", w))
                        saved_h = int(info.get("height", h))
                        out_path = base_path.with_suffix(f".{ext}")
                        with open(out_path, "wb") as f:
                            f.write(img_bytes)
                        saved_path, saved_ext = out_path, ext
                        print(f"✅ {figure_id}: xref (стр. {page_num1})")
                    else:
                        matrix = fitz.Matrix(render_scale, render_scale)
                        pix = page.get_pixmap(matrix=matrix, clip=bbox, alpha=False)
                        out_path = base_path.with_suffix(".png")
                        pix.save(out_path)
                        saved_path, saved_ext = out_path, "png"
                        saved_w, saved_h = pix.width, pix.height
                        print(f"✅ {figure_id}: bbox-рендер (стр. {page_num1})")
                except Exception:
                    cand = None

            if not cand:
                top_line = _closest_nonstar_line_above(page, caption_y0)
                y_top = top_line.y1 if top_line is not None else page.rect.y0 + 36.0
                if caption_y0 - y_top < fallback_min_h:
                    y_top = max(page.rect.y0 + 12.0, caption_y0 - fallback_min_h)
                clip = fitz.Rect(
                    page.rect.x0 + band_side_margin,
                    y_top,
                    page.rect.x1 - band_side_margin,
                    caption_y0
                )
                try:
                    matrix = fitz.Matrix(render_scale, render_scale)
                    pix = page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
                    out_path = base_path.with_suffix(".png")
                    pix.save(out_path)
                    saved_path, saved_ext = out_path, "png"
                    saved_w, saved_h = pix.width, pix.height
                    used_bbox = clip
                    print(f"🖼 {figure_id}: fallback (стр. {page_num1})")
                except Exception as e:
                    print(f"❌ {figure_id}: fallback ошибка на стр. {page_num1}: {e}")
                    continue

        figures.append({
            "figure_id": figure_id,
            "figure_number": fig_num,
            "page": page_num1,
            "caption_chunk": cap.get("chunk_id"),
            "caption_text": cap.get("text"),
            "file": str(saved_path),
            "saved_ext": saved_ext,
            "bbox": (used_bbox.x0, used_bbox.y0, used_bbox.x1, used_bbox.y1) if used_bbox else None,
            "width_px": saved_w,
            "height_px": saved_h,
            "anchor": "caption",
            "anchor_y0": caption_y0,
        })
        seen_ids.add(figure_id)

    pd.DataFrame(figures).to_csv(figures_csv, index=False, encoding="utf-8-sig")
    print(f"✅ Извлечено рисунков: {len(figures)}. Метаданные: {figures_csv}")
