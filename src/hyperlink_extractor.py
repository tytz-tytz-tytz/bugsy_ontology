"""
hyperlink_extractor.py

Модуль для извлечения ссылок (hyperlink_target) из chunks.csv.

Что делает:
- читает chunks.csv
- создаёт ReferenceTarget / Url-ноды
- связывает Chunk → Target через LINKS_TO

Логика:
- если hyperlink_target — число → ReferenceTarget(id="ref_<number>")
- если hyperlink_target — строка, начинающаяся с http → Url
- если пусто → пропускаем

Выход:
- output/nodes_hyperlinks.csv
- output/edges_hyperlinks.csv
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict


class HyperlinkExtractor:
    """
    Извлекает hyperlink_target из чанков и строит граф ссылок.
    """

    def __init__(self, chunks_csv_path: Path):
        if not chunks_csv_path.exists():
            raise FileNotFoundError(f"Файл не найден: {chunks_csv_path}")

        self.chunks_csv_path = chunks_csv_path
        self.df = pd.read_csv(chunks_csv_path)

        required = [
            "chunk_id", "hyperlink_target",
            "page_start", "page_end", "text"
        ]
        missing = [c for c in required if c not in self.df.columns]
        if missing:
            raise ValueError(f"В chunks.csv отсутствуют колонки: {missing}")

    # 1. Классифицируем target
    @staticmethod
    def classify_target(raw):
        """
        Возвращает:
        {
          "type": "reference" | "url" | "none",
          "value": <string>
        }
        """

        if raw is None or pd.isna(raw):
            return {"type": "none", "value": None}

        raw = str(raw).strip()
        if raw == "":
            return {"type": "none", "value": None}

        # URL
        if raw.startswith("http://") or raw.startswith("https://"):
            return {"type": "url", "value": raw}

        # Числовая ссылка (обычно ссылка на страницу или примечание)
        if raw.isdigit():
            return {"type": "reference", "value": raw}

        # fallback — считаем числом, если возможно
        try:
            int(raw)
            return {"type": "reference", "value": raw}
        except:
            pass

        # fallback — считаем URL
        return {"type": "url", "value": raw}

    # 2. Основной метод: создание нод и связей
    def build(self):
        hyperlink_nodes: List[Dict] = []
        edges: List[Dict] = []

        seen_refs = set()
        seen_urls = set()

        for _, row in self.df.iterrows():
            chunk_id = row["chunk_id"]
            node_chunk_id = f"chunk_{chunk_id}"

            raw = row["hyperlink_target"]
            classified = self.classify_target(raw)
            h_type = classified["type"]
            value = classified["value"]

            if h_type == "none":
                continue

            # CASE 1: ReferenceTarget
            if h_type == "reference":
                ref_id = f"ref_{value}"

                # Добавляем ноду только один раз
                if ref_id not in seen_refs:
                    hyperlink_nodes.append({
                        "id": ref_id,
                        "label": "ReferenceTarget",
                        "value": value,
                    })
                    seen_refs.add(ref_id)

                edges.append({
                    "source": node_chunk_id,
                    "target": ref_id,
                    "relation": "LINKS_TO"
                })

            # CASE 2: Url
            elif h_type == "url":
                # Уникальный ID для URL
                import hashlib
                md5 = hashlib.md5(value.encode("utf-8")).hexdigest()[:12]
                url_id = f"url_{md5}"

                if url_id not in seen_urls:
                    hyperlink_nodes.append({
                        "id": url_id,
                        "label": "Url",
                        "value": value,
                    })
                    seen_urls.add(url_id)

                edges.append({
                    "source": node_chunk_id,
                    "target": url_id,
                    "relation": "LINKS_TO"
                })

        return pd.DataFrame(hyperlink_nodes), pd.DataFrame(edges)

# Вспомогательная функция для вызова из main.py
def build_hyperlinks(chunks_csv: str, out_nodes: str, out_edges: str):
    extractor = HyperlinkExtractor(Path(chunks_csv))
    nodes_df, edges_df = extractor.build()

    nodes_df.to_csv(out_nodes, index=False)
    edges_df.to_csv(out_edges, index=False)

    print(f"Ноды ReferenceTarget/Url сохранены в {out_nodes}")
    print(f"Связи LINKS_TO сохранены в {out_edges}")


if __name__ == "__main__":
    build_hyperlinks(
        chunks_csv="output/chunks.csv",
        out_nodes="output/nodes_hyperlinks.csv",
        out_edges="output/edges_hyperlinks.csv"
    )