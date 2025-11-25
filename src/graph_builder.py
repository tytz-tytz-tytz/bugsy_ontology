"""
graph_builder.py

Объединяет все части графа, собранные предыдущими модулями:

- Section ноды       → nodes_sections.csv
- Section рёбра      → edges_sections.csv
- ListItem ноды      → nodes_list_items.csv
- ListItem рёбра     → edges_list_items.csv
- Figure ноды        → nodes_figures.csv
- Figure рёбра       → edges_figures.csv
- Hyperlink ноды     → nodes_hyperlinks.csv
- Hyperlink рёбра    → edges_hyperlinks.csv

И собирает ЕДИНЫЙ граф:

- output/all_nodes.csv
- output/all_edges.csv

Эти файлы полностью готовы для импорта в Neo4j:
LOAD CSV WITH HEADERS FROM 'file:///all_nodes.csv' AS row ...
LOAD CSV WITH HEADERS FROM 'file:///all_edges.csv' AS row ...

А также подходят для последующего экспорта в GraphRAG JSON.
"""

import pandas as pd
from pathlib import Path


class GraphBuilder:

    def __init__(
        self,
        chunks_csv: Path,
        nodes_sections: Path,
        edges_sections: Path,
        nodes_list_items: Path,
        edges_list_items: Path,
        nodes_figures: Path,
        edges_figures: Path,
        nodes_hyperlinks: Path,
        edges_hyperlinks: Path,
    ):
        self.chunks_csv = chunks_csv
        self.nodes_sections = nodes_sections
        self.edges_sections = edges_sections
        self.nodes_list_items = nodes_list_items
        self.edges_list_items = edges_list_items
        self.nodes_figures = nodes_figures
        self.edges_figures = edges_figures
        self.nodes_hyperlinks = nodes_hyperlinks
        self.edges_hyperlinks = edges_hyperlinks

    # Основной метод
    def build(self, out_nodes: Path, out_edges: Path):

        # 1. Загружаем чанки как ноды Chunk
        df_chunks = pd.read_csv(self.chunks_csv)

        chunk_nodes = []
        for _, row in df_chunks.iterrows():
            chunk_nodes.append({
                "id": f"chunk_{row['chunk_id']}",
                "label": "Chunk",
                "chunk_id": row["chunk_id"],
                "page_start": row["page_start"],
                "page_end": row["page_end"],
                "type": row["type"],
                "font_size": row["font_size"],
                "text": row["text"],
                "bbox": row["bbox"],
                "hyperlink_target": row["hyperlink_target"],
                "items_raw": row["items"],
            })

        df_chunk_nodes = pd.DataFrame(chunk_nodes)

        # 2. Загружаем все остальные ноды
        df_sections_nodes = pd.read_csv(self.nodes_sections)
        df_list_nodes = pd.read_csv(self.nodes_list_items)
        df_figure_nodes = pd.read_csv(self.nodes_figures)
        df_hyperlink_nodes = pd.read_csv(self.nodes_hyperlinks)

        # Объединяем
        df_all_nodes = pd.concat([
            df_chunk_nodes,
            df_sections_nodes,
            df_list_nodes,
            df_figure_nodes,
            df_hyperlink_nodes
        ], ignore_index=True)

        # 3. Загружаем ребра
        df_sections_edges = pd.read_csv(self.edges_sections)
        df_list_edges = pd.read_csv(self.edges_list_items)
        df_figure_edges = pd.read_csv(self.edges_figures)
        df_hyperlink_edges = pd.read_csv(self.edges_hyperlinks)

        df_all_edges = pd.concat([
            df_sections_edges,
            df_list_edges,
            df_figure_edges,
            df_hyperlink_edges
        ], ignore_index=True)

        # 4. Сохраняем
        df_all_nodes.to_csv(out_nodes, index=False)
        df_all_edges.to_csv(out_edges, index=False)

        print(f"Все ноды сохранены в {out_nodes}")
        print(f"Все рёбра сохранены в {out_edges}")
        print("Граф успешно собран.")


# Удобная функция для main.py

def build_full_graph(
    chunks_csv="output/chunks.csv",
    nodes_sections="output/nodes_sections.csv",
    edges_sections="output/edges_sections.csv",
    nodes_list_items="output/nodes_list_items.csv",
    edges_list_items="output/edges_list_items.csv",
    nodes_figures="output/nodes_figures.csv",
    edges_figures="output/edges_figures.csv",
    nodes_hyperlinks="output/nodes_hyperlinks.csv",
    edges_hyperlinks="output/edges_hyperlinks.csv",
    out_nodes="output/all_nodes.csv",
    out_edges="output/all_edges.csv",
):
    builder = GraphBuilder(
        Path(chunks_csv),
        Path(nodes_sections),
        Path(edges_sections),
        Path(nodes_list_items),
        Path(edges_list_items),
        Path(nodes_figures),
        Path(edges_figures),
        Path(nodes_hyperlinks),
        Path(edges_hyperlinks),
    )

    builder.build(Path(out_nodes), Path(out_edges))


if __name__ == "__main__":
    build_full_graph()