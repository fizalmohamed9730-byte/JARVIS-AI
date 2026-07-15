@echo off
echo ============================================
echo   JARVIS - AI Personal Assistant
echo   Starting services...
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

:: Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

:: Create .env if missing
if not exist .env (
    echo [INFO] Creating .env from .env.example...
    copy .env.example .env >nul
)

:: Install Python dependencies
echo [1/4] Installing Python dependencies...
pip install -r requirements.txt -q

:: Install frontend dependencies
echo [2/4] Installing frontend dependencies...
cd frontend
call npm install --silent
cd ..

:: Create data directories
echo [3/4] Creating data directories...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist data\workspace mkdir data\workspace
if not exist data\generated_images mkdir data\generated_images

:: Start backend
echo [4/4] Starting services...
echo.
echo Starting Backend on http://localhost:8000
start "JARVIS Backend" cmd /c "cd /d %~dp0 && python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

:: Wait for backend
timeout /t 3 /nobreak >nul

:: Start frontend
echo Starting Frontend on http://localhost:5173
start "JARVIS Frontend" cmd /c "cd /d %~dp0\frontend && npm run dev"

echo.
echo ============================================
echo   JARVIS is starting up!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   API Docs: http://localhost:8000/docs
echo ============================================
echo.
echo Press any key to open JARVIS in your browser...
pause >nul
start http://localhost:5173
