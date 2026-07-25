"""
Builds the LangGraph pipeline: Data Agent -> Analysis Agent -> Report Agent
"""

from langgraph.graph import StateGraph, END
from state import AnalystState
from data_agent import data_agent
from analysis_agent import analysis_agent
from report_agent import report_agent


def build_graph():
    graph = StateGraph(AnalystState)

    # Add each agent as a node
    graph.add_node("data_agent", data_agent)
    graph.add_node("analysis_agent", analysis_agent)
    graph.add_node("report_agent", report_agent)

    # Define the flow: data -> analysis -> report -> end
    graph.set_entry_point("data_agent")
    graph.add_edge("data_agent", "analysis_agent")
    graph.add_edge("analysis_agent", "report_agent")
    graph.add_edge("report_agent", END)

    return graph.compile()


# Quick standalone test — run the full pipeline end-to-end
if __name__ == "__main__":
    app = build_graph()

    initial_state: AnalystState = {
        "question": "How many bookings are there in total, and what is the total amount received for flat bookings?",
        "retrieved_data": [],
        "analysis": "",
        "final_report": "",
    }

    result = app.invoke(initial_state)

    print("\n" + "=" * 50)
    print("FINAL REPORT")
    print("=" * 50)
    print(result["final_report"])