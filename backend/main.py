from sentence_transformers import SentenceTransformer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from openai import OpenAI
import os

load_dotenv()


class ChatRequest(BaseModel):
    message: str


def load_knowledge(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return ""


def chunk_text(text: str) -> list[str]:
    if not text.strip():
        return []

    chunks = text.split("\n\n")
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def create_index_data(chunks: list[str], embedding_model: SentenceTransformer):
    """
    Create local vector index data from knowledge chunks.
    This is structured as an Endee-ready retrieval layer.
    """
    if not chunks:
        return []

    embeddings = embedding_model.encode(chunks, convert_to_numpy=True)

    index_data = []
    for i, chunk in enumerate(chunks):
        index_data.append({
            "id": str(i),
            "text": chunk,
            "embedding": embeddings[i]
        })

    return index_data


def create_query_embedding(query: str, embedding_model: SentenceTransformer):
    embedding = embedding_model.encode([query], convert_to_numpy=True)
    return embedding[0]


def cosine_similarity(vec1, vec2):
    dot_product = float((vec1 * vec2).sum())
    norm_a = float((vec1 * vec1).sum()) ** 0.5
    norm_b = float((vec2 * vec2).sum()) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def search_endee(query_embedding, index_data, top_k: int = 3) -> list[str]:
    """
    Endee-ready search layer.
    Currently uses local semantic similarity over index_data.
    Can later be replaced with real Endee server/API calls
    without changing the rest of the pipeline.
    """
    if not index_data:
        return []

    scored = []
    for item in index_data:
        score = cosine_similarity(query_embedding, item["embedding"])
        scored.append((score, item["text"]))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [text for score, text in scored[:top_k]]


def generate_answer(query: str, context_chunks: list[str], client: OpenAI) -> str:
    context = "\n\n".join(context_chunks) if context_chunks else "No additional context found."

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
            "content": f"Retrieved context:\n{context}"
        },
        {
            "role": "user",
            "content": query
        }
    ]

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.7,
    )

    return completion.choices[0].message.content


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting backend...")

    app.state.client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )

    app.state.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    knowledge_text = load_knowledge("knowledge.txt")
    chunks = chunk_text(knowledge_text)
    index_data = create_index_data(chunks, app.state.embedding_model)

    app.state.knowledge_text = knowledge_text
    app.state.chunks = chunks
    app.state.index_data = index_data

    print("Backend startup complete.")
    print(f"Loaded {len(chunks)} knowledge chunks.")

    yield

    print("Shutting down backend...")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/warmup")
def warmup():
    return {
        "status": "ready",
        "message": "Server warmed up successfully"
    }


@app.get("/knowledge-status")
def knowledge_status():
    return {
        "chunks_loaded": len(app.state.chunks),
        "knowledge_loaded": bool(app.state.knowledge_text.strip())
    }


@app.get("/debug-state")
def debug_state():
    return {
        "chunks_loaded": len(app.state.chunks),
        "index_data_loaded": len(app.state.index_data),
        "knowledge_loaded": bool(app.state.knowledge_text.strip())
    }


@app.post("/chat")
def chat(req: ChatRequest):
    try:
        print("Incoming message:", req.message)

        client = app.state.client
        embedding_model = app.state.embedding_model
        index_data = app.state.index_data

        print("Index data count:", len(index_data))

        query_embedding = create_query_embedding(req.message, embedding_model)
        print("Query embedding created")

        matched_chunks = search_endee(query_embedding, index_data, top_k=3)
        print("Matched chunks:", matched_chunks)

        reply = generate_answer(req.message, matched_chunks, client)
        print("Reply generated successfully")

        return {
            "reply": reply,
            "matched_chunks": matched_chunks
        }

    except Exception as e:
        import traceback
        print("ERROR IN /chat:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))