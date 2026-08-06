from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from core.date_fmt import format_date_display
from core.paises import nombre_pais
from core.rips_3374.constants import (
    AF_IDX_COD_ENTIDAD,
    AF_IDX_COD_PRESTADOR,
    AF_IDX_FECHA_FACTURA,
    AF_IDX_FECHA_FIN,
    AF_IDX_FECHA_INICIO,
    AF_IDX_NOMBRE_ENTIDAD,
    AF_IDX_NOMBRE_IPS,
    AF_IDX_NUM_FACTURA,
    AF_IDX_VALOR_NETO,
    SERVICE_TYPES,
    SVC_DATE_IDX,
    SVC_IDX_NUM_DOC,
    SVC_IDX_TIPO_DOC,
    SVC_VALOR_IDX,
    US_IDX_COD_PAIS,
    US_IDX_NUM_DOC,
    US_IDX_PRIMER_APELLIDO,
    US_IDX_PRIMER_NOMBRE,
    US_IDX_SEGUNDO_APELLIDO,
    US_IDX_SEGUNDO_NOMBRE,
    US_IDX_TIPO_DOC,
)
from core.rips_3374.txt_parser import Rips3374Package
from models.relation_record import RelationRecord


def _field(row: list[str], idx: int) -> str:
    if idx < 0 or idx >= len(row):
        return ""
    return row[idx].strip()


def _parse_money(value: str) -> Decimal:
    text = (value or "").strip()
    if not text:
        return Decimal("0")
    try:
        return Decimal(text.replace(",", ""))
    except Exception:
        return Decimal("0")


def _user_key(tipo: str, num: str) -> tuple[str, str]:
    return (tipo.strip().upper(), num.strip())


def _nombre_usuario(row: list[str]) -> str:
    return " ".join(
        p
        for p in (
            _field(row, US_IDX_PRIMER_NOMBRE),
            _field(row, US_IDX_SEGUNDO_NOMBRE),
            _field(row, US_IDX_PRIMER_APELLIDO),
            _field(row, US_IDX_SEGUNDO_APELLIDO),
        )
        if p
    )


def _apply_af_to_record(rec: RelationRecord, af_row: list[str]) -> None:
    rec.values["CodIps"] = _field(af_row, AF_IDX_COD_PRESTADOR)[:12]
    rec.values["NombreIps"] = _field(af_row, AF_IDX_NOMBRE_IPS)
    rec.values["NroFac"] = _field(af_row, AF_IDX_NUM_FACTURA)
    rec.values["Fecha factura"] = format_date_display(_field(af_row, AF_IDX_FECHA_FACTURA))
    rec.values["FECHAING"] = format_date_display(_field(af_row, AF_IDX_FECHA_INICIO))
    rec.values["FECHAFIN"] = format_date_display(_field(af_row, AF_IDX_FECHA_FIN))
    neto = _parse_money(_field(af_row, AF_IDX_VALOR_NETO))
    if neto and not rec.values.get("VlorNeto"):
        rec.values["VlorNeto"] = str(neto)
    # Entidad administradora (EPS) — útil en relación / revisión
    eps = _field(af_row, AF_IDX_NOMBRE_ENTIDAD)
    if eps and not rec.values.get("SERVICIO"):
        rec.values["SERVICIO"] = eps[:30]


def _apply_us_to_record(rec: RelationRecord, us_row: list[str]) -> None:
    rec.values["TipoIde"] = _field(us_row, US_IDX_TIPO_DOC)
    rec.values["NumIde"] = _field(us_row, US_IDX_NUM_DOC)
    rec.values["Nombre"] = _nombre_usuario(us_row)
    cod_pais = _field(us_row, US_IDX_COD_PAIS)
    if cod_pais:
        rec.values["NACION"] = nombre_pais(cod_pais) or cod_pais


def _service_valor(row: list[str], stype: str) -> Decimal:
    idx = SVC_VALOR_IDX.get(stype, 14)
    val = _parse_money(_field(row, idx))
    if val > 0:
        return val
    # Respaldo: último campo numérico de la línea
    for part in reversed(row):
        v = _parse_money(part)
        if v > 0:
            return v
    return Decimal("0")


def build_records_from_package(pkg: Rips3374Package) -> list[RelationRecord]:
    """Una fila por usuario y factura (cruce US + AF + archivos de servicios)."""
    us_by_key: dict[tuple[str, str], list[str]] = {}
    for row in pkg.rows.get("US", []):
        key = _user_key(_field(row, US_IDX_TIPO_DOC), _field(row, US_IDX_NUM_DOC))
        if key[0] and key[1]:
            us_by_key[key] = row

    af_by_factura: dict[str, list[str]] = {}
    for row in pkg.rows.get("AF", []):
        fac = _field(row, AF_IDX_NUM_FACTURA)
        if fac:
            af_by_factura[fac] = row

    # Agregados por (factura, tipo doc, num doc)
    totals: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    svc_counts: dict[tuple[str, str, str], dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    dates: dict[tuple[str, str, str], list[str]] = defaultdict(list)

    for stype in SERVICE_TYPES:
        d_idx = SVC_DATE_IDX.get(stype, 4)
        for row in pkg.rows.get(stype, []):
            fac = _field(row, 0)
            tipo = _field(row, SVC_IDX_TIPO_DOC)
            num = _field(row, SVC_IDX_NUM_DOC)
            if not fac or not tipo or not num:
                continue
            key3 = (fac, tipo.upper(), num)
            totals[key3] += _service_valor(row, stype)
            svc_counts[key3][stype] += 1
            fd = _field(row, d_idx)
            if fd:
                dates[key3].append(fd.split(" ")[0])

    records: list[RelationRecord] = []
    seen_us_only: set[tuple[str, str]] = set()

    for (fac, tipo, num), total in sorted(totals.items()):
        ukey = (tipo, num)
        us_row = us_by_key.get(ukey)
        if not us_row:
            continue
        seen_us_only.add(ukey)
        rec = RelationRecord(source_file=pkg.source_label)
        _apply_us_to_record(rec, us_row)
        af_row = af_by_factura.get(fac)
        if af_row:
            _apply_af_to_record(rec, af_row)
        rec.values["NroFac"] = fac
        if total > 0:
            rec.values["VlorNeto"] = str(total)
        dlist = dates.get((fac, tipo, num), [])
        if dlist:
            rec.values["FECHAING"] = format_date_display(min(dlist))
            rec.values["FECHAFIN"] = format_date_display(max(dlist))
        parts = svc_counts.get((fac, tipo, num), {})
        if parts:
            rec.values["SERVICIO"] = "+".join(f"{k}:{v}" for k, v in sorted(parts.items()))
        records.append(rec)

    # Usuarios en US sin servicios en el paquete: fila con datos US + datos del prestador (AF)
    first_af = pkg.rows.get("AF", [None])[0]
    for key, us_row in us_by_key.items():
        if key in seen_us_only:
            continue
        rec = RelationRecord(source_file=pkg.source_label)
        _apply_us_to_record(rec, us_row)
        if first_af:
            rec.values["CodIps"] = _field(first_af, AF_IDX_COD_PRESTADOR)[:12]
            rec.values["NombreIps"] = _field(first_af, AF_IDX_NOMBRE_IPS)
            eps = _field(first_af, AF_IDX_NOMBRE_ENTIDAD)
            if eps:
                rec.values["SERVICIO"] = eps[:40]
        records.append(rec)

    # Solo AF sin US (caso raro)
    if not records and af_by_factura:
        for fac, af_row in af_by_factura.items():
            rec = RelationRecord(source_file=pkg.source_label)
            _apply_af_to_record(rec, af_row)
            rec.values["NroFac"] = fac
            records.append(rec)

    return records
