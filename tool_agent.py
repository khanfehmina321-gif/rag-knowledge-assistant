# Tool Agent — by Salt
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

# AI model banao
llm = ChatGroq(model="llama-3.1-8b-instant")

# =====================
# TOOLS BANAO
# =====================

# Tool 1 — Calculator
@tool
def calculate(expression: str) -> str:
    """Calculate a math expression. Example: '15 * 24'"""
    try:
        result = eval(expression)
        return f"Answer: {result}"
    except:
        return "Error: Invalid expression"

# Tool 2 — Greeting tool
@tool
def greet(name: str) -> str:
    """Greet a person by their name."""
    return f"Hello {name}! Aap AI engineer ban rahe ho — bahut acha! 🚀"

# Tool 3 — AI learning tip
@tool
def ai_tip(topic: str) -> str:
    """Give a tip about an AI topic like LangChain, LangGraph, etc."""
    tips = {
        "langchain": "LangChain mein pipe operator | sabse important hai!",
        "langgraph": "LangGraph mein State, Node aur Edge — bas teen cheezein yaad rakho!",
        "crewai": "CrewAI mein multiple AI agents ek team ki tarah kaam karte hain!",
        "default": f"{topic} ek bahut important AI concept hai — keep learning!"
    }
    return tips.get(topic.lower(), tips["default"])

# =====================
# AI KO TOOLS DO
# =====================
tools = [calculate, greet, ai_tip]
llm_with_tools = llm.bind_tools(tools)

# =====================
# AGENT LOOP
# =====================
def run_agent(user_message: str):
    print(f"\nTum: {user_message}")
    print("-" * 40)
    
    messages = [HumanMessage(content=user_message)]
    
    # AI ko message bhejo
    response = llm_with_tools.invoke(messages)
    
    # Kya AI ne tool use kiya?
    if response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            print(f"🔧 AI ne tool choose kiya: {tool_name}")
            print(f"📥 Arguments: {tool_args}")
            
            # Sahi tool chalao
            if tool_name == "calculate":
                result = calculate.invoke(tool_args)
            elif tool_name == "greet":
                result = greet.invoke(tool_args)
            elif tool_name == "ai_tip":
                result = ai_tip.invoke(tool_args)
            
            print(f"✅ Tool result: {result}")
    else:
        # Koi tool nahi — seedha jawab
        print(f"🤖 AI ka seedha jawab: {response.content}")

# =====================
# TEST KARO
# =====================
run_agent("25 * 4 calculate karo")
run_agent("Mera naam Salt hai — greet karo")
run_agent("LangGraph ke baare mein tip do")
run_agent("Tera naam kya hai?")
