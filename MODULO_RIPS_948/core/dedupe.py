from __future__ import annotations

from core.factura_index import is_rips_payload
from models.relation_record import RelationRecord


def record_dedupe_key(rec: RelationRecord) -> tuple[str, str, str, str]:
    return (
        rec.source_file,
        str(rec.values.get("NroFac") or ""),
        str(rec.values.get("TipoIde") or ""),
        str(rec.values.get("NumIde") or ""),
    )


def dedupe_records(records: list[RelationRecord]) -> tuple[list[RelationRecord], int]:
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[RelationRecord] = []
    skipped = 0
    for rec in records:
        key = record_dedupe_key(rec)
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


def is_rips_json_data(data: dict) -> bool:
    return is_rips_payload(data)
