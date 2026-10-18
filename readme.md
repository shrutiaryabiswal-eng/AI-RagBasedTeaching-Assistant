# RAG AI Teaching Assistant

Ask questions about the video transcripts in `jsons/`. The web app retrieves relevant transcript segments, asks Gemini to answer from those segments, and returns the video titles and timestamps used as sources.

## Deploy a shareable assistant

The web interface is hosted on Netlify. Its Python API is hosted on Render, because the original scripts depend on local Ollama and cannot run as a public Netlify site. Render builds a Gemini embedding index from the checked-in transcript JSON files. The API key is only stored on Render.

1. Push this repository to GitHub. Keep the transcript files in `jsons/`; the large local `embeddings.joblib` is not needed.
2. Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/apikey).
3. In Render, create a new Blueprint from this GitHub repository and set `GOOGLE_API_KEY` when prompted. Wait for the `rag-teaching-assistant-api` service to finish its first build; it embeds the transcript corpus.
4. Copy the service URL from Render. In `netlify.toml`, replace `https://YOUR-RENDER-SERVICE.onrender.com` with that URL and push the change to GitHub.
5. In Netlify, import the same GitHub repository. Netlify reads `netlify.toml`, publishes `web/`, and displays the shareable site URL when the deploy finishes.

The first Render build can take several minutes while Gemini indexes the transcripts. A free Render service may sleep when idle, so its first response after a quiet period can be slow. The Gemini key is used for embedding and answer requests; configure usage limits in Google AI Studio before sharing the public link.

## Run locally

Install the packages in `requirements.txt`, set `GOOGLE_API_KEY`, then build the transcript index and start the API:

```bash
python build_index.py
uvicorn api:app --reload
```

Serve `web/` locally and proxy `/api/*` to `http://localhost:8000/*`, or deploy using the steps above. The legacy scripts for extracting transcripts and building a local Ollama index remain available for offline experimentation.