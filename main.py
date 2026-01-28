import os
import time
import datetime
import threading
import json
from flask import Flask, request, jsonify, send_from_directory, abort
from PyPDF2 import PdfReader

app = Flask(__name__, static_folder='static', static_url_path='/static')

# --- Configuration ---
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mock Configuration info
CONFIG_INFO = {
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "llm_model": "llama2-7b-chat.gguf",
    "last_trained_at": None,
    "vectors_indexed": 0
}

# Global state for training progress
training_state = {
    "is_training": False,
    "progress": 0,
    "stage": "Idle",
    "message": "Ready."
}

# In-memory chat history (Mock for consistency with previous code)
chat_sessions = {}

# --- Helpers ---
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
    
    with app.app_context():
        try:
            # Step 1: Extracting
            training_state.update({"stage": "Extracting pages...", "progress": 10})
            time.sleep(2) 
            
            # Step 2: Chunking
            training_state.update({"stage": "Chunking text...", "progress": 40})
            time.sleep(2)
            
            # Step 3: Embedding
            training_state.update({"stage": "Embedding vectors...", "progress": 70})
            time.sleep(3)
            
            # Step 4: Saving
            training_state.update({"stage": "Saving index...", "progress": 90})
            time.sleep(1)
            
            # Finish
            files = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith('.pdf')]
            total_vectors = len(files) * 150 # Mock calculation
            
            CONFIG_INFO["last_trained_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            CONFIG_INFO["vectors_indexed"] = total_vectors
            
            training_state.update({
                "is_training": False, 
                "progress": 100, 
                "stage": "Complete", 
                "message": "Index updated successfully."
            })
        except Exception as e:
            training_state.update({"is_training": False, "stage": "Error", "message": str(e)})

# --- Page Routes ---

@app.route('/')
def page_upload():
    return app.send_static_file('index.html')

@app.route('/chat')
def page_chat():
    return app.send_static_file('chat.html')

# --- API Endpoints ---

@app.route('/files', methods=['GET'])
def list_files():
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
    return jsonify(files_data)

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({"error": "No files part"}), 400
    
    files = request.files.getlist('files')
    uploaded_details = []
    
    for file in files:
        if file.filename == '':
            continue
        if file.filename.lower().endswith('.pdf'):
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            file.save(file_path)
            
            uploaded_details.append({
                "filename": file.filename,
                "pages": get_pdf_page_count(file_path),
                "size": format_size(os.path.getsize(file_path))
            })
            
    return jsonify(uploaded_details)

@app.route('/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": f"Deleted {filename}"})
    return jsonify({"error": "File not found"}), 404

@app.route('/files/view/<filename>', methods=['GET'])
def view_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/info', methods=['GET'])
def get_index_info():
    pdf_count = 0
    if os.path.exists(UPLOAD_DIR):
        pdf_count = len([f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith('.pdf')])
    
    return jsonify({
        "pdf_count": pdf_count,
        "embedding_model": CONFIG_INFO["embedding_model"],
        "llm_model": CONFIG_INFO["llm_model"],
        "last_trained_at": CONFIG_INFO["last_trained_at"],
        "vectors_indexed": CONFIG_INFO["vectors_indexed"]
    })

# --- Training Endpoints ---

@app.route('/train', methods=['POST'])
def start_training():
    if training_state["is_training"]:
        return jsonify({"message": "Training already in progress"})
    
    # Check if files exist
    files = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith('.pdf')]
    if not files:
         return jsonify({"error": "No files to train"}), 400

    training_state["is_training"] = True
    training_state["progress"] = 0
    
    # Run in background thread so we don't block the UI
    thread = threading.Thread(target=background_training_task)
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Training started"})

@app.route('/train/status', methods=['GET'])
def get_training_status():
    return jsonify(training_state)

# --- Chat API Endpoints (Stubbed for completeness) ---

@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify(CONFIG_INFO)

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    data = request.json
    # Simulate processing delay
    time.sleep(1.5)
    
    question = data.get('question', '')
    client_id = data.get('client_id', 'anon')
    top_k = data.get('top_k', 3)
    
    # Mock Response
    response_text = f"Flask Backend: I found information regarding **{question}**."
    
    sources = []
    files = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith('.pdf')]
    if files:
        import random
        selected_file = random.choice(files)
        sources = [
            {
                "file": selected_file,
                "page": 1,
                "score": 0.89,
                "text": "Flask Mock: This is a raw chunk extracted from the PDF."
            }
        ]

    return jsonify({
        "answer": response_text,
        "sources": sources[:top_k]
    })

@app.route('/api/reset', methods=['POST'])
def reset_chat():
    # In a real app, you would clear the session from a DB
    return jsonify({"message": "History cleared"})

# 
if __name__ == "__main__":
    # Ensure uploads dir exists
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
        
    app.run(host="0.0.0.0", port=8000, debug=True)