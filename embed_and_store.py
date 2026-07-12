"""
Step 3: Generate embeddings for each chunk and store them in Neon PostgreSQL (pgvector).
"""

import os
from dotenv import load_dotenv
import psycopg2
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# ---------- Step A: Load document ----------
def load_document(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# ---------- Step B: Chunk document ----------
def chunk_document(text: str, chunk_size: int = 500, chunk_overlap: int = 50):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


# ---------- Step C: Generate embeddings ----------
def generate_embeddings(chunks, model):
    """
    Converts a list of text chunks into a list of vector embeddings.
    Each embedding is a list of 384 floating point numbers.
    """
    embeddings = model.encode(chunks, show_progress_bar=True)
    return embeddings


# ---------- Step D: Store in Neon PostgreSQL ----------
def store_chunks(chunks, embeddings, document_id: str):
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    for chunk_text, embedding in zip(chunks, embeddings):
        # pgvector expects the embedding as a string like '[0.1, 0.2, 0.3, ...]'
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        cursor.execute(
            """
            INSERT INTO document_chunks (document_id, chunk_text, embedding, metadata)
            VALUES (%s, %s, %s, %s)
            """,
            (document_id, chunk_text, embedding_str, '{"source": "sample_document.txt"}'),
        )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Stored {len(chunks)} chunks in the database.")


if __name__ == "__main__":
    file_path = "sample_document.txt"
    document_id = "sample_document"

    print("📄 Loading document...")
    text = load_document(file_path)

    print("✂️  Chunking document...")
    chunks = chunk_document(text)
    print(f"✅ Created {len(chunks)} chunks.\n")

    print("🧠 Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("✅ Model loaded.\n")

    print("🔢 Generating embeddings for all chunks...")
    embeddings = generate_embeddings(chunks, model)
    print(f"✅ Generated {len(embeddings)} embeddings, each of size {len(embeddings[0])}.\n")

    print("💾 Storing chunks + embeddings in Neon PostgreSQL...")
    store_chunks(chunks, embeddings, document_id)

    print("\n🎉 Pipeline complete! Your chunks are now searchable in the database.")