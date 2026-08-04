"""Reglas de validación RIPS JSON — Resolución 948 / estructura FEV-RIPS."""

from __future__ import annotations

# Bloques de servicios admitidos en el JSON RIPS (Res. 948)
SERVICE_BLOCKS: tuple[str, ...] = (
    "consultas",
    "procedimientos",
    "urgencias",
    "hospitalizacion",
    "recienNacidos",
    "medicamentos",
    "otrosServicios",
)

# Campos mínimos por tipo de servicio (Documento técnico RIPS — soporte FEV)
SERVICE_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "consultas": (
        "codPrestador",
        "fechaInicioAtencion",
        "codConsulta",
        "vrServicio",
        "consecutivo",
    ),
    "procedimientos": (
        "codPrestador",
        "fechaInicioAtencion",
        "codProcedimiento",
        "vrServicio",
        "consecutivo",
    ),
    "urgencias": (
        "codPrestador",
        "fechaInicioAtencion",
        "fechaEgreso",
        "consecutivo",
    ),
    "hospitalizacion": (
        "codPrestador",
        "fechaInicioAtencion",
        "consecutivo",
    ),
    "recienNacidos": (
        "codPrestador",
        "consecutivo",
    ),
    "medicamentos": (
        "codPrestador",
        "fechaDispensAdmon",
        "codTecnologiaSalud",
        "vrServicio",
        "consecutivo",
    ),
    "otrosServicios": (
        "codPrestador",
        "fechaSuministroTecnologia",
        "tipoOS",
        "vrServicio",
        "consecutivo",
    ),
}

ROOT_REQUIRED = ("numDocumentoIdObligado", "numFactura", "usuarios")

USUARIO_REQUIRED = (
    "tipoDocumentoIdentificacion",
    "numDocumentoIdentificacion",
    "tipoUsuario",
    "fechaNacimiento",
    "codSexo",
    "codPaisResidencia",
    "codMunicipioResidencia",
    "codZonaTerritorialResidencia",
    "incapacidad",
    "consecutivo",
    "servicios",
)

# Campos opcionales en raíz que pueden traer nombre IPS o fecha de factura (si el emisor los incluye)
NOMBRE_IPS_JSON_KEYS = (
    "nombrePrestador",
    "nomPrestador",
    "nombreIPS",
    "nombreIps",
    "razonSocial",
)

FECHA_FACTURA_JSON_KEYS = (
    "fechaFactura",
    "fechaInicioFactura",
    "fechaGeneracionFactura",
)
