@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m uvicorn owner_main:app --host 127.0.0.1 --port 9000
pause
