from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _text(elem: ET.Element | None) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def parse_fev_xml(path: Path) -> dict[str, str]:
    """
    Extrae fecha de factura y nombre del prestador desde XML FEV (UBL / sector salud).
    Res. 948: el RIPS se cruza con la factura electrónica; la fecha y el emisor están en el XML.
    """
    result: dict[str, str] = {}
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return result

    root = tree.getroot()
    supplier_names: list[str] = []
    issue_dates: list[str] = []

    inside_supplier = False
    for elem in root.iter():
        tag = _local(elem.tag)
        if tag == "AccountingSupplierParty":
            inside_supplier = True
        elif tag in ("AccountingCustomerParty", "InvoiceLine", "LegalMonetaryTotal"):
            inside_supplier = False

        if tag == "IssueDate" and elem.text:
            issue_dates.append(elem.text.strip())
        if tag in ("RegistrationName", "Name") and elem.text and inside_supplier:
            supplier_names.append(elem.text.strip())

    if issue_dates:
        result["fecha_factura"] = issue_dates[0].split(" ")[0]
    if supplier_names:
        result["nombre_ips"] = supplier_names[0]

    return result


def find_companion_xml(json_path: Path) -> Path | None:
    """Busca XML de la misma factura en la carpeta del JSON."""
    folder = json_path.parent
    stem = json_path.stem
    candidates: list[Path] = [folder / f"{stem}.xml"]

    # Rips_FE0239105_66e4.json -> FE0239105.xml
    parts = stem.replace("Rips_", "").replace("rips_", "").split("_")
    if parts:
        candidates.append(folder / f"{parts[0]}.xml")

    for cand in candidates:
        if cand.is_file():
            return cand

    num_hint = parts[0] if parts else stem
    for xml_file in sorted(folder.glob("*.xml")):
        try:
            text = xml_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if num_hint and num_hint in text:
            return xml_file

    return None
