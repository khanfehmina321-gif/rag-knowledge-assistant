# RAG Knowledge Assistant

A full-stack Retrieval-Augmented Generation (RAG) system that answers questions using information retrieved from a document knowledge base — combining true hybrid search (exact match + full-text + semantic) with LLM-powered generation for accurate, grounded responses.

## 🎯 Overview

This project demonstrates a production-style RAG pipeline: documents (text or spreadsheets) are chunked, embedded, and stored in a PostgreSQL vector database. When a user asks a question, the system retrieves the most relevant chunks using a three-signal hybrid search and passes them to an LLM to generate a natural language answer grounded in the source material.

Users can upload multiple documents directly through the UI, manage their document library, and hold a persistent multi-turn conversation with the assistant.

## 🏗️ Architecture

User Question (Next.js Frontend)
↓
HTTP POST /query
↓
FastAPI Backend
↓
Embed the question (Sentence Transformers)
↓
Run THREE parallel searches on Neon PostgreSQL:

Exact code/ID match (ILIKE)
Full-text keyword search (tsvector/tsquery)
Semantic vector search (pgvector cosine similarity)
↓
Merge results via Reciprocal Rank Fusion (RRF)
↓
Send fused context + question to Groq (Llama 3.1)
↓
JSON Response (answer + sources)
↓
Answer displayed in a persistent chat UI

## 🛠️ Tech Stack

**Backend**
- FastAPI — REST API framework
- PostgreSQL + pgvector (hosted on Neon.tech) — vector database
- PostgreSQL full-text search (tsvector/tsquery) — keyword search
- Sentence Transformers (`all-MiniLM-L6-v2`) — text embeddings
- Groq API (Llama 3.1 8B Instant) — LLM generation
- LangChain — document chunking (RecursiveCharacterTextSplitter)
- LangGraph — multi-agent orchestration (AI Business Analyst mode)
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

## AI Business Analyst — Multi-Agent Pipeline

Built on top of the RAG system, this multi-agent pipeline (Data Agent → Analysis Agent → Report Agent, orchestrated with LangGraph) answers complex business questions directly from uploaded Excel data, going beyond simple fact retrieval.

### Why this exists

Standard RAG retrieval only pulls the *k* most similar chunks to a query. For a question like *"What is the total amount received for all bookings?"*, this means the LLM only sees a handful of records — not the full dataset — and any "total" it calculates is based on an incomplete, effectively random sample. Worse, for a question like *"what is the lowest amount received"*, the LLM may pick a low-looking number from whatever sample it was given, rather than the true minimum across all records.

**Example — same question, two modes:**

| Question | Normal Search (RAG) | Business Analyst Mode |
|---|---|---|
| "What is the lowest amount received for a booking?" | ₹50,000 *(wrong — based on a partial sample of retrieved chunks)* | ₹10,000 *(correct — calculated via SQL across all records)* |

### Features

- **Aggregate calculations** — SUM, AVG, MAX, MIN, COUNT, computed via direct SQL queries (not LLM math), including compound questions asking for multiple aggregates at once (e.g. "how many bookings and what's the total amount").

- **Group-by breakdowns** — Per-building revenue breakdowns via SQL `GROUP BY` on the sheet name, with automatic exclusion of non-building sheets (cancellation logs, commission sheets, month-wise summaries). Amounts formatted in Indian numbering style (lakh/crore) with ₹.

- **Chart/graph generation** — Triggered by explicit chart/graph/plot keywords. Backend builds structured chart data (bar for group-by breakdowns, line for growth trends); frontend renders it as an interactive Recharts chart with Indian crore/lakh axis formatting.

- **KPI calculations**:
  - *Collection efficiency* per building (amount received ÷ basic rate, as a %)
  - *Month-over-month growth trend* (parsed from booking dates), with % change calculated between consecutive months

- **Natural language record search** — Handles specific-record questions (e.g. "who booked flat 503") using a hybrid of word-boundary exact-match SQL search (for flat numbers/codes) and semantic vector search, synthesized into a clean answer by the LLM.

- **Executive summary generation** — A single "executive summary" or "overview" request runs all key metrics together (total revenue, bookings, per-building breakdown, collection efficiency, growth trend) and formats them into a structured report with Overview, Building Performance, Collection Efficiency, Growth Trend, and Key Insights sections.

### Architecture

User question
│
▼
Data Agent — routes the question (KPI / group-by / aggregate / exec-summary / semantic+exact search)
│ and runs the matching SQL query or hybrid search directly on Postgres
▼
Analysis Agent — passes through pre-calculated SQL results as-is (no LLM needed),
│ or runs LLM analysis for open-ended/semantic questions
▼
Report Agent — formats the final answer as a client-facing report
│ (paragraph, bullets, or full executive summary depending on the question)
▼
Frontend (Next.js + Recharts) — renders the report text, and any chart data, inline


### Key design decisions

- **SQL-first for aggregates**: rather than asking the LLM to "add up" numbers from a handful of retrieved chunks, aggregate questions (total, average, highest, lowest, count) are answered by running the appropriate SQL function (`SUM`, `AVG`, `MAX`, `MIN`, `COUNT`) directly against the full dataset, using regex extraction on the stored text. This guarantees numerically correct answers and avoids LLM hallucination on arithmetic.
- **Compound question support**: a single question like *"how many bookings are there, and what is the total amount received?"* is detected as needing **two** aggregates, and both are computed and returned together — rather than the system answering only one part or fabricating the other.
- **LLM skip for pre-calculated values**: when the Data Agent has already computed an exact number via SQL, the Analysis Agent skips calling the LLM entirely — this avoids unnecessary token usage/cost and removes any chance of the LLM altering a correct number.
- **Orchestration via LangGraph**: the three agents (Data → Analysis → Report) are wired together as a `StateGraph`, with a shared `AnalystState` passed between nodes — a pattern that scales cleanly if more specialized agents are added later.

### Tech stack

- **Backend:** FastAPI, LangGraph, Groq (Llama 3.1) for generation
- **Database:** Neon PostgreSQL with pgvector, all data stored as text chunks with regex-based field extraction (no separate structured tables)
- **Embeddings:** fastembed (ONNX) — `sentence-transformers/all-MiniLM-L6-v2`
- **Frontend:** Next.js, Tailwind, Recharts for interactive charts

### Status

All planned features implemented, tested, and confirmed working on the live production deployment (Render backend + Vercel frontend).

### Try it

The frontend includes a **"Business Analyst Mode"** toggle next to the question input — switching modes changes which backend endpoint (`/query` vs `/business-query`) handles the request, using the same uploaded documents.

## 📂 Project Structure

├── main_api.py # FastAPI backend: /query, /upload, /documents, /business-query endpoints
├── data_agent.py # Business Analyst: retrieval + SQL aggregate/group-by/KPI routing
├── analysis_agent.py # Business Analyst: calculation/analysis via Groq
├── report_agent.py # Business Analyst: final client-facing report generation
├── graph.py # LangGraph orchestration of the three agents
├── state.py # Shared state schema (AnalystState) for the agent pipeline
├── ingest_documents.py # CLI script for bulk-loading multiple files/formats
├── embed_and_store.py # Script to chunk, embed, and store a single text document
├── load_excel.py # Script to load a single Excel file
├── retrieval_test.py # Standalone retrieval testing script
├── rag_pipeline.py # End-to-end RAG pipeline (CLI version)
├── test_connection.py # Database connection test utility
├── sample_document.txt # Sample knowledge base document
├── frontend/ # Next.js frontend application
│ └── src/app/
│ ├── page.js # Main chat interface with upload + document management
│ └── components/
│ └── BarChartDisplay.jsx # Recharts bar/line chart renderer
└── .env # Environment variables (not committed)


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

DATABASE_URL=postgresql://user:password@your-neon-host/neondb?sslmode=require
GROQ_API_KEY=your_groq_api_key_here


### 3. Install backend dependencies
```bash
pip install fastapi uvicorn psycopg2-binary sentence-transformers groq python-dotenv langchain-text-splitters langgraph pandas openpyxl python-multipart --break-system-packages
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
Use the upload area in the UI to add `.txt`, `.xlsx`, `.xls`, or `.csv` files — no need to run any scripts manually. Use the **"Business Analyst Mode"** toggle for aggregate/analytical questions (totals, averages, comparisons, breakdowns, charts, KPIs, and executive summaries).

## 🔮 Future Improvements

- [ ] PDF document upload support
- [ ] Cross-encoder re-ranking for further retrieval precision improvements
- [ ] RAGAS-based evaluation (faithfulness, relevance, precision/recall)
- [ ] Automatic Excel header-row detection (to handle messy real-world spreadsheets)
- [ ] Backend-persisted conversation history (multi-device sync)
- [ ] Upload progress percentage (currently shows per-file status, not byte-level progress)
- [x] Group-by aggregate support in Business Analyst Mode
- [x] Chart/graph generation for aggregate and KPI questions
- [x] KPI calculations (collection efficiency, growth trends)
- [x] Natural language specific-record search (exact-match + semantic hybrid)
- [x] Executive summary generation

## 📝 License

This project is open source and available for learning purposes.

---

Built as a hands-on learning project to understand production RAG architecture — from vector databases and hybrid search to full-stack deployment, extended with a multi-agent LangGraph pipeline for reliable analytical querying.