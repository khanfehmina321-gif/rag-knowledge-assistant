# My first AI program using Groq — by Salt
from groq import Groq
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()

# Connect to Groq
client = Groq()

# Send message to AI
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",  # free and fast model
    messages=[
        {"role": "user", "content": "Give me a daily study plan for RAG."},
        {"role": "user",   "content": "Hello! I am Salt. I am learning AI. Encourage me!"}
    ]
)

# Print the reply
print("AI says:", response.choices[0].message.content)