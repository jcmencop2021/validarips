from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import orjson
except ImportError:  # pragma: no cover
    orjson = None  # type: ignore

from core.factura_index import FacturaIndex, FacturaMetadata, normalize_num_factura
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


def _sidecar_from_path(json_path: Path, factura_index: FacturaIndex | None) -> FacturaMetadata | None:
    num_hint = ""
    data, _ = load_json_file(json_path)
    if isinstance(data, dict):
        rips = unwrap_rips_root(data)
        if isinstance(rips, dict):
            num_hint = str(rips.get("numFactura") or "")

    if factura_index and num_hint:
        meta = factura_index.get(num_hint)
        if meta:
            return meta

    meta_dict: dict[str, str] = {}
    xml_path = find_companion_xml(json_path)
    if xml_path:
        meta_dict.update(parse_fev_xml(xml_path))
    if not meta_dict:
        return None
    return FacturaMetadata(
        num_factura=meta_dict.get("num_factura", num_hint),
        fecha_factura=meta_dict.get("fecha_factura", ""),
        nombre_ips=meta_dict.get("nombre_ips", ""),
        source_file=xml_path.name if xml_path else "",
    )


def _apply_factura_to_values(
    values: dict[str, Any],
    factura: FacturaMetadata | None,
    tipo_doc: str,
    num_doc: str,
) -> None:
    if not factura:
        return
    if factura.fecha_factura and not values.get("Fecha factura"):
        values["Fecha factura"] = factura.fecha_factura
    if factura.nombre_ips and not values.get("NombreIps"):
        values["NombreIps"] = factura.nombre_ips
    nombre = factura.nombre_paciente(tipo_doc, num_doc)
    if nombre and not values.get("Nombre"):
        values["Nombre"] = nombre


def build_records_from_rips(
    data: dict[str, Any],
    source_file: str,
    json_path: Path | None = None,
    factura_index: FacturaIndex | None = None,
) -> list[RelationRecord]:
    full_doc = data
    rips = unwrap_rips_root(data)
    if not isinstance(rips, dict):
        rips = {}

    factura_meta: FacturaMetadata | None = None
    num_factura = str(rips.get("numFactura") or full_doc.get("numFactura") or "")
    if factura_index and num_factura:
        factura_meta = factura_index.get(num_factura)

    if json_path is not None and factura_meta is None:
        factura_meta = _sidecar_from_path(json_path, factura_index)

    nit = str(rips.get("numDocumentoIdObligado") or full_doc.get("numDocumentoIdObligado") or "")

    fecha_factura = extract_fecha_factura(full_doc, rips)
    nombre_ips = extract_nombre_ips(full_doc, rips)
    if factura_meta:
        fecha_factura = fecha_factura or factura_meta.fecha_factura
        nombre_ips = nombre_ips or factura_meta.nombre_ips

    usuarios = rips.get("usuarios") or []
    records: list[RelationRecord] = []

    if not isinstance(usuarios, list) or not usuarios:
        rec = RelationRecord(source_file=source_file, num_documento_obligado=nit)
        rec.values["NroFac"] = num_factura
        rec.values["NombreIps"] = nombre_ips
        rec.values["Fecha factura"] = fecha_factura
        _apply_factura_to_values(rec.values, factura_meta, "", "")
        records.append(rec)
        return records

    for usuario in usuarios:
        if not isinstance(usuario, dict):
            continue
        feching, fechfin, cod_ips, total, count = _collect_user_metrics(usuario)
        cod_ips_str = str(cod_ips or "")
        tipo_doc = str(usuario.get("tipoDocumentoIdentificacion") or "")
        num_doc = str(usuario.get("numDocumentoIdentificacion") or "")
        nombre_paciente = extract_nombre_paciente(usuario)

        rec = RelationRecord(source_file=source_file, num_documento_obligado=nit)
        rec.values.update(
            {
                "FECHAING": feching,
                "FECHAFIN": fechfin,
                "CodIps": cod_ips_str,
                "NombreIps": nombre_ips,
                "NroFac": num_factura,
                "TipoIde": tipo_doc,
                "NumIde": num_doc,
                "Nombre": nombre_paciente,
                "VlorNeto": total if total else "",
                "SERVICIO": count if count else "",
                "NACION": usuario.get("codPaisOrigen")
                or usuario.get("codPaisResidencia")
                or "",
                "Fecha factura": fecha_factura,
            }
        )
        _apply_factura_to_values(rec.values, factura_meta, tipo_doc, num_doc)
        records.append(rec)

    return records


def reload_records_with_facturas(
    documents: list[tuple[str, dict, list[RelationRecord]]],
    json_paths_by_source: dict[str, Path],
    factura_index: FacturaIndex,
) -> tuple[list[RelationRecord], list[tuple[str, dict, list[RelationRecord]]]]:
    all_records: list[RelationRecord] = []
    new_docs: list[tuple[str, dict, list[RelationRecord]]] = []
    for source, data, _old in documents:
        jp = json_paths_by_source.get(source)
        recs = build_records_from_rips(data, source, jp, factura_index)
        all_records.extend(recs)
        new_docs.append((source, data, recs))
    return all_records, new_docs
