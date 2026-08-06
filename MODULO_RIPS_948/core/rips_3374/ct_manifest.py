from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from core.rips_3374.txt_parser import Rips3374Package

# Orden recomendado en CT (lineamientos IPS — advertencia si difiere)
CT_RECOMMENDED_ORDER: tuple[str, ...] = (
    "US",
    "AF",
    "AC",
    "AP",
    "AU",
    "AH",
    "AN",
    "AM",
    "AT",
)

CT_IDX_COD_PRESTADOR = 0
CT_IDX_FECHA_REMISION = 1
CT_IDX_CODIGO_ARCHIVO = 2
CT_IDX_TOTAL_REGISTROS = 3


@dataclass
class CtEntry:
    line_no: int
    cod_prestador: str
    fecha_remision: str
    codigo_archivo: str
    total_registros: int


def _valid_date_ddmmyyyy(value: str) -> bool:
    return bool(re.match(r"^\d{2}/\d{2}/\d{4}$", (value or "").strip()))


def parse_ct_entries(rows: list[list[str]]) -> tuple[list[CtEntry], list[str]]:
    errors: list[str] = []
    entries: list[CtEntry] = []
    seen_codes: set[str] = set()
    for i, row in enumerate(rows, start=1):
        if len(row) < 4:
            errors.append(f"CT línea {i}: se esperan 4 campos (prestador, fecha, archivo, total).")
            continue
        cod_prest = row[CT_IDX_COD_PRESTADOR].strip()
        fecha = row[CT_IDX_FECHA_REMISION].strip()
        cod_arch = row[CT_IDX_CODIGO_ARCHIVO].strip().upper()
        total_s = row[CT_IDX_TOTAL_REGISTROS].strip()
        if len(cod_prest) != 12 or not cod_prest.isdigit():
            errors.append(f"CT línea {i}: código prestador debe tener 12 dígitos ({cod_prest!r}).")
        if not _valid_date_ddmmyyyy(fecha):
            errors.append(f"CT línea {i}: fecha de remisión inválida ({fecha!r}), use dd/mm/aaaa.")
        if len(cod_arch) < 3:
            errors.append(f"CT línea {i}: código de archivo inválido ({cod_arch!r}).")
        else:
            ftype = cod_arch[:2]
            if ftype == "CT":
                errors.append(f"CT línea {i}: el manifiesto no debe listar el propio CT.")
            elif ftype not in {"US", "AF", "AD", "AC", "AP", "AU", "AH", "AN", "AM", "AT"}:
                errors.append(f"CT línea {i}: tipo de archivo desconocido en {cod_arch!r}.")
        if cod_arch in seen_codes:
            errors.append(f"CT línea {i}: código de archivo repetido ({cod_arch}).")
        seen_codes.add(cod_arch)
        try:
            total = int(total_s)
        except ValueError:
            errors.append(f"CT línea {i}: total de registros no es entero ({total_s!r}).")
            continue
        if total < 0:
            errors.append(f"CT línea {i}: total de registros no puede ser negativo.")
            continue
        entries.append(
            CtEntry(
                line_no=i,
                cod_prestador=cod_prest,
                fecha_remision=fecha,
                codigo_archivo=cod_arch,
                total_registros=total,
            )
        )
    return entries, errors


def _stem_matches_codigo(stem: str, codigo_archivo: str) -> bool:
    s = stem.upper()
    code = codigo_archivo.upper()
    return s == code or s.startswith(code)


def package_file_for_ct_code(
    pkg: Rips3374Package, codigo_archivo: str
) -> tuple[str | None, str | None]:
    """Devuelve (tipo RIPS, nombre archivo) si hay coincidencia en el paquete."""
    ftype = codigo_archivo[:2].upper()
    path = pkg.files.get(ftype)
    if path is None:
        return None, None
    name = path.name if isinstance(path, Path) else str(path)
    stem = Path(name).stem
    if _stem_matches_codigo(stem, codigo_archivo):
        return ftype, name
    return None, None


def ct_codes_covered_by_package(pkg: Rips3374Package) -> dict[str, str]:
    """Mapa código CT (ej. AF010100) -> nombre de archivo cargado."""
    found: dict[str, str] = {}
    for ftype, path in pkg.files.items():
        if ftype == "CT":
            continue
        name = path.name if isinstance(path, Path) else str(path)
        stem = Path(name).stem.upper()
        found[stem] = name
        # también clave por prefijo mínimo tipo+remisión si el stem es más largo
        if len(stem) > 2:
            found[stem[:8]] = name
    return found
