"""
section_hierarchy.py

Модуль для извлечения иерархии секций из chunks.csv.

Функции:
- анализ шрифтов и определение уровней секций (L1/L2)
- построение дерева секций через стек
- формирование связей HAS_SUBSECTION и HAS_CHUNK
- сохранение результатов в CSV
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict


class SectionHierarchyBuilder:
    """
    Класс строит иерархию секций на основе chunks.csv.
    """

    def __init__(self, chunks_csv_path: Path):
        if not chunks_csv_path.exists():
            raise FileNotFoundError(f"Файл не найден: {chunks_csv_path}")

        self.chunks_csv_path = chunks_csv_path
        self.df = pd.read_csv(chunks_csv_path)

        # Проверяем наличие обязательных колонок
        required_cols = [
            "chunk_id", "page_start", "page_end",
            "type", "font_size", "text", "bbox",
            "hyperlink_target", "items"
        ]
        missing = [c for c in required_cols if c not in self.df.columns]
        if missing:
            raise ValueError(f"В chunks.csv отсутствуют необходимые колонки: {missing}")

    # 1. Определение уровней секций

    def detect_section_levels(self) -> Dict[float, int]:
        """
        Определяем уровни секций по font_size среди параграфов.
        Логика:
        - выбираем уникальные font_size из type=paragraph
        - сортируем по убыванию
        - берём два самых крупных > 12
        - присваиваем им уровни 1 и 2

        Возвращает:
            словарь {font_size: уровень}
        """

        para = self.df[self.df["type"] == "paragraph"]
        unique_sizes = sorted(para["font_size"].dropna().unique(), reverse=True)

        # Берём только шрифты, которые могут быть заголовками
        candidate_sizes = [s for s in unique_sizes if s > 12]

        # Нам нужно 2 уровня: L1 и L2
        NUM_LEVELS = 2
        section_sizes = candidate_sizes[:NUM_LEVELS]

        if len(section_sizes) == 0:
            raise ValueError("Не найдено ни одного font_size, подходящего для уровней секций.")

        font_to_level = {size: i + 1 for i, size in enumerate(section_sizes)}

        print("Обнаружены уровни секций:")
        for fs, lvl in font_to_level.items():
            print(f"   font_size={fs} → уровень L{lvl}")

        return font_to_level

    # 2. Построение дерева секций

    def build(self):
        """
        Основной метод:
        - определяет уровни секций
        - проходит по чанкам сверху вниз
        - формирует Section-ноды
        - строит связи HAS_SUBSECTION и HAS_CHUNK

        Возвращает:
            (sections_df, edges_df)
        """

        font_to_level = self.detect_section_levels()

        section_nodes = []    # список нод секций
        edges = []            # связи: HAS_SUBSECTION, HAS_CHUNK

        # Стек текущей вложенности секций
        # каждый элемент: {"id": ..., "level": ...}
        section_stack: List[Dict] = []

        def get_section_level(row):
            """
            Возвращает уровень секции по font_size.
            0 означает, что чанк не является секцией.
            """
            if row["type"] != "paragraph":
                return 0
            return font_to_level.get(row["font_size"], 0)

        # === Проходим по чанкам в порядке появления ===
        for _, row in self.df.iterrows():
            chunk_id = row["chunk_id"]
            node_chunk_id = f"chunk_{chunk_id}"
            level = get_section_level(row)

            # Это заголовок (Section)
            if level > 0:
                section_id = f"section_{chunk_id}"

                # Добавляем ноду Section
                section_nodes.append({
                    "id": section_id,
                    "label": "Section",
                    "level": level,
                    "chunk_id": chunk_id,
                    "page_start": row["page_start"],
                    "page_end": row["page_end"],
                    "font_size": row["font_size"],
                    "text": row["text"],
                    "bbox": row["bbox"],
                })

                # Создаём иерархию через стек
                # Пока на вершине стек секция того же или более глубокого уровня — удаляем её
                while section_stack and section_stack[-1]["level"] >= level:
                    section_stack.pop()

                if section_stack:
                    parent = section_stack[-1]
                    edges.append({
                        "source": parent["id"],
                        "target": section_id,
                        "relation": "HAS_SUBSECTION"
                    })

                # Добавляем новую секцию в стек
                section_stack.append({"id": section_id, "level": level})

                # Заголовок сам является chunk → привязываем его к своей же секции
                edges.append({
                    "source": section_id,
                    "target": node_chunk_id,
                    "relation": "HAS_CHUNK"
                })

            else:
                # обычный chunk → привязываем к последней секции
                if section_stack:
                    current = section_stack[-1]
                    edges.append({
                        "source": current["id"],
                        "target": node_chunk_id,
                        "relation": "HAS_CHUNK"
                    })
                else:
                    # Встречается редко: документ начинается без заголовка.
                    # Можно пропустить или создать виртуальную секцию.
                    pass

        return pd.DataFrame(section_nodes), pd.DataFrame(edges)


# CLI / вызов из main.py

def build_section_hierarchy(chunks_csv: str, out_nodes: str, out_edges: str):
    """
    Удобная функция для вызова из main.py.
    """
    builder = SectionHierarchyBuilder(Path(chunks_csv))
    nodes_df, edges_df = builder.build()

    nodes_df.to_csv(out_nodes, index=False)
    edges_df.to_csv(out_edges, index=False)

    print(f"Секции сохранены в {out_nodes}")
    print(f"Связи сохранены в {out_edges}")


if __name__ == "__main__":
    build_section_hierarchy(
        chunks_csv="output/chunks.csv",
        out_nodes="output/nodes_sections.csv",
        out_edges="output/edges_sections.csv"
    )
