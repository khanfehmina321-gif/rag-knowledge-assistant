# AI Document Analyzer — Real World Project by Salt
import streamlit as st
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
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
    page_title="AI Document Analyzer",
    page_icon="📄",
    layout="wide"
)

st.title("📄 AI Document Analyzer")
st.markdown("**Upload any PDF and ask questions in plain English!**")
st.markdown("---")

# =====================
# SIDEBAR
# =====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/artificial-intelligence.png", width=80)
    st.title("How to use")
    st.markdown("""
    1. 📤 Upload a PDF file
    2. ⏳ Wait for processing
    3. ❓ Ask any question
    4. 🤖 Get AI answer!
    """)
    st.markdown("---")
    st.markdown("**Built by Salt** 🚀")
    st.markdown("*AI Engineer in making!*")

# =====================
# LLM SETUP
# =====================
@st.cache_resource
def load_llm():
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0.3)

@st.cache_resource
def load_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

# =====================
# PDF PROCESSING
# =====================
def process_pdf(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    
    # PDF load karo
    loader = PyPDFLoader(tmp_path)
    documents = loader.load()
    
    # Chunks mein todo
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = splitter.split_documents(documents)
    
    # Vector store banao
    embeddings = load_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)
    
    os.unlink(tmp_path)
    return vectorstore, len(documents)

# =====================
# ANSWER FUNCTION
# =====================
def get_answer(question, vectorstore):
    llm = load_llm()
    
    # Relevant chunks dhundo
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    relevant_docs = retriever.invoke(question)
    context = "\n\n".join([doc.page_content for doc in relevant_docs])
    
    # Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert document analyzer. 
        Answer questions based ONLY on the provided document context.
        If the answer is not in the document, say "This information is not in the document."
        Be clear, concise and helpful.
        
        Document Context:
        {context}"""),
        ("human", "{question}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    answer = chain.invoke({
        "context": context,
        "question": question
    })
    
    return answer, relevant_docs

# =====================
# MAIN UI
# =====================

# File upload
uploaded_file = st.file_uploader(
    "📤 Upload your PDF here",
    type=["pdf"],
    help="Upload any PDF document to analyze"
)

if uploaded_file:
    # Process PDF
    with st.spinner("🔄 Processing your PDF... Please wait!"):
        try:
            vectorstore, num_pages = process_pdf(uploaded_file)
            st.success(f"✅ PDF processed! **{num_pages} pages** analyzed successfully!")
            
            # Store in session
            st.session_state.vectorstore = vectorstore
            st.session_state.pdf_name = uploaded_file.name
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.stop()
    
    st.markdown("---")
    
    # Chat section
    st.subheader("💬 Ask questions about your document")
    
    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Show chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Question input
    question = st.chat_input("Ask anything about your PDF...")
    
    if question:
        # Show user question
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.messages.append({
            "role": "user",
            "content": question
        })
        
        # Get AI answer
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                answer, relevant_docs = get_answer(
                    question,
                    st.session_state.vectorstore
                )
            
            st.markdown(answer)
            
            # Show sources
            with st.expander("📚 View Sources"):
                for i, doc in enumerate(relevant_docs[:2]):
                    st.markdown(f"**Source {i+1}** (Page {doc.metadata.get('page', '?') + 1})")
                    st.markdown(f"_{doc.page_content[:200]}..._")
                    st.markdown("---")
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

else:
    # Welcome screen
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("📄 **Any PDF**\nLegal, Medical, Research, Business documents")
    
    with col2:
        st.info("🤖 **AI Powered**\nGroq + LLaMA 3.1 for fast accurate answers")
    
    with col3:
        st.info("💬 **Chat Interface**\nAsk multiple questions naturally")
    
    st.markdown("---")
    st.markdown("### 👆 Upload a PDF above to get started!")