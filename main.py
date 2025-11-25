from src.section_hierarchy import build_section_hierarchy
from src.list_item_extractor import build_list_items
from src.figure_graph_builder import build_figures
from src.hyperlink_extractor import build_hyperlinks
from src.graph_builder import build_full_graph
from src.graphrag_export import export_graphrag

if __name__ == "__main__":
    # 1. Иерархия секций
    build_section_hierarchy(
        chunks_csv="output/chunks.csv",
        out_nodes="output/nodes_sections.csv",
        out_edges="output/edges_sections.csv"
    )

    # 2. Списки
    build_list_items(
        chunks_csv="output/chunks.csv",
        out_nodes="output/nodes_list_items.csv",
        out_edges="output/edges_list_items.csv"
    )

    # 3. Фигуры
    build_figures(
        figures_csv="output/figures.csv",
        out_nodes="output/nodes_figures.csv",
        out_edges="output/edges_figures.csv"
    )

    # 4. Ссылки
    build_hyperlinks(
        chunks_csv="output/chunks.csv",
        out_nodes="output/nodes_hyperlinks.csv",
        out_edges="output/edges_hyperlinks.csv"
    )

    # 5. Собираем единый граф
    build_full_graph()

    # 6. Экспорт в формат GraphRAG
    export_graphrag()
