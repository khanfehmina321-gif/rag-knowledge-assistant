"""
Report Agent — takes the analysis and turns it into a final,
client-ready answer. Format adapts to the question: simple
questions get a clean paragraph, complex/multi-part questions
get structured output with headings/bullets.
"""

import os
from dotenv import load_dotenv
from groq import Groq
from state import AnalystState

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def build_report_prompt(question: str, analysis: str) -> str:
    return f"""You are a business analyst writing a final answer for a client.

Original Question: {question}

Analysis & Calculations:
{analysis}

Write the final answer for the client, using ONLY the numbers given in the
Analysis above. Do not introduce any additional figures, calculations, or
claims that are not explicitly present in the Analysis.

Choose the format that fits the question:
- If it's a simple, single-value question (e.g. "what is the total X"), answer in a
  short, clear paragraph — no headings or bullets needed.
- If it's a multi-part or comparative question (e.g. trends, comparisons, breakdowns
  by category), use light structure — a short summary line followed by bullet points
  or a small section for each part.

Keep it client-facing: no mention of "chunks", "database", or internal process.
Be concise and confident. State numbers clearly.
"""


def report_agent(state: AnalystState) -> dict:
    """
    Node function: takes analysis + question, asks Groq Llama 3.1 to
    write the final client-facing report, returns it as final_report.
    """
    print("📝 Report Agent: writing final report...")

    prompt = build_report_prompt(state["question"], state["analysis"])

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a skilled business analyst who writes clear, client-ready reports."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,  # a little more natural language flexibility than the analysis step
    )

    final_report = response.choices[0].message.content
    print("✅ Report Agent: report ready.")

    return {"final_report": final_report}


# Quick standalone test
if __name__ == "__main__":
    test_state: AnalystState = {
        "question": "What is the total amount received for flat bookings?",
        "retrieved_data": [],
        "analysis": """Extracted values:
- Flat 1502: AMT. RECVD = 500,000
- Flat 1503: AMT. RECVD = 750,000
Total Amount Received = 500,000 + 750,000 = 1,250,000""",
        "final_report": "",
    }

    result = report_agent(test_state)
    print("\n📝 Final Report:")
    print(result["final_report"])