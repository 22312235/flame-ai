
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag.vector_store import load_chunks
from rag.retriever import retrieve_chunks
from rag.generator import generate_answer


BASE_DIR = Path(__file__).resolve().parent
STORE_PATH = BASE_DIR / "storage" / "psi159_vector_store.json"

app = FastAPI(
    title="FLAME AI",
    description="NASA Combustion Research Assistant",
    version="0.1.0"
)

# Load the vector store once when the API starts.
chunks = load_chunks(str(STORE_PATH))


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@app.get("/")
def root():
    return {
        "name": "FLAME AI",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "indexed_chunks": len(chunks)
    }


@app.post("/ask")
def ask_question(request: QuestionRequest):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    try:
        retrieved_chunks = retrieve_chunks(
            query=question,
            chunks=chunks,
            top_k=5
        )

        answer = generate_answer(
            query=question,
            retrieved_chunks=retrieved_chunks
        )

        return {
            "question": question,
            "answer": answer,
            "sources": [
                {
                    "source": chunk["source"],
                    "page": chunk["page_number"],
                    "similarity": round(chunk["similarity"], 4)
                }
                for chunk in retrieved_chunks
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
