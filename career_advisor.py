# AI Career Advisor — Portfolio Project by Salt
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)

# =====================
# TOOLS
# =====================

@tool
def analyze_skills(skills: str) -> str:
    """Analyze a person's skills and rate their AI readiness."""
    ai_skills = ["python", "langchain", "langgraph", "machine learning", 
                 "nlp", "api", "llm", "openai", "groq"]
    
    user_skills = skills.lower().split(",")
    matched = [s for s in ai_skills if any(s in u for u in user_skills)]
    score = len(matched) * 10
    
    return f"""
Skills Analysis:
✅ AI-relevant skills found: {', '.join(matched) if matched else 'None yet'}
📊 AI Readiness Score: {score}/100
💡 Skills to add: LangChain, LangGraph, RAG, Groq API
    """

@tool
def recommend_jobs(experience: str) -> str:
    """Recommend AI jobs based on experience level."""
    exp = experience.lower()
    
    if "fresher" in exp or "0" in exp or "beginner" in exp:
        return """
🎯 Recommended Jobs for Beginners:
1. Junior AI Engineer — startups
2. Prompt Engineer — any company
3. AI Integration Developer
4. Chatbot Developer
5. AI Tools Specialist

💰 Salary Range: ₹4-8 LPA (India) | $40-60k (Remote)
🌐 Best platforms: Wellfound, LinkedIn, Upwork
        """
    elif "1" in exp or "2" in exp:
        return """
🎯 Recommended Jobs for 1-2 years experience:
1. AI Engineer
2. LLM Application Developer  
3. Agentic AI Developer ⭐ (hottest right now!)
4. ML Engineer
5. AI Product Engineer

💰 Salary Range: ₹8-18 LPA (India) | $60-100k (Remote)
🌐 Best platforms: LinkedIn, Toptal, Turing
        """
    else:
        return """
🎯 Recommended Jobs for Senior level:
1. Senior AI Engineer
2. AI Architect
3. Head of AI
4. AI Consultant

💰 Salary Range: ₹20+ LPA (India) | $100k+ (Remote)
        """

@tool
def interview_tips(topic: str) -> str:
    """Give interview tips for AI engineering topics."""
    tips = {
        "langchain": """
📚 LangChain Interview Tips:
Q: What is LCEL? → pipe operator | joining chains
Q: What is a chain? → prompt | llm | parser
Q: What is RAG? → Retrieval Augmented Generation
Q: Memory types? → ConversationBufferMemory, Summary
        """,
        "langgraph": """
📚 LangGraph Interview Tips:
Q: What is State? → shared memory across nodes
Q: What is a Node? → a function that does one task
Q: What is an Edge? → connection between nodes
Q: Conditional edge? → AI decides which path to take
        """,
        "general": """
📚 General AI Interview Tips:
Q: What is an LLM? → Large Language Model trained on text
Q: What is prompt engineering? → crafting inputs for better AI output
Q: What is an AI agent? → AI that can reason, use tools, take actions
Q: Difference RAG vs finetuning? → RAG adds knowledge, finetuning changes behavior
        """
    }
    return tips.get(topic.lower(), tips["general"])

@tool  
def create_study_plan(days: str) -> str:
    """Create a personalized AI study plan based on number of days available."""
    d = int(days) if days.isdigit() else 30
    
    if d <= 7:
        return """
📅 7-Day Intensive Plan:
Day 1-2: LangChain basics + first project
Day 3-4: LangGraph + agents
Day 5-6: Portfolio project
Day 7: GitHub + Apply!
        """
    elif d <= 30:
        return """
📅 30-Day Job-Ready Plan:
Week 1: LangChain + Groq API + 2 projects
Week 2: LangGraph + Tool agents + RAG
Week 3: Portfolio project + GitHub
Week 4: Apply daily — 10 jobs/day!

🎯 Target: Junior AI Engineer / Prompt Engineer
        """
    else:
        return """
📅 60-Day Expert Plan:
Month 1: Full stack AI — LangChain, LangGraph, CrewAI, RAG
Month 2: 3 portfolio projects + open source contribution + job hunt

🎯 Target: AI Engineer / Agentic AI Developer
        """

# =====================
# TOOLS LIST
# =====================
tools = [analyze_skills, recommend_jobs, interview_tips, create_study_plan]
llm_with_tools = llm.bind_tools(tools)

# =====================
# SYSTEM PROMPT
# =====================
system = SystemMessage(content="""You are an expert AI Career Advisor helping people 
get jobs in AI engineering. You have access to tools for:
- Analyzing skills
- Recommending jobs  
- Giving interview tips
- Creating study plans

Always be encouraging and practical. Use tools when relevant.""")

# =====================
# AGENT LOOP
# =====================
def run_career_advisor():
    print("\n" + "="*50)
    print("🤖 AI CAREER ADVISOR — by Salt")
    print("="*50)
    print("Main aapki AI career mein help karunga!")
    print("Type 'quit' to exit\n")
    
    history = [system]
    
    while True:
        user_input = input("Aap: ").strip()
        
        if user_input.lower() == "quit":
            print("\n👋 Best of luck with your AI career! You've got this! 🚀")
            break
            
        if not user_input:
            continue
        
        history.append(HumanMessage(content=user_input))
        response = llm_with_tools.invoke(history)
        
        # Tool use kiya?
        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                print(f"\n🔧 Tool use kar raha hoon: {tool_name}")
                
                if tool_name == "analyze_skills":
                    result = analyze_skills.invoke(tool_args)
                elif tool_name == "recommend_jobs":
                    result = recommend_jobs.invoke(tool_args)
                elif tool_name == "interview_tips":
                    result = interview_tips.invoke(tool_args)
                elif tool_name == "create_study_plan":
                    result = create_study_plan.invoke(tool_args)
                else:
                    result = "Tool not found"
                    
                print(result)
                history.append(AIMessage(content=str(result)))
        else:
            print(f"\n🤖 Advisor: {response.content}")
            history.append(AIMessage(content=response.content))
        
        print()

# =====================
# START!
# =====================
run_career_advisor()