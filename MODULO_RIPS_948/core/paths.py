from __future__ import annotations

import shutil
import sys
from pathlib import Path

_MODULE_ROOT = Path(__file__).resolve().parent.parent


def get_module_root() -> Path:
    """Carpeta del módulo en desarrollo, o la carpeta donde está el .exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _MODULE_ROOT


def get_bundle_dir() -> Path:
    """Recursos empaquetados dentro del ejecutable (PyInstaller _MEIPASS)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", str(get_module_root())))
    return _MODULE_ROOT


def config_path() -> Path:
    local = get_module_root() / "config.json"
    if local.is_file():
        return local
    bundled = get_bundle_dir() / "config.json"
    return bundled if bundled.is_file() else local


def template_path() -> Path:
    """Plantilla Excel junto al exe; si no existe, copia desde el bundle."""
    dest = get_module_root() / "templates" / "plantilla_relacion.xlsx"
    if dest.is_file():
        return dest
    bundled = get_bundle_dir() / "templates" / "plantilla_relacion.xlsx"
    if bundled.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundled, dest)
    return dest
