from __future__ import annotations

from typing import Any

# Campos de transacción RIPS (Anexo Técnico 1 — §4.1): solo T01–T04 en el JSON estándar.
# Fecha de factura y razón social del prestador se validan contra la FEV (cruce XML/JSON).

TRANSACTION_FECHA_FACTURA_KEYS: tuple[str, ...] = (
    "fechaFactura",
    "fechaEmision",
    "fecha_emision",
    "fechaDocumento",
    "fecha_documento",
)

TRANSACTION_NOMBRE_IPS_KEYS: tuple[str, ...] = (
    "nombrePrestador",
    "nomPrestador",
    "razonSocial",
    "razon_social",
    "nombreIPS",
    "nombreIps",
    "nombreObligado",
)

USUARIO_NOMBRE_KEYS: tuple[str, ...] = (
    "nombreCompleto",
    "nombreUsuario",
    "nombrePaciente",
    "nombresApellidos",
)

USUARIO_NOMBRE_PARTES: tuple[str, ...] = (
    "primerNombre",
    "segundoNombre",
    "primerApellido",
    "segundoApellido",
    "nombres",
    "apellidos",
)

RIPS_WRAPPER_KEYS: tuple[str, ...] = (
    "rips",
    "Rips",
    "RIPS",
    "json_rips",
    "jsonRips",
    "contenidoRips",
    "data",
)


def unwrap_rips_root(data: Any) -> dict[str, Any]:
    """Devuelve el objeto transacción RIPS (root sin nombre según norma)."""
    if not isinstance(data, dict):
        return {}
    for key in RIPS_WRAPPER_KEYS:
        inner = data.get(key)
        if isinstance(inner, dict) and "usuarios" in inner:
            return inner
        if isinstance(inner, str):
            continue
    if "usuarios" in data or "numFactura" in data:
        return data
    return data


def _get_path(obj: Any, path: tuple[str, ...]) -> Any:
    cur = obj
    for part in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _first_string_from_paths(root: dict[str, Any], paths: tuple[tuple[str, ...], ...]) -> str:
    for path in paths:
        val = _get_path(root, path)
        if val not in (None, ""):
            return str(val).strip()
    return ""


def _nombre_from_object(obj: dict[str, Any]) -> str:
    if not isinstance(obj, dict):
        return ""
    if obj.get("razon_social"):
        return str(obj["razon_social"]).strip()
    if obj.get("razonSocial"):
        return str(obj["razonSocial"]).strip()
    parts: list[str] = []
    for key in (
        "primer_nombre",
        "segundo_nombre",
        "primer_apellido",
        "segundo_apellido",
        "primerNombre",
        "segundoNombre",
        "primerApellido",
        "segundoApellido",
        "nombres",
        "apellidos",
    ):
        val = obj.get(key)
        if val:
            parts.append(str(val).strip())
    return " ".join(parts).strip()


def extract_fecha_factura(full_doc: dict[str, Any], rips: dict[str, Any]) -> str:
    """Fecha de la FEV asociada (no es campo T01–T04 del RIPS)."""
    paths: tuple[tuple[str, ...], ...] = (
        ("informacion_documento", "fecha_documento"),
        ("informacion_documento", "fechaDocumento"),
        ("factura", "encabezado", "fecha"),
        ("facturas", 0, "encabezado", "fecha"),
    )
    # paths with list index - handle separately
    val = _first_string_from_paths(full_doc, paths[:2])
    if val:
        return val.split(" ")[0]

    facturas = full_doc.get("facturas")
    if isinstance(facturas, list) and facturas:
        enc = facturas[0].get("encabezado") if isinstance(facturas[0], dict) else None
        if isinstance(enc, dict) and enc.get("fecha"):
            return str(enc["fecha"]).split(" ")[0]

    factura = full_doc.get("factura")
    if isinstance(factura, dict):
        enc = factura.get("encabezado")
        if isinstance(enc, dict) and enc.get("fecha"):
            return str(enc["fecha"]).split(" ")[0]

    for key in TRANSACTION_FECHA_FACTURA_KEYS:
        if rips.get(key):
            return str(rips[key]).split(" ")[0]
        if full_doc.get(key):
            return str(full_doc[key]).split(" ")[0]

    return ""


def extract_nombre_ips(full_doc: dict[str, Any], rips: dict[str, Any]) -> str:
    """Nombre del prestador (FEV / metadatos); en RIPS solo viene codPrestador en servicios."""
    emisor = full_doc.get("emisor") or full_doc.get("prestador")
    if isinstance(emisor, dict):
        name = _nombre_from_object(emisor)
        if name:
            return name
        for key in TRANSACTION_NOMBRE_IPS_KEYS:
            if emisor.get(key):
                return str(emisor[key]).strip()

    info = full_doc.get("informacion_emisor")
    if isinstance(info, dict):
        nombre = info.get("nombre")
        if isinstance(nombre, dict):
            n = _nombre_from_object(nombre)
            if n:
                return n

    for key in TRANSACTION_NOMBRE_IPS_KEYS:
        if rips.get(key):
            return str(rips[key]).strip()
        if full_doc.get(key):
            return str(full_doc[key]).strip()

    return ""


def extract_nombre_paciente(usuario: dict[str, Any]) -> str:
    """
    El bloque usuario RIPS (U01–U12) no incluye nombre en el Anexo Técnico 1.
    Si el emisor agrega campos o envía estructura tipo FEV, se leen sin inventar valores.
    """
    nombre = usuario.get("nombre")
    if isinstance(nombre, str) and nombre.strip():
        return nombre.strip()
    if isinstance(nombre, dict):
        built = _nombre_from_object(nombre)
        if built:
            return built

    for key in USUARIO_NOMBRE_KEYS:
        if usuario.get(key):
            return str(usuario[key]).strip()

    parts = [str(usuario[k]).strip() for k in USUARIO_NOMBRE_PARTES if usuario.get(k)]
    return " ".join(parts).strip()
