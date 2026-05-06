"""Fill BA Insolvenzgeld AcroForm PDFs from extracted Stammdaten.

Two form templates from the Bundesagentur für Arbeit:
- IB_Bescheinigung.pdf  (Insolvenzgeld-Bescheinigung des Arbeitgebers)
- Antrag_Insolvenzgeld.pdf  (Antrag auf Insolvenzgeld)

Both ship with the project under /templates. Only the personal data
(Stammdaten) we extracted is filled. All other fields (bank, tax bracket,
employer info, etc.) stay empty for the user to complete manually.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Callable

from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject

from .models import EmployeeRecord


def _templates_dir() -> Path:
    """Locate the bundled templates folder.

    When packaged with PyInstaller --onefile, data files live under
    `sys._MEIPASS`. In dev (running from source), they're in the repo.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "templates"
    return Path(__file__).resolve().parent.parent / "templates"


TEMPLATES_DIR = _templates_dir()
IB_TEMPLATE = TEMPLATES_DIR / "IB_Bescheinigung.pdf"
ANTRAG_TEMPLATE = TEMPLATES_DIR / "Antrag_Insolvenzgeld.pdf"


def _full_name(r: EmployeeRecord) -> str:
    n, v = (r.data.name or "").strip(), (r.data.vorname or "").strip()
    if n and v:
        return f"{n}, {v}"
    return n or v


def _strasse_hnr(r: EmployeeRecord) -> str:
    s, h = (r.data.strasse or "").strip(), (r.data.hausnummer or "").strip()
    return f"{s} {h}".strip()


def _plz_ort(r: EmployeeRecord) -> str:
    p, o = (r.data.plz or "").strip(), (r.data.ort or "").strip()
    return f"{p} {o}".strip()


# Map of AcroForm field name → function(record) -> string value.
# Only personal data (Stammdaten) — everything else stays empty.
IB_FIELD_MAP: dict[str, Callable[[EmployeeRecord], str]] = {
    "InsgBescheinigungAN[0].Seite1[0].tfAngabenAN[0].txtNameAN[0]": _full_name,
    "InsgBescheinigungAN[0].Seite1[0].tfAngabenAN[0].txtGebDatAN[0]": lambda r: r.data.geb_datum or "",
    "InsgBescheinigungAN[0].Seite1[0].tfAngabenAN[0].txtAN_Anschrift[0]": _strasse_hnr,
    "InsgBescheinigungAN[0].Seite1[0].tfAngabenAN[0].txtAN_PLZOrt[0]": _plz_ort,
    "InsgBescheinigungAN[0].Seite1[0].tfAngabenAN[0].txtSteuerklasse[0]": lambda r: r.data.steuerklasse or "",
    "InsgBescheinigungAN[0].Seite1[0].tfAngabenAN[0].txtKinderFreiBetraege[0]": lambda r: r.data.kinderfreibetrag or "",
    "InsgBescheinigungAN[0].Seite1[0].tfAngabenAN[0].txtMonatlicherFreibetrag[0]": lambda r: r.data.monatlicher_freibetrag or "",
    "InsgBescheinigungAN[0].Seite1[0].tfAngabenAN[0].Steuer-Identifikationsnummer[0]": lambda r: r.data.steuer_id or "",
    "InsgBescheinigungAN[0].Seite1[0].tfAngabenAN[0].Rentenversicherungsnummer[0]": lambda r: r.data.sv_nr or "",
    "InsgBescheinigungAN[0].Seite1[0].tfAngabeAV[0].txtBeginnAV[0]": lambda r: r.data.eintritt or "",
    # Page 2 / 3 cross-references (the form repeats name on each page)
    "InsgBescheinigungAN[0].Seite2[0].txtNameAN[0]": _full_name,
}

ANTRAG_FIELD_MAP: dict[str, Callable[[EmployeeRecord], str]] = {
    "txtf_2_Vorname": lambda r: r.data.vorname or "",
    "txtf_3_Nachname": lambda r: r.data.name or "",
    "txtf_4_GebDatum": lambda r: r.data.geb_datum or "",
    "txtf_6_Staatsangeh": lambda r: r.data.staatsangehoerigkeit or "",
    "txtf_8_Rentenversicherungsnr": lambda r: r.data.sv_nr or "",
    "txtf_9_Steuernr": lambda r: r.data.steuer_id or "",
    "txtf_10_Strasse": lambda r: r.data.strasse or "",
    "txtf_11_Hnr": lambda r: r.data.hausnummer or "",
    "txtf_12_PLZ": lambda r: r.data.plz or "",
    "txtf_13_Wohnort": lambda r: r.data.ort or "",
    "txtf_15_Geldinstitut": lambda r: r.data.geldinstitut or "",
    "txtf_16_IBAN": lambda r: r.data.iban or "",
    "txtf_17_BIC": lambda r: r.data.bic or "",
    "txtf_26_BeginnBeschaeftigung": lambda r: r.data.eintritt or "",
    "txtf_27_zuletztBeschaeftigt": lambda r: r.data.austritt or "",
    "txtf_51_Krankenkasse": lambda r: r.data.krankenkasse or "",
    "txtf_59_Steuerklasse": lambda r: r.data.steuerklasse or "",
}


def _safe_filename_part(s: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", s, flags=re.UNICODE).strip("_")
    return s or "Unbekannt"


def read_template_values(pdf_path: Path) -> dict[str, str]:
    """Extract all populated AcroForm field values from a filled PDF.

    Use case: father fills out one Antrag (or IB) per case with the case-wide
    info — Insolvenzgeld-Nr, employer info, all the yes/no checkboxes — and
    that filled PDF becomes the "Schema F" template. We read those values
    here and apply them to every newly generated PDF in the batch, on top
    of which the per-employee Stammdaten get overlaid.

    Skips empty text fields and unselected (`/Off`) checkboxes/radios.
    Keeps the `/<value>` form for button states so pypdf round-trips them.
    """
    reader = PdfReader(str(pdf_path))
    fields = reader.get_fields() or {}
    out: dict[str, str] = {}
    for name, f in fields.items():
        v = f.get("/V")
        if v is None:
            continue
        s = str(v)
        if s in ("", "/Off"):
            continue
        out[name] = s
    return out


def _fill_pdf(
    template: Path,
    record: EmployeeRecord,
    field_map: dict[str, Callable[[EmployeeRecord], str]],
    output_path: Path,
    base_values: dict[str, str] | None = None,
) -> None:
    """Fill a single AcroForm PDF with one employee's data.

    `base_values` are case-wide answers from a "Schema F" template PDF
    (yes/no checkboxes, Insolvenzgeld-Nr, employer info, etc.). They get
    applied first; per-employee Stammdaten from `field_map` overwrite any
    overlap so personal data always wins.
    """
    reader = PdfReader(str(template))
    writer = PdfWriter(clone_from=reader)

    record_values = {fname: fn(record) for fname, fn in field_map.items()}
    record_values = {k: v for k, v in record_values.items() if v}

    final_values: dict[str, str] = {}
    if base_values:
        final_values.update(base_values)
    final_values.update(record_values)  # per-employee values win

    for page in writer.pages:
        try:
            writer.update_page_form_field_values(page, final_values, auto_regenerate=False)
        except Exception:
            # Some pages have no form fields — skip silently.
            pass

    # Tell PDF readers (Acrobat, Preview) to regenerate field appearances
    # so values become visible immediately when the file is opened.
    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as fh:
        writer.write(fh)


def fill_forms(
    records: list[EmployeeRecord],
    output_dir: Path,
    template: Path,
    field_map: dict[str, Callable[[EmployeeRecord], str]],
    prefix: str,
    schema_f_pdf: Path | None = None,
) -> list[Path]:
    """Fill `template` once per employee. Returns list of generated paths.

    If `schema_f_pdf` is given, all field values from that pre-filled PDF are
    used as a baseline for every output (case-wide answers like yes/no
    checkboxes). Per-employee fields still come from `field_map`.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    base_values = read_template_values(schema_f_pdf) if schema_f_pdf else None
    paths: list[Path] = []
    for r in records:
        name = _safe_filename_part(r.data.name or "")
        vorname = _safe_filename_part(r.data.vorname or "")
        pers = _safe_filename_part(r.data.pers_nr or "")
        stem = "_".join(p for p in [prefix, name, vorname, pers] if p and p != "Unbekannt")
        out = output_dir / f"{stem}.pdf"
        _fill_pdf(template, r, field_map, out, base_values=base_values)
        paths.append(out)
    return paths


def fill_ib_forms(
    records: list[EmployeeRecord],
    output_dir: Path,
    schema_f_pdf: Path | None = None,
) -> list[Path]:
    return fill_forms(records, output_dir, IB_TEMPLATE, IB_FIELD_MAP, "IB", schema_f_pdf)


def fill_antrag_forms(
    records: list[EmployeeRecord],
    output_dir: Path,
    schema_f_pdf: Path | None = None,
) -> list[Path]:
    return fill_forms(records, output_dir, ANTRAG_TEMPLATE, ANTRAG_FIELD_MAP, "Antrag", schema_f_pdf)
