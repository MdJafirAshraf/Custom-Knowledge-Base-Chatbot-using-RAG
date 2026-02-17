import os
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq

from dotenv import load_dotenv
load_dotenv()

class DataPreparation:

    # Initialize embeddings
    def __init__(self):
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={"device": "cpu"},
            encode_kwargs={
                "normalize_embeddings": True,
                "batch_size": 64
            }
        )

        # Check if vector store exists and load it
        if os.path.exists("vectorstore/faiss_vectorstore"):
            self.vectorstore = FAISS.load_local(
                folder_path="vectorstore/faiss_vectorstore",
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
            print(self.vectorstore.index.ntotal, "documents loaded from the vector store")

        else:
            print("No existing vector store found. Please run the data preparation process to create one.")
    
    # Load data from directory
    def load_data_from_directory(self, directory_path, file_extension=".txt"):        
        documents = []
        if os.path.exists(directory_path):
            for filename in os.listdir(directory_path):
                if filename.endswith(file_extension):
                    if file_extension == ".txt":
                        file_path = os.path.join(directory_path, filename)
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read()
                            doc = Document(
                                page_content=content, 
                                metadata={"source": file_path, "filename": filename}
                            )
                            documents.append(doc)

                    elif file_extension == ".pdf":
                        from langchain_community.document_loaders import PyPDFLoader
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
    def embedding_documents(self, docs, embeddings=None):
        use_embeddings = embeddings if embeddings is not None else self.embeddings
        db = FAISS.from_documents(docs, use_embeddings)
        db.save_local("vectorstore/faiss_vectorstore")
        print(db.index.ntotal, "documents loaded from the vector store")
        return db.index.ntotal

    # Load embeddings from FAISS vector store
    def load_embeddings(self, embeddings=None):
        use_embeddings = embeddings if embeddings is not None else self.embeddings
        db = FAISS.load_local("vectorstore/faiss_vectorstore", use_embeddings, allow_dangerous_deserialization=True)
        print(db.index.ntotal, "documents loaded from the vector store")
        return db

    # Answer query using the RetrievalQA chain
    def answer_query(self, query, top_k=4, max_tokens=256, temperature=0.3):
        if not hasattr(self, 'vectorstore'):
            raise ValueError("Vector store is not initialized. Please ensure the vector store is loaded.")
        
        llm = ChatGroq(
            model="llama-3.1-8b-instant",  # ✅ valid Groq model
            temperature=0.3,
            max_tokens=256,
            api_key=self.GROQ_API_KEY
        )
        
        retriever = self.vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": top_k,"fetch_k": 20})
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )
        
        result = qa_chain({"query": query})
        answer = result.get("result", "")
        src_docs = result.get("source_documents", [])
        print(f"Query: {query}\nAnswer: {answer}\nRetrieved {len(src_docs)} source documents.")

        # Normalize source documents (handle both Document objects and plain dicts)
        sources = []
        for doc in (src_docs or []):
            if isinstance(doc, dict):
                meta = doc.get('metadata', {}) or {}
                text = doc.get('page_content') or doc.get('text') or ''
            else:
                meta = getattr(doc, 'metadata', {}) or {}
                text = getattr(doc, 'page_content', '') or ''

            source_path = meta.get('source') or meta.get('filename') or 'unknown'
            sources.append({
                'file': os.path.basename(source_path),
                'page': meta.get('page', 1),
                'score': meta.get('score', 0),
                'text': text[:1000]
            })

        return {'answer': answer, 'sources': sources}

if __name__ == "__main__":
    prepare_data = DataPreparation()
    embeddings = prepare_data.embeddings
    query = "tell me about the document"

    if not os.path.exists("vectorstore/faiss_vectorstore"):
        print("Vector store not found, preparing data...")
        data = prepare_data.load_data_from_directory("static/uploads", file_extension=".pdf")
        chunks = prepare_data.chunk_text(data)
        prepare_data.embedding_documents(chunks, embeddings)
        print("Data preparation completed.")
    else:
        print("Vector store found, skipping data preparation.")
        db = prepare_data.load_embeddings(embeddings)
        answer = prepare_data.answer_query(query)
        print("Answer:", answer['answer'])
