from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from core.rips_3374.constants import (
    AF_IDX_NUM_FACTURA,
    AF_IDX_VALOR_NETO,
    AF_TOTAL_BY_SERVICE,
    SERVICE_TYPES,
    SVC_IDX_NUM_DOC,
    SVC_IDX_TIPO_DOC,
    SVC_VALOR_IDX,
    US_IDX_NUM_DOC,
    US_IDX_PRIMER_APELLIDO,
    US_IDX_PRIMER_NOMBRE,
    US_IDX_SEGUNDO_APELLIDO,
    US_IDX_SEGUNDO_NOMBRE,
    US_IDX_TIPO_DOC,
)
from core.rips_3374.ct_manifest import (
    CT_RECOMMENDED_ORDER,
    CtEntry,
    package_file_for_ct_code,
    parse_ct_entries,
)
from core.rips_3374.txt_parser import Rips3374Package, remision_from_filename
from core.validator import Severity, ValidationMessage, ValidationReport
from models.relation_record import RELATION_COLUMNS, RelationRecord


def _parse_money(value: str) -> Decimal | None:
    text = (value or "").strip()
    if not text:
        return Decimal("0")
    try:
        return Decimal(text.replace(",", ""))
    except InvalidOperation:
        return None


def _user_key(tipo: str, num: str) -> tuple[str, str]:
    return (tipo.strip().upper(), num.strip())


def _field(row: list[str], idx: int) -> str:
    if idx < 0 or idx >= len(row):
        return ""
    return row[idx].strip()


def build_records_from_package(pkg: Rips3374Package) -> list[RelationRecord]:
    records: list[RelationRecord] = []
    us_rows = pkg.rows.get("US", [])
    af_rows = pkg.rows.get("AF", [])
    af_by_factura: dict[str, list[str]] = {}
    for row in af_rows:
        fac = _field(row, AF_IDX_NUM_FACTURA)
        if fac:
            af_by_factura[fac] = row

    default_af = af_rows[0] if len(af_rows) == 1 else None
    fechas: dict[str, str] = {}
    for row in af_rows:
        fac = _field(row, AF_IDX_NUM_FACTURA)
        if fac and len(row) > 6:
            fechas[fac] = _field(row, 6)

    for row in us_rows:
        tipo = _field(row, US_IDX_TIPO_DOC)
        num = _field(row, US_IDX_NUM_DOC)
        if not tipo or not num:
            continue
        nombre = " ".join(
            p
            for p in (
                _field(row, US_IDX_PRIMER_NOMBRE),
                _field(row, US_IDX_SEGUNDO_NOMBRE),
                _field(row, US_IDX_PRIMER_APELLIDO),
                _field(row, US_IDX_SEGUNDO_APELLIDO),
            )
            if p
        )
        rec = RelationRecord(source_file=pkg.source_label)
        rec.values["TipoIde"] = tipo
        rec.values["NumIde"] = num
        rec.values["Nombre"] = nombre
        if default_af:
            rec.values["NroFac"] = _field(default_af, AF_IDX_NUM_FACTURA)
            rec.values["Fecha factura"] = _field(default_af, 6)
            rec.values["CodIps"] = _field(default_af, 0)[:12]
        records.append(rec)

    if not records and af_rows:
        for row in af_rows:
            rec = RelationRecord(source_file=pkg.source_label)
            rec.values["NroFac"] = _field(row, AF_IDX_NUM_FACTURA)
            rec.values["Fecha factura"] = _field(row, 6)
            rec.values["CodIps"] = _field(row, 0)[:12]
            records.append(rec)
    return records


def _validate_ct_manifest(pkg: Rips3374Package, report: ValidationReport) -> list[CtEntry]:
    """Valida CT: relación de archivos del paquete y conteo de registros."""
    ct_rows = pkg.rows.get("CT", [])
    if not ct_rows:
        report.messages.append(
            ValidationMessage(
                Severity.ERROR,
                "CT",
                "Falta archivo CT (control). Todo envío RIPS debe incluir el manifiesto CT.",
            )
        )
        return []

    entries, parse_errors = parse_ct_entries(ct_rows)
    for err in parse_errors:
        report.messages.append(ValidationMessage(Severity.ERROR, "CT", err))

    if not entries and parse_errors:
        return []

    listed_codes: set[str] = set()
    order_types: list[str] = []

    for entry in entries:
        listed_codes.add(entry.codigo_archivo)
        order_types.append(entry.codigo_archivo[:2])

        ftype, fname = package_file_for_ct_code(pkg, entry.codigo_archivo)
        if not ftype or not fname:
            report.messages.append(
                ValidationMessage(
                    Severity.ERROR,
                    "CT",
                    f"Línea {entry.line_no}: archivo {entry.codigo_archivo} declarado en CT "
                    "no está en el paquete cargado.",
                )
            )
            continue

        actual = len(pkg.rows.get(ftype, []))
        if actual != entry.total_registros:
            report.messages.append(
                ValidationMessage(
                    Severity.ERROR,
                    "CT",
                    f"Archivo {fname} ({entry.codigo_archivo}): CT indica {entry.total_registros} "
                    f"registros, el archivo tiene {actual}.",
                )
            )

    # Archivos cargados que no están en el CT
    for ftype, path in pkg.files.items():
        if ftype == "CT":
            continue
        name = path.name if hasattr(path, "name") else str(path)
        stem = Path(name).stem.upper()
        matched = any(
            stem == code or stem.startswith(code) for code in listed_codes
        )
        if not matched:
            report.messages.append(
                ValidationMessage(
                    Severity.ERROR,
                    "CT",
                    f"El archivo {name} está en el paquete pero no aparece en el CT.",
                )
            )

    # Orden en CT (advertencia)
    recommended = [t for t in CT_RECOMMENDED_ORDER if t in order_types]
    actual_order = [t for t in order_types if t in CT_RECOMMENDED_ORDER]
    if actual_order != recommended:
        report.messages.append(
            ValidationMessage(
                Severity.ADVERTENCIA,
                "CT",
                "El orden de archivos en CT no coincide con el recomendado "
                f"({', '.join(CT_RECOMMENDED_ORDER)}).",
            )
        )

    if entries and not any(m.source == "CT" and m.severity == Severity.ERROR for m in report.messages):
        report.messages.append(
            ValidationMessage(
                Severity.OK,
                "CT",
                f"Manifiesto CT: {len(entries)} archivo(s) declarados; conteos verificados.",
            )
        )

    return entries


def validate_package(pkg: Rips3374Package) -> ValidationReport:
    report = ValidationReport()
    if pkg.load_errors:
        for err in pkg.load_errors:
            report.messages.append(
                ValidationMessage(Severity.ERROR, "Carga", err)
            )

    _validate_ct_manifest(pkg, report)

    # Sin CT válido no continuar validaciones de detalle (lineamiento IPS)
    ct_ok = "CT" in pkg.rows and not any(
        m.source == "CT" and m.severity == Severity.ERROR for m in report.messages
    )
    if not ct_ok:
        return report

    remissions: set[str] = set()
    for name in pkg.files:
        rem = remision_from_filename(name if isinstance(name, str) else pkg.files[name].name)
        if rem:
            remissions.add(rem)
    if len(remissions) > 1:
        report.messages.append(
            ValidationMessage(
                Severity.ADVERTENCIA,
                "Remisión",
                f"Hay varios números de remisión en nombres de archivo: {', '.join(sorted(remissions))}",
            )
        )

    if "US" not in pkg.rows:
        report.messages.append(
            ValidationMessage(Severity.ERROR, "Estructura", "Falta archivo US (usuarios).")
        )
    if "AF" not in pkg.rows:
        report.messages.append(
            ValidationMessage(Severity.ADVERTENCIA, "Estructura", "No se encontró archivo AF (transacciones).")
        )

    us_set: set[tuple[str, str]] = set()
    for i, row in enumerate(pkg.rows.get("US", []), start=1):
        key = _user_key(_field(row, US_IDX_TIPO_DOC), _field(row, US_IDX_NUM_DOC))
        if not key[0] or not key[1]:
            report.messages.append(
                ValidationMessage(
                    Severity.ERROR,
                    "US",
                    f"Línea {i}: tipo o número de documento vacío.",
                )
            )
            continue
        us_set.add(key)

    for stype in SERVICE_TYPES:
        rows = pkg.rows.get(stype, [])
        if not rows:
            continue
        vidx = SVC_VALOR_IDX.get(stype, 14)
        for i, row in enumerate(rows, start=1):
            tipo = _field(row, SVC_IDX_TIPO_DOC)
            num = _field(row, SVC_IDX_NUM_DOC)
            key = _user_key(tipo, num)
            if key[0] and key[1] and key not in us_set:
                report.messages.append(
                    ValidationMessage(
                        Severity.ERROR,
                        stype,
                        f"Línea {i}: usuario {tipo}-{num} no está en archivo US.",
                    )
                )
            val = _parse_money(_field(row, vidx))
            if val is None:
                report.messages.append(
                    ValidationMessage(
                        Severity.ADVERTENCIA,
                        stype,
                        f"Línea {i}: valor de servicio no numérico (campo índice {vidx}).",
                    )
                )

    sums_by_factura: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    sums_by_factura_type: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: Decimal("0"))
    )
    for stype in SERVICE_TYPES:
        vidx = SVC_VALOR_IDX.get(stype, 14)
        for row in pkg.rows.get(stype, []):
            fac = _field(row, 0)
            val = _parse_money(_field(row, vidx)) or Decimal("0")
            sums_by_factura[fac] += val
            sums_by_factura_type[fac][stype] += val

    for i, row in enumerate(pkg.rows.get("AF", []), start=1):
        fac = _field(row, AF_IDX_NUM_FACTURA)
        neto = _parse_money(_field(row, AF_IDX_VALOR_NETO))
        if neto is None:
            report.messages.append(
                ValidationMessage(
                    Severity.ERROR,
                    "AF",
                    f"Línea {i} factura {fac or '?'}: valor neto no válido.",
                )
            )
            continue
        total_svc = sums_by_factura.get(fac, Decimal("0"))
        if total_svc > 0 and abs(neto - total_svc) > Decimal("0.01"):
            report.messages.append(
                ValidationMessage(
                    Severity.ERROR,
                    "AF",
                    f"Factura {fac}: valor neto AF ({neto}) ≠ suma servicios AC+AP+AM+AT+AU+AH+AN ({total_svc}).",
                )
            )
        for stype, af_idx in AF_TOTAL_BY_SERVICE.items():
            if len(row) <= af_idx:
                continue
            af_total = _parse_money(_field(row, af_idx))
            if af_total is None:
                continue
            svc_sum = sums_by_factura_type[fac].get(stype, Decimal("0"))
            if svc_sum > 0 and abs(af_total - svc_sum) > Decimal("0.01"):
                report.messages.append(
                    ValidationMessage(
                        Severity.ERROR,
                        "AF",
                        f"Factura {fac}: total {stype} en AF ({af_total}) ≠ suma archivo {stype} ({svc_sum}).",
                    )
                )

    if not report.messages:
        report.messages.append(
            ValidationMessage(
                Severity.OK,
                "RIPS 3374",
                "Validación básica completada sin hallazgos.",
            )
        )
    elif not any(
        m.severity in (Severity.ERROR, Severity.ADVERTENCIA) for m in report.messages
    ):
        report.messages.append(
            ValidationMessage(
                Severity.OK,
                "RIPS 3374",
                "Validación básica completada sin hallazgos.",
            )
        )
    return report


def validation_summary_3374(report: ValidationReport) -> str:
    errors = sum(1 for m in report.messages if m.severity == Severity.ERROR)
    warnings = sum(1 for m in report.messages if m.severity == Severity.ADVERTENCIA)
    lines = [
        "Validación RIPS archivos planos — Resolución 3374 de 2000 (lineamientos IPS)",
        f"Resultado: {report.status_label}",
        f"Errores: {errors} | Advertencias: {warnings}",
        "",
    ]
    for msg in report.messages:
        if msg.severity == Severity.OK:
            continue
        lines.append(msg.line())
    if errors == 0 and warnings == 0:
        lines.append("[OK] Sin errores ni advertencias.")
    return "\n".join(lines)
