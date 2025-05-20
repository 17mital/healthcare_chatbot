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
import os

load_dotenv()

app = Flask(__name__)
CORS(app)

### --- Shared embedding model instance to save memory --- ###
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

### --- Load JSON and Chunk Documents --- ###
def load_json_chunks(file_path, content_key="content"):
    loader = JSONLoader(
        file_path=file_path,
        jq_schema=f'.[] | .{content_key}'
    )
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    return splitter.split_documents(docs)

### --- Lazy loaded vectorstores and QA chains caches --- ###
vectorstores_cache = {}
qa_chains_cache = {}

def get_vectorstore_cached(language="en"):
    if language not in vectorstores_cache:
        index_path = f"faiss_{language}_index"
        if os.path.exists(index_path):
            vectorstores_cache[language] = FAISS.load_local(index_path, embedding_model)
        else:
            content_key = "content_hi" if language == "hi" else "content_en"
            docs = load_json_chunks("conditions_multilang.json", content_key=content_key)
            store = FAISS.from_documents(docs, embedding_model)
            store.save_local(index_path)
            vectorstores_cache[language] = store
    return vectorstores_cache[language]

def get_qa_chain_cached(language="en"):
    if language not in qa_chains_cache:
        vectorstore = get_vectorstore_cached(language)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama3-70b-8192",
            temperature=0
        )
        qa_chains_cache[language] = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
    return qa_chains_cache[language]

### --- FAQ Endpoint --- ###
@app.route('/api/faq', methods=['POST'])
def handle_faq():
    data = request.get_json()
    question = data.get("question", "")
    language = data.get("lang", "en")

    if not question:
        return jsonify({"error": "Question is required."}), 400

    try:
        qa_chain = get_qa_chain_cached(language)
        answer = qa_chain.run(question)
        return jsonify({"response": answer})
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False)
