"""
FastAPI backend for the RAG system.
This exposes our RAG pipeline (retrieval + generation) as a web API
so a frontend (like Next.js) can send questions and get answers.
"""

import os
from dotenv import load_dotenv
import psycopg2
from sentence_transformers import SentenceTransformer
from groq import Groq

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# ---------- Setup ----------
app = FastAPI(title="RAG System API")

# CORS allows our Next.js frontend (running on a different port)
# to make requests to this backend without being blocked by the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with your actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the embedding model once when the server starts (not on every request —
# that would be slow). This stays in memory as long as the server is running.
print("🧠 Loading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ Embedding model loaded.")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------- File loaders for upload endpoint ----------
def load_txt_chunks(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def load_xlsx_chunks(file_path: str) -> list[str]:
    all_sheets = pd.read_excel(file_path, sheet_name=None)
    chunks = []
    for sheet_name, df in all_sheets.items():
        for _, row in df.iterrows():
            parts = [f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])]
            if parts:
                chunks.append(f"Sheet: {sheet_name}. " + ". ".join(parts) + ".")
    return chunks


def load_csv_chunks(file_path: str) -> list[str]:
    df = pd.read_csv(file_path)
    chunks = []
    for _, row in df.iterrows():
        parts = [f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])]
        if parts:
            chunks.append(". ".join(parts) + ".")
    return chunks


def store_uploaded_chunks(chunks, embeddings, document_id: str):
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


# ---------- Request/Response schemas ----------
# Pydantic models define what data the frontend must send us,
# and FastAPI automatically validates incoming requests against this.
class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]


# ---------- Core RAG functions (same logic as before) ----------
def get_query_embedding(query: str) -> str:
    embedding = embedding_model.encode(query)
    return "[" + ",".join(str(x) for x in embedding) + "]"


def keyword_search(query: str, top_k: int = 10):
    """
    PostgreSQL full-text search using tsvector/tsquery.

    We build the query as an OR of each word (not the default AND) —
    this matters because real-world data is often abbreviated or messy
    (e.g. "BKNG DATE" instead of "booked"), so requiring every query word
    to match exactly would miss too many valid results.
    """
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    # Split the query into individual words
    words = [w for w in query.split() if w.strip()]

    if not words:
        cursor.close()
        conn.close()
        return []

    # Build a tsquery that is the OR (||) of each word's own plainto_tsquery.
    # Using plainto_tsquery per word (instead of raw to_tsquery) keeps this
    # safe against punctuation like "G-01" or "?" causing syntax errors.
    tsquery_parts = " || ".join(["plainto_tsquery('english', %s)"] * len(words))

    sql = f"""
        SELECT id, chunk_text,
               ts_rank(text_search, {tsquery_parts}) AS rank
        FROM document_chunks
        WHERE text_search @@ ({tsquery_parts})
        ORDER BY rank DESC
        LIMIT %s
    """

    # The word list needs to appear twice (once for SELECT rank, once for WHERE)
    params = words + words + [top_k]
    cursor.execute(sql, params)

    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def semantic_search(query_embedding: str, top_k: int = 10):
    """
    Vector similarity search using pgvector cosine distance.
    Returns chunks ranked by semantic similarity.
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
    # Returns list of (id, chunk_text, distance) — lower distance = more similar
    return results


def exact_code_search(query: str, top_k: int = 10):
    """
    Detect code-like tokens in the query (e.g. G-01, 1407, phone numbers)
    and search for an exact substring match. This is separate from the
    full-text search because hyphenated codes like "G-01" don't reliably
    match via tsquery — PostgreSQL's parser treats them as phrases, which
    can fail to match depending on surrounding punctuation in the stored text.
    """
    import re

    candidates = re.findall(r"[A-Za-z]+-?\d+|\b\d{3,}\b", query)
    if not candidates:
        return []

    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    results = []
    for token in candidates:
        cursor.execute(
            """
            SELECT id, chunk_text, 1.0 AS rank
            FROM document_chunks
            WHERE chunk_text ILIKE %s
            LIMIT %s
            """,
            (f"%{token}%", top_k),
        )
        results.extend(cursor.fetchall())

    cursor.close()
    conn.close()

    seen = set()
    unique_results = []
    for r in results:
        if r[0] not in seen:
            seen.add(r[0])
            unique_results.append(r)

    return unique_results[:top_k]


def reciprocal_rank_fusion(result_lists, top_k: int = 3, k: int = 60):
    """
    Combine multiple ranked result lists using Reciprocal Rank Fusion (RRF).
    result_lists is a list of ranked lists, e.g. [exact_results, keyword_results, semantic_results].
    A chunk appearing near the top of MORE lists gets a much higher combined score.
    """
    scores = {}
    chunk_texts = {}

    for result_list in result_lists:
        for rank, (chunk_id, chunk_text, _) in enumerate(result_list, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
            chunk_texts[chunk_id] = chunk_text

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [(chunk_id, chunk_texts[chunk_id], score) for chunk_id, score in ranked[:top_k]]


def search_similar_chunks(query: str, query_embedding: str, top_k: int = 3):
    """
    Hybrid search combining three signals:
    1. Exact code/ID matching (highest precision for things like "G-01")
    2. Full-text keyword search (good for general word matches)
    3. Semantic vector search (good for meaning/concepts)
    All three are merged using Reciprocal Rank Fusion.
    """
    exact_results = exact_code_search(query, top_k=10)
    keyword_results = keyword_search(query, top_k=10)
    semantic_results = semantic_search(query_embedding, top_k=10)

    print(f"🎯 Exact code search found {len(exact_results)} candidates.")
    print(f"🔑 Keyword search found {len(keyword_results)} candidates.")
    print(f"🧠 Semantic search found {len(semantic_results)} candidates.")

    # Exact matches are included twice in the fusion — this effectively gives
    # them extra weight, since an exact code match is very high-confidence.
    fused_results = reciprocal_rank_fusion(
        [exact_results, exact_results, keyword_results, semantic_results],
        top_k=top_k,
    )
    print(f"🔀 Fused into top {len(fused_results)} results via RRF.")

    return fused_results


def build_context(results) -> str:
    return "\n\n---\n\n".join(chunk_text for _, chunk_text, _ in results)


def generate_answer(query: str, context: str) -> str:
    prompt = f"""You are a helpful assistant answering questions about documents,
which may include structured records (bookings, sales, financial data) or
general text content.

Instructions:
- Answer using ONLY the context provided below.
- If the context contains a structured record (e.g. a row with fields like
  name, flat number, date, amount), summarize ALL the relevant fields in a
  clear, readable way — don't just repeat a single field like the name.
  For example, if asked "Who is X?", describe what record(s) mention X,
  including any associated details like flat/booking number, date, amount, city.
- If the context doesn't contain enough information to answer, say so honestly
  instead of making something up.

Context:
{context}

Question: {query}

Answer:"""

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return response.choices[0].message.content


# ---------- API Endpoints ----------
@app.get("/")
def root():
    """Simple health check endpoint — visit this in a browser to confirm the server is running."""
    return {"status": "RAG API is running"}


@app.get("/documents")
def list_documents():
    """
    Return a summary of all uploaded documents: their document_id,
    how many chunks they have, and when they were first added.
    """
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT document_id, COUNT(*) AS chunk_count, MIN(created_at) AS uploaded_at
        FROM document_chunks
        GROUP BY document_id
        ORDER BY uploaded_at DESC
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    documents = [
        {
            "document_id": row[0],
            "chunk_count": row[1],
            "uploaded_at": row[2].isoformat() if row[2] else None,
        }
        for row in rows
    ]
    return {"documents": documents}


@app.delete("/documents/{document_id}")
def delete_document(document_id: str):
    """Delete all chunks belonging to a specific document_id."""
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM document_chunks WHERE document_id = %s",
        (document_id,),
    )
    deleted_count = cursor.rowcount

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "deleted", "document_id": document_id, "chunks_removed": deleted_count}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Accept an uploaded file, save it temporarily, process it through the
    same chunking + embedding pipeline used for local files, and store
    the results in the database.
    """
    import tempfile
    from pathlib import Path

    # Get the file extension so we know which loader to use
    ext = Path(file.filename).suffix.lower()

    supported = {".txt", ".xlsx", ".xls", ".csv"}
    if ext not in supported:
        return {"error": f"Unsupported file type '{ext}'. Supported types: {supported}"}

    # Save the uploaded file to a temporary location on disk so pandas/open()
    # can read it just like a regular local file
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        import time
        document_id = f"{Path(file.filename).stem}_{int(time.time())}"

        if ext == ".txt":
            chunks = load_txt_chunks(tmp_path)
        elif ext in (".xlsx", ".xls"):
            chunks = load_xlsx_chunks(tmp_path)
        elif ext == ".csv":
            chunks = load_csv_chunks(tmp_path)

        if not chunks:
            return {"error": "No content could be extracted from this file."}

        embeddings = embedding_model.encode(chunks, show_progress_bar=False, batch_size=32)
        store_uploaded_chunks(chunks, embeddings, document_id)

        return {
            "status": "success",
            "filename": file.filename,
            "document_id": document_id,
            "chunks_stored": len(chunks),
        }
    finally:
        # Clean up the temporary file regardless of success or failure
        os.remove(tmp_path)


@app.post("/query", response_model=QueryResponse)
def query_rag(request: QueryRequest):
    """
    Main RAG endpoint. Takes a question, retrieves relevant chunks,
    and returns a generated answer along with the source chunks used.
    """
    query_embedding = get_query_embedding(request.question)
    results = search_similar_chunks(request.question, query_embedding, top_k=3)
    context = build_context(results)
    answer = generate_answer(request.question, context)

    sources = [chunk_text[:150] + "..." for _, chunk_text, _ in results]

    return QueryResponse(answer=answer, sources=sources)