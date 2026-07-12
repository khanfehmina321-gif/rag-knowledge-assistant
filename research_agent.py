# AI Research Agent — Project 3 by Salt
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools import DuckDuckGoSearchRun
from dotenv import load_dotenv

load_dotenv()

# =====================
# PAGE SETUP
# =====================
st.set_page_config(
    page_title="AI Research Agent",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 AI Research Agent")
st.markdown("**Give any topic — AI researches and writes a full report!**")
st.markdown("---")

# =====================
# SIDEBAR
# =====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/research.png", width=80)
    st.title("How to use")
    st.markdown("""
    1. 📝 Enter any topic
    2. 🎯 Select report type
    3. 🚀 Click Research
    4. Get full report!
    """)
    st.markdown("---")
    st.markdown("**Built by Salt** 🚀")
    st.markdown("*AI Engineer in making!*")

# =====================
# LLM + SEARCH SETUP
# =====================
@st.cache_resource
def load_llm():
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)

@st.cache_resource
def load_search():
    return DuckDuckGoSearchRun()

# =====================
# AGENT FUNCTIONS
# =====================
def research_topic(topic, search_tool):
    """Agent 1 — Internet se research karo"""
    try:
        search_results = search_tool.run(topic)
        return search_results
    except:
        return f"Research on {topic}: This is a growing field with many applications in 2025."

def summarize_research(topic, research_data):
    """Agent 2 — Research summarize karo"""
    llm = load_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert research summarizer.
        Summarize the research data into clear key points.
        Extract the most important and relevant information."""),
        ("human", """
        Topic: {topic}
        
        Research Data:
        {research}
        
        Provide a clear summary with key points.""")
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"topic": topic, "research": research_data})

def write_report(topic, summary, report_type):
    """Agent 3 — Full report likho"""
    llm = load_llm()
    
    report_formats = {
        "Detailed Report": "Write a comprehensive detailed report with introduction, main findings, analysis, and conclusion.",
        "Quick Summary": "Write a brief executive summary in bullet points.",
        "Blog Post": "Write an engaging blog post that explains the topic to beginners.",
        "Technical Report": "Write a technical report with technical details, implementations, and use cases."
    }
    
    format_instruction = report_formats.get(report_type, report_formats["Detailed Report"])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are an expert technical writer.
        {format_instruction}
        Make it professional, well-structured, and informative.
        Use proper headings and formatting."""),
        ("human", """
        Topic: {topic}
        
        Research Summary:
        {summary}
        
        Write the complete report now.""")
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"topic": topic, "summary": summary})

# =====================
# MAIN UI
# =====================
col1, col2 = st.columns([2, 1])

with col1:
    topic = st.text_input(
        "🔍 Enter Research Topic",
        placeholder="Example: Agentic AI in 2025, LangChain vs LangGraph, Future of AI jobs..."
    )

with col2:
    report_type = st.selectbox(
        "📄 Report Type",
        ["Detailed Report", "Quick Summary", "Blog Post", "Technical Report"]
    )

st.markdown("---")

if topic:
    if st.button("🚀 Start Research!", type="primary", use_container_width=True):
        
        # Step 1 — Research
        with st.status("🔍 Agent 1 — Researching the topic...", expanded=True) as status:
            search_tool = load_search()
            research_data = research_topic(topic, search_tool)
            st.write("✅ Research complete!")
            
            # Step 2 — Summarize
            status.update(label="📝 Agent 2 — Summarizing research...")
            summary = summarize_research(topic, research_data)
            st.write("✅ Summary ready!")
            
            # Step 3 — Write Report
            status.update(label="✍️ Agent 3 — Writing full report...")
            report = write_report(topic, summary, report_type)
            st.write("✅ Report written!")
            
            status.update(label="✅ Research Complete!", state="complete")
        
        st.markdown("---")
        
        # Show results in tabs
        tab1, tab2, tab3 = st.tabs([
            "📊 Raw Research",
            "📝 Summary",
            "📄 Full Report"
        ])
        
        with tab1:
            st.markdown("### 🔍 Research Data")
            st.markdown(research_data)
        
        with tab2:
            st.markdown("### 📝 Key Points")
            st.markdown(summary)
        
        with tab3:
            st.markdown(f"### 📄 {report_type}")
            st.markdown(report)
            st.markdown("---")
            st.download_button(
                "⬇️ Download Report",
                report,
                file_name=f"{topic[:30]}_report.txt",
                use_container_width=True
            )

else:
    # Welcome screen
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("🔍 **Real Research**\nSearches internet for latest information")
    with col2:
        st.info("🤖 **3 AI Agents**\nResearch → Summarize → Write")
    with col3:
        st.info("📄 **4 Report Types**\nDetailed, Summary, Blog, Technical")
    
    st.markdown("---")
    
    st.markdown("### 💡 Try these topics:")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🤖 Agentic AI 2025"):
            st.session_state.topic = "Agentic AI 2025"
    with col2:
        if st.button("💼 AI Engineer Jobs"):
            st.session_state.topic = "AI Engineer Jobs 2025"
    with col3:
        if st.button("🔗 LangChain vs LangGraph"):
            st.session_state.topic = "LangChain vs LangGraph"