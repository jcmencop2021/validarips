from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import orjson
except ImportError:  # pragma: no cover
    orjson = None  # type: ignore

from core.fev_xml import find_companion_xml, parse_fev_xml
from core.json_extract import (
    extract_fecha_factura,
    extract_nombre_ips,
    extract_nombre_paciente,
    unwrap_rips_root,
)
from models.relation_record import RelationRecord


def _parse_json_bytes(raw: bytes) -> Any:
    if orjson is not None:
        return orjson.loads(raw)
    return json.loads(raw.decode("utf-8"))


def load_json_file(path: Path) -> tuple[Any | None, str | None]:
    try:
        raw = path.read_bytes()
        return _parse_json_bytes(raw), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{path.name}: JSON inválido ({exc})"


def discover_json_paths(paths: list[str]) -> list[Path]:
    result: list[Path] = []
    seen: set[Path] = set()
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for child in sorted(path.glob("*.json")):
                if child.resolve() not in seen:
                    seen.add(child.resolve())
                    result.append(child)
        elif path.is_file() and path.suffix.lower() == ".json":
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                result.append(path)
    return result


def list_json_in_folder(folder: str | Path) -> list[Path]:
    path = Path(folder)
    if not path.is_dir():
        return []
    return sorted(path.glob("*.json"))


def _parse_service_date(value: str | None) -> str:
    if not value:
        return ""
    return value.split(" ")[0].strip()


def _collect_user_metrics(
    usuario: dict[str, Any],
) -> tuple[str, str, str | None, float, int]:
    servicios = usuario.get("servicios") or {}
    dates: list[str] = []
    total = 0.0
    count = 0
    cod_ips: str | None = None

    if not isinstance(servicios, dict):
        return "", "", cod_ips, total, count

    for items in servicios.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            count += 1
            vr = item.get("vrServicio")
            if vr is not None:
                try:
                    total += float(vr)
                except (TypeError, ValueError):
                    pass
            cod_ips = cod_ips or item.get("codPrestador")
            for field in (
                "fechaInicioAtencion",
                "fechaDispensAdmon",
                "fechaSuministroTecnologia",
                "fechaEgreso",
            ):
                d = _parse_service_date(item.get(field))
                if d:
                    dates.append(d)

    feching = min(dates) if dates else ""
    fechfin = max(dates) if dates else ""
    return feching, fechfin, cod_ips, total, count


def _load_sidecar_metadata(json_path: Path) -> dict[str, str]:
    meta: dict[str, str] = {}
    xml_path = find_companion_xml(json_path)
    if xml_path:
        meta.update(parse_fev_xml(xml_path))
    return meta


def build_records_from_rips(
    data: dict[str, Any],
    source_file: str,
    json_path: Path | None = None,
) -> list[RelationRecord]:
    full_doc = data
    rips = unwrap_rips_root(data)
    if not isinstance(rips, dict):
        rips = {}

    sidecar: dict[str, str] = {}
    if json_path is not None:
        sidecar = _load_sidecar_metadata(json_path)

    num_factura = str(rips.get("numFactura") or full_doc.get("numFactura") or "")
    nit = str(rips.get("numDocumentoIdObligado") or full_doc.get("numDocumentoIdObligado") or "")

    fecha_factura = extract_fecha_factura(full_doc, rips) or sidecar.get("fecha_factura", "")
    nombre_ips = extract_nombre_ips(full_doc, rips) or sidecar.get("nombre_ips", "")

    usuarios = rips.get("usuarios") or []
    records: list[RelationRecord] = []

    if not isinstance(usuarios, list) or not usuarios:
        rec = RelationRecord(source_file=source_file, num_documento_obligado=nit)
        rec.values["NroFac"] = num_factura
        rec.values["NombreIps"] = nombre_ips
        rec.values["Fecha factura"] = fecha_factura
        records.append(rec)
        return records

    for usuario in usuarios:
        if not isinstance(usuario, dict):
            continue
        feching, fechfin, cod_ips, total, count = _collect_user_metrics(usuario)
        cod_ips_str = str(cod_ips or "")
        nombre_paciente = extract_nombre_paciente(usuario)

        rec = RelationRecord(source_file=source_file, num_documento_obligado=nit)
        rec.values.update(
            {
                "FECHAING": feching,
                "FECHAFIN": fechfin,
                "CodIps": cod_ips_str,
                "NombreIps": nombre_ips,
                "NroFac": num_factura,
                "TipoIde": usuario.get("tipoDocumentoIdentificacion") or "",
                "NumIde": usuario.get("numDocumentoIdentificacion") or "",
                "Nombre": nombre_paciente,
                "VlorNeto": total if total else "",
                "SERVICIO": count if count else "",
                "NACION": usuario.get("codPaisOrigen")
                or usuario.get("codPaisResidencia")
                or "",
                "Fecha factura": fecha_factura,
            }
        )
        records.append(rec)

    return records
