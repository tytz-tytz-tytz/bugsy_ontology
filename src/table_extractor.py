import re
from pathlib import Path
from typing import Dict, List

import fitz  # PyMuPDF
import pandas as pd
from PIL import Image
import torch
from transformers import AutoProcessor, TableTransformerForObjectDetection, DetrForObjectDetection

# регулярка для поиска подписей
TABLE_RE = re.compile(r"^\s*Табл(?:ица)?\s*(\d+)\s*[—–\-:\.]?.*", re.IGNORECASE)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# модель для нахождения таблиц
det_model_name = "microsoft/table-transformer-detection"
det_processor = AutoProcessor.from_pretrained(det_model_name)
det_model = TableTransformerForObjectDetection.from_pretrained(det_model_name).to(DEVICE)

# модель для структуры таблиц (через DetrForObjectDetection)
struct_model_name = "microsoft/table-transformer-structure-recognition"
struct_processor = AutoProcessor.from_pretrained(struct_model_name)
struct_model = DetrForObjectDetection.from_pretrained(struct_model_name).to(DEVICE)


def _detect_tables(image: Image.Image, score_thr: float = 0.9):
    """Находим таблицы на изображении страницы через Table Transformer Detection."""
    inputs = det_processor(images=image, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        outputs = det_model(**inputs)
    target_sizes = torch.tensor([image.size[::-1]]).to(DEVICE)  # (h, w)
    results = det_processor.post_process_object_detection(
        outputs, target_sizes=target_sizes, threshold=score_thr
    )[0]

    tables = []
    for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
        if det_model.config.id2label[label.item()] == "table":
            box = [round(x.item(), 2) for x in box]
            tables.append((score.item(), box))
    return tables


def _extract_structure(image: Image.Image, bbox: List[float]) -> pd.DataFrame:
    """Извлекаем структуру таблицы (с учётом colspan/rowspan)."""
    x0, y0, x1, y1 = map(int, bbox)
    crop = image.crop((x0, y0, x1, y1))

    inputs = struct_processor(images=crop, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        outputs = struct_model(**inputs)

    # target_sizes должен быть torch.Tensor
    target_sizes = torch.tensor([crop.size[::-1]], device=outputs.logits.device)
    result = struct_processor.post_process_object_detection(outputs, target_sizes=target_sizes)[0]

    if "cells" not in result or len(result["cells"]) == 0:
        return pd.DataFrame()

    # размеры таблицы
    max_row = max(cell["row"] + cell.get("rowspan", 1) - 1 for cell in result["cells"])
    max_col = max(cell["col"] + cell.get("colspan", 1) - 1 for cell in result["cells"])
    table = [["" for _ in range(max_col + 1)] for _ in range(max_row + 1)]

    # заполняем с учётом colspan/rowspan
    for cell in result["cells"]:
        r, c = cell["row"], cell["col"]
        rs = cell.get("rowspan", 1)
        cs = cell.get("colspan", 1)
        txt = cell.get("text", "").strip()

        for rr in range(r, r + rs):
            for cc in range(c, c + cs):
                table[rr][cc] = txt

    return pd.DataFrame(table)


def extract_tables(
    pdf_path: Path,
    chunks_csv: Path,
    tables_dir: Path,
    index_csv: Path,
    *,
    dpi: int = 300
):
    print("📊 Извлекаем таблицы через Table Transformer (с поддержкой colspan/rowspan)...")
    doc = fitz.open(pdf_path)
    chunks = pd.read_csv(chunks_csv)

    # ищем подписи "Таблица N"
    captions: Dict[int, dict] = {}
    for _, row in chunks.iterrows():
        text = str(row.get("text", "") or "")
        m = TABLE_RE.match(text)
        if not m:
            continue
        tbl_num = int(m.group(1))
        if tbl_num in captions:
            continue
        captions[tbl_num] = {
            "page": int(row["page_start"]),
            "text": text,
            "chunk_id": row.get("chunk_id"),
        }

    tables_dir.mkdir(parents=True, exist_ok=True)
    index_records: List[dict] = []

    for tbl_num, cap in sorted(captions.items()):
        page_no = cap["page"]
        page = doc[page_no - 1]

        # рендер страницы
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        print(f"🔍 Таблица {tbl_num} (стр. {page_no})")
        detections = _detect_tables(img)

        if not detections:
            print(f"⚠️ Таблица {tbl_num} не найдена")
            continue

        # берём bbox с наибольшим score
        detections.sort(key=lambda x: x[0], reverse=True)
        score, bbox = detections[0]

        # извлекаем структуру
        df = _extract_structure(img, bbox)
        if df.empty:
            print(f"⚠️ Таблица {tbl_num} — не удалось извлечь структуру")
            continue

        # сохраняем
        out_path = tables_dir / f"table_{tbl_num:04d}.csv"
        df.to_csv(out_path, index=False, header=False, encoding="utf-8-sig")

        index_records.append({
            "table_id": f"table_{tbl_num:04d}",
            "table_number": tbl_num,
            "page": page_no,
            "caption_text": cap["text"],
            "caption_chunk": cap.get("chunk_id"),
            "file": str(out_path),
            "rows": int(df.shape[0]),
            "cols": int(df.shape[1]),
            "score": score
        })

        print(f"✅ table_{tbl_num:04d}: {df.shape[0]}×{df.shape[1]} → {out_path}")

    if index_records:
        pd.DataFrame(index_records).to_csv(index_csv, index=False, encoding="utf-8-sig")
        print(f"📑 Индекс сохранён: {index_csv}")
    else:
        print("⚠️ Ни одной таблицы не извлечено")
