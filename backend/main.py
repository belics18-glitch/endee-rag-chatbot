from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer
import os
import uuid
from knowledge_base import SAMPLE_DOCS

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

embedder = SentenceTransformer("all-MiniLM-L6-v2")

SYSTEM_PROMPT = """
You are a strict RAG assistant.

Rules:
1. Answer ONLY from the retrieved context.
2. Do NOT use outside knowledge.
3. If the answer is not in the context, reply exactly:
   "The answer is not available in the knowledge base."
4. Keep answers short and clear.
"""

chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]

VECTOR_DB = []

# ---------- CHUNK ----------
def chunk_text(text, size=200):
    return [text[i:i+size] for i in range(0, len(text), size)]

# ---------- EMBEDDING ----------
def embed(text):
    return embedder.encode(text).tolist()

# ---------- PRELOAD ----------
def preload():
    for doc in SAMPLE_DOCS:
        chunks = chunk_text(doc["content"])
        for chunk in chunks:
            VECTOR_DB.append({
                "id": str(uuid.uuid4()),
                "text": chunk,
                "vector": embed(chunk),
                "source": doc["title"]
            })

preload()

# ---------- SEARCH ----------
def search(query, top_k=2, threshold=0.75):
    q_vec = embed(query)

    scored = []
    for item in VECTOR_DB:
        score = sum(a * b for a, b in zip(q_vec, item["vector"]))
        scored.append((score, item))

    scored.sort(reverse=True, key=lambda x: x[0])

    # 🔥 IMPORTANT: only keep HIGH similarity
    filtered = []
    for score, item in scored:
        if score >= threshold:
            filtered.append(item)

    return filtered[:top_k]

# ---------- ROUTES ----------
@app.get("/")
def home():
    return {"status": "running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(req: ChatRequest):
    user_msg = req.message.strip()

    if not user_msg:
        return {
            "reply": "Message cannot be empty.",
            "matched_chunks": []
        }

    results = search(user_msg, top_k=2, threshold=0.75)

    # 🚨 HARD STOP — NO LLM CALL
    if not results:
        return {
            "reply": "The answer is not available in the knowledge base.",
            "matched_chunks": []
        }

    matched_chunks = [r["text"] for r in results]
    context = "\n".join(matched_chunks)

    rag_prompt = f"""
Answer ONLY from the context.

Context:
{context}

Question:
{user_msg}
"""

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": rag_prompt}
        ],
        temperature=0.0
    )

    reply = completion.choices[0].message.content

    return {
        "reply": reply,
        "matched_chunks": matched_chunks
    }

@app.post("/clear")
def clear():
    return {"message": "No memory to clear"}