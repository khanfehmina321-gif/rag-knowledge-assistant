# My first LangGraph program — by Salt
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from typing import TypedDict, List

load_dotenv()

llm = ChatGroq(model="llama-3.1-8b-instant")

# Step 1 — State banao
# State = AI ki memory — har step mein kya ho raha hai
class State(TypedDict):
    messages: List
    step: int

# Step 2 — Node banao
# Node = ek kaam karne wala agent
def ai_node(state: State):
    print(f"\n🤖 AI soch raha hai... (Step {state['step']})")
    
    response = llm.invoke(state["messages"])
    
    # State update karo
    state["messages"].append(AIMessage(content=response.content))
    state["step"] += 1
    
    print(f"AI: {response.content}")
    return state

def check_node(state: State):
    print(f"\n🔍 Check kar raha hai...")
    # Agar 2 steps ho gaye toh band karo
    if state["step"] >= 2:
        print("✅ Done!")
        return "end"
    return "continue"

# Step 3 — Graph banao
graph = StateGraph(State)

# Nodes add karo
graph.add_node("ai", ai_node)

# Edges add karo — kaunsa node kahan jaayega
graph.set_entry_point("ai")
graph.add_conditional_edges(
    "ai",
    check_node,
    {
        "continue": "ai",  # dobara ai node par jao
        "end": END          # band karo
    }
)

# Graph compile karo
app = graph.compile()

# Step 4 — Run karo
print("🚀 LangGraph start!\n")

result = app.invoke({
    "messages": [HumanMessage(content="Mera naam Salt hai. Mujhe AI engineer banna hai. 2 tips do.")],
    "step": 0
})

print("\n✅ Graph complete!")