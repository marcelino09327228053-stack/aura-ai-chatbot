"""
Edge TTS text-to-speech.

Generates MP3 files under static/ and schedules cleanup after 20 seconds.
"""

import asyncio
import os
import re
import uuid

import edge_tts

# Global voice mode flag (shared across requests — same as original main.py).
tts_mode = False

VOICE_MAP = {
    "filipino": {"male": "fil-PH-AngeloNeural", "female": "fil-PH-BlessicaNeural"},
    "english": {"male": "en-US-GuyNeural", "female": "en-US-AriaNeural"},
    "japanese": {"male": "ja-JP-KeitaNeural", "female": "ja-JP-NanamiNeural"},
    "chinese": {"male": "zh-CN-YunxiNeural", "female": "zh-CN-XiaoxiaoNeural"},
    "korean": {"male": "ko-KR-InJoonNeural", "female": "ko-KR-SunHiNeural"},
    "hindi": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural"},
    "spanish": {"male": "es-ES-AlvaroNeural", "female": "es-ES-ElviraNeural"},
    "french": {"male": "fr-FR-HenriNeural", "female": "fr-FR-DeniseNeural"},
    "german": {"male": "de-DE-ConradNeural", "female": "de-DE-KatjaNeural"},
    "portuguese": {
        "male": "pt-BR-AntonioNeural",
        "female": "pt-BR-FranciscaNeural",
    },
    "arabic": {"male": "ar-SA-HamedNeural", "female": "ar-SA-ZariyahNeural"},
    "russian": {"male": "ru-RU-DmitryNeural", "female": "ru-RU-SvetlanaNeural"},
    "indonesian": {"male": "id-ID-ArdiNeural", "female": "id-ID-GadisNeural"},
    "thai": {"male": "th-TH-NiwatNeural", "female": "th-TH-PremwadeeNeural"},
    "vietnamese": {"male": "vi-VN-NamMinhNeural", "female": "vi-VN-HoaiMyNeural"},
}


def _clean_text_for_speech(text: str) -> str:
    """Remove Markdown/formatting characters that should not be spoken."""
    cleaned = re.sub(r"```(?:\w+)?\s*([\s\S]*?)```", r"\1", text)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"[*_~]+", "", cleaned)
    return re.sub(r"[ \t]+", " ", cleaned).strip()


async def delete_file_later(filename: str) -> None:
    await asyncio.sleep(20)
    if os.path.exists(filename):
        os.remove(filename)


async def text_to_speech(text: str, voice_type: str, language: str) -> str:
    """Synthesize speech and return the public URL path (e.g. /static/uuid.mp3)."""
    os.makedirs("static", exist_ok=True)
    filename = f"static/{uuid.uuid4()}.mp3"

    language_voices = VOICE_MAP.get(language, VOICE_MAP["english"])
    normalized_voice_type = "male" if voice_type == "male" else "female"
    voice_name = language_voices[normalized_voice_type]

    communicate = edge_tts.Communicate(
        text=_clean_text_for_speech(text),
        voice=voice_name,
        rate="+0%",
    )

    await communicate.save(filename)

    asyncio.create_task(delete_file_later(filename))

    return "/" + filename
