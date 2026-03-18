from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer
import numpy as np
import os
import uuid
import re
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
The answer is not available in the knowledge base.
4. Keep answers short and clear.
"""

VECTOR_DB = []

STOPWORDS = {
    "what", "is", "the", "a", "an", "of", "and", "to", "in", "for",
    "how", "does", "this", "that", "it", "on", "with", "used", "are"
}

def tokenize(text: str):
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}

# ---------- CHUNK ----------
def chunk_text(text, size=200):
    return [text[i:i + size] for i in range(0, len(text), size)]

# ---------- EMBEDDING ----------
def embed(text):
    vec = embedder.encode(text, normalize_embeddings=True)
    return vec.tolist()

# ---------- PRELOAD ----------
def preload():
    for doc in SAMPLE_DOCS:
        chunks = chunk_text(doc["content"])
        for chunk in chunks:
            VECTOR_DB.append({
                "id": str(uuid.uuid4()),
                "text": chunk,
                "vector": embed(chunk),
                "source": doc["title"],
                "tokens": tokenize(chunk)
            })

preload()

# ---------- SEARCH ----------
def search(query, top_k=2, threshold=0.62, min_keyword_overlap=1):
    query_tokens = tokenize(query)
    q_vec = np.array(embed(query), dtype=np.float32)

    scored = []
    for item in VECTOR_DB:
        item_vec = np.array(item["vector"], dtype=np.float32)
        score = float(np.dot(q_vec, item_vec))  # cosine similarity due to normalized embeddings
        overlap = len(query_tokens.intersection(item["tokens"]))

        scored.append({
            "score": score,
            "overlap": overlap,
            "item": item
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    print("TOP RESULTS:", [
        {
            "score": round(x["score"], 4),
            "overlap": x["overlap"],
            "source": x["item"]["source"]
        }
        for x in scored[:5]
    ])

    filtered = []
    for entry in scored:
        if entry["score"] >= threshold and entry["overlap"] >= min_keyword_overlap:
            filtered.append(entry["item"])

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

    results = search(user_msg, top_k=2, threshold=0.62, min_keyword_overlap=1)

    # HARD BLOCK: if retrieval is not confident enough, do not call LLM
    if not results:
        return {
            "reply": "The answer is not available in the knowledge base.",
            "matched_chunks": []
        }

    matched_chunks = [r["text"] for r in results]
    context = "\n".join(matched_chunks)

    rag_prompt = f"""
Answer ONLY from the context below.

Context:
{context}

Question:
{user_msg}

If the answer is not clearly present in the context, reply exactly:
The answer is not available in the knowledge base.
"""

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": rag_prompt}
        ],
        temperature=0.0
    )

    reply = completion.choices[0].message.content or "The answer is not available in the knowledge base."

    return {
        "reply": reply,
        "matched_chunks": matched_chunks
    }

@app.post("/clear")
def clear():
    return {"message": "No memory to clear"}