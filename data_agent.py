"""
Data Agent — retrieves relevant chunks from the Neon database.

Smart routing:
- KPI questions (efficiency/growth) -> run the appropriate KPI calculation
  directly on the database
- Group-by questions (per building/breakdown) -> run a grouped SQL
  aggregate query directly on the database
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

GROUP_BY_KEYWORDS = [
    "per building", "by building", "building-wise", "breakdown",
    "each building", "group by", "per sheet",
]

EXEC_SUMMARY_KEYWORDS = [
    "executive summary", "overview", "how is the business",
    "summarize the business", "business summary", "summary of the business",
]
def is_exec_summary_question(question: str) -> bool:
    q = question.lower()
    return any(keyword in q for keyword in EXEC_SUMMARY_KEYWORDS)

# Sheet names that are NOT actual buildings — exclude these from group-by
# results (cancellation logs, commission sheets, month-wise summary sheets).
NON_BUILDING_SHEET_KEYWORDS = ["CANCELLATION", "COMM"]
MONTH_SHEET_PATTERN = r'^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s*\d{2}$'

CHART_KEYWORDS = ["chart", "graph", "plot", "visualize", "visualise"]

KPI_KEYWORDS = ["kpi", "efficiency", "collection efficiency", "growth", "trend"]
GROWTH_KEYWORDS = ["growth", "trend", "month over month", "month-over-month", "over time"]
EFFICIENCY_KEYWORDS = ["efficiency", "collection efficiency", "collected vs"]


def is_aggregate_question(question: str) -> bool:
    q = question.lower()
    return any(keyword in q for keyword in AGGREGATE_KEYWORDS)


def is_group_by_question(question: str) -> bool:
    q = question.lower()
    return any(keyword in q for keyword in GROUP_BY_KEYWORDS)


def is_chart_question(question: str) -> bool:
    q = question.lower()
    return any(keyword in q for keyword in CHART_KEYWORDS)


def is_kpi_question(question: str) -> bool:
    q = question.lower()
    return any(keyword in q for keyword in KPI_KEYWORDS)


def detect_kpi_type(question: str) -> str:
    q = question.lower()
    if any(keyword in q for keyword in GROWTH_KEYWORDS):
        return "growth"
    return "efficiency"  # default


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

    return types if types else ["SUM"]


def format_inr(amount) -> str:
    """
    Formats a number in Indian comma style (lakh/crore grouping),
    e.g. 1065354668 -> "1,06,53,54,668"
    """
    amount = float(amount)
    is_negative = amount < 0
    amount = abs(amount)

    whole = int(amount)
    decimal_part = amount - whole
    whole_str = str(whole)

    if len(whole_str) <= 3:
        formatted = whole_str
    else:
        last_three = whole_str[-3:]
        remaining = whole_str[:-3]
        parts = []
        while len(remaining) > 2:
            parts.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            parts.insert(0, remaining)
        formatted = ",".join(parts) + "," + last_three

    if decimal_part > 0:
        formatted += f"{decimal_part:.2f}".lstrip("0")

    return ("-" if is_negative else "") + formatted


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

def exact_match_search(query: str, top_k: int = 5):
    """
    Detects code-like tokens in the query (e.g. flat numbers like "503",
    hyphenated codes like "G-01") and searches for an exact, word-boundary
    match — not a plain substring — so "503" doesn't falsely match inside
    a longer number like "8108503620".
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
        # Build the word-boundary regex fully in Python and pass it as a
        # bound parameter — building it via SQL-side E'' concatenation
        # silently drops the backslash in \y (Postgres escape-string
        # parsing quirk), which breaks the match entirely.
        escaped_token = re.escape(token)
        pattern = f"\\y{escaped_token}\\y"
        cursor.execute(
            """
            SELECT chunk_text
            FROM document_chunks
            WHERE chunk_text ~ %s
            LIMIT %s
            """,
            (pattern, top_k),
        )
        results.extend(row[0] for row in cursor.fetchall())

    cursor.close()
    conn.close()

    # Deduplicate while preserving order
    seen = set()
    unique_results = []
    for r in results:
        if r not in seen:
            seen.add(r)
            unique_results.append(r)
    return unique_results[:top_k]

    
        
def run_aggregate_query(aggregate_type: str):
    """
    Runs the appropriate SQL aggregate (SUM/AVG/MAX/MIN/COUNT) directly
    on the database using regex extraction of AMT. RECVD values.
    """
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    if aggregate_type == "COUNT":
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


def _build_exclusion_clause(column_expr: str) -> str:
    """
    Builds a SQL WHERE clause fragment that excludes non-building sheet
    names, using ILIKE for keyword matches and a regex for month-pattern
    sheets like 'APR 23'.
    """
    keyword_clauses = " AND ".join(
        f"{column_expr} NOT ILIKE '%{kw}%'" for kw in NON_BUILDING_SHEET_KEYWORDS
    )
    return f"{keyword_clauses} AND {column_expr} !~* '{MONTH_SHEET_PATTERN}'"


def run_group_by_query(aggregate_type: str = "SUM"):
    """
    Groups AMT. RECVD by the sheet name (= building), using the same
    regex extraction as run_aggregate_query but adding a GROUP BY on
    the 'Sheet:' field. Excludes non-building sheets (cancellation,
    commission, month-wise summary sheets). Returns a list of
    (building_name, result) tuples, ordered highest-to-lowest.
    """
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    building_expr = "(regexp_match(chunk_text, 'Sheet:\\s*([^.]+)\\.'))[1]"
    exclusion_clause = _build_exclusion_clause(building_expr)

    if aggregate_type == "COUNT":
        cursor.execute(
            f"""
            SELECT
                {building_expr} AS building,
                COUNT(*) AS result
            FROM document_chunks
            WHERE chunk_text ~ 'AMT\\.\\s*RECVD\\.?:\\s*[\\d\\.]+\\.'
            GROUP BY building
            HAVING {exclusion_clause}
            ORDER BY result DESC;
            """
        )
    else:
        cursor.execute(
            f"""
            SELECT
                {building_expr} AS building,
                {aggregate_type}(
                    (regexp_match(chunk_text, 'AMT\\.\\s*RECVD\\.?:\\s*([\\d\\.]+)\\.'))[1]::numeric
                ) AS result
            FROM document_chunks
            WHERE chunk_text ~ 'AMT\\.\\s*RECVD\\.?:\\s*[\\d\\.]+\\.'
            GROUP BY building
            HAVING {exclusion_clause}
            ORDER BY result DESC;
            """
        )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def run_efficiency_query():
    """
    Collection efficiency per building: (SUM(AMT. RECVD) / SUM(BASIC RATE)) * 100.
    Reuses the same building/exclusion logic as group-by.
    """
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    building_expr = "(regexp_match(chunk_text, 'Sheet:\\s*([^.]+)\\.'))[1]"
    exclusion_clause = _build_exclusion_clause(building_expr)

    cursor.execute(
        f"""
        SELECT
            {building_expr} AS building,
            SUM((regexp_match(chunk_text, 'AMT\\.\\s*RECVD\\.?:\\s*([\\d\\.]+)\\.'))[1]::numeric) AS recvd,
            SUM((regexp_match(chunk_text, 'BASIC RATE:\\s*([\\d\\.]+)\\.'))[1]::numeric) AS basic
        FROM document_chunks
        WHERE chunk_text ~ 'AMT\\.\\s*RECVD\\.?:\\s*[\\d\\.]+\\.'
        AND chunk_text ~ 'BASIC RATE:\\s*[\\d\\.]+\\.'
        GROUP BY building
        HAVING {exclusion_clause}
        ORDER BY building;
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    results = []
    for building, recvd, basic in rows:
        if basic and basic > 0:
            efficiency = round((float(recvd) / float(basic)) * 100, 2)
            results.append((building, efficiency))
    return results


def run_growth_query():
    """
    Month-wise total AMT. RECVD using BKNG DATE, ordered chronologically,
    with month-over-month % growth calculated in Python.
    """
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            to_char(
                (regexp_match(chunk_text, 'BKNG DATE:\\s*([\\d-]+)'))[1]::date,
                'YYYY-MM'
            ) AS month,
            SUM((regexp_match(chunk_text, 'AMT\\.\\s*RECVD\\.?:\\s*([\\d\\.]+)\\.'))[1]::numeric) AS total
        FROM document_chunks
        WHERE chunk_text ~ 'BKNG DATE:\\s*[\\d-]+'
        AND chunk_text ~ 'AMT\\.\\s*RECVD\\.?:\\s*[\\d\\.]+\\.'
        GROUP BY month
        ORDER BY month;
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    results = []
    prev_total = None
    for month, total in rows:
        total = float(total)
        if prev_total is not None and prev_total > 0:
            growth_pct = round(((total - prev_total) / prev_total) * 100, 1)
        else:
            growth_pct = None
        results.append((month, total, growth_pct))
        prev_total = total
    return results


def data_agent(state: AnalystState) -> dict:
    """
    Node function: takes the user's question, decides whether it's a
    KPI question, a group-by question, an aggregate question, or a
    specific-fact question, and retrieves accordingly. Also builds
    chart_data when the question explicitly asks for a chart/graph/plot
    on top of a group-by.
    """
    question = state["question"]
    chart_data = None  # default: no chart unless explicitly requested
    
    if is_exec_summary_question(question):
        print("📋 Data Agent: executive summary requested — running all key metrics...")

        total_revenue = run_aggregate_query("SUM")
        total_bookings = run_aggregate_query("COUNT")
        building_totals = run_group_by_query("SUM")
        efficiency_rows = run_efficiency_query()
        growth_rows = run_growth_query()

        chunks = ["Pre-calculated: Executive summary inputs (from database):"]
        chunks.append(f"  Overall total revenue: ₹{format_inr(total_revenue)}")
        chunks.append(f"  Overall total bookings: {total_bookings}")

        chunks.append("  Revenue per building:")
        for building, value in building_totals:
            chunks.append(f"    - {building}: ₹{format_inr(value)}")

        chunks.append("  Collection efficiency per building:")
        for building, efficiency in efficiency_rows:
            chunks.append(f"    - {building}: {efficiency}%")

        if growth_rows:
            first_month, first_total, _ = growth_rows[0]
            last_month, last_total, last_growth = growth_rows[-1]
            peak_month, peak_total, _ = max(growth_rows, key=lambda r: r[1])
            chunks.append(
                f"  Growth trend: from ₹{format_inr(first_total)} in {first_month} "
                f"to ₹{format_inr(last_total)} in {last_month} "
                f"(peak was ₹{format_inr(peak_total)} in {peak_month})"
            )

        print("✅ Data Agent: executive summary inputs prepared.")

    elif is_kpi_question(question):
        kpi_type = detect_kpi_type(question)
        print(f"📈 Data Agent: KPI question detected ({kpi_type})...")

        if kpi_type == "growth":
            rows = run_growth_query()
            chunks = ["Pre-calculated: Month-over-month growth (from database):"]
            for month, total, growth_pct in rows:
                growth_str = f"{growth_pct:+.1f}%" if growth_pct is not None else "N/A (first month)"
                chunks.append(f"  - {month}: ₹{format_inr(total)} (growth: {growth_str})")
            print(f"✅ Data Agent: growth trend for {len(rows)} months.")

            if is_chart_question(question):
                chart_data = {
                    "type": "line",
                    "title": "Revenue Growth Trend",
                    "labels": [month for month, _, _ in rows],
                    "values": [total for _, total, _ in rows],
                }
                print("📈 Data Agent: chart data prepared (line).")
        else:
            rows = run_efficiency_query()
            chunks = ["Pre-calculated: Collection efficiency per building (from database):"]
            for building, efficiency in rows:
                chunks.append(f"  - {building}: {efficiency}%")
            print(f"✅ Data Agent: efficiency calculated for {len(rows)} buildings.")

    elif is_group_by_question(question):
        aggregate_types = detect_aggregate_types(question)
        agg_type = aggregate_types[0]
        print(f"📊 Data Agent: group-by question detected ({agg_type} per building)...")
        rows = run_group_by_query(agg_type)
        chunks = [f"Pre-calculated: {agg_type} per building (from database group-by query):"]
        for building, value in rows:
            chunks.append(f"  - {building}: ₹{format_inr(value)}")
        print(f"✅ Data Agent: grouped results for {len(rows)} buildings.")
        if is_chart_question(question):
            chart_data = {
                "type": "bar",
                "title": f"{agg_type} per Building",
                "labels": [building for building, _ in rows],
                "values": [float(value) for _, value in rows],
            }
            print("📈 Data Agent: chart data prepared.")

    elif is_aggregate_question(question):
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
        exact_results = exact_match_search(question, top_k=5)
        if exact_results:
            print(f"🎯 Data Agent: found {len(exact_results)} exact matches.")
        query_embedding = get_query_embedding(question)
        semantic_results = semantic_search(query_embedding, top_k=10)
        # Exact matches first (higher confidence), then semantic results,
        # deduplicated so the same chunk isn't shown twice
        chunks = exact_results + [c for c in semantic_results if c not in exact_results]
        print(f"✅ Data Agent: found {len(chunks)} relevant chunks total.")

    return {"retrieved_data": chunks, "chart_data": chart_data}


if __name__ == "__main__":
    test_state: AnalystState = {
        "question": "Give me an executive summary of the business",
        "retrieved_data": [],
        "analysis": "",
        "final_report": "",
    }

    result = data_agent(test_state)
    print("\n📦 Retrieved chunks:")
    for chunk in result["retrieved_data"]:
        print(f"  - {chunk}")
    print("\n📈 Chart data:")
    print(result["chart_data"])