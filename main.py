from pathlib import Path
from src.table_extractor import extract_tables

def main():
    pdf_path = Path("data/marketer.pdf")
    chunks_csv = Path("output/chunks.csv")
    tables_dir = Path("data/tables")
    index_csv = Path("output/tables_index.csv")

    extract_tables(pdf_path, chunks_csv, tables_dir, index_csv, dpi=300)
    print("Готово! Таблицы в data/tables/, индекс в output/tables_index.csv")

if __name__ == "__main__":
    main()