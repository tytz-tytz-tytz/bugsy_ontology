import fitz

def parse_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    structure = []

    for page_num, page in enumerate(doc):
        # собираем все ссылки на странице
        links = page.get_links()

        text_dict = page.get_text("dict")

        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue

                    span_rect = fitz.Rect(*span["bbox"])
                    target_page = None

                    # проверяем: попадает ли ссылка в bbox текущего span
                    for link in links:
                        link_rect = fitz.Rect(link["from"])
                        if link_rect.intersects(span_rect):
                            if link["kind"] == 1:  # внутренняя ссылка
                                target_page = link.get("page")
                            elif link["kind"] == 2:  # внешняя ссылка (URL)
                                target_page = link.get("uri")

                    structure.append({
                        "page": page_num + 1,
                        "text": text,
                        "bbox": span.get("bbox"),
                        "font": span.get("font"),
                        "size": span.get("size"),
                        "color": span.get("color"),
                        "flags": span.get("flags"),
                        "bold": bool(span.get("flags", 0) & 2),
                        "italic": bool(span.get("flags", 0) & 1),
                        "hyperlink_target": target_page  # внутренняя страница или URL
                    })

    return structure