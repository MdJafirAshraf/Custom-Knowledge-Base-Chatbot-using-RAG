import os
import time
import uvicorn
import datetime
import threading
import configparser
from PyPDF2 import PdfReader
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from prepare_data import DataPreparation


# --- Data Preparation and Embeddings Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize data preparation and embeddings on startup
    app.state.data_preparation = DataPreparation()
    print("✓ Embeddings initialized and ready")
    yield

app = FastAPI(lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")


# --- Page Routes ---

@app.get("/")
async def upload(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/chat")
async def chat(request: Request):

    return templates.TemplateResponse("chat.html", {"request": request})
    

config = configparser.ConfigParser()
config.read("config.cfg")

UPLOAD_DIR = config["app"]["upload_directory"]
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Global state for training progress
training_state = {
    "is_training": False,
    "progress": 0,
    "stage": "Idle",
    "message": "Ready."
}

def get_pdf_page_count(filepath):
    try:
        reader = PdfReader(filepath)
        return len(reader.pages)
    except Exception:
        return 0

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

def background_training_task():
    """
    Simulates a long-running RAG indexing process in a separate thread.
    """
    global training_state, CONFIG_INFO
    
    try:
        training_state.update({"stage": "Extracting pages...", "progress": 20})
        time.sleep(1)

        training_state.update({"stage": "Preparing data...", "progress": 40})
        data = app.state.data_preparation.load_data_from_directory("static/uploads", file_extension=".pdf")
        chunks = app.state.data_preparation.chunk_text(data)
        
        training_state.update({"stage": "Embedding vectors...", "progress": 80})
        total_vectors = app.state.data_preparation.embedding_documents(chunks, app.state.data_preparation.embeddings)
        training_state.update({"stage": "Saving index...", "progress": 90})
                    
        config["training"]["last_trained_at"] = str(datetime.datetime.now().strftime("%d-%m-%Y %H:%M"))
        config["training"]["vectors_indexed"] = str(total_vectors)
        config["training"]["no_of_files_to_train"] = str(len(os.listdir(UPLOAD_DIR)))

        with open("config.cfg", "w") as f:
            config.write(f)
        
        training_state.update({
            "is_training": False, 
            "progress": 100, 
            "stage": "Complete", 
            "message": "Index updated successfully."
        })

    except Exception as e:
        training_state.update({"is_training": False, "stage": "Error", "message": str(e)})


# --- API Endpoints ---
@app.get('/api/status')
async def api_status():
    return {
        "last_trained_at": config["training"]["last_trained_at"],
        "vectors_indexed": config["training"]["vectors_indexed"]
    }

@app.post('/upload')
async def upload_files(files: list[UploadFile] = File(...)):
    uploaded_details = []
    
    for file in files:
        if file.filename and file.filename.lower().endswith('.pdf'):
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            # Save uploaded file
            contents = await file.read()
            with open(file_path, 'wb') as f:
                f.write(contents)
            
            uploaded_details.append({
                "filename": file.filename,
                "pages": get_pdf_page_count(file_path),
                "size": format_size(os.path.getsize(file_path))
            })
            
    return uploaded_details

@app.get('/info')
async def get_index_info():
    pdf_count = 0
    if os.path.exists(UPLOAD_DIR):
        pdf_count = len([f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith('.pdf')])
    
    return {
        "pdf_count": pdf_count,
        "embedding_model": config["models"]["embedding_model"],
        "llm_model": config["models"]["llm_model"],
        "last_trained_at": config["training"]["last_trained_at"],
        "vectors_indexed": config["training"]["vectors_indexed"],
        "no_of_files_to_train": config["training"]["no_of_files_to_train"]
    }

@app.get('/files')
async def list_files():
    files_data = []
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(filepath) and filename.lower().endswith('.pdf'):
                stat = os.stat(filepath)
                files_data.append({
                    "filename": filename,
                    "size": format_size(stat.st_size),
                    "pages": get_pdf_page_count(filepath)
                })
    return files_data

@app.delete('/files/{filename}')
async def delete_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": f"Deleted {filename}"}
    raise HTTPException(status_code=404, detail="File not found")

@app.get('/files/view/{filename}')
async def view_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

# --- Training Endpoints ---

@app.post('/train')
async def start_training():
    if training_state["is_training"]:
        return {"message": "Training already in progress"}
    
    # Check if files exist
    files = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith('.pdf')]
    if not files:
         raise HTTPException(status_code=400, detail="No files to train")

    training_state["is_training"] = True
    training_state["progress"] = 0
    
    # Run in background thread so we don't block the UI
    thread = threading.Thread(target=background_training_task)
    thread.daemon = True
    thread.start()
    
    return {"message": "Training started"}

# Chat API


@app.post('/api/chat')
async def api_chat(payload: dict):
    question = payload.get('question')
    top_k = int(payload.get('top_k', 4))
    max_tokens = int(payload.get('max_tokens', 256))
    temperature = float(payload.get('temperature', 0.3))

    if not hasattr(app.state, 'data_preparation'):
        raise HTTPException(status_code=500, detail="Data preparation not initialized")

    try:
        result = app.state.data_preparation.answer_query(question, top_k=top_k)
        return {"answer": result.get('answer', ''), "sources": result.get('sources', [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/reset')
async def reset_chat(client_id: str = None):
    # Placeholder: no persistent session store currently. Keep for frontend compatibility.
    return {"message": "Reset complete"}


@app.get('/train/status')
async def get_training_status():
    return training_state



if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)