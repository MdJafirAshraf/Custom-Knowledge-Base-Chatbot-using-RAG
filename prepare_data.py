from transformers import AutoTokenizer, AutoModelForQuestionAnswering
from transformers import pipeline
from langchain import HuggingFacePipeline
from langchain.chains import RetrievalQA

import os

from langchain.vectorstores import FAISS
from langchain_core.documents import Document
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.document_loaders import HuggingFaceDatasetLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

class PrepareData:

    # Initialize embeddings
    model_kwargs = {'device':'cpu'}
    encode_kwargs = {'normalize_embeddings': False}

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-l6-v2",     
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )

    # Load dataset
    def load_dataset(self, dataset_name, page_content_column):
        loader = HuggingFaceDatasetLoader(dataset_name, page_content_column)
        data = loader.load()
        return data
    
    # Load data from directory
    def load_data_from_directory(self, directory_path, file_extension=".txt"):        
        documents = []
        if os.path.exists(directory_path):
            for filename in os.listdir(directory_path):
                if filename.endswith(".txt"):
                    file_path = os.path.join(directory_path, filename)
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        doc = Document(
                            page_content=content, 
                            metadata={"source": file_path, "filename": filename}
                        )
                        documents.append(doc)

                if filename.endswith(".pdf"):
                    from langchain.document_loaders import PyPDFLoader
                    file_path = os.path.join(directory_path, filename)
                    loader = PyPDFLoader(file_path)
                    pdf_docs = loader.load()
                    documents.extend(pdf_docs)

        return documents
            
    # Chunk text
    def chunk_text(self, data, chunk_size=1000, chunk_overlap=300):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = text_splitter.split_documents(data)
        return chunks

    # Embed documents and save to FAISS vector store
    def embedding_documents(self, docs, embeddings):
        db = FAISS.from_documents(docs, embeddings)
        db.save_local("vectorstore/faiss_vectorstore")
        print(db.index.ntotal, "documents loaded from the vector store")
        return db.index.ntotal

    # Load embeddings from FAISS vector store
    def load_embeddings(self, embeddings):
        db = FAISS.load_local("vectorstore/faiss_vectorstore", embeddings, allow_dangerous_deserialization=True)
        print(db.index.ntotal, "documents loaded from the vector store")
        return db



# check vector folder
# page_content_column = "context"
# dataset_name = "databricks/databricks-dolly-15k"

# prepare_data = PrepareData()
# embeddings = prepare_data.embeddings

# if not os.path.exists("vectorstore/faiss_vectorstore"):
#     print("Vector store not found, preparing data...")
#     # data = prepare_data.load_dataset(dataset_name, page_content_column)
#     data = prepare_data.load_data_from_directory("static/uploads", file_extension=".pdf")
#     chunks = prepare_data.chunk_text(data)
#     prepare_data.embedding_documents(chunks, embeddings)
    
#     print("Data preparation completed.")
# else:
#     print("Vector store found, skipping data preparation.")
#     db = prepare_data.load_embeddings(embeddings)
