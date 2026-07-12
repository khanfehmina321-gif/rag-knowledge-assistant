"""
Step 5: Full RAG pipeline — retrieve relevant chunks, then use Groq (Llama 3.1)
to generate a natural language answer based on those chunks.
"""

import os
from dotenv import load_dotenv
import psycopg2
from sentence_transformers import SentenceTransformer
from groq import Groq

load_dotenv()


def get_query_embedding(query: str, model) -> str:
    embedding = model.encode(query)
    return "[" + ",".join(str(x) for x in embedding) + "]"


def search_similar_chunks(query_embedding: str, top_k: int = 3):
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


def build_context(results) -> str:
    """
    Combine the retrieved chunks into a single context string
    that we'll feed to the LLM along with the user's question.
    """
    context_parts = []
    for chunk_id, chunk_text, distance in results:
        context_parts.append(chunk_text)
    return "\n\n---\n\n".join(context_parts)


def generate_answer(query: str, context: str) -> str:
    """
    Send the query + retrieved context to Groq's Llama 3.1 model
    and get back a generated answer.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = f"""You are a helpful assistant. Answer the user's question using ONLY
the context provided below. If the context doesn't contain enough information
to answer the question, say so honestly instead of making something up.

Context:
{context}

Question: {query}

Answer:"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    print("🧠 Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("✅ Model loaded.\n")

    # Try changing this question!
    query = "What is Retrieval-Augmented Generation and why is it useful?"

    print(f"🔍 Question: {query}\n")

    # Step 1: Retrieve relevant chunks
    query_embedding = get_query_embedding(query, model)
    results = search_similar_chunks(query_embedding, top_k=3)
    print(f"✅ Retrieved {len(results)} relevant chunks.\n")

    # Step 2: Build context from those chunks
    context = build_context(results)

    # Step 3: Generate answer using Groq LLM
    print("🤖 Generating answer using Llama 3.1...\n")
    answer = generate_answer(query, context)

    print("=" * 60)
    print("💬 ANSWER:")
    print("=" * 60)
    print(answer)