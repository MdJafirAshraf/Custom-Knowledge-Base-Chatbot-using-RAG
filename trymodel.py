import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import LlamaCpp
from langchain.chains import RetrievalQA


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-l6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": False}
)


VECTORSTORE_PATH = "vectorstore/faiss_vectorstore"

if not os.path.exists(VECTORSTORE_PATH):
    raise FileNotFoundError("FAISS vector store not found")

db = FAISS.load_local(
    VECTORSTORE_PATH,
    embeddings,
    allow_dangerous_deserialization=True
)

print(f"Loaded {db.index.ntotal} vectors")


retriever = db.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 4}
)


llm = LlamaCpp(
    model_path='models\\Phi-3-mini-4k-instruct-q4.gguf',
    n_ctx=2048,
    n_threads=4,
    max_tokens=64,
    verbose=False
)


qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True
)

query = "tell me about my list of experience?"

result = qa_chain(query)

print("\nAnswer:\n", result["result"])

print("\nSources:")
for doc in result["source_documents"]:
    print("-", doc.metadata.get("source", "unknown"))

# Cleanup
del llm
del qa_chain
del db
