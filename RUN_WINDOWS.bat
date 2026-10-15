@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python seed_demo.py
start http://localhost:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
