@echo off
cd /d %~dp0

echo Installing dependencies...
python -m pip install fastapi uvicorn

echo Starting server...
python -m uvicorn online_chess_server:app --reload

pause