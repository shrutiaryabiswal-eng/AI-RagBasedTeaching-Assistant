import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "video_index.npz"
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
GENERATION_MODEL = os.environ.get("GEMINI_GENERATION_MODEL", "gemini-3.8-flash")
RESULT_COUNT = 5

client: genai.Client | None = None
chunks: list[dict[str, object]] = []
embeddings: np.ndarray | None = None


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_index()
    yield


app = FastAPI(title="Video Teaching Assistant API", lifespan=lifespan)


def load_index() -> None:
    global client, chunks, embeddings

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    if not INDEX_PATH.exists():
        raise RuntimeError("Transcript index is missing; run build_index.py first")

    client = genai.Client(api_key=api_key)
    with np.load(INDEX_PATH, allow_pickle=False) as index:
        embeddings = np.asarray(index["embeddings"], dtype=np.float32)
        chunks = [json.loads(item) for item in index["chunks"].tolist()]
    if len(chunks) != len(embeddings):
        raise RuntimeError("Transcript index data is inconsistent")


@app.get("/healthz")
def health_check() -> dict[str, str]:
    if embeddings is None or not chunks:
        raise HTTPException(status_code=503, detail="Transcript index is not loaded")
    return {"status": "ok"}


@app.get("/catalog")
def catalog() -> dict[str, list[dict[str, object]]]:
    video_counts: dict[int, dict[str, object]] = {}
    for chunk in chunks:
        video_number = int(chunk["video_number"])
        entry = video_counts.setdefault(
            video_number,
            {"video_number": video_number, "title": chunk["title"], "chunks": 0},
        )
        entry["chunks"] = int(entry["chunks"]) + 1
    return {"videos": list(video_counts.values())}


@app.post("/ask")
def ask_question(request: QuestionRequest) -> dict[str, object]:
    question = request.question.strip()
    if len(question) < 3:
        raise HTTPException(status_code=422, detail="Ask a question with at least 3 characters")
    if client is None or embeddings is None:
        raise HTTPException(status_code=503, detail="The assistant is still starting")

    try:
        query_result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=question,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=EMBEDDING_DIMENSIONS,
            ),
        )
        if not query_result.embeddings:
            raise RuntimeError("Gemini did not return a query embedding")

        query_vector = np.asarray(query_result.embeddings[0].values, dtype=np.float32)
        query_vector /= max(float(np.linalg.norm(query_vector)), 1e-12)
        scores = embeddings @ query_vector
        best_indices = np.argsort(scores)[-RESULT_COUNT:][::-1]
        sources = [chunks[int(index)] for index in best_indices]
        context = "\n\n".join(
            f"Video {source['video_number']}: {source['title']} "
            f"({source['start']:.1f}s-{source['end']:.1f}s)\n{source['text']}"
            for source in sources
        )
        response = client.interactions.create(
            model=GENERATION_MODEL,
            store=False,
            system_instruction=(
                "You are a teaching assistant for the video course represented by the supplied "
                "transcript excerpts. Answer the learner's question using only those excerpts. "
                "Explain the relevant idea clearly and mention the video title and approximate "
                "timestamp. If the excerpts do not support an answer, say so and do not guess. "
                "If the question is unrelated to the course, politely say you can only answer "
                "questions about the course videos."
            ),
            input=f"Transcript excerpts:\n{context}\n\nLearner question: {question}",
        )
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="Gemini could not answer right now. Please try again shortly.",
        ) from error

    return {
        "answer": response.output_text or "I could not generate an answer from those excerpts.",
        "sources": [
            {
                "video_number": source["video_number"],
                "title": source["title"],
                "start": source["start"],
                "end": source["end"],
                "text": source["text"],
            }
            for source in sources
        ],
    }