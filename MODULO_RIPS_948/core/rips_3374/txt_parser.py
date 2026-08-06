from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from core.rips_3374.constants import RIPS_TXT_TYPES

_SKIP_DIR_NAMES = frozenset({".git", "__pycache__", "node_modules", ".venv", "venv"})


def split_rips_line(line: str) -> list[str]:
    """Campos separados por coma (Res. 3374)."""
    return line.rstrip("\r\n").split(",")


def normalize_folder_path(text: str) -> Path | None:
    """Ruta de carpeta escrita en UI o devuelta por QFileDialog (Windows/Linux)."""
    raw = (text or "").strip().strip('"').strip("'")
    if not raw:
        return None
    try:
        p = Path(os.path.expandvars(raw)).expanduser()
    except (ValueError, OSError):
        return None
    try:
        return p.resolve(strict=False)
    except OSError:
        return p


def file_type_from_name(name: str) -> str | None:
    """Tipo RIPS por prefijo CT/AF/US… (p. ej. CT9959.txt o CT9959 sin extensión)."""
    stem = Path(name).name
    if stem.lower().endswith(".txt"):
        stem = Path(stem).stem
    stem = stem.upper()
    if len(stem) < 2:
        return None
    prefix = stem[:2]
    if prefix in RIPS_TXT_TYPES:
        return prefix
    if len(stem) > 2:
        suffix = stem[-2:]
        if suffix in RIPS_TXT_TYPES:
            return suffix
    return None


def _is_rips_txt_file(path: Path) -> bool:
    if not path.is_file():
        return False
    name = path.name
    if not name or name.startswith("."):
        return False
    if path.suffix.lower() == ".txt":
        return file_type_from_name(name) is not None
    if not path.suffix and file_type_from_name(name):
        return True
    return False


def discover_txt_files_in_tree(root: Path, *, max_depth: int = 12) -> list[Path]:
    """
    Busca archivos RIPS planos bajo la carpeta elegida (recursivo).
    Nombres habituales: CT9959.txt, AF9959.TXT o CT9959 sin extensión.
    """
    base = root if root.is_absolute() else normalize_folder_path(str(root))
    if base is None or not base.is_dir():
        return []

    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        if not _is_rips_txt_file(path):
            return
        key = str(path.resolve()).lower()
        if key in seen:
            return
        seen.add(key)
        found.append(path)

    def walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            with os.scandir(directory) as it:
                entries = sorted(it, key=lambda e: e.name.lower())
        except OSError:
            return
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in _SKIP_DIR_NAMES or entry.name.startswith("."):
                        continue
                    walk(Path(entry.path), depth + 1)
                elif entry.is_file(follow_symlinks=False):
                    add(Path(entry.path))
            except OSError:
                continue

    walk(base, 0)
    return sorted(found, key=lambda p: str(p).lower())


def parse_txt_file(path: Path) -> tuple[str | None, list[list[str]], str | None]:
    ftype = file_type_from_name(path.name)
    if not ftype:
        return None, [], f"Nombre no reconocido como RIPS: {path.name}"
    try:
        text = path.read_text(encoding="latin-1", errors="replace")
    except OSError as exc:
        return ftype, [], str(exc)
    rows: list[list[str]] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        rows.append(split_rips_line(raw))
    return ftype, rows, None


@dataclass
class Rips3374Package:
    """Conjunto de archivos .txt de un envío RIPS."""

    source_label: str = ""
    files: dict[str, Path] = field(default_factory=dict)
    rows: dict[str, list[list[str]]] = field(default_factory=dict)
    load_errors: list[str] = field(default_factory=list)

    def types_present(self) -> set[str]:
        return set(self.rows.keys())


def load_from_txt_paths(paths: list[Path]) -> Rips3374Package:
    pkg = Rips3374Package(source_label="archivos TXT")
    for path in paths:
        ftype, rows, err = parse_txt_file(path)
        if err:
            pkg.load_errors.append(f"{path.name}: {err}")
            continue
        if not ftype:
            continue
        if ftype in pkg.files:
            pkg.load_errors.append(
                f"Archivo duplicado para tipo {ftype}: {path.name} (ya {pkg.files[ftype].name})"
            )
            continue
        pkg.files[ftype] = path
        pkg.rows[ftype] = rows
    return pkg


def _zip_entry_is_rips_txt(name: str) -> bool:
    base = Path(name).name
    if not base:
        return False
    if base.lower().endswith(".txt"):
        return file_type_from_name(base) is not None
    return file_type_from_name(base) is not None and Path(base).suffix == ""


def load_from_zip(zip_path: Path) -> Rips3374Package:
    pkg = Rips3374Package(source_label=zip_path.name)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                if not _zip_entry_is_rips_txt(name):
                    continue
                ftype = file_type_from_name(name)
                if not ftype:
                    continue
                if ftype in pkg.files:
                    pkg.load_errors.append(f"ZIP: tipo {ftype} duplicado ({name})")
                    continue
                data = zf.read(info)
                text = data.decode("latin-1", errors="replace")
                rows: list[list[str]] = []
                for raw in text.splitlines():
                    if raw.strip():
                        rows.append(split_rips_line(raw))
                pkg.files[ftype] = Path(name)
                pkg.rows[ftype] = rows
    except zipfile.BadZipFile:
        pkg.load_errors.append(f"ZIP inválido: {zip_path}")
    except OSError as exc:
        pkg.load_errors.append(str(exc))
    return pkg


def list_txt_in_folder_for_preview(folder: Path) -> list[Path]:
    """Archivos RIPS visibles en el diálogo de carpeta."""
    base = normalize_folder_path(str(folder)) or folder
    return discover_txt_files_in_tree(base)


def list_matching_txt_in_folder(folder: Path) -> list[Path]:
    return list_txt_in_folder_for_preview(folder)


def remision_from_filename(name: str) -> str | None:
    stem = Path(name).name
    if stem.lower().endswith(".txt"):
        stem = Path(stem).stem
    stem = stem.upper()
    ftype = file_type_from_name(name)
    if not ftype:
        return None
    if stem.startswith(ftype):
        rem = stem[2:].strip("_-")
        return rem or None
    if stem.endswith(ftype):
        rem = stem[: -len(ftype)].strip("_-")
        return rem or None
    return None


def display_path_under_root(root: Path, file_path: Path) -> str:
    try:
        rel = file_path.resolve().relative_to(root.resolve())
        return rel.as_posix()
    except ValueError:
        return file_path.name
