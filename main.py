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

from fastapi.responses import FileResponse

@app.get("/")
async def root():
    return FileResponse("index.html")

from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = genai.GenerativeModel("gemini-pro")

tts_mode = False

# 👇 ILAGAY MO DITO
# from google.cloud import texttospeech_v1 as texttospeech

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

        return {"reply": reply}

    except Exception as e:
        return {"reply": str(e)}