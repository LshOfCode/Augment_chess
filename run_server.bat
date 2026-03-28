@echo off
cd /d %~dp0

echo Installing dependencies...
python -m pip install fastapi "uvicorn[standard]"

echo Starting server...
python -m uvicorn Augment_chess_server:app --reload

pause