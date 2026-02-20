# Custom Knowledge Base Chatbot (RAG)

Custom Knowledge Base Chatbot FastAPI app that provides a retrieval-augmented generation (RAG) chatbot using a local FAISS vectorstore.

## Features
- Upload documents via web UI and index them into a FAISS vectorstore
- Chat against your documents using a simple web interface

## Repo structure
- `app.py` — FastAPI app / main server (exposes the API and web UI)
- `prepare_data.py` — optional helper to (re)generate the vector index
- `vectorstore/faiss_vectorstore/index.faiss` — FAISS index used by the app
- `static/` and `templates/` — frontend assets and HTML

## Prerequisites
- Python 3.11+
- See `requirements.txt` for exact dependencies

## Setup
1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Data indexing

The app handles indexing and retrieval at runtime. You do not need to run `prepare_data.py` separately to start the server. Use `prepare_data.py` only if you want to manually rebuild the FAISS index from scratch.

## Run the app

Run with `uvicorn` (the `app` object is expected in `app.py`):

```powershell
uvicorn app:app --reload --host 127.0.0.1
```

Open http://127.0.0.1:8000/ in your browser. Use the upload page to add documents and then chat. No other scripts need to be run separately.

## Notes
 - The project uses a local FAISS index at `vectorstore/faiss_vectorstore/index.faiss` — back this up if you regenerate indexes.

## License
See the `LICENSE` file in the repository.
