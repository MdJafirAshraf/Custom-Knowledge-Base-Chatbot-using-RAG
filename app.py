import os
import datetime
import threading
import configparser
from PyPDF2 import PdfReader
from flask import Flask, render_template, request, jsonify, send_from_directory

from prepare_data import PrepareData
data_preparation = PrepareData()

app = Flask(__name__)


# --- Page Routes ---

@app.route('/')
def upload():
    return render_template('upload.html')


@app.route('/chat')
def chat():
    return render_template('chat.html')
    

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
    
    with app.app_context():
        try:
            data = data_preparation.load_data_from_directory("static/uploads", file_extension=".pdf")
            training_state.update({"stage": "Extracting pages...", "progress": 40})
            
            chunks = data_preparation.chunk_text(data)
            training_state.update({"stage": "Chunking text...", "progress": 60})
            
            total_vectors = data_preparation.embedding_documents(chunks, data_preparation.embeddings)
            training_state.update({"stage": "Embedding vectors...", "progress": 80})
            training_state.update({"stage": "Saving index...", "progress": 90})
                        
            config["training"]["last_trained_at"] = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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
@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify(config["training"]["last_trained_at"])

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

@app.route('/info', methods=['GET'])
def get_index_info():
    pdf_count = 0
    if os.path.exists(UPLOAD_DIR):
        pdf_count = len([f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith('.pdf')])
    
    return jsonify({
        "pdf_count": pdf_count,
        "embedding_model": config["models"]["embedding_model"],
        "llm_model": config["models"]["llm_model"],
        "last_trained_at": config["training"]["last_trained_at"],
        "vectors_indexed": config["training"]["vectors_indexed"],
        "no_of_files_to_train": config["training"]["no_of_files_to_train"]
    })

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








if __name__ == '__main__':
    app.run(debug=True)