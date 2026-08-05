@echo off
setlocal
cd /d "%~dp0.."

echo === Modulo RIPS 948 - generar ejecutable Windows ===
python --version >nul 2>&1
if errorlevel 1 (
  echo No se encontro Python. Instale Python 3.10+ desde python.org
  exit /b 1
)

python -m pip install -r requirements.txt pyinstaller
python scripts\init_template.py
if not exist "templates\plantilla_relacion.xlsx" (
  echo Error: no se creo la plantilla Excel.
  exit /b 1
)

pyinstaller --noconfirm --clean --windowed --onefile ^
  --name ModuloRIPS948 ^
  --add-data "config.json;." ^
  --add-data "templates\plantilla_relacion.xlsx;templates" ^
  --collect-all PySide6 ^
  --hidden-import orjson ^
  --hidden-import openpyxl ^
  app.py

if errorlevel 1 (
  echo Fallo PyInstaller.
  exit /b 1
)

echo.
echo Listo: dist\ModuloRIPS948.exe
echo Copie ModuloRIPS948.exe a la carpeta de trabajo (ej. D:\MODULORIPS).
echo La primera vez creara templates\ junto al .exe si hace falta.
echo.
pause
