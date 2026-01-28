import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import SentenceTransformerEmbeddings
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

try:
    vectorstore = FAISS.load_local(
        folder_path="vectorstore/faiss_vectorstore",
        embeddings=embeddings,
        allow_dangerous_deserialization=True
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    print("FAISS index loaded successfully.")
except Exception as e:
    print(f"Error loading FAISS index: {e}")
    print("Please ensure your FAISS index is saved in the specified directory.")
    
from langchain_community.llms import Ollama
llm = Ollama(model="tinyllama")

template = """
You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question.
If you don't know the answer, just say that you don't know.
Keep the answer concise and based ONLY on the provided context.

Context:
{context}

Question: {question}

Answer:
"""
prompt = ChatPromptTemplate.from_template(template)

rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)


user_question = "give me a summary of the document stored in the vector store"
print(f"\n--- User Question: {user_question} ---")

result = rag_chain.invoke(user_question)

print(f"\n--- RAG Response ---")
print(result)
print("------------------------")