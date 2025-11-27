@echo off
chcp 65001 > nul
echo Activating virtual environment...
call .\venv\Scripts\activate.bat


echo Starting FastAPI server with UVicorn...
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause