@echo off
cd /d I:\ai-chatbot
call venv\Scripts\activate
python -m uvicorn main:app --reload
pause