"""
Chat orchestration: voice commands, FAQ lookup, AI providers, optional TTS.
"""

import html
import os
import re
from html.parser import HTMLParser

from fastapi import HTTPException

from app.database import (
    conversation_repository,
    usage_repository,
)
from app.database.knowledge_repository import search as search_knowledge
from app.database.faq_repository import find_faq_answer
from app.services import ai_gateway, tts_service
from app.services import customer_memory_service
from app.services.response_style_service import build_response_style_instruction
from app.services.subscription_service import check_message_limit


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "svg", "noscript"}:
            self.ignored_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "svg", "noscript"}:
            self.ignored_depth = max(0, self.ignored_depth - 1)

    def handle_data(self, data):
        if not self.ignored_depth:
            self.parts.append(data)


def _plain_company_profile(profile: str) -> str:
    if not profile:
        return ""
    parser = _VisibleTextParser()
    try:
        parser.feed(profile)
        text = " ".join(parser.parts)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", profile)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50_000]


def _professional_plain_reply(reply: str) -> str:
    """Remove model-generated Markdown while keeping readable plain text."""
    text = str(reply or "").replace("```", "")
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[*+-]\s+", "• ", text)
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"__([^\n]+?)__", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _company_representative_reply(reply: str) -> str:
    """Enforce a direct first-person company voice for customer answers."""
    text = _professional_plain_reply(reply)
    source_openers = (
        r"^\s*Batay sa (?:ibinigay na )?(?:company |kumpanya )?profile(?: ng kumpanya)?\s*,?\s*",
        r"^\s*Ayon sa (?:ibinigay na )?(?:company |kumpanya )?profile(?: ng kumpanya)?\s*,?\s*",
        r"^\s*Based on (?:the )?(?:provided )?(?:company )?profile\s*,?\s*",
        r"^\s*According to (?:the )?(?:provided )?(?:company )?profile\s*,?\s*",
    )
    for pattern in source_openers:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\bAng pangalan ng (?:aming )?kumpanya ay\b",
        "Ang pangalan ng aming kumpanya ay",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bThe company(?:'s)? name is\b",
        "Our company name is",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^\s*(.+?)\s+ang pangalan ng kumpanya\.?$",
        r"Ang pangalan ng kumpanya namin ay \1.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^\s*Ang mga produkto at serbisyo ng .+? ay kinabibilangan ng\s*:?",
        "Ang mga produkto at serbisyong inaalok ng kumpanya namin ay: ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^\s*Ang mga produkto ng .+? ay kinabibilangan ng\s*:?",
        "Ang mga produkto ng kumpanya namin ay: ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b(?:halimbawa|hal\.|for example|e\.g\.)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r":[ \t]+", ": ", text)
    text = re.sub(r"\.{2,}$", ".", text)
    return text.strip()


def _language_instruction(language: str) -> str:
    if language in {"auto", "auto-detect", "detect"}:
        return (
            "Detect the language used in the user's latest message and respond in that same "
            "language. If the message mixes languages, follow its dominant language and natural "
            "speaking style. Do not mention language detection."
        )
    if language == "filipino":
        return "Respond only in Filipino."
    if language == "english":
        return "Respond only in English."
    if language == "japanese":
        return "Respond only in Japanese."
    if language == "chinese":
        return "Respond only in Simplified Chinese."
    if language == "korean":
        return "Respond only in Korean."
    if language == "hindi":
        return "Respond only in Hindi."
    if language in {"bisaya", "cebuano"}:
        return "Respond only in natural Cebuano/Bisaya."
    return ""


def _build_prompt(
    text: str,
    company_profile: str,
    language: str,
    conversation_context: str = "",
    response_style_instruction: str = "",
    customer_memory_context: str = "",
    earlier_conversation_summary: str = "",
) -> str:
    language_instruction = _language_instruction(language)
    clean_profile = _plain_company_profile(company_profile)
    return f"""
You are MB Future Tech AI Chatbot, a professional AI business assistant.

{language_instruction}

Rules:
- Be concise and professional.
- Write like a courteous, knowledgeable human representative.
- Speak as an official representative of the company in Company Information. Use a
  natural first-person company voice such as "we", "our", "kami", and "aming".
- Never say "based on the company profile", "according to the provided information",
  "the company", "the business", or similar third-person source disclaimers when the
  requested fact is available. State the answer naturally on behalf of the company.
- Never use "for example", "such as", "halimbawa", or "hal." merely to qualify facts
  already listed in Company Information. Present those names directly and confidently.
- Prefer direct phrasing: "Ang pangalan ng aming kumpanya ay...", "Ang aming mga
  produkto ay...", "Nag-aalok kami ng...", and "Makipag-ugnayan sa amin sa...".
- Previous assistant messages may contain third-person wording. Do not copy that style.
- Do not claim to be a human employee. You may identify yourself as the company's AI
  assistant only when the customer specifically asks who or what you are.
- Return plain text only. Never use Markdown, asterisks, bold markers, hashtags,
  code fences, decorative symbols, or robotic section labels.
- When an answer contains three or more distinct products, services, projects,
  locations, requirements, or steps, do not place them in one long sentence. Write one
  short introduction, then put each item on its own line prefixed with the plain bullet
  character "•". If both products and services are present, group them under the simple
  labels "Products:" and "Services:". Bullets are allowed; asterisks are not.
- Avoid long numbered questionnaires unless necessary.
- Ask at most one or two follow-up questions.
- Give direct answers first.
- Use short paragraphs.
- Sound like a professional consultant.
- Never overwhelm the user with too many questions.
- For questions about the company, products, services, prices, policies, contact
  details, or operations, use the Company Information below as the primary truth.
- Do not invent company facts that are not explicitly present in Company Information
  or Relevant Company Knowledge.
- If the requested company fact is missing, clearly say that the information is not
  available in the company profile and suggest contacting a human representative.
- A new conversation does not reset or remove Company Information.
- When asked for the company name, answer directly using a natural sentence such as
  "Our company name is [exact company name]." Use the equivalent sentence in the
  user's language. Do not introduce yourself as MB Future Tech unless that is the
  company name explicitly stated in Company Information.
- Copy the company name exactly as written in Company Information. Never expand "Inc."
  into "Incorporated", shorten the name, translate it, or alter its legal suffix.
- Never reveal, guess, or discuss the underlying AI provider, model name, API account,
  routing order, or server credentials. Identify only as the customer's business assistant.

{response_style_instruction}

Explicit Customer Preferences:
{customer_memory_context or "No explicitly saved customer preferences."}

Earlier Conversation Summary:
{earlier_conversation_summary or "No earlier conversation summary."}

Company Information:
{clean_profile or "No company profile has been provided."}

Recent Conversation:
{conversation_context or "No previous messages in this conversation."}

User:
{text}
"""


def _build_system_guide_prompt(
    text: str,
    language: str,
    conversation_context: str = "",
) -> str:
    language_instruction = _language_instruction(language)
    return f"""
You are the MB Future Tech AI System Guide. Your only job is to help users understand
and operate the MB Future Tech AI Chatbot platform.

{language_instruction}

Platform capabilities you may explain:
- Company Workspace and Company Profile Manager: paste or edit company information,
  Save & Auto Edit, review AI suggestions, activate a profile, undo changes, search the
  profile, test sample customer questions, and restore or delete profile versions.
- AI access: an active subscription includes a monthly AI allowance. Provider accounts,
  API keys, model selection, retries, and authorized fallbacks are securely managed by
  the server-side AI Gateway. Customers never need to supply a provider API key.
- Social Connections: connect supported business messaging channels such as Facebook
  Messenger; other displayed channels may be marked Coming soon.
- Multiple dashboards: each business or Page should use its own dashboard and company
  profile, while all AI requests remain isolated to the active customer allowance.
- Language and voice settings, microphone speech-to-text, themes and animated
  backgrounds, billing, analytics and reports, attachments, and account/profile settings.
- Test Your AI is for checking customer answers based on the active company profile.

Rules:
- Explain the interface step by step in simple, non-technical language.
- Give the direct next action first and keep answers concise.
- Return professional plain text only. Never use Markdown or asterisks.
- Ask at most one follow-up question when the request is unclear.
- Never use, quote, summarize, or make claims from a customer's company profile.
- Do not answer as the customer's business assistant. If asked about customer/company
  facts, explain that those belong in Test Your AI or the customer-facing chatbot.
- Do not claim a feature is already connected or active unless the user says it is.
- Do not invent buttons, menus, integrations, prices, or capabilities.
- This guide is text-only. Never offer or generate text-to-speech audio.
- Never reveal or guess the underlying AI provider, model name, routing order, API
  account, or server credentials. Refer to it only as managed AI access.

Recent System Guide Conversation:
{conversation_context or "No previous guide messages."}

User:
{text}
"""


async def handle_chat(
    text: str,
    company_id: int,
    company_profile: str = "",
    voice_type: str = "female",
    language: str = "english",
    session_id: str | None = None,
    providers: list[str] | None = None,
    system_guide: bool = False,
    user_id: int | None = None,
    request_id: str | None = None,
) -> dict:
    """
    Process a chat message and return {"reply": ...} or {"reply": ..., "audio": ...}.
    """
    try:
        text_lower = text.lower()
        session_id = session_id or conversation_repository.new_session_id()
        contact_key = session_id

        if not system_guide and "voice on" in text_lower:
            tts_service.tts_mode = True
            return {"reply": "🔊 Voice ON", "session_id": session_id}

        if not system_guide and "voice off" in text_lower:
            tts_service.tts_mode = False
            return {"reply": "🔇 Voice OFF", "session_id": session_id}

        use_voice = False if system_guide else tts_service.tts_mode

        preferences = {}
        earlier_summary = ""
        effective_language = language
        if not system_guide:
            preferences = customer_memory_service.update_explicit_preferences(
                company_id, contact_key, text
            )
            earlier_summary = customer_memory_service.get_conversation_summary(
                company_id, contact_key
            )
            if language in {"auto", "auto-detect", "detect"}:
                preferred = preferences.get("preferred_language", "").casefold()
                effective_language = {
                    "english": "english",
                    "filipino": "filipino",
                    "cebuano/bisaya": "cebuano",
                }.get(preferred, language)

        check_message_limit(company_id)
        conversation_repository.add_message(company_id, session_id, "user", text)

        usage_repository.record_message(company_id)

        faq_answer = None if system_guide else find_faq_answer(text, company_id)
        if faq_answer:
            reply = _company_representative_reply(faq_answer)
            conversation_repository.add_message(
                company_id, session_id, "assistant", reply
            )
            result = {
                "reply": reply,
                "session_id": session_id,
                "provider_responses": [],
                "sources": [{"type": "faq"}],
            }
            if use_voice:
                result["audio"] = await tts_service.text_to_speech(
                    reply, voice_type, language
                )
            return result

        recent_messages = conversation_repository.list_messages(company_id, session_id, 13)
        previous_messages = recent_messages[:-1]
        conversation_context = "\n".join(
            f"{item['role'].title()}: {item['content']}"
            for item in previous_messages[-12:]
        )
        knowledge_matches = [] if system_guide else search_knowledge(company_id, text)
        if knowledge_matches:
            knowledge_context = "\n\n".join(
                f"Source: {item['document_name']}\n{item['content']}"
                for item in knowledge_matches
            )
            company_profile = (
                f"{company_profile}\n\nRelevant company knowledge:\n{knowledge_context}"
            )
        prompt = (
            _build_system_guide_prompt(text, language, conversation_context)
            if system_guide
            else _build_prompt(
                text,
                company_profile,
                effective_language,
                conversation_context,
                build_response_style_instruction(company_id),
                customer_memory_service.build_customer_memory_context(preferences),
                earlier_summary,
            )
        )
        # Provider hints from customers are intentionally ignored. Selection and
        # authorized fallback order are controlled centrally by the Gateway.
        del providers
        gateway_result = await ai_gateway.generate(
            prompt,
            company_id=company_id,
            user_id=user_id,
            request_id=request_id,
        )
        reply = gateway_result["reply"]
        successful = [{
            "reply": reply,
            "ok": True,
        }]
        provider_responses = successful

        reply = _professional_plain_reply(reply) if system_guide else _company_representative_reply(reply)
        conversation_repository.add_message(company_id, session_id, "assistant", reply)

        if not system_guide:
            total_messages = conversation_repository.count_messages(company_id, session_id)
            if total_messages >= 40 and total_messages % 40 == 0 and successful:
                try:
                    summary_messages = conversation_repository.list_messages(
                        company_id, session_id, 50
                    )[:-12]
                    transcript = "\n".join(
                        f"{item['role'].title()}: {item['content']}"
                        for item in summary_messages
                    )[-9000:]
                    summary_prompt = f"""
Summarize the earlier customer conversation in no more than 150 words. Preserve only
useful unresolved questions, decisions, customer needs, and explicitly stated preferences.
Do not infer sensitive traits and do not include company-profile boilerplate. Return plain
text only.

Previous summary:
{earlier_summary or "None"}

Conversation to compact:
{transcript}
"""
                    summary_result = await ai_gateway.generate(
                        summary_prompt,
                        company_id=company_id,
                        user_id=user_id,
                        request_id=f"{request_id or session_id}:summary:{total_messages}",
                    )
                    customer_memory_service.save_conversation_summary(
                        company_id,
                        contact_key,
                        _professional_plain_reply(summary_result["reply"]),
                    )
                except Exception:
                    # Summary memory is optional and must never block a customer reply.
                    pass

        if use_voice:
            audio_file = await tts_service.text_to_speech(reply, voice_type, language)
            return {
                "reply": reply,
                "audio": audio_file,
                "session_id": session_id,
                "provider_responses": provider_responses,
            }

        return {
            "reply": reply,
            "session_id": session_id,
            "provider_responses": provider_responses,
            "sources": [
                {
                    "document_id": item["document_id"],
                    "document_name": item["document_name"],
                }
                for item in knowledge_matches
            ],
        }

    except HTTPException as exc:
        return {
            "reply": exc.detail,
            "session_id": session_id or "",
        }
    except Exception:
        return {
            "reply": "⚠️ AI is currently busy. Please try again in a moment.",
            "session_id": session_id or "",
        }
