#!/usr/bin/env bash
# Genera ejecutable (en Linux produce binario Linux; en Windows use build_exe.bat)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m pip install -r requirements.txt pyinstaller
python3 scripts/init_template.py

pyinstaller --noconfirm --clean --windowed --onefile \
  --name ModuloRIPS948 \
  --add-data "config.json:." \
  --add-data "templates/plantilla_relacion.xlsx:templates" \
  --collect-all PySide6 \
  --hidden-import orjson \
  --hidden-import openpyxl \
  app.py

echo "Listo: $ROOT/dist/ModuloRIPS948"
