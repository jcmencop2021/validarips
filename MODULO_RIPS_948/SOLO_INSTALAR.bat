@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instalando dependencias en: %CD%
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts\init_template.py
echo.
echo Listo. Ahora ejecute: python app.py
echo O doble clic en INSTALAR_Y_EJECUTAR.bat
pause
