@echo off
echo Starting ProductFind AI Server on http://localhost:8000...
cd /d "%~dp0"
.\.venv\Scripts\python.exe -m uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload
