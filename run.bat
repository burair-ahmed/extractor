@echo off
title Email Extractor Pro
echo ========================================================
echo        Starting Email Extractor Pro Web Application
echo ========================================================
echo.

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Setting up...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
) ELSE (
    call .venv\Scripts\activate
)

echo [*] Opening Web Application on http://127.0.0.1:8000
start http://127.0.0.1:8000
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
pause
