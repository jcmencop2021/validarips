from __future__ import annotations

# Tipos de archivo RIPS (prefijo de nombre, 2 caracteres)
RIPS_TXT_TYPES: frozenset[str] = frozenset(
    {"CT", "AF", "US", "AD", "AC", "AP", "AU", "AH", "AN", "AM", "AT"}
)

SERVICE_TYPES: tuple[str, ...] = ("AC", "AP", "AM", "AT", "AU", "AH", "AN")

# Índices 0-based en líneas CSV (lineamientos técnicos IPS / Res. 3374)
AF_IDX_NUM_FACTURA = 5
AF_IDX_VALOR_NETO = 16
# Totales por tipo de servicio en AF (cuando el registro los trae)
AF_TOTAL_BY_SERVICE: dict[str, int] = {
    "AC": 21,
    "AP": 22,
    "AU": 23,
    "AH": 24,
    "AN": 25,
    "AM": 26,
    "AT": 27,
}

US_IDX_TIPO_DOC = 0
US_IDX_NUM_DOC = 1
US_IDX_PRIMER_APELLIDO = 4
US_IDX_SEGUNDO_APELLIDO = 5
US_IDX_PRIMER_NOMBRE = 6
US_IDX_SEGUNDO_NOMBRE = 7

SVC_IDX_FACTURA = 0
SVC_IDX_TIPO_DOC = 2
SVC_IDX_NUM_DOC = 3

# Valor cobrado (campo principal por archivo de servicio)
SVC_VALOR_IDX: dict[str, int] = {
    "AC": 14,
    "AP": 14,
    "AU": 15,
    "AH": 15,
    "AN": 12,
    "AM": 20,
    "AT": 12,
}
