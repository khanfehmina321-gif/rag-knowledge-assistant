# Memory Chatbot — by Salt
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

# API key load karo
load_dotenv()

# AI model banao
llm = ChatGroq(model="llama-3.1-8b-instant")

# Memory — poori conversation yahan store hogi
history = []

print("Chatbot ready! 'quit' likho band karne ke liye\n")

# Loop — jab tak quit na karo
while True:

    # Tumhara message lo
    user_input = input("Tum: ")

    # Agar quit likha toh band karo
    if user_input.lower() == "quit":
        print("Goodbye Salt! 👋")
        break

    # Tumhara message history mein save karo
    history.append(HumanMessage(content=user_input))

    # Poori history AI ko bhejo
    response = llm.invoke(history)

    # AI ka reply history mein save karo
    history.append(AIMessage(content=response.content))

    # AI ka reply dikhao
    print(f"AI: {response.content}\n")