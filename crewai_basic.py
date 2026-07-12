# My first CrewAI program — by Salt
from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
import os

load_dotenv()

# =====================
# LLM — sahi tarike se
# =====================
llm = LLM(
    model="groq/llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    api_base="https://api.groq.com/openai/v1",
    temperature=0.7
)

# =====================
# AGENTS BANAO
# =====================
researcher = Agent(
    role="AI Research Specialist",
    goal="Research topics clearly and find key points",
    backstory="You are an expert researcher who finds the most important information about any topic.",
    llm=llm,
    verbose=True
)

writer = Agent(
    role="Content Writer",
    goal="Write clear and simple content based on research",
    backstory="You are a skilled writer who explains complex topics in simple words.",
    llm=llm,
    verbose=True
)

# =====================
# TASKS BANAO
# =====================
research_task = Task(
    description="Research and find 3 key points: What is Agentic AI and why is it important for jobs in 2025?",
    expected_output="A clear summary with 3 key points about Agentic AI",
    agent=researcher
)

writing_task = Task(
    description="Using the research, write a simple 5 line explanation of Agentic AI for beginners.",
    expected_output="5 simple lines explaining Agentic AI",
    agent=writer
)

# =====================
# CREW BANAO
# =====================
crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, writing_task],
    verbose=True
)

# =====================
# CHALAO!
# =====================
print("\n🚀 CrewAI starting!\n")
print("=" * 50)

result = crew.kickoff()

print("\n" + "=" * 50)
print("✅ FINAL OUTPUT:")
print("=" * 50)
print(result)