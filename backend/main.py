from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer
import os
import uuid
from typing import List

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Models ----------
class ChatRequest(BaseModel):
    message: str

class IngestRequest(BaseModel):
    title: str
    content: str

# ---------- LLM ----------
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY is missing")

client = OpenAI(
    api_key=groq_api_key,
    base_url="https://api.groq.com/openai/v1",
)

# ---------- Embedding Model ----------
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ---------- Simple session memory ----------
SYSTEM_PROMPT = (
    "You are a helpful RAG assistant. "
    "Answer only from the provided retrieved context when possible. "
    "If the answer is not in the context, say that clearly."
)

chat_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

# ---------- Endee Adapter ----------
# Replace these methods with your actual Endee integration.
# The rest of the code can remain unchanged.
class EndeeAdapter:
    def __init__(self):
        # Initialize your Endee connection here
        # Example: create/open collection or index
        pass

    def upsert_chunks(self, items: List[dict]):
        """
        items format:
        [
            {
                "id": "...",
                "text": "...",
                "vector": [...],
                "metadata": {"source": "...", "chunk_index": 0}
            }
        ]
        """
        # TODO: Replace with actual Endee upsert/index code
        # For now, this stores in fallback local memory so app works
        global LOCAL_VECTOR_STORE
        LOCAL_VECTOR_STORE.extend(items)

    def search(self, query_vector: List[float], top_k: int = 3) -> List[dict]:
        # TODO: Replace with actual Endee similarity search
        # Fallback local cosine-like dot similarity
        scored = []
        for item in LOCAL_VECTOR_STORE:
            score = sum(a * b for a, b in zip(query_vector, item["vector"]))
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

LOCAL_VECTOR_STORE = []
endee = EndeeAdapter()

# ---------- Helpers ----------
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def embed_text(text: str) -> List[float]:
    return embedder.encode(text).tolist()

def build_context(chunks: List[dict]) -> str:
    return "\n\n".join(
        [f"[Source: {c['metadata'].get('source', 'unknown')}]\n{c['text']}" for c in chunks]
    )

# ---------- Routes ----------
@app.get("/")
def home():
    return {"status": "Backend is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ingest")
def ingest(req: IngestRequest):
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Content is required")

    chunks = chunk_text(req.content)
    items = []

    for i, chunk in enumerate(chunks):
        vector = embed_text(chunk)
        items.append({
            "id": str(uuid.uuid4()),
            "text": chunk,
            "vector": vector,
            "metadata": {
                "source": req.title,
                "chunk_index": i
            }
        })

    endee.upsert_chunks(items)

    return {
        "message": "Document ingested successfully",
        "chunks_indexed": len(items)
    }

@app.post("/chat")
def chat(req: ChatRequest):
    global chat_history

    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        query_vector = embed_text(user_message)
        matched = endee.search(query_vector, top_k=3)

        matched_chunks = [m["text"] for m in matched]
        context_text = build_context(matched)

        rag_user_prompt = (
            f"User question:\n{user_message}\n\n"
            f"Retrieved context:\n{context_text}\n\n"
            "Answer the user using the retrieved context."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *chat_history[-6:],   # lightweight memory
            {"role": "user", "content": rag_user_prompt}
        ]

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.4,
        )

        reply = completion.choices[0].message.content or "No reply received."

        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": reply})

        if len(chat_history) > 14:
            chat_history = [chat_history[0]] + chat_history[-12:]

        return {
            "reply": reply,
            "matched_chunks": matched_chunks
        }

    except Exception as e:
        print("CHAT ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear")
def clear_chat():
    global chat_history
    chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    return {"message": "Chat history cleared successfully"}