
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag.vector_store import load_chunks
from rag.retriever import retrieve_chunks
from rag.generator import generate_answer

from api.catalog import router as catalog_router


BASE_DIR = Path(__file__).resolve().parent
STORE_PATH = BASE_DIR / "storage" / "psi159_vector_store.json"


app = FastAPI(
    title="FLAME AI",
    description="NASA Combustion Research Assistant",
    version="0.1.0"
)


# Load the vector store when available.
chunks = []

if STORE_PATH.exists():
    chunks = load_chunks(str(STORE_PATH))


# Register the catalogue API.
app.include_router(catalog_router)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


def build_retrieval_query(question: str) -> str:
    question_lower = question.lower()

    if (
        "spherical" in question_lower
        and any(
            fuel in question_lower
            for fuel in ["propane", "ethane", "butane"]
        )
    ):
        return (
            f"{question} "
            "Experimental observations and actual reported results "
            "for spherical gas-fueled cool diffusion flames. "
            "Identify the fuels and experimental conditions associated "
            "with observed outcomes. Distinguish experimental findings "
            "from planned research objectives and hypotheses."
        )

    return question


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
        "indexed_chunks": len(chunks),
        "rag_available": bool(chunks)
    }


@app.post("/ask")
def ask_question(request: QuestionRequest):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    if not chunks:
        raise HTTPException(
            status_code=503,
            detail="RAG vector store is unavailable. Please configure it first."
        )

    try:
        retrieval_query = build_retrieval_query(question)

        retrieved_chunks = retrieve_chunks(
            query=retrieval_query,
            chunks=chunks,
            top_k=8
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
