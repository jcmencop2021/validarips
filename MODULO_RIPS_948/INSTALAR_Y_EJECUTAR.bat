@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo  Modulo RIPS - instalar y ejecutar
echo  Carpeta: %CD%
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo No se encontro Python. Instale desde https://www.python.org
  echo Marque "Add python to PATH" al instalar.
  pause
  exit /b 1
)

echo Instalando dependencias (PySide6, openpyxl, orjson)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Error al instalar. Revise su conexion a internet.
  pause
  exit /b 1
)

python scripts\init_template.py
echo.
echo Iniciando aplicacion...
python app.py
pause
