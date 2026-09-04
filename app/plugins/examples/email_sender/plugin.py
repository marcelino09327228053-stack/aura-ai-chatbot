"""Email sender example plugin (draft — does not send real email)."""

from app.plugins.sdk.base import BasePlugin


class Plugin(BasePlugin):
    def execute(self, context, settings=None, **kwargs):
        settings = settings or {}
        profile = context.read_company_profile()
        to = settings.get("to") or kwargs.get("to", "customer@example.com")
        subject = settings.get("subject") or kwargs.get("subject", "MB Future Tech AI Chatbot Notification")
        recent = context.read_conversations(limit=3)

        body_lines = [
            f"From: {profile['company_name']}",
            f"To: {to}",
            f"Subject: {subject}",
            "",
            profile.get("company_profile", "")[:500],
        ]
        if recent:
            body_lines.append("\nRecent conversation context:")
            for msg in recent[:3]:
                body_lines.append(f"- [{msg['role']}] {msg['content'][:80]}")

        return {
            "status": "draft",
            "to": to,
            "subject": subject,
            "body_preview": "\n".join(body_lines)[:1000],
            "message": "Email draft prepared (not sent — configure SMTP in settings).",
        }
