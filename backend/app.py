from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq
from langchain_community.document_loaders import JSONLoader
from dotenv import load_dotenv
import uuid
import json
import os
import pickle
import shutil

load_dotenv()

app = Flask(__name__)
CORS(app)


### --- Load JSON and Chunk Documents --- ###
def load_json_chunks(file_path, content_key="content"):
    loader = JSONLoader(
    file_path=file_path,
    jq_schema=f'.[] | .{content_key}'
)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    return splitter.split_documents(docs)


### --- FAISS Vectorstore (English/Hindi) --- ###
def get_vectorstore(language="en"):
    index_path = f"faiss_{language}_index"
    if os.path.exists(index_path):
        return FAISS.load_local(index_path, HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"))

    # Load and embed
    content_key = "content_hi" if language == "hi" else "content_en"
    docs = load_json_chunks("conditions_multilang.json", content_key=content_key)
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    store = FAISS.from_documents(docs, embedding)
    store.save_local(index_path)
    return store


### --- Setup QA Chain with Groq API --- ###
vectorstores = {
    "en": get_vectorstore("en"),
    "hi": get_vectorstore("hi")
}

def get_qa_chain(language="en"):
    vectorstore = vectorstores.get(language, vectorstores["en"])
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    llm = ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model_name="llama3-70b-8192", temperature=0)
    return RetrievalQA.from_chain_type(llm=llm, retriever=retriever)


### --- FAQ Endpoint --- ###
qa_chains = {
    "en": get_qa_chain("en"),
    "hi": get_qa_chain("hi")
}

@app.route('/api/faq', methods=['POST'])
def handle_faq():
    data = request.get_json()
    question = data.get("question", "")
    language = data.get("lang", "en")

    if not question:
        return jsonify({"error": "Question is required."}), 400

    try:
        qa_chain = qa_chains.get(language, qa_chains["en"])
        answer = qa_chain.run(question)
        return jsonify({"response": answer})
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500
if __name__ == "__main__":
    app.run(debug=False)