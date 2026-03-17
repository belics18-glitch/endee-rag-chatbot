🚀 Endee-Powered RAG Chatbot

Built with FastAPI, Sentence Transformers, and Groq LLM to demonstrate a real-world RAG system architecture.
An intelligent AI chatbot built using Retrieval-Augmented Generation (RAG).
It retrieves relevant knowledge and generates accurate, context-aware responses using an LLM.

📌 Project Overview

This project demonstrates a complete RAG pipeline:

Frontend → FastAPI Backend → Vector Retrieval → LLM → Response

The system uses semantic search instead of keyword matching to improve answer quality.

🧠 Key Features

Semantic search using embeddings

Context-aware AI responses

Local embedding model (no API cost)

Modern UI (black + neon green theme)

Debug endpoints for testing

Endee-ready architecture

⚙️ Tech Stack

Frontend:

HTML

CSS

JavaScript

Backend:

FastAPI (Python)

Uvicorn

AI:

Sentence Transformers (all-MiniLM-L6-v2)

Groq API (LLaMA 3.3)

🏗️ System Flow

User Query
↓
Frontend
↓
FastAPI Backend
↓
Query Embedding
↓
Semantic Search
↓
Top Relevant Chunks
↓
LLM Response
↓
Frontend Display

📂 Project Structure

backend/
├── main.py
├── knowledge.txt
├── requirements.txt
└── README.md

🔄 RAG Pipeline

Load knowledge from file

Split into chunks

Convert chunks into embeddings

Store embeddings in memory

Convert user query into embedding

Perform semantic search

Retrieve top relevant chunks

Send context to LLM

Generate final answer

📡 API Endpoints

/ → Backend status
/health → Health check
/warmup → Server ready
/knowledge-status → Knowledge info
/debug-state → Debug info
/chat → Main chatbot API

🧪 Example Request

POST /chat

{
"message": "What is RAG?"
}

🎨 UI Features

Dark theme with neon green accents

Suggestion prompts

Context display

Chat history

Clear chat option

🚀 How to Run

Install dependencies
pip install -r requirements.txt

Add .env file
GROQ_API_KEY=your_api_key

Run server
python -m uvicorn main:app --reload

Open browser
http://127.0.0.1:8000

🧠 Endee Note

This project follows an Endee-compatible architecture.
Currently, vector search is implemented locally and can be replaced with Endee without changing the pipeline.

⚠️ Limitations

Local vector storage

No persistent database

Limited knowledge base

🔮 Future Improvements

Integrate Endee vector database

Add persistent storage

Improve retrieval accuracy

Deploy to cloud

👨‍💻 Author

Belics B
Final Year CSE

⭐ Conclusion

This project demonstrates how modern AI systems combine retrieval, embeddings, and LLMs to generate accurate responses.