from __future__ import annotations

from dataclasses import dataclass, field

from core.json_extract import (
    _nombre_from_object,
    extract_fecha_factura,
    extract_nombre_ips,
    extract_nombre_paciente,
    unwrap_rips_root,
)
from core.fev_xml import parse_fev_xml


def normalize_num_factura(value: str) -> str:
    return "".join(str(value or "").upper().split())


@dataclass
class FacturaMetadata:
    num_factura: str = ""
    fecha_factura: str = ""
    nombre_ips: str = ""
    pacientes: dict[str, str] = field(default_factory=dict)
    source_file: str = ""

    def nombre_paciente(self, tipo_doc: str, num_doc: str) -> str:
        if not num_doc:
            return ""
        keys = [
            f"{tipo_doc}|{num_doc}",
            f"{tipo_doc}|{num_doc}".upper(),
            num_doc,
            num_doc.upper(),
        ]
        for key in keys:
            if key in self.pacientes:
                return self.pacientes[key]
        return ""


def _paciente_key(tipo: str, num: str) -> str:
    return f"{tipo}|{num}".upper()


def _collect_pacientes_from_obj(obj: dict) -> dict[str, str]:
    found: dict[str, str] = {}
    usuarios = obj.get("usuarios") or obj.get("pacientes") or obj.get("beneficiarios")
    if isinstance(usuarios, list):
        for u in usuarios:
            if not isinstance(u, dict):
                continue
            tipo = str(u.get("tipoDocumentoIdentificacion") or u.get("tipo_identificacion") or "")
            num = str(u.get("numDocumentoIdentificacion") or u.get("identificacion") or "")
            nombre = extract_nombre_paciente(u)
            if num and nombre:
                found[_paciente_key(tipo, num)] = nombre
    return found


def parse_factura_json(data: dict, source: str = "") -> list[FacturaMetadata]:
    """Interpreta JSON de FEV / factura electrónica (no RIPS)."""
    results: list[FacturaMetadata] = []

    def add_one(num: str, fecha: str, ips: str, pacientes: dict[str, str]) -> None:
        if not num and not fecha and not ips:
            return
        results.append(
            FacturaMetadata(
                num_factura=num,
                fecha_factura=fecha.split(" ")[0] if fecha else "",
                nombre_ips=ips,
                pacientes=pacientes,
                source_file=source,
            )
        )

    # Paquete con arreglo facturas
    facturas = data.get("facturas")
    if isinstance(facturas, list):
        for fac in facturas:
            if not isinstance(fac, dict):
                continue
            enc = fac.get("encabezado") or {}
            pref = str(enc.get("prefijo") or "")
            num_id = str(enc.get("id_factura") or enc.get("numero") or "")
            num = str(enc.get("numero_factura") or f"{pref}{num_id}".strip() or data.get("numFactura") or "")
            fecha = str(enc.get("fecha") or "")
            ips = extract_nombre_ips(fac, {}) or extract_nombre_ips(data, {})
            pacientes = _collect_pacientes_from_obj(fac)
            add_one(num, fecha, ips, pacientes)
        if results:
            return results

    # Documento único
    rips = unwrap_rips_root(data)
    num = str(
        data.get("numFactura")
        or rips.get("numFactura")
        or _nested_numero_documento(data)
        or ""
    )
    fecha = extract_fecha_factura(data, rips if isinstance(rips, dict) else {})
    ips = extract_nombre_ips(data, rips if isinstance(rips, dict) else {})
    pacientes = _collect_pacientes_from_obj(data)
    add_one(num, fecha, ips, pacientes)
    return results


def _nested_numero_documento(data: dict) -> str:
    info = data.get("informacion_documento")
    if isinstance(info, dict):
        return str(info.get("numero_documento") or info.get("numeroDocumento") or "")
    return ""


def parse_factura_xml(path) -> list[FacturaMetadata]:
    from pathlib import Path

    p = Path(path)
    parsed = parse_fev_xml(p)
    if not parsed:
        return []
    num = parsed.get("num_factura", "")
    return [
        FacturaMetadata(
            num_factura=num,
            fecha_factura=parsed.get("fecha_factura", ""),
            nombre_ips=parsed.get("nombre_ips", ""),
            source_file=p.name,
        )
    ]


def is_rips_payload(data: dict) -> bool:
    rips = unwrap_rips_root(data)
    return isinstance(rips, dict) and isinstance(rips.get("usuarios"), list)


class FacturaIndex:
    """Índice de metadatos de factura por número de factura (cruce con RIPS)."""

    def __init__(self) -> None:
        self._by_num: dict[str, FacturaMetadata] = {}

    def __len__(self) -> int:
        return len(self._by_num)

    def get(self, num_factura: str) -> FacturaMetadata | None:
        key = normalize_num_factura(num_factura)
        return self._by_num.get(key)

    def merge(self, meta: FacturaMetadata) -> None:
        key = normalize_num_factura(meta.num_factura)
        if not key:
            return
        existing = self._by_num.get(key)
        if existing is None:
            self._by_num[key] = meta
            return
        if meta.fecha_factura and not existing.fecha_factura:
            existing.fecha_factura = meta.fecha_factura
        if meta.nombre_ips and not existing.nombre_ips:
            existing.nombre_ips = meta.nombre_ips
        existing.pacientes.update(meta.pacientes)
        if meta.source_file:
            existing.source_file = meta.source_file

    def ingest_json_file(self, path, data: dict) -> None:
        if is_rips_payload(data):
            return
        for meta in parse_factura_json(data, path.name):
            self.merge(meta)

    def ingest_xml_file(self, path) -> None:
        for meta in parse_factura_xml(path):
            self.merge(meta)

    def ingest_paths(self, paths: list) -> int:
        from pathlib import Path

        from core.loader import load_json_file

        added = 0
        for raw in paths:
            path = Path(raw)
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix == ".xml":
                before = len(self._by_num)
                self.ingest_xml_file(path)
                if len(self._by_num) > before:
                    added += 1
            elif suffix == ".json":
                data, err = load_json_file(path)
                if err or not isinstance(data, dict):
                    continue
                before = len(self._by_num)
                self.ingest_json_file(path, data)
                if len(self._by_num) > before:
                    added += 1
        return added

    def scan_directories(self, directories: set) -> int:
        from pathlib import Path

        from core.loader import load_json_file

        count = 0
        for directory in directories:
            folder = Path(directory)
            if not folder.is_dir():
                continue
            for xml_path in sorted(folder.glob("*.xml")):
                before = len(self._by_num)
                self.ingest_xml_file(xml_path)
                if len(self._by_num) > before:
                    count += 1
            for json_path in sorted(folder.glob("*.json")):
                data, err = load_json_file(json_path)
                if err or not isinstance(data, dict) or is_rips_payload(data):
                    continue
                before = len(self._by_num)
                self.ingest_json_file(json_path, data)
                if len(self._by_num) > before:
                    count += 1
        return count
