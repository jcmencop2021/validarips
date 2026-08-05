from __future__ import annotations

from models.relation_record import RelationRecord


def record_dedupe_key(rec: RelationRecord) -> tuple[str, str, str]:
    """Una fila por factura + paciente (sin importar archivo origen)."""
    nro = str(rec.values.get("NroFac") or "").upper().replace(" ", "")
    tipo = str(rec.values.get("TipoIde") or "").upper().strip()
    num = str(rec.values.get("NumIde") or "").upper().strip()
    return (nro, tipo, num)


def dedupe_records(records: list[RelationRecord]) -> tuple[list[RelationRecord], int]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[RelationRecord] = []
    skipped = 0
    for rec in records:
        key = record_dedupe_key(rec)
        if not key[0] and not key[2]:
            unique.append(rec)
            continue
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        unique.append(rec)
    return unique, skipped


def dedupe_documents(
    documents: list[tuple[str, dict, list[RelationRecord]]],
) -> tuple[list[tuple[str, dict, list[RelationRecord]]], int]:
    seen_sources: set[str] = set()
    unique_docs: list[tuple[str, dict, list[RelationRecord]]] = []
    skipped = 0
    for source, data, recs in documents:
        if source in seen_sources:
            skipped += 1
            continue
        seen_sources.add(source)
        unique_docs.append((source, data, recs))
    return unique_docs, skipped


def dedupe_path_strings(paths: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        key = str(raw)
        if key in seen:
            continue
        seen.add(key)
        unique.append(raw)
    return unique
