from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

def load_knowledge() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "Knowledge.txt")  # exact filename
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return ""

@app.get("/")
def home():
    return {
        "status": "Backend is running",
        "project": "Endee RAG Chatbot"
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "Backend is awake"
    }

@app.get("/check-env")
def check_env():
    return {
        "groq_key_loaded": bool(os.getenv("GROQ_API_KEY"))
    }

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        knowledge = load_knowledge()

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an intelligent AI assistant for an Endee-powered RAG chatbot project. "
                    "Answer clearly, professionally, and use the provided context when relevant."
                )
            },
            {
                "role": "system",
                "content": f"Knowledge:\n{knowledge[:4000] if knowledge else 'No knowledge file found.'}"
            },
            {
                "role": "user",
                "content": req.message
            }
        ]

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
        )

        return {"reply": completion.choices[0].message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))