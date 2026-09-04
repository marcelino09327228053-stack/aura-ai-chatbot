"""
Translation engine — built-in phrase dictionary + AI-powered fallback.

Supported languages: en, fil (Filipino), zh (Chinese), ja (Japanese),
                     ko (Korean), es (Spanish).

Architecture:
  1. Look up in built-in phrase dictionary (instant, no external call)
  2. If phrase not found, generate a structured translation prompt for the AI
     service and return the result
  3. Cache translated pairs in the database per company
"""

from __future__ import annotations

# ── Built-in phrase dictionary ────────────────────────────────────────────────
# Format: PHRASES[target_lang][source_english] = translated
PHRASES: dict[str, dict[str, str]] = {
    "fil": {
        "Hello": "Kamusta",
        "Welcome": "Maligayang pagdating",
        "Thank you": "Salamat",
        "Good morning": "Magandang umaga",
        "Good afternoon": "Magandang hapon",
        "Good evening": "Magandang gabi",
        "How can I help you?": "Paano kita matutulungan?",
        "Order confirmed": "Nakumpirma ang order",
        "Payment received": "Natanggap ang bayad",
        "Invoice": "Invoice",
        "Report": "Ulat",
        "Dashboard": "Dashboard",
        "Settings": "Mga Setting",
        "Logout": "Mag-logout",
        "Yes": "Oo",
        "No": "Hindi",
        "Save": "I-save",
        "Cancel": "Kanselahin",
        "Error": "Error",
        "Success": "Tagumpay",
    },
    "zh": {
        "Hello": "你好",
        "Welcome": "欢迎",
        "Thank you": "谢谢",
        "Good morning": "早上好",
        "Good afternoon": "下午好",
        "Good evening": "晚上好",
        "How can I help you?": "我能帮助你吗？",
        "Order confirmed": "订单已确认",
        "Payment received": "已收款",
        "Invoice": "发票",
        "Report": "报告",
        "Dashboard": "仪表板",
        "Settings": "设置",
        "Logout": "登出",
        "Yes": "是",
        "No": "否",
        "Save": "保存",
        "Cancel": "取消",
        "Error": "错误",
        "Success": "成功",
    },
    "ja": {
        "Hello": "こんにちは",
        "Welcome": "ようこそ",
        "Thank you": "ありがとう",
        "Good morning": "おはようございます",
        "Good afternoon": "こんにちは",
        "Good evening": "こんばんは",
        "How can I help you?": "何かお手伝いできますか？",
        "Order confirmed": "注文が確認されました",
        "Payment received": "お支払いを受け付けました",
        "Invoice": "請求書",
        "Report": "レポート",
        "Dashboard": "ダッシュボード",
        "Settings": "設定",
        "Logout": "ログアウト",
        "Yes": "はい",
        "No": "いいえ",
        "Save": "保存",
        "Cancel": "キャンセル",
        "Error": "エラー",
        "Success": "成功",
    },
    "ko": {
        "Hello": "안녕하세요",
        "Welcome": "환영합니다",
        "Thank you": "감사합니다",
        "Good morning": "좋은 아침입니다",
        "Good afternoon": "안녕하세요",
        "Good evening": "좋은 저녁입니다",
        "How can I help you?": "어떻게 도와드릴까요?",
        "Order confirmed": "주문이 확인되었습니다",
        "Payment received": "결제가 완료되었습니다",
        "Invoice": "청구서",
        "Report": "보고서",
        "Dashboard": "대시보드",
        "Settings": "설정",
        "Logout": "로그아웃",
        "Yes": "예",
        "No": "아니요",
        "Save": "저장",
        "Cancel": "취소",
        "Error": "오류",
        "Success": "성공",
    },
    "es": {
        "Hello": "Hola",
        "Welcome": "Bienvenido",
        "Thank you": "Gracias",
        "Good morning": "Buenos días",
        "Good afternoon": "Buenas tardes",
        "Good evening": "Buenas noches",
        "How can I help you?": "¿Cómo puedo ayudarte?",
        "Order confirmed": "Pedido confirmado",
        "Payment received": "Pago recibido",
        "Invoice": "Factura",
        "Report": "Informe",
        "Dashboard": "Panel de control",
        "Settings": "Configuración",
        "Logout": "Cerrar sesión",
        "Yes": "Sí",
        "No": "No",
        "Save": "Guardar",
        "Cancel": "Cancelar",
        "Error": "Error",
        "Success": "Éxito",
    },
    "en": {},  # English → English is a no-op
}

SUPPORTED_LANGUAGES = {
    "en": "English",
    "fil": "Filipino",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
}

LANGUAGE_META = {
    "en":  {"flag": "🇺🇸", "direction": "ltr", "locale": "en-US"},
    "fil": {"flag": "🇵🇭", "direction": "ltr", "locale": "fil-PH"},
    "zh":  {"flag": "🇨🇳", "direction": "ltr", "locale": "zh-CN"},
    "ja":  {"flag": "🇯🇵", "direction": "ltr", "locale": "ja-JP"},
    "ko":  {"flag": "🇰🇷", "direction": "ltr", "locale": "ko-KR"},
    "es":  {"flag": "🇪🇸", "direction": "ltr", "locale": "es-ES"},
}


def translate_text(text: str, target_lang: str, source_lang: str = "en") -> str:
    """
    Translate `text` from `source_lang` to `target_lang`.

    Strategy:
      1. Same language → return as-is
      2. Dictionary lookup (normalised English source)
      3. AI-generated translation via ai_service
    """
    if source_lang == target_lang or target_lang == "en":
        return text

    # Dictionary lookup (English source only)
    if source_lang == "en":
        lang_dict = PHRASES.get(target_lang, {})
        if text in lang_dict:
            return lang_dict[text]

    # AI fallback — build a structured prompt
    try:
        from app.services.ai_service import generate_reply
        prompt = (
            f"Translate the following text from {SUPPORTED_LANGUAGES.get(source_lang, source_lang)} "
            f"to {SUPPORTED_LANGUAGES.get(target_lang, target_lang)}. "
            f"Return ONLY the translated text, no explanation.\n\nText: {text}"
        )
        return generate_reply(prompt)
    except Exception:
        return f"[{target_lang.upper()}] {text}"


def translate_batch(texts: list[str], target_lang: str, source_lang: str = "en") -> list[dict]:
    return [
        {
            "source": t,
            "translated": translate_text(t, target_lang, source_lang),
            "target_lang": target_lang,
        }
        for t in texts
    ]


def detect_language(text: str) -> str:
    """Simple heuristic language detector (script-based)."""
    for ch in text:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF:
            return "zh"
        if 0x3040 <= cp <= 0x30FF:
            return "ja"
        if 0xAC00 <= cp <= 0xD7AF:
            return "ko"
    # Spanish heuristic
    es_markers = ["ñ", "¿", "¡", "ó", "á", "é", "í", "ú"]
    if any(m in text.lower() for m in es_markers):
        return "es"
    # Filipino heuristic
    fil_words = ["ang", "ng", "mga", "sa", "na", "at", "ay", "ko", "mo"]
    words = text.lower().split()
    fil_hits = sum(1 for w in words if w in fil_words)
    if fil_hits >= 2:
        return "fil"
    return "en"


def list_supported_languages() -> list[dict]:
    return [
        {
            "code": code,
            "name": name,
            **LANGUAGE_META.get(code, {}),
        }
        for code, name in SUPPORTED_LANGUAGES.items()
    ]
