"""SMS sender example plugin (draft — does not send real SMS)."""

from app.plugins.sdk.base import BasePlugin


class Plugin(BasePlugin):
    def execute(self, context, settings=None, **kwargs):
        settings = settings or {}
        profile = context.read_company_profile()
        faqs = context.read_faq()
        phone = settings.get("phone") or kwargs.get("phone", "+639000000000")
        message = settings.get("message") or kwargs.get("message", "")

        if not message and faqs:
            message = f"{profile['company_name']}: {faqs[0]['answer'][:120]}"

        return {
            "status": "draft",
            "phone": phone,
            "message": message[:160],
            "note": "SMS draft prepared (not sent — configure SMS gateway in settings).",
        }
