"""
figure_graph_builder.py

Модуль для извлечения графа фигур (рисунков) из figures.csv.

Что делает:
- создаёт ноды Figure
- связывает Figure ↔ Chunk через CAPTIONS (caption_chunk → figure)
- (опционально) создаёт связи NEAR_FIGURE — все чанки на той же странице

Выход:
- output/nodes_figures.csv
- output/edges_figures.csv
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict


class FigureGraphBuilder:
    """
    Строит ноды Figure и связи CAPTIONS.
    """

    def __init__(self, figures_csv_path: Path):
        if not figures_csv_path.exists():
            raise FileNotFoundError(f"Файл не найден: {figures_csv_path}")

        self.figures_csv_path = figures_csv_path
        self.df = pd.read_csv(figures_csv_path)

        required = ["figure_id", "figure_number", "page",
                    "caption_chunk", "caption_text",
                    "file", "saved_ext", "bbox",
                    "width_px", "height_px"]
        missing = [c for c in required if c not in self.df.columns]
        if missing:
            raise ValueError(f"В figures.csv отсутствуют колонки: {missing}")

    # Основной метод
    def build(self):
        figure_nodes: List[Dict] = []
        edges: List[Dict] = []

        for _, row in self.df.iterrows():
            fig_id = row["figure_id"]
            section_fig_id = f"figure_{fig_id}"

            # Нода Figure
            figure_nodes.append({
                "id": section_fig_id,
                "label": "Figure",
                "figure_id": fig_id,
                "figure_number": row["figure_number"],
                "page": row["page"],
                "caption_text": row["caption_text"],
                "file": row["file"],
                "saved_ext": row["saved_ext"],
                "bbox": row["bbox"],
                "width_px": row["width_px"],
                "height_px": row["height_px"],
            })

            # CAPTIONS связь
            # caption_chunk → figure
            cap_chunk = row["caption_chunk"]
            if isinstance(cap_chunk, str) or not pd.isna(cap_chunk):
                chunk_node_id = f"chunk_{cap_chunk}"
                edges.append({
                    "source": chunk_node_id,
                    "target": section_fig_id,
                    "relation": "CAPTIONS"
                })

        return pd.DataFrame(figure_nodes), pd.DataFrame(edges)


# Вспомогательная удобная функция
def build_figures(figures_csv: str, out_nodes: str, out_edges: str):
    builder = FigureGraphBuilder(Path(figures_csv))
    nodes_df, edges_df = builder.build()
    nodes_df.to_csv(out_nodes, index=False)
    edges_df.to_csv(out_edges, index=False)
    print(f"Ноды фигур сохранены в {out_nodes}")
    print(f"Связи CAPTIONS сохранены в {out_edges}")


if __name__ == "__main__":
    build_figures(
        figures_csv="output/figures.csv",
        out_nodes="output/nodes_figures.csv",
        out_edges="output/edges_figures.csv"
    )
