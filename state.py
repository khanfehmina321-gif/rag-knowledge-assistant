"""
State design for the AI Business Analyst multi-agent system.

This defines the "shared whiteboard" that flows through all agents:
Data Agent -> Analysis Agent -> Report Agent
"""

from typing import TypedDict


class AnalystState(TypedDict):
    # The original question the user asked
    question: str

    # Raw data chunks retrieved from the database (filled by Data Agent)
    retrieved_data: list[str]

    # Numbers/calculations extracted or computed (filled by Analysis Agent)
    analysis: str

    # The final, polished answer shown to the user (filled by Report Agent)
    final_report: str