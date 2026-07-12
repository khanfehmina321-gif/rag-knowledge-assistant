"""
Load a multi-sheet Excel file. Each row becomes a text chunk that includes
the sheet name as context (so retrieval knows which sheet/category the data
came from), then generate embeddings and store in Neon PostgreSQL.
"""

import os
from dotenv import load_dotenv
import pandas as pd
import psycopg2
from sentence_transformers import SentenceTransformer

load_dotenv()


def load_excel_as_chunks(file_path: str) -> list[str]:
    """
    Read every sheet in the Excel file. For each row, build a readable
    text chunk like:
    "Sheet: APR 23. SR NO: 1. NAME: MUZAFFAR BHAI. FLAT NO: G-01. ..."

    Rows that are completely empty are skipped.
    """
    # sheet_name=None reads ALL sheets into a dictionary: {sheet_name: DataFrame}
    all_sheets = pd.read_excel(file_path, sheet_name=None)

    chunks = []
    for sheet_name, df in all_sheets.items():
        for _, row in df.iterrows():
            parts = [f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])]

            # Skip rows that had no usable data
            if not parts:
                continue

            chunk_text = f"Sheet: {sheet_name}. " + ". ".join(parts) + "."
            chunks.append(chunk_text)

    return chunks


def generate_embeddings(chunks, model):
    return model.encode(chunks, show_progress_bar=True, batch_size=32)


def store_chunks(chunks, embeddings, document_id: str):
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    for chunk_text, embedding in zip(chunks, embeddings):
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        cursor.execute(
            """
            INSERT INTO document_chunks (document_id, chunk_text, embedding, metadata)
            VALUES (%s, %s, %s, %s)
            """,
            (document_id, chunk_text, embedding_str, '{"source": "excel"}'),
        )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Stored {len(chunks)} rows (as chunks) in the database.")


if __name__ == "__main__":
    # 👉 Update this to match your actual file name/location
    file_path = "SALES MAASH.xlsx"
    document_id = "sales_maash"

    print(f"📊 Loading Excel file: {file_path}")
    chunks = load_excel_as_chunks(file_path)
    print(f"✅ Converted {len(chunks)} rows (across all sheets) into text chunks.\n")

    print("🔍 Preview of first 3 chunks:")
    for c in chunks[:3]:
        print(f"  - {c}\n")

    print("🧠 Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("✅ Model loaded.\n")

    print("🔢 Generating embeddings (this may take a minute for large files)...")
    embeddings = generate_embeddings(chunks, model)
    print(f"✅ Generated {len(embeddings)} embeddings.\n")

    print("💾 Storing in Neon PostgreSQL...")
    store_chunks(chunks, embeddings, document_id)

    print("\n🎉 Excel data is now searchable in your RAG system!")