from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import os

from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GEMINI_API_KEY")
print("KEY FOUND:", key)

genai.configure(api_key=key)

app = FastAPI()

from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = genai.GenerativeModel("gemini-2.5-flash")

tts_mode = False

# 👇 ILAGAY MO DITO
from google.cloud import texttospeech_v1 as texttospeech

def text_to_speech(text, voice_type="female"):
    import time

    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=text)

    if voice_type == "male":
        gender = texttospeech.SsmlVoiceGender.MALE
    else:
        gender = texttospeech.SsmlVoiceGender.FEMALE

    voice = texttospeech.VoiceSelectionParams(
        language_code="fil-PH",
        ssml_gender=gender
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=input_text,
        voice=voice,
        audio_config=audio_config
    )

    filename = f"static/output_{int(time.time())}.mp3"

    with open(filename, "wb") as out:
       out.write(response.audio_content)

    import threading
    import time
    import os

    def delete_file_later(path):
        time.sleep(60)

        if os.path.exists(path):
            os.remove(path)
            print("Deleted:", path)

    threading.Thread(
        target=delete_file_later,
        args=(filename,),
        daemon=True
    ).start()

    return f"/{filename}"
    

# 👇 AFTER NITO
class Message(BaseModel):
    text: str
    companyProfile: str = ""
    voiceType: str = "female"

@app.post("/chat")
def chat(msg: Message):
    try:
        global tts_mode  # 👈 pinaka una

        text_lower = msg.text.lower()

        # 🔊 ON
        if "voice on" in text_lower:
            tts_mode = True
            return {"reply": "🔊 Voice ON"}

        # 🔇 OFF
        if "voice off" in text_lower:
            tts_mode = False
            return {"reply": "🔇 Voice OFF"}

        use_voice = tts_mode

        # 👇 AI prompt (after command check)
        prompt = f"""
You are the official AI assistant of this business.

Use a professional, natural, and clean chat style.
Keep answers short, clear, and easy to read.
Use simple paragraphs instead of too many bullet points.
Answer directly.
Sound like a real company representative.
Avoid repeating unnecessary details.

Company Information:
{msg.companyProfile}

Customer Message:
{msg.text}
"""

        response = model.generate_content(prompt)

        reply = getattr(response, "text", None)

        if not reply:
            reply = "Sorry, no response generated."

        import re

        if use_voice:
            clean_reply = re.sub(r'\s+', ' ', reply).strip()
            audio_file = text_to_speech(clean_reply, msg.voiceType)
            return {"reply": reply, "audio": audio_file}

        return {"reply": reply}

    except Exception as e:
        return {"reply": str(e)}