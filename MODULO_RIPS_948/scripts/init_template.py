#!/usr/bin/env python3
"""Genera la plantilla Excel inicial."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.excel_export import ensure_template  # noqa: E402


def main() -> None:
    path = ROOT / "templates" / "plantilla_relacion.xlsx"
    ensure_template(path)
    print(f"Plantilla creada: {path}")


if __name__ == "__main__":
    main()
