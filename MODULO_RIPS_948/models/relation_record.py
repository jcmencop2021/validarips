from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Orden exacto de la plantilla de relación (Res. 948)
RELATION_COLUMNS: list[str] = [
    "CAJA",
    "RADICADO",
    "FECHA RADICADO",
    "PERIODO FACTURADO",
    "Fecha factura",
    "FECHAING",
    "FECHAFIN",
    "CodIps",
    "NombreIps",
    "NroFac",
    "TipoIde",
    "NumIde",
    "Nombre",
    "VlorNeto",
    "SERVICIO",
    "REL",
    "NACION",
]

ADMIN_FIELDS: list[str] = [
    "CAJA",
    "RADICADO",
    "FECHA RADICADO",
    "PERIODO FACTURADO",
    "Fecha factura",
    "REL",
]


@dataclass
class RelationRecord:
    """Una fila de la relación (típicamente un usuario dentro de una factura RIPS)."""

    source_file: str = ""
    num_documento_obligado: str = ""
    values: dict[str, Any] = field(default_factory=dict)
    admin_applied: bool = False
    validation_messages: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for col in RELATION_COLUMNS:
            self.values.setdefault(col, "")

    def apply_admin(self, admin: dict[str, str]) -> None:
        for key in ADMIN_FIELDS:
            if admin.get(key):
                self.values[key] = admin[key]
        self.admin_applied = True

    def to_row(self) -> list[Any]:
        return [self.values.get(col, "") for col in RELATION_COLUMNS]
