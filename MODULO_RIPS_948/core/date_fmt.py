from __future__ import annotations

from datetime import datetime

# Formato visible y editable: dd/mm/aaaa
DISPLAY_FMT = "dd/MM/yyyy"
DATE_PLACEHOLDER = "dd/mm/aaaa"


def format_date_display(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).strip().split(" ")[0]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            continue
    return text


def normalize_typed_date(value: str) -> str:
    """Valida texto ingresado y devuelve dd/mm/aaaa o el texto si no parsea."""
    text = str(value or "").strip()
    if not text:
        return ""
    return format_date_display(text) or text
