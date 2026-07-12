# AI Job Application Assistant — Project 2 by Salt
import streamlit as st
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import tempfile
import os

load_dotenv()

# =====================
# PAGE SETUP
# =====================
st.set_page_config(
    page_title="AI Job Application Assistant",
    page_icon="💼",
    layout="wide"
)

st.title("💼 AI Job Application Assistant")
st.markdown("**Upload your resume, paste job description — AI does the rest!**")
st.markdown("---")

# =====================
# SIDEBAR
# =====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/resume.png", width=80)
    st.title("How to use")
    st.markdown("""
    1. 📤 Upload your Resume PDF
    2. 📝 Paste Job Description
    3. 🤖 Click Analyze
    4. Get:
       - ✅ Resume Analysis
       - 📄 Cover Letter
       - ❓ Interview Questions
    """)
    st.markdown("---")
    st.markdown("**Built by Salt** 🚀")
    st.markdown("*AI Engineer in making!*")

# =====================
# LLM SETUP
# =====================
@st.cache_resource
def load_llm():
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)

# =====================
# PDF READER
# =====================
def read_pdf(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    loader = PyPDFLoader(tmp_path)
    documents = loader.load()
    os.unlink(tmp_path)
    return "\n".join([doc.page_content for doc in documents])

# =====================
# AI FUNCTIONS
# =====================
def analyze_resume(resume_text, job_description):
    llm = load_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert HR consultant and career advisor.
        Analyze the resume against the job description and provide:
        1. Match percentage (how well resume fits the job)
        2. Strong points (what matches well)
        3. Missing skills (what is lacking)
        4. Improvement suggestions
        Be specific and encouraging."""),
        ("human", """
        RESUME:
        {resume}
        
        JOB DESCRIPTION:
        {job}
        
        Provide a detailed analysis.""")
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"resume": resume_text, "job": job_description})

def generate_cover_letter(resume_text, job_description):
    llm = load_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert cover letter writer.
        Write a professional, personalized cover letter based on the resume and job description.
        Make it compelling, specific, and highlight the best matching skills.
        Format: Professional business letter format."""),
        ("human", """
        RESUME:
        {resume}
        
        JOB DESCRIPTION:
        {job}
        
        Write a tailored cover letter.""")
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"resume": resume_text, "job": job_description})

def generate_interview_questions(resume_text, job_description):
    llm = load_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert interview coach.
        Generate 10 likely interview questions based on the resume and job description.
        Include:
        - 3 technical questions
        - 3 behavioral questions  
        - 2 situational questions
        - 2 role-specific questions
        Also provide brief tips for answering each question."""),
        ("human", """
        RESUME:
        {resume}
        
        JOB DESCRIPTION:
        {job}
        
        Generate interview questions with tips.""")
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"resume": resume_text, "job": job_description})

# =====================
# MAIN UI
# =====================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📤 Upload Your Resume")
    uploaded_resume = st.file_uploader(
        "Upload Resume PDF",
        type=["pdf"],
        help="Upload your resume in PDF format"
    )
    if uploaded_resume:
        st.success("✅ Resume uploaded!")

with col2:
    st.subheader("📝 Paste Job Description")
    job_description = st.text_area(
        "Job Description",
        height=200,
        placeholder="Paste the job description here...\n\nExample:\nWe are looking for an AI Engineer with experience in LangChain, Python, and LLMs..."
    )

st.markdown("---")

# Analyze button
if uploaded_resume and job_description:
    if st.button("🚀 Analyze & Generate", type="primary", use_container_width=True):
        
        # Read resume
        with st.spinner("📖 Reading your resume..."):
            resume_text = read_pdf(uploaded_resume)
        
        # Create tabs
        tab1, tab2, tab3 = st.tabs([
            "📊 Resume Analysis",
            "📄 Cover Letter",
            "❓ Interview Questions"
        ])
        
        with tab1:
            with st.spinner("🔍 Analyzing your resume..."):
                analysis = analyze_resume(resume_text, job_description)
            st.markdown("### 📊 Resume Analysis")
            st.markdown(analysis)
            st.download_button(
                "⬇️ Download Analysis",
                analysis,
                file_name="resume_analysis.txt"
            )
        
        with tab2:
            with st.spinner("✍️ Writing your cover letter..."):
                cover_letter = generate_cover_letter(resume_text, job_description)
            st.markdown("### 📄 Your Cover Letter")
            st.markdown(cover_letter)
            st.download_button(
                "⬇️ Download Cover Letter",
                cover_letter,
                file_name="cover_letter.txt"
            )
        
        with tab3:
            with st.spinner("🎯 Preparing interview questions..."):
                questions = generate_interview_questions(resume_text, job_description)
            st.markdown("### ❓ Interview Preparation")
            st.markdown(questions)
            st.download_button(
                "⬇️ Download Questions",
                questions,
                file_name="interview_questions.txt"
            )
        
        st.success("✅ All done! Good luck with your application! 🍀")

else:
    if not uploaded_resume:
        st.warning("👆 Please upload your resume PDF")
    if not job_description:
        st.warning("👆 Please paste the job description")