import json
import os
import time
from pathlib import Path

import numpy as np
from google import genai
from google.genai import types


ROOT = Path(__file__).resolve().parent
JSON_DIR = ROOT / "jsons"
INDEX_PATH = ROOT / "video_index.npz"
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
BATCH_SIZE = 80


def embed_batch(client: genai.Client, texts: list[str]) -> list[list[float]]:
    for attempt in range(4):
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=EMBEDDING_DIMENSIONS,
                ),
            )
            if not result.embeddings or len(result.embeddings) != len(texts):
                raise RuntimeError("Gemini returned an unexpected number of embeddings")
            return [embedding.values for embedding in result.embeddings]
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2**attempt)

    raise RuntimeError("Could not build transcript embeddings")


def main() -> None:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Set GOOGLE_API_KEY before building the transcript index")

    json_files = sorted(JSON_DIR.glob("*.json"))
    if not json_files:
        raise RuntimeError(f"No transcript JSON files found in {JSON_DIR}")

    chunks: list[dict[str, object]] = []
    for video_number, file_path in enumerate(json_files, start=1):
        with file_path.open(encoding="utf-8") as transcript_file:
            transcript = json.load(transcript_file)
        for chunk in transcript.get("chunks", []):
            text = str(chunk.get("text", "")).strip()
            if not text:
                continue
            chunks.append(
                {
                    "video_number": video_number,
                    "title": str(chunk.get("title") or file_path.stem),
                    "start": float(chunk.get("start", 0)),
                    "end": float(chunk.get("end", 0)),
                    "text": text,
                }
            )

    if not chunks:
        raise RuntimeError("The transcript files contain no searchable chunks")

    client = genai.Client(api_key=api_key)
    vectors: list[list[float]] = []
    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start : batch_start + BATCH_SIZE]
        vectors.extend(embed_batch(client, [str(chunk["text"]) for chunk in batch]))
        print(f"Indexed {len(vectors)} of {len(chunks)} transcript chunks", flush=True)

    embeddings = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings /= np.maximum(norms, 1e-12)
    serialized_chunks = np.asarray(
        [json.dumps(chunk, ensure_ascii=True) for chunk in chunks], dtype=np.str_
    )
    np.savez_compressed(INDEX_PATH, embeddings=embeddings, chunks=serialized_chunks)
    print(f"Saved {len(chunks)} chunks to {INDEX_PATH}", flush=True)


if __name__ == "__main__":
    main()