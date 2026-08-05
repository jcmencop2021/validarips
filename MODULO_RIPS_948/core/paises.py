"""Nombres de país (ISO 3166-1 numérico) — tabla Pais MinSalud / RIPS."""

from __future__ import annotations

# Códigos frecuentes en RIPS colombiano; si no está, se deja el código.
PAIS_POR_CODIGO: dict[str, str] = {
    "004": "AFGANISTAN",
    "170": "COLOMBIA",
    "218": "ECUADOR",
    "604": "PERU",
    "862": "VENEZUELA",
    "840": "ESTADOS UNIDOS",
    "032": "ARGENTINA",
    "076": "BRASIL",
    "152": "CHILE",
    "484": "MEXICO",
    "724": "ESPAÑA",
    "250": "FRANCIA",
    "380": "ITALIA",
    "276": "ALEMANIA",
    "124": "CANADA",
    "591": "PANAMA",
    "188": "COSTA RICA",
    "320": "GUATEMALA",
    "340": "HONDURAS",
    "558": "NICARAGUA",
    "222": "EL SALVADOR",
    "192": "CUBA",
    "214": "REPUBLICA DOMINICANA",
    "630": "PUERTO RICO",
    "858": "URUGUAY",
    "068": "BOLIVIA",
    "600": "PARAGUAY",
}


def nombre_pais(codigo: str | int | None) -> str:
    if codigo is None or codigo == "":
        return ""
    text = str(codigo).strip()
    if not text.isdigit():
        return text
    key = text.lstrip("0") or "0"
    key3 = text.zfill(3)
    return (
        PAIS_POR_CODIGO.get(text)
        or PAIS_POR_CODIGO.get(key3)
        or PAIS_POR_CODIGO.get(key)
        or text
    )
