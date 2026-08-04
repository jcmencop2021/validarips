from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from core.rips_rules import (
    FECHA_FACTURA_JSON_KEYS,
    ROOT_REQUIRED,
    SERVICE_BLOCKS,
    SERVICE_REQUIRED_FIELDS,
    USUARIO_REQUIRED,
)
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
            "Validación conforme estructura RIPS JSON — Resolución 948 de 2026",
            f"Resultado RIPS: {self.status_label}",
            f"Errores: {errors} | Advertencias: {warnings}",
            "",
        ]
        for msg in self.messages:
            lines.append(msg.line())
        return "\n".join(lines)

    def to_file_text(self) -> str:
        return self.summary_text()


def _valid_date(value: Any, with_time: bool = False) -> bool:
    if not value or not isinstance(value, str):
        return False
    formats = ("%Y-%m-%d %H:%M", "%Y-%m-%d") if with_time else ("%Y-%m-%d",)
    for fmt in formats:
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            continue
    if with_time:
        return _valid_date(value, with_time=False)
    return False


def _valid_cod_prestador(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return text.isdigit() and len(text) == 12


def _validate_nota_credito(data: dict[str, Any], source: str) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    tipo_nota = data.get("tipoNota")
    num_nota = data.get("numNota")
    if tipo_nota not in (None, ""):
        if not num_nota:
            messages.append(
                ValidationMessage(
                    Severity.ERROR,
                    source,
                    "Si tipoNota está informado, numNota es obligatorio (Res. 948).",
                )
            )
    return messages


def validate_rips_document(
    data: Any, source: str, records: list[RelationRecord]
) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []

    if not isinstance(data, dict):
        messages.append(
            ValidationMessage(Severity.ERROR, source, "La raíz del JSON debe ser un objeto.")
        )
        return messages

    messages.extend(_validate_nota_credito(data, source))

    for key in ROOT_REQUIRED:
        if key not in data or data[key] in (None, ""):
            messages.append(
                ValidationMessage(
                    Severity.ERROR,
                    source,
                    f"Campo obligatorio ausente o vacío: {key}",
                )
            )

    nit = data.get("numDocumentoIdObligado")
    if nit is not None and str(nit).strip() and not str(nit).strip().isdigit():
        messages.append(
            ValidationMessage(
                Severity.ERROR,
                source,
                "numDocumentoIdObligado debe ser numérico (NIT del obligado).",
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
    consecutivos_usuario: list[int] = []

    if isinstance(usuarios, list):
        for idx, usuario in enumerate(usuarios, start=1):
            prefix = f"{source} / usuario #{idx}"
            if not isinstance(usuario, dict):
                messages.append(
                    ValidationMessage(Severity.ERROR, prefix, "Usuario debe ser un objeto.")
                )
                continue

            for key in USUARIO_REQUIRED:
                if key not in usuario:
                    messages.append(
                        ValidationMessage(
                            Severity.ERROR, prefix, f"Campo obligatorio ausente: {key}"
                        )
                    )

            cons = usuario.get("consecutivo")
            if cons is not None:
                try:
                    consecutivos_usuario.append(int(cons))
                except (TypeError, ValueError):
                    messages.append(
                        ValidationMessage(
                            Severity.ERROR, prefix, "consecutivo de usuario debe ser entero."
                        )
                    )

            if usuario.get("fechaNacimiento") and not _valid_date(
                usuario.get("fechaNacimiento")
            ):
                messages.append(
                    ValidationMessage(
                        Severity.ERROR,
                        prefix,
                        "fechaNacimiento inválida (YYYY-MM-DD).",
                    )
                )

            servicios = usuario.get("servicios")
            if servicios is not None and not isinstance(servicios, dict):
                messages.append(
                    ValidationMessage(Severity.ERROR, prefix, "servicios debe ser un objeto.")
                )
                continue

            if isinstance(servicios, dict):
                unknown = [k for k in servicios if k not in SERVICE_BLOCKS]
                for uk in unknown:
                    messages.append(
                        ValidationMessage(
                            Severity.ADVERTENCIA,
                            prefix,
                            f"Bloque de servicio no reconocido en RIPS: '{uk}'.",
                        )
                    )

                user_svc = 0
                for svc_key in SERVICE_BLOCKS:
                    items = servicios.get(svc_key)
                    if not items:
                        continue
                    if not isinstance(items, list):
                        messages.append(
                            ValidationMessage(
                                Severity.ERROR,
                                prefix,
                                f"{svc_key} debe ser una lista.",
                            )
                        )
                        continue
                    required = SERVICE_REQUIRED_FIELDS.get(svc_key, ("codPrestador",))
                    for sidx, item in enumerate(items, start=1):
                        svc_prefix = f"{prefix} / {svc_key} #{sidx}"
                        if not isinstance(item, dict):
                            messages.append(
                                ValidationMessage(
                                    Severity.ERROR, svc_prefix, "Ítem de servicio inválido."
                                )
                            )
                            continue
                        user_svc += 1
                        total_services += 1
                        for req in required:
                            if req not in item or item[req] in (None, ""):
                                messages.append(
                                    ValidationMessage(
                                        Severity.ERROR,
                                        svc_prefix,
                                        f"Campo obligatorio ausente: {req}",
                                    )
                                )
                        if "codPrestador" in item and not _valid_cod_prestador(
                            item.get("codPrestador")
                        ):
                            messages.append(
                                ValidationMessage(
                                    Severity.ERROR,
                                    svc_prefix,
                                    "codPrestador debe tener 12 dígitos.",
                                )
                            )
                        for date_field in (
                            "fechaInicioAtencion",
                            "fechaDispensAdmon",
                            "fechaSuministroTecnologia",
                            "fechaEgreso",
                        ):
                            if date_field in item and item[date_field]:
                                if not _valid_date(item[date_field], with_time=True):
                                    messages.append(
                                        ValidationMessage(
                                            Severity.ERROR,
                                            svc_prefix,
                                            f"{date_field} con formato inválido.",
                                        )
                                    )
                        if "vrServicio" in item and item["vrServicio"] is not None:
                            try:
                                if float(item["vrServicio"]) < 0:
                                    messages.append(
                                        ValidationMessage(
                                            Severity.ERROR,
                                            svc_prefix,
                                            "vrServicio no puede ser negativo.",
                                        )
                                    )
                            except (TypeError, ValueError):
                                messages.append(
                                    ValidationMessage(
                                        Severity.ERROR,
                                        svc_prefix,
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

        if consecutivos_usuario:
            expected = list(range(1, len(consecutivos_usuario) + 1))
            if sorted(consecutivos_usuario) != expected:
                messages.append(
                    ValidationMessage(
                        Severity.ADVERTENCIA,
                        source,
                        "Los consecutivos de usuario deberían ir de 1 a N sin saltos.",
                    )
                )

    if total_services == 0 and isinstance(usuarios, list) and usuarios:
        messages.append(
            ValidationMessage(
                Severity.ERROR,
                source,
                "La factura no contiene servicios RIPS en ningún usuario.",
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

    ok_for_file = not any(m.severity == Severity.ERROR for m in messages)
    if ok_for_file and not any(m.severity == Severity.OK for m in messages):
        messages.append(
            ValidationMessage(
                Severity.OK,
                source,
                "Estructura y reglas básicas Res. 948 verificadas sin errores.",
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
