from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import pyttsx3
from gtts import gTTS
from googletrans import Translator
from io import BytesIO
import base64
import PyPDF2
import tempfile
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Tone adjustments: rate multiplier
tones = {
    "Normal": 1.0,
    "Soft": 0.8,
    "Loud": 1.2,
    "Cry": 1.1,
    "Happy": 1.1
}

# Supported languages (gTTS codes)
LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Telugu": "te",
    "Tamil": "ta",
    "Marathi": "mr",
    "Bengali": "bn",
    "Kannada": "kn"
}

translator = Translator()

def extract_text_from_file(file):
    """Extract text from .txt or .pdf"""
    filename = file.filename.lower()
    text = ""
    if filename.endswith(".txt"):
        text = file.read().decode("utf-8", errors="ignore")
    elif filename.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
    return text

def synthesize_pyttsx3(text, speed=180, tone="Normal"):
    """System TTS for English (Mark/Zira voices automatically)"""
    try:
        engine = pyttsx3.init()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_path = tmp.name
        tmp.close()

        rate_multiplier = tones.get(tone, 1.0)
        # Automatically choose male/female voices based on pyttsx3 voice availability
        voices = engine.getProperty('voices')
        if voices:
            if "female" in voices[0].name.lower():
                engine.setProperty('voice', voices[0].id)
            else:
                engine.setProperty('voice', voices[1].id)
        engine.setProperty('rate', int(speed * rate_multiplier))
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        engine.stop()
        return tmp_path
    except Exception as e:
        print("pyttsx3 error:", e)
        return None

def synthesize_gtts(text, lang):
    """gTTS TTS for other languages"""
    try:
        tts = gTTS(text=text, lang=LANGUAGES.get(lang, "en"), slow=False)
        audio_file = BytesIO()
        tts.write_to_fp(audio_file)
        audio_file.seek(0)
        return audio_file
    except Exception as e:
        print("gTTS error:", e)
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    audio_base64 = None
    uploaded_text = ""
    translated_text = ""
    if request.method == "POST":
        text = request.form.get("text", "")
        speed = int(request.form.get("speed", 180))
        tone = request.form.get("tone", "Normal")
        lang = request.form.get("language", "English")
        translate = request.form.get("translate") == "on"
        action = request.form.get("action", "preview")

        uploaded_file = request.files.get("file")
        if uploaded_file and uploaded_file.filename != "":
            uploaded_text = extract_text_from_file(uploaded_file)
            if not text.strip():
                text = uploaded_text

        if not text.strip():
            flash("Please enter text or upload a file!", "warning")
            return redirect(url_for("index"))

        # Translation
        if translate and lang in LANGUAGES:
            translated_text = translator.translate(text, dest=LANGUAGES[lang]).text
        else:
            translated_text = text

        # English -> pyttsx3, others -> gTTS
        if lang == "English":
            audio_path = synthesize_pyttsx3(translated_text, speed, tone)
            if not audio_path:
                flash("TTS generation failed!", "danger")
                return redirect(url_for("index"))
            if action == "preview":
                with open(audio_path, "rb") as f:
                    audio_base64 = base64.b64encode(f.read()).decode("utf-8")
                os.remove(audio_path)
            elif action == "download":
                return send_file(audio_path, as_attachment=True,
                                 download_name=f"echoverse_{tone}.wav",
                                 mimetype="audio/wav")
        else:
            audio_file = synthesize_gtts(translated_text, lang)
            if not audio_file:
                flash("TTS generation failed!", "danger")
                return redirect(url_for("index"))
            if action == "preview":
                audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")
            elif action == "download":
                return send_file(audio_file, as_attachment=True,
                                 download_name=f"echoverse_{lang}.mp3",
                                 mimetype="audio/mpeg")

    return render_template("index.html",
                           audio_base64=audio_base64,
                           uploaded_text=uploaded_text,
                           translated_text=translated_text,
                           tones=tones.keys(),
                           languages=LANGUAGES.keys())

if __name__ == "__main__":
    app.run(debug=True)
