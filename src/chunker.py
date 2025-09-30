import numpy as np
import re
from typing import List, Dict

def group_into_chunks(spans: List[Dict]) -> List[Dict]:
    chunks = []
    if not spans:
        return chunks

    current_chunk = {
        "lines": [spans[0]],
        "page_start": spans[0]["page"],
        "page_end": spans[0]["page"]
    }

    i = 1
    while i < len(spans):
        prev = spans[i - 1]
        curr = spans[i]

        vertical_gap = 0
        if prev.get("bbox") and curr.get("bbox"):
            vertical_gap = curr["bbox"][1] - prev["bbox"][3]

        same_style = (
            curr["size"] == prev["size"] and
            curr["bold"] == prev["bold"] and
            curr["italic"] == prev["italic"] and
            abs(curr["color"] - prev["color"]) < 10 and
            curr["font"] == prev["font"]
        )

        max_gap = 10 if curr["size"] >= 13 else 6

        # объединяем маркер списка с текстом
        if prev["text"].strip() in ("•", "-", "–", "·", "◦", "*"):
            current_chunk["lines"].append(curr)
            current_chunk["page_end"] = curr["page"]
            i += 1
            continue

        if not same_style or vertical_gap > max_gap:
            chunks.append(current_chunk)
            current_chunk = {
                "lines": [curr],
                "page_start": curr["page"],
                "page_end": curr["page"]
            }
        else:
            current_chunk["lines"].append(curr)
            current_chunk["page_end"] = curr["page"]

        i += 1

    chunks.append(current_chunk)
    return chunks


def classify_chunk(chunk: Dict) -> str:
    lines = chunk["lines"]
    full_text = " ".join([l["text"] for l in lines]).strip()
    avg_size = np.mean([l["size"] for l in lines])
    is_bold = any(l["bold"] for l in lines)
    is_short_heading = len(full_text) < 160

    has_reference = any(
        "рис" in l["text"].lower() or
        "табл" in l["text"].lower() or
        "см." in l["text"].lower()
        for l in lines
    )

    unordered_markers = ("•", "-", "–", "·", "◦", "*")
    starts_with_unordered = full_text.lstrip().startswith(unordered_markers)

    ordered_pattern = re.compile(r"^(\d+[.)]|[a-zа-яA-Z]\))\s")
    starts_with_ordered = ordered_pattern.match(full_text.lstrip()) is not None

    if starts_with_ordered:
        return "ordered_list_item"
    elif starts_with_unordered:
        return "list_item"
    elif avg_size >= 16 and is_bold and is_short_heading:
        return "section_h1"
    elif 13.5 <= avg_size < 16 and is_bold and is_short_heading:
        return "section_h2"
    elif 12 <= avg_size < 13.5 and is_bold and is_short_heading:
        return "section_h3"
    elif has_reference:
        return "reference"
    elif avg_size < 12 and not is_bold and len(full_text) < 100:
        return "caption"
    else:
        return "paragraph"


def process_structure(spans: List[Dict]) -> List[Dict]:
    chunks_raw = group_into_chunks(spans)
    result = []

    for idx, chunk in enumerate(chunks_raw):
        lines = chunk["lines"]
        full_text = " ".join([l["text"] for l in lines]).strip()
        avg_size = np.mean([l["size"] for l in lines])
        chunk_type = classify_chunk(chunk)

        # собираем все ссылки внутри чанка
        hyperlinks = [l.get("hyperlink_target") for l in lines if l.get("hyperlink_target")]
        hyperlink_target = hyperlinks[0] if hyperlinks else None

        result.append({
            "chunk_id": f"ch{idx:04d}",
            "page_start": chunk["page_start"],
            "page_end": chunk["page_end"],
            "type": chunk_type,
            "font_size": round(avg_size, 2),
            "text": full_text,
            "bbox": lines[0]["bbox"] if lines and lines[0].get("bbox") else None,
            "hyperlink_target": hyperlink_target
        })

    result = group_lists(result)
    return result


def group_lists(chunks: List[Dict]) -> List[Dict]:
    grouped = []
    i = 0
    while i < len(chunks):
        if chunks[i]["type"] in ("list_item", "ordered_list_item"):
            list_items = [chunks[i]]
            current_type = chunks[i]["type"]
            i += 1
            while i < len(chunks) and chunks[i]["type"] == current_type:
                list_items.append(chunks[i])
                i += 1
            grouped.append({
                "chunk_id": list_items[0]["chunk_id"],
                "page_start": list_items[0]["page_start"],
                "page_end": list_items[-1]["page_end"],
                "type": "ordered_list_block" if current_type == "ordered_list_item" else "list_block",
                "font_size": list_items[0]["font_size"],
                "text": "\n".join([item["text"] for item in list_items]),
                "items": [item["text"] for item in list_items],
                "bbox": list_items[0]["bbox"],
                "hyperlink_target": None
            })
        else:
            grouped.append(chunks[i])
            i += 1
    return grouped


def merge_adjacent_headings(chunks: List[Dict]) -> List[Dict]:
    merged = []
    i = 0
    while i < len(chunks):
        current = chunks[i]
        if current["type"].startswith("section"):
            j = i + 1
            while j < len(chunks) and chunks[j]["type"] == current["type"]:
                current["text"] += " " + chunks[j]["text"]
                current["page_end"] = chunks[j]["page_end"]
                j += 1
            merged.append(current)
            i = j
        else:
            merged.append(current)
            i += 1
    return merged
