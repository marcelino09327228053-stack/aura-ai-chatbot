"""PDF generator example plugin — builds report data for export."""

from app.plugins.sdk.base import BasePlugin


class Plugin(BasePlugin):
    def execute(self, context, settings=None, **kwargs):
        settings = settings or {}
        report_type = settings.get("report_type") or kwargs.get("report_type", "daily")
        profile = context.read_company_profile()
        report = context.generate_reports(report_type)

        return {
            "status": "ready",
            "company": profile["company_name"],
            "report_type": report_type,
            "summary": report,
            "message": "Report data prepared. Use /reports/export/pdf for full PDF download.",
        }
