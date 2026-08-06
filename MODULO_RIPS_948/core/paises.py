"""Nombres de país (ISO 3166-1 numérico) — tabla Pais MinSalud / RIPS."""

from __future__ import annotations

# Código numérico → nombre (ampliado para selector en grilla)
PAIS_POR_CODIGO: dict[str, str] = {
    "004": "AFGANISTAN",
    "008": "ALBANIA",
    "012": "ARGELIA",
    "032": "ARGENTINA",
    "036": "AUSTRALIA",
    "040": "AUSTRIA",
    "050": "BANGLADESH",
    "051": "ARMENIA",
    "056": "BELGICA",
    "068": "BOLIVIA",
    "076": "BRASIL",
    "084": "BELICE",
    "090": "ISLAS SALOMON",
    "124": "CANADA",
    "152": "CHILE",
    "156": "CHINA",
    "170": "COLOMBIA",
    "188": "COSTA RICA",
    "192": "CUBA",
    "214": "REPUBLICA DOMINICANA",
    "218": "ECUADOR",
    "222": "EL SALVADOR",
    "250": "FRANCIA",
    "276": "ALEMANIA",
    "320": "GUATEMALA",
    "340": "HONDURAS",
    "380": "ITALIA",
    "484": "MEXICO",
    "558": "NICARAGUA",
    "591": "PANAMA",
    "600": "PARAGUAY",
    "604": "PERU",
    "630": "PUERTO RICO",
    "724": "ESPAÑA",
    "740": "SURINAM",
    "756": "SUIZA",
    "792": "TURQUIA",
    "826": "REINO UNIDO",
    "840": "ESTADOS UNIDOS",
    "858": "URUGUAY",
    "862": "VENEZUELA",
    "900": "OTRO",
}

# Código numérico RIPS → sigla ISO2 (iniciales) para el listado
CODIGO_A_ISO2: dict[str, str] = {
    "004": "AF",
    "032": "AR",
    "068": "BO",
    "076": "BR",
    "124": "CA",
    "152": "CL",
    "170": "CO",
    "188": "CR",
    "192": "CU",
    "214": "DO",
    "218": "EC",
    "222": "SV",
    "250": "FR",
    "276": "DE",
    "320": "GT",
    "340": "HN",
    "380": "IT",
    "484": "MX",
    "558": "NI",
    "591": "PA",
    "600": "PY",
    "604": "PE",
    "724": "ES",
    "840": "US",
    "858": "UY",
    "862": "VE",
}

NOMBRE_A_ISO2: dict[str, str] = {}
for _cod, _nombre in PAIS_POR_CODIGO.items():
    _iso = CODIGO_A_ISO2.get(_cod, "")
    if _iso:
        NOMBRE_A_ISO2[_nombre.upper()] = _iso


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


def _iso2_for_codigo(cod: str) -> str:
    return CODIGO_A_ISO2.get(cod, CODIGO_A_ISO2.get(cod.zfill(3), ""))


def country_choices() -> list[tuple[str, str]]:
    """(texto en combo, valor a guardar en celda = nombre país)."""
    items: list[tuple[str, str]] = []
    seen: set[str] = set()
    for cod, nombre in sorted(PAIS_POR_CODIGO.items(), key=lambda x: x[1]):
        iso2 = _iso2_for_codigo(cod)
        label = f"{iso2} - {nombre}" if iso2 else nombre
        if nombre in seen:
            continue
        seen.add(nombre)
        items.append((label, nombre))
    return items


def match_country_display(value: str) -> str:
    """Encuentra etiqueta del combo para un valor de celda."""
    text = (value or "").strip()
    if not text:
        return ""
    upper = text.upper()
    for display, nombre in country_choices():
        if nombre.upper() == upper or display.upper().startswith(upper):
            return display
        iso = NOMBRE_A_ISO2.get(upper, "")
        if iso and display.startswith(f"{iso} -"):
            return display
    return text
