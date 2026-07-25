"""
Data Agent — retrieves relevant chunks from the Neon database.

Smart routing:
- Aggregate questions (total/sum/average/highest/lowest/count) -> run the
  appropriate SQL aggregate query directly on the database (fast, accurate,
  no token limit issues)
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

AGGREGATE_KEYWORDS = [
    "total", "sum", "average", "how many", "count", "overall",
    "highest", "lowest", "maximum", "minimum",
]


def is_aggregate_question(question: str) -> bool:
    q = question.lower()
    return any(keyword in q for keyword in AGGREGATE_KEYWORDS)


def detect_aggregate_types(question: str) -> list[str]:
    """
    Detect ALL aggregate types mentioned in the question (not just one),
    so compound questions like "how many bookings AND what is the total
    amount" get both pieces of data instead of just one.
    """
    q = question.lower()
    types = []

    if any(word in q for word in ["average", "avg", "mean"]):
        types.append("AVG")
    if any(word in q for word in ["highest", "maximum", "max", "largest", "biggest"]):
        types.append("MAX")
    if any(word in q for word in ["lowest", "minimum", "min", "smallest"]):
        types.append("MIN")
    if any(word in q for word in ["how many", "count", "number of"]):
        types.append("COUNT")
    if any(word in q for word in ["total", "sum", "overall"]):
        types.append("SUM")

    # Default to SUM if nothing specific matched but it was flagged as aggregate
    return types if types else ["SUM"]


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


def run_aggregate_query(aggregate_type: str):
    """
    Runs the appropriate SQL aggregate (SUM/AVG/MAX/MIN/COUNT) directly
    on the database using regex extraction of AMT. RECVD values.
    """
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    if aggregate_type == "COUNT":
        # Count doesn't need to extract a number — just count matching rows
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM document_chunks
            WHERE chunk_text ~ 'AMT\\.\\s*RECVD\\.?:\\s*[\\d\\.]+\\.';
            """
        )
    else:
        cursor.execute(
            f"""
            SELECT {aggregate_type}(
                (regexp_match(chunk_text, 'AMT\\.\\s*RECVD\\.?:\\s*([\\d\\.]+)\\.'))[1]::numeric
            ) AS result
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
    accordingly. Handles compound questions (e.g. count AND total) by
    detecting and calculating multiple aggregate types at once.
    """
    question = state["question"]

    if is_aggregate_question(question):
        aggregate_types = detect_aggregate_types(question)
        print(f"🔢 Data Agent: aggregate question detected {aggregate_types}...")

        label_map = {
            "SUM": "Total amount received",
            "AVG": "Average amount received",
            "MAX": "Highest amount received",
            "MIN": "Lowest amount received",
            "COUNT": "Total count of bookings",
        }

        chunks = []
        for agg_type in aggregate_types:
            result = run_aggregate_query(agg_type)
            label = label_map.get(agg_type, "Result")
            chunks.append(f"Pre-calculated: {label} (from database {agg_type} query): {result}")
            print(f"✅ Data Agent: {agg_type} calculated = {result}")
    else:
        print(f"🔍 Data Agent: searching for '{question}'...")
        query_embedding = get_query_embedding(question)
        chunks = semantic_search(query_embedding, top_k=15)
        print(f"✅ Data Agent: found {len(chunks)} relevant chunks.")

    return {"retrieved_data": chunks}


# Quick standalone test — lets us verify this agent works before wiring up the full graph
if __name__ == "__main__":
    test_state: AnalystState = {
        "question": "How many bookings are there in total, and what is the total amount received for flat bookings?",
        "retrieved_data": [],
        "analysis": "",
        "final_report": "",
    }

    result = data_agent(test_state)
    print("\n📦 Retrieved chunks:")
    for chunk in result["retrieved_data"]:
        print(f"  - {chunk}")