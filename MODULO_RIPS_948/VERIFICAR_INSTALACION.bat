@echo off
chcp 65001 >nul
echo ============================================
echo  MODULO RIPS - Verificacion de instalacion
echo ============================================
cd /d "%~dp0"
if not exist config.json (
  echo ERROR: Ejecute este archivo dentro de la carpeta MODULO_RIPS_948
  pause
  exit /b 1
)
findstr version config.json
echo.
echo Carpeta del modulo:
cd
echo.
echo Para abrir la aplicacion:
echo   python -m venv .venv
echo   .venv\Scripts\activate
echo   pip install -r requirements.txt
echo   python app.py
echo.
echo En la ventana debe verse el cartel naranja: VERSION 1.0.8
pause
