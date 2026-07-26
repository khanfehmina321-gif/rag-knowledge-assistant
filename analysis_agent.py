"""
Analysis Agent — takes the retrieved data chunks and performs
calculations, comparisons, and trend analysis using Groq's Llama 3.1.
"""

import os
from dotenv import load_dotenv
from groq import Groq
from state import AnalystState

load_dotenv()

# Initialize the Groq client once
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def build_analysis_prompt(question: str, chunks: list[str]) -> str:
    context = "\n".join(f"- {chunk}" for chunk in chunks)

    return f"""You are a data analyst. Below is raw data retrieved from a database,
followed by a business question. All monetary amounts are in Indian Rupees (INR) —
always use ₹, never $ or "dollars".

Your job is to:
1. Extract the relevant numeric values from the data
2. Perform any needed calculations (totals, averages, comparisons, trends)
3. Show your work briefly, then state the final numeric answer clearly using ₹

Retrieved Data:
{context}

Question: {question}

Respond with your calculations and findings. Be precise with numbers.
If the data is insufficient to fully answer, say what's missing.
"""


def analysis_agent(state: AnalystState) -> dict:
    """
    Node function: takes retrieved_data + question, asks Groq Llama 3.1
    to do the analysis, and returns the result to update state["analysis"].
    """
    chunks = state["retrieved_data"]

    # If Data Agent already did a SQL aggregate/group-by calculation, skip
    # the LLM entirely — the numbers are already final and correct.
    # (Only the first chunk carries the "Pre-calculated" marker; group-by
    # results have indented list lines after it that don't.)
    if chunks and chunks[0].startswith("Pre-calculated"):
        print("📊 Analysis Agent: using pre-calculated values, skipping LLM.")
        return {"analysis": "\n".join(chunks)}

    print(f"📊 Analysis Agent: analyzing {len(chunks)} chunks...")

    prompt = build_analysis_prompt(state["question"], chunks)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a precise data analyst who shows your calculations."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )

    analysis_result = response.choices[0].message.content
    print("✅ Analysis Agent: analysis complete.")

    return {"analysis": analysis_result}

# Quick standalone test
if __name__ == "__main__":
    test_state: AnalystState = {
        "question": "What is the total amount received for flat bookings?",
        "retrieved_data": [
            "Sheet: CANCELLATION. FLAT NO: 1502. NAME: SHABNAM PARVEZ AHMED. AMT. RECVD: 500000",
            "Sheet: CANCELLATION. FLAT NO: 1503. NAME: RAHUL SHARMA. AMT. RECVD: 750000",
        ],
        "analysis": "",
        "final_report": "",
    }

    result = analysis_agent(test_state)
    print("\n📊 Analysis:")
    print(result["analysis"])