from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq
from langchain_community.document_loaders import JSONLoader
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
import uuid
import json
import os
import pickle
import shutil
from gtts import gTTS
import io

load_dotenv()

app = Flask(__name__)
CORS(app)

### Task 1: Data Loading - Load JSON dataset as knowledge base and chunk documents for effective retrieval ###
def load_json_chunks(file_path, content_key="content"):
    loader = JSONLoader(
        file_path=file_path,
        jq_schema=f'.[] | .{content_key}'  # Extract content for each document from JSON array
    )
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)  
    # Split large documents into smaller chunks for better retrieval performance
    return splitter.split_documents(docs)

### Task 2: RAG Setup - Create FAISS vectorstore with multilingual embeddings and load indexed vectors if available ###
def get_vectorstore(language="en"):
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    index_path = f"faiss_{language}_index"

    # Load existing FAISS index for faster startup if exists
    if os.path.exists(index_path):
        return FAISS.load_local(index_path, embedding, allow_dangerous_deserialization=True)

    # Load and chunk language-specific content from JSON
    content_key = "content_hi" if language == "hi" else "content_en"
    docs = load_json_chunks("conditions_multilang.json", content_key=content_key)

    # Build FAISS vectorstore from document chunks and save locally for reuse
    store = FAISS.from_documents(docs, embedding)
    store.save_local(index_path)
    return store

### Task 2: RAG Setup - Setup RetrievalQA chain with Groq LLM and language-specific prompt instructions ###
def get_qa_chain(language="en"):
    vectorstore = get_vectorstore(language)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})  # Retrieve top 3 relevant chunks

    # Initialize ChatGroq LLM with your API key and model
    llm = ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model_name="llama3-70b-8192", temperature=0)

    # Define prompt with contextual instruction for the LLM based on selected language
    instruction = (
        "आप एक सहायक हेल्थकेयर सहायक हैं। कृपया हिंदी में उत्तर दें।"
        if language == "hi"
        else "You are a helpful healthcare assistant. Please respond in English."
    )

    prompt_template = PromptTemplate(
        input_variables=["context", "question"],
        template=(
            "{context}\n\n"
            + instruction +
            "\n\nQuestion: {question}\nAnswer:"
        )
    )

    # Create RetrievalQA chain to combine retrieval and generation for answering user questions
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt_template}
    )

vectorstores = {
    "en": get_vectorstore("en"),
    "hi": get_vectorstore("hi")
}

### Task 3: Build Chatbot Endpoint - Handle user queries, perform retrieval and generate answers dynamically ###
@app.route('/api/faq', methods=['POST'])
def handle_faq():
    data = request.get_json()
    question = data.get("question", "")
    language = data.get("lang", "en")  # Support English and Hindi input

    if not question:
        return jsonify({"error": "Question is required."}), 400

    try:
        qa_chain = get_qa_chain(language)
        answer = qa_chain.run(question)  # Run the RAG pipeline to get contextual answer
        return jsonify({"response": answer})
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

### Additional Feature: Text-to-Speech Endpoint for voice response playback in frontend ###
@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    data = request.get_json()
    text = data.get("text", "")
    lang = data.get("lang", "en")

    if not text:
        return jsonify({"error": "Text is required"}), 400

    try:
        tts = gTTS(text=text, lang=lang)
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        audio_io.seek(0)
        return send_file(audio_io, mimetype='audio/mpeg')
    except Exception as e:
        return jsonify({"error": str(e)}), 500 

if __name__ == "__main__":
    app.run(debug=True)
