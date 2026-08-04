from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from models.relation_record import RelationRecord


class Severity(str, Enum):
    OK = "OK"
    ADVERTENCIA = "ADVERTENCIA"
    ERROR = "ERROR"


@dataclass
class ValidationMessage:
    severity: Severity
    source: str
    message: str

    def line(self) -> str:
        return f"[{self.severity.value}] {self.source}: {self.message}"


@dataclass
class ValidationReport:
    messages: list[ValidationMessage] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(m.severity == Severity.ERROR for m in self.messages)

    @property
    def status_label(self) -> str:
        if self.has_errors:
            return "ERROR"
        if any(m.severity == Severity.ADVERTENCIA for m in self.messages):
            return "ADVERTENCIA"
        return "OK"

    def summary_text(self) -> str:
        errors = sum(1 for m in self.messages if m.severity == Severity.ERROR)
        warnings = sum(1 for m in self.messages if m.severity == Severity.ADVERTENCIA)
        lines = [
            f"Resultado RIPS: {self.status_label}",
            f"Errores: {errors} | Advertencias: {warnings}",
            "",
        ]
        for msg in self.messages:
            lines.append(msg.line())
        return "\n".join(lines)

    def to_file_text(self) -> str:
        return self.summary_text()


REQUIRED_ROOT = ("numDocumentoIdObligado", "numFactura", "usuarios")
REQUIRED_USUARIO = (
    "tipoDocumentoIdentificacion",
    "numDocumentoIdentificacion",
    "tipoUsuario",
    "fechaNacimiento",
    "codSexo",
    "consecutivo",
    "servicios",
)

SERVICE_ARRAY_KEYS = (
    "consultas",
    "procedimientos",
    "urgencias",
    "hospitalizacion",
    "recienNacidos",
    "medicamentos",
    "otrosServicios",
)


def _valid_date(value: Any) -> bool:
    if not value or not isinstance(value, str):
        return False
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M"):
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def validate_rips_document(
    data: Any, source: str, records: list[RelationRecord]
) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []

    if not isinstance(data, dict):
        messages.append(
            ValidationMessage(Severity.ERROR, source, "La raíz del JSON debe ser un objeto.")
        )
        return messages

    for key in REQUIRED_ROOT:
        if key not in data or data[key] in (None, ""):
            messages.append(
                ValidationMessage(
                    Severity.ERROR, source, f"Campo obligatorio ausente o vacío: {key}"
                )
            )

    usuarios = data.get("usuarios")
    if usuarios is not None and not isinstance(usuarios, list):
        messages.append(
            ValidationMessage(Severity.ERROR, source, "usuarios debe ser una lista.")
        )
        return messages

    if isinstance(usuarios, list) and len(usuarios) == 0:
        messages.append(
            ValidationMessage(Severity.ERROR, source, "usuarios no puede estar vacío.")
        )

    total_services = 0
    if isinstance(usuarios, list):
        for idx, usuario in enumerate(usuarios, start=1):
            prefix = f"{source} / usuario #{idx}"
            if not isinstance(usuario, dict):
                messages.append(
                    ValidationMessage(Severity.ERROR, prefix, "Usuario debe ser un objeto.")
                )
                continue
            for key in REQUIRED_USUARIO:
                if key not in usuario:
                    messages.append(
                        ValidationMessage(
                            Severity.ERROR, prefix, f"Campo obligatorio ausente: {key}"
                        )
                    )
            if usuario.get("fechaNacimiento") and not _valid_date(
                usuario.get("fechaNacimiento")
            ):
                messages.append(
                    ValidationMessage(
                        Severity.ERROR,
                        prefix,
                        "fechaNacimiento con formato inválido (esperado YYYY-MM-DD).",
                    )
                )
            servicios = usuario.get("servicios")
            if servicios is not None and not isinstance(servicios, dict):
                messages.append(
                    ValidationMessage(Severity.ERROR, prefix, "servicios debe ser un objeto.")
                )
                continue
            if isinstance(servicios, dict):
                user_svc = 0
                for svc_key, items in servicios.items():
                    if not isinstance(items, list):
                        continue
                    user_svc += len(items)
                    total_services += len(items)
                    for sidx, item in enumerate(items, start=1):
                        if not isinstance(item, dict):
                            messages.append(
                                ValidationMessage(
                                    Severity.ERROR,
                                    f"{prefix} / {svc_key} #{sidx}",
                                    "Ítem de servicio inválido.",
                                )
                            )
                            continue
                        if "vrServicio" in item and item["vrServicio"] is not None:
                            try:
                                if float(item["vrServicio"]) < 0:
                                    messages.append(
                                        ValidationMessage(
                                            Severity.ERROR,
                                            f"{prefix} / {svc_key} #{sidx}",
                                            "vrServicio no puede ser negativo.",
                                        )
                                    )
                            except (TypeError, ValueError):
                                messages.append(
                                    ValidationMessage(
                                        Severity.ERROR,
                                        f"{prefix} / {svc_key} #{sidx}",
                                        "vrServicio debe ser numérico.",
                                    )
                                )
                if user_svc == 0:
                    messages.append(
                        ValidationMessage(
                            Severity.ADVERTENCIA,
                            prefix,
                            "El usuario no tiene líneas de servicio registradas.",
                        )
                    )

    if total_services == 0 and isinstance(usuarios, list) and usuarios:
        messages.append(
            ValidationMessage(
                Severity.ADVERTENCIA,
                source,
                "No se encontraron servicios en ningún usuario.",
            )
        )

    for rec in records:
        if not rec.values.get("NroFac"):
            messages.append(
                ValidationMessage(
                    Severity.ERROR,
                    source,
                    "No fue posible determinar NroFac para un registro de relación.",
                )
            )
        if rec.values.get("VlorNeto") == "":
            messages.append(
                ValidationMessage(
                    Severity.ADVERTENCIA,
                    source,
                    f"Valor neto vacío para factura {rec.values.get('NroFac')}.",
                )
            )

    if not messages:
        messages.append(
            ValidationMessage(
                Severity.OK,
                source,
                "Estructura RIPS conforme a validación básica Res. 948 (v1.0).",
            )
        )

    return messages


def validate_all(
    documents: list[tuple[str, dict[str, Any], list[RelationRecord]]],
) -> ValidationReport:
    report = ValidationReport()
    for source, data, records in documents:
        report.messages.extend(validate_rips_document(data, source, records))
    return report
