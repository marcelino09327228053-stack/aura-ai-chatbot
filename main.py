"""
MB Future Tech AI Chatbot entry point.

uvicorn main:app --reload

The application lives under app/; this file re-exports the FastAPI instance
so run.bat, Procfile, and existing deploy scripts keep working unchanged.
"""

from app.main import app

__all__ = ["app"]
