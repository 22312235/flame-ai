
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag.vector_store import load_chunks
from rag.retriever import retrieve_chunks
from rag.generator import generate_answer
from fastapi.middleware.cors import CORSMiddleware


BASE_DIR = Path(__file__).resolve().parent
STORE_PATH = BASE_DIR / "storage" / "psi159_vector_store.json"

app = FastAPI(
    title="FLAME AI",
    description="NASA Combustion Research Assistant",
    version="0.1.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Load the vector store if it exists.
chunks = []
index_error = None

if STORE_PATH.exists():
    try:
        chunks = load_chunks(str(STORE_PATH))
    except Exception as error:
        index_error = str(error)


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
        "status": "healthy" if chunks else "degraded",
        "indexed_chunks": len(chunks),
        "index_ready": len(chunks) > 0
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
            detail="Research index is not ready. Please try again later."
        )

    try:
        retrieval_query = build_retrieval_query(question)

        retrieved_chunks = retrieve_chunks(
            query=retrieval_query,
            chunks=chunks,
            top_k=8
        )

        if not retrieved_chunks:
            raise HTTPException(
                status_code=404,
                detail="No relevant research passages were found."
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

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your question."
        )
