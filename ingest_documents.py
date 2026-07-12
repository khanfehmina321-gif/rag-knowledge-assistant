"""
Universal document ingestion pipeline.

Supports multiple file formats (.txt, .xlsx) and multiple files in a single run.
Add support for new formats by writing a new "loader" function and registering
it in the FILE_LOADERS dictionary at the bottom.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import psycopg2
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()


# ---------------------------------------------------------
# LOADERS — one function per file type.
# Each loader takes a file path and returns a list of text chunks.
# ---------------------------------------------------------

def load_txt(file_path: str) -> list[str]:
    """Load a .txt file and split it into semantic chunks."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def load_xlsx(file_path: str) -> list[str]:
    """Load every sheet of an Excel file. Each row becomes one chunk."""
    all_sheets = pd.read_excel(file_path, sheet_name=None)

    chunks = []
    for sheet_name, df in all_sheets.items():
        for _, row in df.iterrows():
            parts = [f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])]
            if not parts:
                continue
            chunk_text = f"Sheet: {sheet_name}. " + ". ".join(parts) + "."
            chunks.append(chunk_text)

    return chunks


def load_csv(file_path: str) -> list[str]:
    """Load a CSV file. Each row becomes one chunk."""
    df = pd.read_csv(file_path)
    chunks = []
    for _, row in df.iterrows():
        parts = [f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])]
        if parts:
            chunks.append(". ".join(parts) + ".")
    return chunks


# Registry mapping file extensions to their loader function.
# To support a new file type later (e.g. .pdf, .docx), write a loader
# function above and add one line here.
FILE_LOADERS = {
    ".txt": load_txt,
    ".xlsx": load_xlsx,
    ".xls": load_xlsx,
    ".csv": load_csv,
}


# ---------------------------------------------------------
# SHARED PIPELINE — embedding + storage (same for every file type)
# ---------------------------------------------------------

def process_file(file_path: str, model, top_preview: int = 2):
    """Load, chunk, embed, and store a single file. Returns number of chunks stored."""
    ext = Path(file_path).suffix.lower()
    loader = FILE_LOADERS.get(ext)

    if loader is None:
        print(f"⚠️  Skipping {file_path} — unsupported file type '{ext}'.")
        return 0

    document_id = Path(file_path).stem  # filename without extension, used as document_id

    print(f"📄 Loading: {file_path}  (type: {ext})")
    chunks = loader(file_path)
    print(f"   → {len(chunks)} chunks created.")

    if not chunks:
        return 0

    print(f"   Preview:")
    for c in chunks[:top_preview]:
        print(f"     - {c[:150]}")

    embeddings = model.encode(chunks, show_progress_bar=False, batch_size=32)
    store_chunks(chunks, embeddings, document_id)
    return len(chunks)


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
            (document_id, chunk_text, embedding_str, f'{{"source": "{document_id}"}}'),
        )

    conn.commit()
    cursor.close()
    conn.close()


# ---------------------------------------------------------
# MAIN — list every file you want to ingest here
# ---------------------------------------------------------

if __name__ == "__main__":
    # 👉 Add or remove files here. Any mix of supported formats works.
    files_to_load = [
        "SALES MAASH.xlsx",
        "SALES DZ.xlsx",
        "Updated Share Calculation of Landlord.xlsx",
        "sample_document.txt",
    ]

    print("🧠 Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("✅ Model loaded.\n")

    total_chunks = 0
    for file_path in files_to_load:
        if not os.path.exists(file_path):
            print(f"⚠️  File not found, skipping: {file_path}\n")
            continue
        count = process_file(file_path, model)
        total_chunks += count
        print()

    print(f"🎉 Done! {total_chunks} total chunks stored across {len(files_to_load)} files.")