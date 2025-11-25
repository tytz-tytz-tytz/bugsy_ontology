"""
graphrag_export.py

Модуль для экспорта объединённого графа (all_nodes.csv, all_edges.csv)
в JSON-формат, удобный для GraphRAG.

Вход:
- output/all_nodes.csv
- output/all_edges.csv

Выход:
- output/graphrag_nodes.json
- output/graphrag_edges.json
"""

import json
from pathlib import Path
from typing import Dict, Any

import pandas as pd


class GraphRAGExporter:
    """
    Экспортирует CSV графа в JSON-формат для GraphRAG.
    """

    def __init__(self, all_nodes_path: Path, all_edges_path: Path):
        if not all_nodes_path.exists():
            raise FileNotFoundError(f"Файл all_nodes.csv не найден: {all_nodes_path}")
        if not all_edges_path.exists():
            raise FileNotFoundError(f"Файл all_edges.csv не найден: {all_edges_path}")

        self.all_nodes_path = all_nodes_path
        self.all_edges_path = all_edges_path

        self.nodes_df = pd.read_csv(all_nodes_path)
        self.edges_df = pd.read_csv(all_edges_path)

        # Нормализуем пустые значения, чтобы не улететь в NaN
        self.nodes_df = self.nodes_df.fillna(value=pd.NA)
        self.edges_df = self.edges_df.fillna(value=pd.NA)

    # Построение JSON-нод
    def build_node_json(self, row: pd.Series) -> Dict[str, Any]:
        """
        Преобразует строку all_nodes в JSON-объект узла для GraphRAG.

        Структура:
        {
          "id": "...",
          "type": "Chunk" | "Section" | "ListItem" | "Figure" | "ReferenceTarget" | "Url",
          "text": "...",
          "attributes": { ... }
        }
        """

        node_id = row["id"]
        node_type = row.get("label", "Node")

        # Базовый текст — в зависимости от типа ноды
        text_value = None

        if node_type in ("Chunk", "Section", "ListItem"):
            text_value = row.get("text", "")
        elif node_type == "Figure":
            # Фигуры — используем caption_text
            text_value = row.get("caption_text", "")
        elif node_type in ("ReferenceTarget", "Url"):
            text_value = row.get("value", "")
        else:
            # fallback
            text_value = row.get("text", "") or row.get("caption_text", "") or row.get("value", "")

        # Собираем attributes: все колонки, кроме id и label
        # и кроме "text"/"caption_text"/"value", чтобы не дублировать
        attributes: Dict[str, Any] = {}
        for col in self.nodes_df.columns:
            if col in ("id",):
                continue
            if col == "label":
                # label тоже кладём в attributes, чтобы не потерять тип
                attributes["label"] = row[col]
                continue
            if col in ("text", "caption_text", "value"):
                continue

            val = row[col]
            # Преобразуем NA → None
            if pd.isna(val):
                val = None
            attributes[col] = val

        node_obj = {
            "id": node_id,
            "type": node_type,
            "text": text_value if text_value is not None else "",
            "attributes": attributes
        }
        return node_obj

    # Построение JSON-рёбер
    def build_edge_json(self, row: pd.Series) -> Dict[str, Any]:
        """
        Преобразует строку all_edges в JSON-объект ребра для GraphRAG.

        Структура:
        {
          "source": "...",
          "target": "...",
          "type": "HAS_CHUNK" | "HAS_SUBSECTION" | "HAS_ITEM" | "CAPTIONS" | "LINKS_TO" | ...
        }
        """

        source = row["source"]
        target = row["target"]
        relation = row.get("relation", "")

        edge_obj = {
            "source": source,
            "target": target,
            "type": relation
        }
        return edge_obj

    # Основной метод: экспорт в JSON
    def export(self, out_nodes_json: Path, out_edges_json: Path):
        node_records = []
        for _, row in self.nodes_df.iterrows():
            node_records.append(self.build_node_json(row))

        edge_records = []
        for _, row in self.edges_df.iterrows():
            edge_records.append(self.build_edge_json(row))

        # Сохраняем JSON
        with out_nodes_json.open("w", encoding="utf-8") as f:
            json.dump(node_records, f, ensure_ascii=False, indent=2)

        with out_edges_json.open("w", encoding="utf-8") as f:
            json.dump(edge_records, f, ensure_ascii=False, indent=2)

        print(f"GraphRAG nodes JSON сохранён в {out_nodes_json}")
        print(f"GraphRAG edges JSON сохранён в {out_edges_json}")


# Удобная функция для main.py
def export_graphrag(
    all_nodes: str = "output/all_nodes.csv",
    all_edges: str = "output/all_edges.csv",
    out_nodes_json: str = "output/graphrag_nodes.json",
    out_edges_json: str = "output/graphrag_edges.json",
):
    exporter = GraphRAGExporter(Path(all_nodes), Path(all_edges))
    exporter.export(Path(out_nodes_json), Path(out_edges_json))


if __name__ == "__main__":
    export_graphrag()