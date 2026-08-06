from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from core.rips_3374.constants import RIPS_TXT_TYPES


def split_rips_line(line: str) -> list[str]:
    """Campos separados por coma (Res. 3374)."""
    return line.rstrip("\r\n").split(",")


def file_type_from_name(name: str) -> str | None:
    base = Path(name).name.upper()
    if len(base) < 2:
        return None
    prefix = base[:2]
    if prefix in RIPS_TXT_TYPES:
        return prefix
    return None


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


def load_from_zip(zip_path: Path) -> Rips3374Package:
    pkg = Rips3374Package(source_label=zip_path.name)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                if not name.lower().endswith(".txt"):
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


def list_matching_txt_in_folder(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(folder.glob("*.txt")):
        if file_type_from_name(path.name):
            out.append(path)
    return out


def remision_from_filename(name: str) -> str | None:
    m = re.match(r"^[A-Z]{2}(.+)\.TXT$", name.upper())
    if not m:
        return None
    return m.group(1)
