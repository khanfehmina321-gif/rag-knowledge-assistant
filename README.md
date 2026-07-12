# RAG Knowledge Assistant

A full-stack Retrieval-Augmented Generation (RAG) system that answers questions using information retrieved from a document knowledge base — combining true hybrid search (exact match + full-text + semantic) with LLM-powered generation for accurate, grounded responses.

## 🎯 Overview

This project demonstrates a production-style RAG pipeline: documents (text or spreadsheets) are chunked, embedded, and stored in a PostgreSQL vector database. When a user asks a question, the system retrieves the most relevant chunks using a three-signal hybrid search and passes them to an LLM to generate a natural language answer grounded in the source material.

Users can upload multiple documents directly through the UI, manage their document library, and hold a persistent multi-turn conversation with the assistant.

## 🏗️ Architecture

```
User Question (Next.js Frontend)
        ↓
   HTTP POST /query
        ↓
FastAPI Backend
        ↓
  1. Embed the question (Sentence Transformers)
  2. Run THREE parallel searches on Neon PostgreSQL:
       - Exact code/ID match (ILIKE)
       - Full-text keyword search (tsvector/tsquery)
       - Semantic vector search (pgvector cosine similarity)
  3. Merge results via Reciprocal Rank Fusion (RRF)
  4. Send fused context + question to Groq (Llama 3.1)
        ↓
   JSON Response (answer + sources)
        ↓
Answer displayed in a persistent chat UI
```

## 🛠️ Tech Stack

**Backend**
- FastAPI — REST API framework
- PostgreSQL + pgvector (hosted on Neon.tech) — vector database
- PostgreSQL full-text search (tsvector/tsquery) — keyword search
- Sentence Transformers (`all-MiniLM-L6-v2`) — text embeddings
- Groq API (Llama 3.1 8B Instant) — LLM generation
- LangChain — document chunking (RecursiveCharacterTextSplitter)
- Pandas — multi-sheet Excel/CSV ingestion

**Frontend**
- Next.js (App Router)
- React
- Tailwind CSS

## ✨ Features

- **Multi-format document upload** — drag & drop or select multiple `.txt`, `.xlsx`, `.xls`, `.csv` files directly from the UI
- **Document management** — view all uploaded documents with chunk counts, delete individual documents, collapsible list for large libraries
- **True hybrid search** — combines exact ID/code matching, PostgreSQL full-text search, and vector similarity search, fused via Reciprocal Rank Fusion (RRF) for high-precision retrieval on both structured records (e.g. "flat G-01") and conceptual questions (e.g. "what is RAG?")
- **Grounded generation** — the LLM is prompted to answer only from retrieved context and to properly summarize structured records (not just repeat a single field), reducing hallucination
- **Deterministic answers** — generation temperature set to 0 for consistent, repeatable responses on factual data
- **Persistent conversation history** — multi-turn chat saved to localStorage, survives page refresh, with a "clear conversation" option
- **Source transparency** — every answer displays the source chunks used to generate it
- **Clean, responsive UI** — built with Next.js and Tailwind CSS

## 📂 Project Structure

```
├── main_api.py              # FastAPI backend: /query, /upload, /documents endpoints
├── ingest_documents.py       # CLI script for bulk-loading multiple files/formats
├── embed_and_store.py        # Script to chunk, embed, and store a single text document
├── load_excel.py             # Script to load a single Excel file
├── retrieval_test.py         # Standalone retrieval testing script
├── rag_pipeline.py           # End-to-end RAG pipeline (CLI version)
├── test_connection.py        # Database connection test utility
├── sample_document.txt       # Sample knowledge base document
├── frontend/                  # Next.js frontend application
│   └── src/app/page.js        # Main chat interface with upload + document management
└── .env                       # Environment variables (not committed)
```

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- A [Neon.tech](https://neon.tech) PostgreSQL database with the `pgvector` extension enabled
- A [Groq API](https://console.groq.com) key

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/rag-knowledge-assistant.git
cd rag-knowledge-assistant
```

### 2. Set up environment variables
Create a `.env` file in the root directory:
```
DATABASE_URL=postgresql://user:password@your-neon-host/neondb?sslmode=require
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Install backend dependencies
```bash
pip install fastapi uvicorn psycopg2-binary sentence-transformers groq python-dotenv langchain-text-splitters pandas openpyxl --break-system-packages
```

### 4. Set up the database
Run this in your Neon SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(384),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON document_chunks
USING hnsw (embedding vector_cosine_ops);

-- Full-text search support
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS text_search tsvector
    GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED;

CREATE INDEX IF NOT EXISTS idx_document_chunks_text_search
    ON document_chunks USING GIN (text_search);
```

### 5. Start the backend
```bash
uvicorn main_api:app --reload
```
Backend runs at `http://127.0.0.1:8000` — interactive API docs available at `/docs`.

### 6. Start the frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:3000`.

### 7. Upload documents and start asking questions
Use the upload area in the UI to add `.txt`, `.xlsx`, `.xls`, or `.csv` files — no need to run any scripts manually.

## 🔮 Future Improvements

- [ ] PDF document upload support
- [ ] Cross-encoder re-ranking for further retrieval precision improvements
- [ ] RAGAS-based evaluation (faithfulness, relevance, precision/recall)
- [ ] Automatic Excel header-row detection (to handle messy real-world spreadsheets)
- [ ] Backend-persisted conversation history (multi-device sync)
- [ ] Upload progress percentage (currently shows per-file status, not byte-level progress)

## 📝 License

This project is open source and available for learning purposes.

---

Built as a hands-on learning project to understand production RAG architecture — from vector databases and hybrid search to full-stack deployment.