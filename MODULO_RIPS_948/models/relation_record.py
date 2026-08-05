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

# Campos del encabezado (comunes); Fecha factura es por factura en la grilla.
ADMIN_FIELDS: list[str] = [
    "CAJA",
    "REL",
    "RADICADO",
    "FECHA RADICADO",
    "PERIODO FACTURADO",
]


@dataclass
class RelationRecord:
    """Una fila de la relación (típicamente un usuario dentro de una factura RIPS)."""

    source_file: str = ""
    num_documento_obligado: str = ""
    values: dict[str, Any] = field(default_factory=dict)
    admin_applied: bool = False
    export_selected: bool = False
    _admin_backup: dict[str, Any] = field(default_factory=dict, repr=False)
    validation_messages: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for col in RELATION_COLUMNS:
            self.values.setdefault(col, "")

    def apply_admin(self, admin: dict[str, str]) -> None:
        if not self.admin_applied:
            self._admin_backup = {
                key: self.values.get(key, "") for key in ADMIN_FIELDS
            }
        for key in ADMIN_FIELDS:
            if admin.get(key):
                self.values[key] = admin[key]
        self.admin_applied = True

    def revert_admin(self) -> None:
        """Quita datos del encabezado aplicados con Aplicar y restaura valores previos."""
        if self._admin_backup:
            for key, prev in self._admin_backup.items():
                self.values[key] = prev
        else:
            for key in ADMIN_FIELDS:
                self.values[key] = ""
        self._admin_backup = {}
        self.admin_applied = False
        self.export_selected = False

    def to_row(self) -> list[Any]:
        return [self.values.get(col, "") for col in RELATION_COLUMNS]
