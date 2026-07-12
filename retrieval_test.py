"""
Step 4: Retrieval — given a query, find the most similar chunks from the database.
"""

import os
from dotenv import load_dotenv
import psycopg2
from sentence_transformers import SentenceTransformer

load_dotenv()


def get_query_embedding(query: str, model) -> str:
    """Convert the user's query into an embedding, formatted for pgvector."""
    embedding = model.encode(query)
    return "[" + ",".join(str(x) for x in embedding) + "]"


def search_similar_chunks(query_embedding: str, top_k: int = 3):
    """
    Search the database for the top_k chunks most similar to the query embedding.

    The <=> operator in pgvector calculates cosine distance between vectors.
    Smaller distance = more similar. We order by distance ascending
    (most similar first) and limit to top_k results.
    """
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, chunk_text, embedding <=> %s AS distance
        FROM document_chunks
        ORDER BY distance ASC
        LIMIT %s
        """,
        (query_embedding, top_k),
    )

    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


if __name__ == "__main__":
    print("🧠 Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("✅ Model loaded.\n")

    # Try changing this query to test different questions!
    query = "What is NLP?"

    print(f"🔍 Query: {query}\n")

    query_embedding = get_query_embedding(query, model)
    results = search_similar_chunks(query_embedding, top_k=3)

    print(f"✅ Top {len(results)} most relevant chunks:\n")
    print("=" * 60)

    for rank, (chunk_id, chunk_text, distance) in enumerate(results, start=1):
        print(f"\n#{rank} — Chunk ID: {chunk_id} | Distance: {distance:.4f}")
        print(chunk_text)
        print("-" * 60)