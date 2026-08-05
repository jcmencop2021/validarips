from __future__ import annotations

from datetime import datetime

DISPLAY_FMT = "yyyy/MM/dd"


def format_date_display(value: str | None) -> str:
    """Normaliza a AAAA/MM/DD para la grilla."""
    if not value:
        return ""
    text = str(value).strip().split(" ")[0]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y/%m/%d")
        except ValueError:
            continue
    return text.replace("-", "/")


def parse_date_for_editor(value: str) -> str:
    """Devuelve yyyy-MM-dd para QDate."""
    if not value:
        return ""
    text = str(value).strip().split(" ")[0]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text
