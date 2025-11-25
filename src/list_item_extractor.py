"""
list_item_extractor.py

Модуль для извлечения пунктов списков из chunks.csv.

Что делает:
- находит чанки, у которых есть список (type=list_block / ordered_list_block
  или непустое поле items)
- парсит поле items (строка с Python-списком) в отдельные элементы
- создаёт:
    - ноды ListItem
    - связи Chunk -> ListItem (HAS_ITEM)

Выход:
- output/nodes_list_items.csv
- output/edges_list_items.csv
"""
import ast
from pathlib import Path
from typing import List, Dict

import pandas as pd


class ListItemExtractor:
    """
    Класс для извлечения пунктов списков из chunks.csv.
    """

    def __init__(self, chunks_csv_path: Path):
        if not chunks_csv_path.exists():
            raise FileNotFoundError(f"Файл не найден: {chunks_csv_path}")

        self.chunks_csv_path = chunks_csv_path
        self.df = pd.read_csv(chunks_csv_path)

        # Проверяем, что нужные колонки есть
        required_cols = [
            "chunk_id", "page_start", "page_end",
            "type", "font_size", "text", "bbox",
            "hyperlink_target", "items"
        ]
        missing = [c for c in required_cols if c not in self.df.columns]
        if missing:
            raise ValueError(f"В chunks.csv отсутствуют необходимые колонки: {missing}")

    # 1. Условие: какие чанки считаем списками
    @staticmethod
    def is_list_chunk(row) -> bool:
        """
        Возвращает True, если чанк содержит список.

        Критерии:
        - type == 'list_block' или 'ordered_list_block'
        ИЛИ
        - поле items не пустое (NaN не считается).
        """
        t = str(row["type"]).lower()
        has_list_type = t in ("list_block", "ordered_list_block")

        items_val = row["items"]
        has_items = not (pd.isna(items_val) or str(items_val).strip() == "")

        return has_list_type or has_items

    # 2. Парсинг items
    @staticmethod
    def parse_items(items_raw) -> List[str]:
        """
        Парсит строку items в список строк.
        Ожидаемый формат: "['• пункт1', '• пункт2']"

        Если парсинг не удался, возвращает пустой список.
        """
        if pd.isna(items_raw):
            return []

        s = str(items_raw).strip()
        if not s:
            return []

        try:
            parsed = ast.literal_eval(s)
            # На всякий случай приводим к списку строк
            result = []
            for it in parsed:
                if it is None:
                    continue
                txt = str(it).strip()
                if not txt:
                    continue
                # убираем маркер "• " в начале, если есть
                if txt.startswith("•"):
                    txt = txt.lstrip("•").strip()
                result.append(txt)
            return result
        except Exception:
            # Если что-то пошло не так - не падаем, просто возвращаем пустой список
            return []

    # 3. Основной метод: построение ListItem-нoded и связей
    def build(self):
        listitem_nodes: List[Dict] = []
        edges: List[Dict] = []

        list_chunks = self.df[self.df.apply(self.is_list_chunk, axis=1)].copy()

        print(f"Найдено чанков со списками: {len(list_chunks)}")

        for _, row in list_chunks.iterrows():
            chunk_id = row["chunk_id"]
            node_chunk_id = f"chunk_{chunk_id}"
            items_raw = row["items"]

            items = self.parse_items(items_raw)
            if not items:
                # Нет реальных пунктов списка — идём дальше
                continue

            for idx, item_text in enumerate(items):
                listitem_id = f"listitem_{chunk_id}_{idx}"

                # Нода пункта списка
                listitem_nodes.append({
                    "id": listitem_id,
                    "label": "ListItem",
                    "chunk_id": chunk_id,
                    "order": idx,
                    "page_start": row["page_start"],
                    "page_end": row["page_end"],
                    "text": item_text,
                })

                # Ребро Chunk -> ListItem
                edges.append({
                    "source": node_chunk_id,
                    "target": listitem_id,
                    "relation": "HAS_ITEM"
                })

        nodes_df = pd.DataFrame(listitem_nodes)
        edges_df = pd.DataFrame(edges)
        return nodes_df, edges_df

# Обертка для вызова извне

def build_list_items(chunks_csv: str, out_nodes: str, out_edges: str):
    """
    Функция для вызова из main.py или CLI.
    """
    extractor = ListItemExtractor(Path(chunks_csv))
    nodes_df, edges_df = extractor.build()

    nodes_df.to_csv(out_nodes, index=False)
    edges_df.to_csv(out_edges, index=False)

    print(f"Ноды пунктов списков сохранены в {out_nodes}")
    print(f"Связи Chunk→ListItem (HAS_ITEM) сохранены в {out_edges}")


if __name__ == "__main__":
    build_list_items(
        chunks_csv="output/chunks.csv",
        out_nodes="output/nodes_list_items.csv",
        out_edges="output/edges_list_items.csv"
    )
