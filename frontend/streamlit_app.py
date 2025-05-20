import streamlit as st
import requests
import time
import pyttsx3
import speech_recognition as sr
import os
import base64

# --- Task 3: Build the Chatbot Frontend ---
# Page setup with title and layout for healthcare chatbot supporting English and Hindi
st.set_page_config(page_title="🩺 हेल्थकेयर चैटबॉट / Healthcare Chatbot", layout="centered")

# Initialize session state for chat history, language, and loading status
if "history" not in st.session_state:
    st.session_state.history = [{
        "role": "bot",
        "text": {
            "en": "👋 Hello! I’m your Healthcare Assistant. How can I help you today?",
            "hi": "👋 नमस्ते! मैं आपका हेल्थकेयर सहायक हूँ। मैं आपकी कैसे मदद कर सकता हूँ?"
        }
    }]
if "lang" not in st.session_state:
    st.session_state.lang = "en"
if "loading" not in st.session_state:
    st.session_state.loading = False

# --- Task 3: Text-to-Speech Integration ---
# Function to convert bot response text to speech for better accessibility
def speak_text(text):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 165)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        st.warning(f"TTS error: {e}")
        st.warning(f"TTS failed: {e}")

# --- Task 3: Speech-to-Text Integration ---
# Function to capture user's voice input and convert to text using Google Speech Recognition API
def listen_voice():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙️ Listening... Speak now.")
        audio = recognizer.listen(source, phrase_time_limit=5)
    try:
        text = recognizer.recognize_google(audio, language='hi-IN' if st.session_state.lang == "hi" else 'en-US')
        st.success(f"✅ You said: {text}")
        return text
    except sr.UnknownValueError:
        st.warning("❌ Could not understand audio.")
    except sr.RequestError as e:
        st.warning(f"❌ STT request error: {e}")
    return ""

# Language toggle(Task 3: Multilingual support)
col1, col2, col3 = st.columns([5, 1, 1])
with col2:
    lang_toggle = st.toggle("En/Hi")
    st.session_state.lang = "hi" if lang_toggle else "en"
# with col3:
#     if st.button("🎤"):
#         voice_input = listen_voice()
#         if voice_input:
#             st.session_state.history.append({"role": "user", "text": voice_input})
#             st.session_state.loading = True
#             st.rerun()
lang = st.session_state.lang

# Text labels(Task 3: Multilingual support)
labels = {
    "en": {
        "title": " Healthcare Chatbot",
        "subtitle": "Ask health-related questions in English or Hindi.",
        "placeholder": "Type your question here...",
        "loading": "Getting response...",
        "error": "Connection failed:"
    },
    "hi": {
        "title": " हेल्थकेयर चैटबॉट",
        "subtitle": "स्वास्थ्य से संबंधित प्रश्न अंग्रेजी या हिंदी में पूछें।",
        "placeholder": "अपना प्रश्न यहां लिखें...",
        "loading": "प्रतिक्रिया प्राप्त हो रही है...",
        "error": "कनेक्शन विफल:"
    }
}
st.markdown("""
    <style>
    .stToggleSwitch [data-baseweb="toggle"] {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        border-radius: 20px;
    }
    </style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #f0f4ff, #ffffff);
}
.main > div {
    background-color: #ffffff;
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 0 30px rgba(0, 0, 0, 0.05);
    margin-top: 2rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    .sticky-header {
        position: sticky;
        top: 0;
        background-color: rgba(255, 255, 255, 0.1); /* transparent background */
        padding: 20px 0 10px 0;
        z-index: 999;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        text-align: center;
        
    }

    .sticky-header h1 {
        font-size: 40px;
        color: #96c8e3;
        margin: 0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    .sticky-header p {
        font-size: 16 px;
        color: #555;
        margin: 4px 0 0;
        font-style: italic;
    }
        .chat-container {
            max-height: 500px;
            overflow-y: auto;
            padding: 10px 5px;
            border: 1px solid #eee;
            border-radius: 12px;
            background: #f9f9f9;
        }
        .chat-message {
            max-width: 75%;
            padding: 14px 20px;
            border-radius: 24px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            font-size: 16px;
            line-height: 1.5;
            margin-bottom: 14px;
            word-wrap: break-word;
        }
        .bot-msg {
            background: #e3f2fd;
            color: #0b3d91;
            align-self: flex-start;
        }
        .user-msg {
            background: #d0f0c0;
            color: #1f4d00;
            align-self: flex-end;
        }
        .chat-row {
            display: flex;
            justify-content: flex-start;
        }
        .chat-row.user {
            justify-content: flex-end;
        }
        .icon {
            font-size: 22px;
            margin-right: 10px;
            user-select: none;
        }
        .user .icon {
            margin-left: 10px;
            margin-right: 0;
        }
        /* Inline loader (typing dots) */
        .loader {
            display: flex;
            justify-content: flex-start;
            margin-bottom: 14px;
            padding-left: 40px; /* align under bot messages */
        }
        .dot {
            height: 10px;
            width: 10px;
            margin: 0 5px;
            background-color: #4a90e2;
            border-radius: 50%;
            display: inline-block;
            animation: blink 1.4s infinite both;
        }
        .dot:nth-child(1) {
            animation-delay: 0s;
        }
        .dot:nth-child(2) {
            animation-delay: 0.2s;
        }
        .dot:nth-child(3) {
            animation-delay: 0.4s;
        }
        @keyframes blink {
            0%, 80%, 100% {
                opacity: 0;
            }
            40% {
                opacity: 1;
            }
        }
        .chat-message.bot-msg::after {
    content: "";
    position: absolute;
    left: -10px;
    top: 20px;
    border-width: 10px;
    border-style: solid;
    border-color: transparent #e3f2fd transparent transparent;
}

.chat-message.user-msg::after {
    content: "";
    position: absolute;
    right: -10px;
    top: 20px;
    border-width: 10px;
    border-style: solid;
    border-color: transparent transparent transparent #d0f0c0;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}
.sticky-header h1::before {
    content: "🩺 ";
    display: inline-block;
    animation: bounce 1s infinite;
}

    </style>
""", unsafe_allow_html=True)


st.markdown(f"""
<div class="sticky-header">
    <h1>{labels[lang]['title']}</h1>
    <p>{labels[lang]['subtitle']}</p>
</div>
""", unsafe_allow_html=True)

question = st.chat_input(placeholder=labels[lang]['placeholder'])

# Handle user input and call backend API for RAG-based answer retrieval (Task 2 & 3)
if question:
    st.session_state.history.append({"role": "user", "text": question})
    st.session_state.loading = True
    st.rerun()

if st.session_state.get("loading", False):
    try:
        response = requests.post("http://localhost:5000/api/faq", json={"question": st.session_state.history[-1]["text"], "lang": lang})
        if response.status_code == 200:
            answer = response.json()["response"]
            st.session_state.history.append({"role": "bot", "text": answer})
            speak_text(answer if isinstance(answer, str) else answer.get(lang, ""))
        else:
            error_text = f"❌ Error: {response.json().get('error')}."
            st.session_state.history.append({"role": "bot", "text": error_text})
            speak_text(error_text)
    except Exception as e:
        error_text = f"❌ {labels[lang]['error']} {e}"
        st.session_state.history.append({"role": "bot", "text": error_text})
        speak_text(error_text)
    st.session_state.loading = False
    st.rerun()

# Render chat messages UI with proper styling and roles (Task 3: Chat display)
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
for msg in st.session_state.history:
    role = msg["role"]
    text = msg["text"][lang] if isinstance(msg["text"], dict) else msg["text"]
    css_class = "bot-msg" if role == "bot" else "user-msg"
    row_class = "chat-row" if role == "bot" else "chat-row user"
    icon = "👩‍⚕️" if role == "bot" else "🧑"
    st.markdown(f"""
    <div class="{row_class}">
        <div class="icon">{icon}</div>
        <div class="chat-message {css_class}">{text}</div>
    </div>
    """, unsafe_allow_html=True)
if st.session_state.get("loading", False):
    st.markdown("""
    <div class="loader">
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
    </div>
    """, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)