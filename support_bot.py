# Smart Customer Support Bot — Project 4 by Salt
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

load_dotenv()

# =====================
# PAGE SETUP
# =====================
st.set_page_config(
    page_title="Smart Customer Support Bot",
    page_icon="💬",
    layout="wide"
)

# =====================
# LLM SETUP
# =====================
@st.cache_resource
def load_llm():
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)

# =====================
# SIDEBAR — Company Setup
# =====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/customer-support.png", width=80)
    st.title("🏢 Company Setup")
    st.markdown("---")
    
    company_name = st.text_input(
        "Company Name",
        placeholder="Example: TechCorp, Amazon, Zomato..."
    )
    
    company_type = st.selectbox(
        "Company Type",
        [
            "E-commerce",
            "Food Delivery",
            "Software/Tech",
            "Banking",
            "Healthcare",
            "Education",
            "Travel"
        ]
    )
    
    company_info = st.text_area(
        "Company Information",
        height=150,
        placeholder="""Tell AI about your company:
- What products/services do you offer?
- What are your policies?
- Working hours?
- Any special offers?"""
    )
    
    bot_name = st.text_input(
        "Bot Name",
        value="Alex",
        placeholder="Name your support agent..."
    )
    
    bot_tone = st.selectbox(
        "Bot Personality",
        ["Professional", "Friendly", "Formal", "Casual", "Enthusiastic"]
    )
    
    st.markdown("---")
    
    if st.button("🚀 Create Support Bot!", type="primary", use_container_width=True):
        if company_name and company_info:
            st.session_state.bot_created = True
            st.session_state.company_name = company_name
            st.session_state.company_type = company_type
            st.session_state.company_info = company_info
            st.session_state.bot_name = bot_name
            st.session_state.bot_tone = bot_tone
            st.session_state.messages = []
            st.success(f"✅ {bot_name} is ready!")
        else:
            st.error("Please fill company name and info!")
    
    st.markdown("---")
    st.markdown("**Built by Salt** 🚀")
    st.markdown("*AI Engineer in making!*")

# =====================
# MAIN CHAT UI
# =====================
if "bot_created" not in st.session_state:
    # Welcome screen
    st.title("💬 Smart Customer Support Bot")
    st.markdown("**Create AI-powered support agents for any company!**")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("🏢 **Any Company**\nE-commerce, Food, Banking, Healthcare...")
    with col2:
        st.info("🤖 **Custom AI Agent**\nPersonalized name, tone and knowledge")
    with col3:
        st.info("💬 **Smart Chat**\nMemory + Context aware responses")
    
    st.markdown("---")
    st.markdown("### 👈 Fill company details in the sidebar to get started!")
    
    # Example companies
    st.markdown("### 💡 Try these examples:")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        **🛒 Zomato Support**
        - Food delivery queries
        - Order tracking
        - Refund policies
        """)
    with col2:
        st.markdown("""
        **💻 TechCorp Support**
        - Software issues
        - Billing queries
        - Technical help
        """)
    with col3:
        st.markdown("""
        **🏥 HealthCare Support**
        - Appointment booking
        - Insurance queries
        - Doctor availability
        """)

else:
    # Chat interface
    company = st.session_state.company_name
    bot = st.session_state.bot_name
    tone = st.session_state.bot_tone
    info = st.session_state.company_info
    
    st.title(f"💬 {company} Customer Support")
    st.markdown(f"**Powered by {bot} — AI Support Agent**")
    st.markdown("---")
    
    # System prompt
    system_prompt = f"""You are {bot}, a {tone.lower()} customer support agent for {company}.

Company Type: {st.session_state.company_type}

Company Information:
{info}

Your rules:
1. Always be {tone.lower()} and helpful
2. Answer ONLY based on the company information provided
3. If you don't know something, say "Let me check that for you" and ask them to contact us directly
4. Always refer to yourself as {bot} from {company}
5. Keep responses clear and concise
6. End responses with "Is there anything else I can help you with?"

Never make up information not provided about the company."""

    # Initialize messages
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Show welcome message
    if not st.session_state.messages:
        welcome = f"Hello! I'm {bot}, your {company} support agent. How can I help you today? 😊"
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(welcome)
    
    # Show chat history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg["content"])
    
    # Chat input
    user_input = st.chat_input(f"Ask {bot} anything...")
    
    if user_input:
        # Show user message
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Build conversation history
        history = []
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                history.append(HumanMessage(content=msg["content"]))
            else:
                history.append(AIMessage(content=msg["content"]))
        
        # Get AI response
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(f"{bot} is typing..."):
                llm = load_llm()
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", "{input}")
                ])
                
                chain = prompt | llm | StrOutputParser()
                
                response = chain.invoke({
                    "input": user_input
                })
            
            st.markdown(response)
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })
    
    # Clear chat button
    if st.session_state.messages:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()