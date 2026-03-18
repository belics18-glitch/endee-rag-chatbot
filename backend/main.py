from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

class ChatRequest(BaseModel):
    message: str

# Stores chat history in server memory
chat_history = [
    {
        "role": "system",
        "content": "You are a helpful AI assistant. Answer clearly and briefly."
    }
]

@app.get("/")
def home():
    return {"status": "Backend is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(req: ChatRequest):
    global chat_history

    try:
        user_message = req.message.strip()

        if not user_message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        # Add user message to memory
        chat_history.append({
            "role": "user",
            "content": user_message
        })

        # Keep only recent messages to avoid too much token usage
        if len(chat_history) > 21:
            chat_history = [chat_history[0]] + chat_history[-20:]

        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=chat_history
        )

        reply = completion.choices[0].message.content

        # Add assistant reply to memory
        chat_history.append({
            "role": "assistant",
            "content": reply
        })

        return {
            "reply": reply
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear")
def clear_chat():
    global chat_history

    chat_history = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant. Answer clearly and briefly."
        }
    ]

    return {"message": "Chat history cleared successfully"}