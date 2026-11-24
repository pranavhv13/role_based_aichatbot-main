import os
from typing import Dict
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import requests

app = FastAPI()
security = HTTPBasic()

# Load Vector Database
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

embedding_function = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectordb = Chroma(
    persist_directory=CHROMA_DIR,
    embedding_function=embedding_function,
    collection_name="company_docs"
)

# Dummy Users Database
users_db: Dict[str, Dict[str, str]] = {
    "Tony": {"password": "password123", "role": "engineering"},
    "Bruce": {"password": "securepass", "role": "marketing"},
    "Sam": {"password": "financepass", "role": "finance"},
    "Peter": {"password": "pete123", "role": "engineering"},
    "Sid": {"password": "sidpass123", "role": "marketing"},
    "Natasha": {"password": "hrpass123", "role": "hr"},
    "Alice": {"password": "ceopass", "role": "c-levelexecutives"},
    "Bob": {"password": "employeepass", "role": "employee"}
}

# Helper: Authentication
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    user = users_db.get(username)

    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"username": username, "role": user["role"]}

# Endpoints
@app.get("/")
def root():
    return {"message": "FinSolve AI Chatbot API is running"}

@app.get("/login")
def login(user=Depends(authenticate)):
    """
    Simple login endpoint that returns user role after authentication.
    """
    return {
        "message": f"Welcome {user['username']}!",
        "role": user["role"]
    }

@app.get("/test")
def test(user=Depends(authenticate)):
    """
    Basic test endpoint to verify authentication.
    """
    return {
        "message": f"Hello {user['username']}! You can now chat.",
        "role": user["role"]
    }

@app.post("/chat")
async def chat(request: Request):
    """
    Main chat endpoint that:
    - Retrieves relevant docs based on role
    - Builds prompt for Ollama LLaMA3
    - Returns natural language response
    """
    try:
        data = await request.json()
        user = data["user"]
        message = data["message"]
        user_role = user["role"].lower()

        # Role-based retrieval
        if "c-levelexecutives" in user_role:
            docs = vectordb.similarity_search(message, k=3)
        elif "employee" in user_role:
            docs = vectordb.similarity_search(
                message, k=3, filter={"category": "general"}
            )
        else:
            docs = vectordb.similarity_search(
                message, k=3, filter={"role": user_role}
            )

        if not docs:
            return {
                "response": f"No relevant data found for your role: {user['role']}"
            }

        # Build context & prompt

        context = "\n\n".join(doc.page_content for doc in docs)

        prompt = f"""
You are an AI assistant at FinSolve Technologies. The user has the role: {user['role']}.
Use the context below to answer their question in a friendly, clear, conversational style,
like you're explaining it to a colleague. Summarize naturally — avoid just bullet points.

Context:
{context}

Question: {message}

Answer:
"""
        # Send to Ollama LLaMA3
        ollama_payload = {
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7}
        }

        response = requests.post(
            "http://localhost:11434/api/generate",
            json=ollama_payload
        )

        if response.status_code != 200:
            return {"response": f"Ollama LLM error: {response.text}"}

        return {
            "username": user["username"],
            "role": user["role"],
            "query": message,
            "response": response.json()["response"]
        }

    except Exception as e:
        return {"response": f"Error during chat: {str(e)}"}