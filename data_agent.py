"""
Data Agent — retrieves relevant chunks from the Neon database.

Smart routing:
- Aggregate questions (total/sum/average) -> run a SQL aggregate query
  directly on the database (fast, accurate, no token limit issues)
- Specific fact questions -> semantic search as before
"""

import os
from dotenv import load_dotenv
import psycopg2
from fastembed import TextEmbedding
from state import AnalystState

load_dotenv()

# Load the embedding model once (same one used in the RAG project)
print("🧠 Loading embedding model for Data Agent...")
embedding_model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
print("✅ Embedding model loaded.")

AGGREGATE_KEYWORDS = ["total", "sum", "average", "how many", "count", "overall"]


def is_aggregate_question(question: str) -> bool:
    q = question.lower()
    return any(keyword in q for keyword in AGGREGATE_KEYWORDS)


def get_query_embedding(query: str) -> str:
    embedding = list(embedding_model.embed([query]))[0]
    return "[" + ",".join(str(x) for x in embedding) + "]"


def semantic_search(query_embedding: str, top_k: int = 15):
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
    return [chunk_text for _, chunk_text, _ in results]


def get_total_amount_received():
    """
    Runs a SQL aggregate query directly on the database using regex
    extraction — avoids sending raw text to the LLM entirely.
    """
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT SUM(
            (regexp_match(chunk_text, 'AMT\\.\\s*RECVD\\.?:\\s*([\\d\\.]+)\\.'))[1]::numeric
        ) AS total_amount_received
        FROM document_chunks
        WHERE chunk_text ~ 'AMT\\.\\s*RECVD\\.?:\\s*[\\d\\.]+\\.';
        """
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0]


def data_agent(state: AnalystState) -> dict:
    """
    Node function: takes the user's question, decides whether it's an
    aggregate question or a specific-fact question, and retrieves
    accordingly.
    """
    question = state["question"]

    if is_aggregate_question(question):
        print("🔢 Data Agent: aggregate question detected — running SQL SUM()...")
        total = get_total_amount_received()
        # Pass a clean, pre-computed fact to the Analysis Agent instead of raw chunks
        chunks = [f"Pre-calculated total amount received (from database SUM query): {total}"]
        print(f"✅ Data Agent: total calculated = {total}")
    else:
        print(f"🔍 Data Agent: searching for '{question}'...")
        query_embedding = get_query_embedding(question)
        chunks = semantic_search(query_embedding, top_k=15)
        print(f"✅ Data Agent: found {len(chunks)} relevant chunks.")

    return {"retrieved_data": chunks}


# Quick standalone test — lets us verify this agent works before wiring up the full graph
if __name__ == "__main__":
    test_state: AnalystState = {
        "question": "What is the total amount received for flat bookings?",
        "retrieved_data": [],
        "analysis": "",
        "final_report": "",
    }

    result = data_agent(test_state)
    print("\n📦 Retrieved chunks:")
    for chunk in result["retrieved_data"][:3]:
        print(f"  - {chunk[:150]}")