from __future__ import annotations

# Tipos de archivo RIPS (prefijo de nombre, 2 caracteres)
RIPS_TXT_TYPES: frozenset[str] = frozenset(
    {"CT", "AF", "US", "AD", "AC", "AP", "AU", "AH", "AN", "AM", "AT"}
)

SERVICE_TYPES: tuple[str, ...] = ("AC", "AP", "AM", "AT", "AU", "AH", "AN")

# --- Archivo AF (transacciones) — índices 0-based ---
AF_IDX_COD_PRESTADOR = 0
AF_IDX_NOMBRE_IPS = 1
AF_IDX_TIPO_ID_PRESTADOR = 2
AF_IDX_NUM_ID_PRESTADOR = 3
AF_IDX_NUM_FACTURA = 4
AF_IDX_FECHA_FACTURA = 5
AF_IDX_FECHA_INICIO = 6
AF_IDX_FECHA_FIN = 7
AF_IDX_COD_ENTIDAD = 8
AF_IDX_NOMBRE_ENTIDAD = 9
AF_IDX_VALOR_NETO = 16

AF_TOTAL_BY_SERVICE: dict[str, int] = {
    "AC": 21,
    "AP": 22,
    "AU": 23,
    "AH": 24,
    "AN": 25,
    "AM": 26,
    "AT": 27,
}

# --- Archivo US (usuarios) ---
US_IDX_TIPO_DOC = 0
US_IDX_NUM_DOC = 1
US_IDX_PRIMER_APELLIDO = 4
US_IDX_SEGUNDO_APELLIDO = 5
US_IDX_PRIMER_NOMBRE = 6
US_IDX_SEGUNDO_NOMBRE = 7
# Código país residencia (DIVIPOLA numérico → nombre vía catálogo)
US_IDX_COD_PAIS = 20

SVC_IDX_FACTURA = 0
SVC_IDX_TIPO_DOC = 2
SVC_IDX_NUM_DOC = 3

SVC_DATE_IDX: dict[str, int] = {
    "AC": 4,
    "AP": 4,
    "AU": 4,
    "AH": 4,
    "AN": 4,
    "AM": 4,
    "AT": 4,
}

# Valor cobrado por tipo de archivo (índice principal; records.py tiene respaldo)
SVC_VALOR_IDX: dict[str, int] = {
    "AC": 14,
    "AP": 14,
    "AU": 14,
    "AH": 14,
    "AN": 12,
    "AM": 20,
    "AT": 12,
}
