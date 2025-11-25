# BUGSY Ontology Builder

## 1. Структура репозитория

```text
BUGSY_ONTOLOGY/
│
├── src/
│ ├── parse_pdf.py # Разбор PDF (текст + изображения)
│ ├── chunker.py # Формирование текстовых чанков
│ ├── figure_extractor.py # Извлечение информации об изображениях
│ ├── section_hierarchy.py # Построение структуры разделов (Section)
│ ├── list_item_extractor.py # Извлечение пунктов списков (ListItem)
│ ├── figure_graph_builder.py # Формирование Figure + CAPTIONS
│ ├── hyperlink_extractor.py # Формирование ReferenceTarget/Url + LINKS_TO
│ ├── graph_builder.py # Объединение всех сущностей в единый граф
│ ├── graphrag_export.py # Экспорт графа в JSON для GraphRAG
│ └── main.py # Основной сценарий запуска пайплайна
│
├── output/
│ ├── chunks.csv # Сырые текстовые фрагменты
│ ├── figures.csv # Сырые данные об изображениях
│ ├── nodes_sections.csv # Узлы Section
│ ├── edges_sections.csv # Связи HAS_SUBSECTION, HAS_CHUNK
│ ├── nodes_list_items.csv # Узлы ListItem
│ ├── edges_list_items.csv # Связи HAS_ITEM
│ ├── nodes_figures.csv # Узлы Figure
│ ├── edges_figures.csv # Связи CAPTIONS
│ ├── nodes_hyperlinks.csv # Узлы ReferenceTarget/Url
│ ├── edges_hyperlinks.csv # Связи LINKS_TO
│ ├── all_nodes.csv # Итоговый набор узлов онтологии (для Neo4j)
│ ├── all_edges.csv # Итоговый набор связей онтологии (для Neo4j)
│ ├── graphrag_nodes.json # Узлы для OntologyRAG
│ ├── graphrag_edges.json # Связи для OntologyRAG
│ └── ...
│
└── data/
└── *.pdf # Исходные PDF-документы
```


## 2. Описание онтологии

Онтология представляет документ в виде ориентированного графа, построенного на основе текстовых и графических элементов, извлечённых из PDF.

### Типы узлов:

| Узел | Описание |
|------|-----------|
| Section | Структурные разделы и подразделы документа |
| Chunk | Базовые текстовые фрагменты |
| ListItem | Элементы списков |
| Figure | Графические элементы |
| ReferenceTarget | Внутренние ссылочные цели |
| Url | Внешние гиперссылки |

### Типы связей:

| Связь | Семантика |
|--------|-----------|
| HAS_SUBSECTION | Раздел содержит подраздел |
| HAS_CHUNK | Раздел содержит текст |
| HAS_ITEM | Чанк содержит пункт списка |
| CAPTIONS | Подпись относится к изображению |
| LINKS_TO | Текстовый фрагмент содержит ссылку |

### Форматы выходных данных:

- [`all_nodes.csv`](output/all_nodes.csv) — итоговый набор узлов онтологии для графовых БД  
- [`all_edges.csv`](output/all_edges.csv) — итоговый набор связей онтологии  
- [`graphrag_nodes.json`](output/graphrag_nodes.json) — узлы для OntologyRAG  
- [`graphrag_edges.json`](output/graphrag_edges.json) — связи для OntologyRAG  

## 3. Пайплайн обработки

1. **Парсинг PDF**  
   Скрипты [`parse_pdf.py`](src/parse_pdf.py), [`chunker.py`](src/chunker.py) и [`figure_extractor.py`](src/figure_extractor.py) извлекают текстовые фрагменты и метаданные изображений.  
   Результаты: [`chunks.csv`](output/chunks.csv),[`figures.csv`](output/figures.csv).

2. **Восстановление структуры разделов**  
   [`section_hierarchy.py`](src/section_hierarchy.py) определяет уровни заголовков по размеру шрифта и формирует иерархию разделов.  
   Результаты: [`nodes_sections.csv`](output/nodes_sections.csv), [`edges_sections.csv`](output/edges_sections.csv).

3. **Обработка списков**  
   [`list_item_extractor.py`](src/list_item_extractor.py) выделяет элементы списков в отдельные узлы и формирует связи `HAS_ITEM`.  
   Результаты: [`nodes_list_items.csv`](output/nodes_list_items.csv), [`edges_list_items.csv`](output/edges_list_items.csv).

4. **Интеграция изображений**  
   [`figure_graph_builder.py`](src/figure_graph_builder.py) создаёт узлы Figure и связи `CAPTIONS` между подписью и изображением.  
   Результаты: [`nodes_figures.csv`](output/nodes_figures.csv), [`edges_figures.csv`](output/edges_figures.csv).

5. **Обработка гиперссылок**  
   [`hyperlink_extractor.py`](src/hyperlink_extractor.py) создаёт узлы ссылочного типа (ReferenceTarget/Url) и связи `LINKS_TO`.  
   Результаты: [`nodes_hyperlinks.csv`](output/nodes_hyperlinks.csv), [`edges_hyperlinks.csv`](output/edges_hyperlinks.csv).

6. **Сборка итогового графа**  
   [`graph_builder.py`](src/graph_builder.py) объединяет все сущности и связи в совокупный граф.  
   Результаты: [`all_nodes.csv`](output/all_nodes.csv), [`all_edges.csv`](output/all_edges.csv).

7. **Экспорт для OntologyRAG**  
   [`graphrag_export.py`](src/graphrag_export.py) преобразует итоговый граф в формат JSON, совместимый с OntologyRAG.  
   Результаты: [`graphrag_nodes.json`](output/graphrag_nodes.json), [`graphrag_edges.json`](output/graphrag_edges.json).