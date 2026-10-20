@echo off
cd /d "%~dp0"
"C:\Users\brigh\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn api.main:app --host 0.0.0.0 --port 8000
