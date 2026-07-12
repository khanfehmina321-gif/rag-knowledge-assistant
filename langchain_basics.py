# My first LangChain program — by Salt
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

# Load API key
load_dotenv()

# Step 1: Model banao
llm = ChatGroq(model="llama-3.1-8b-instant")

# Step 2: Prompt template banao
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI tutor. Be concise and friendly."),
    ("human", "{question}")
])

# Step 3: Chain banao — prompt | llm | output
chain = prompt | llm | StrOutputParser()

# Step 4: Chain run karo
response = chain.invoke({
    "question": "I am Salt. What is LangChain in 3 simple lines?"
})

print("AI says:", response)