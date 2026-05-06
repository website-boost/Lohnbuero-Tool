from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


STAMMDATEN_FIELDS: list[tuple[str, str]] = [
    ("pers_nr", "Personal-Nr"),
    ("anrede", "Anrede"),
    ("name", "Name (Nachname)"),
    ("vorname", "Vorname"),
    ("staatsangehoerigkeit", "Staatsangehörigkeit"),
    ("geb_datum", "Geburtsdatum"),
    ("geschlecht", "Geschlecht"),
    ("familienstand", "Familienstand"),
    ("strasse", "Straße"),
    ("hausnummer", "Hausnummer"),
    ("plz", "PLZ"),
    ("ort", "Ort"),
    ("eintritt", "Eintrittsdatum"),
    ("austritt", "Austrittsdatum"),
    ("teilzeit_vollzeit", "Teilzeit/Vollzeit"),
    ("sv_nr", "SV-Nr."),
    ("steuer_id", "Steuer-ID"),
    # Form-only fields (not in Excel template, used to fill BA forms)
    ("steuerklasse", "Steuerklasse"),
    ("konfession", "Konfession"),
    ("kinderfreibetrag", "Kinderfreibetrag"),
    ("monatlicher_freibetrag", "Monatlicher Freibetrag"),
    ("krankenkasse", "Krankenkasse"),
    ("iban", "IBAN"),
    ("bic", "BIC"),
    ("geldinstitut", "Geldinstitut"),
]

EXCEL_COLUMN_MAP: dict[str, str] = {
    "pers_nr": "A",
    "anrede": "B",
    "name": "C",
    "vorname": "D",
    "staatsangehoerigkeit": "E",
    "geb_datum": "F",
    "geschlecht": "G",
    # H = Alter (formula, do not write)
    "familienstand": "I",
    "strasse": "J",
    "hausnummer": "K",
    "plz": "L",
    "ort": "M",
    "eintritt": "N",
    "austritt": "O",
    "teilzeit_vollzeit": "P",
    "sv_nr": "Q",
    "steuer_id": "R",
}


@dataclass
class Stammdaten:
    """Extracted employee master data from a single payslip page."""
    pers_nr: Optional[str] = None
    anrede: Optional[str] = None
    name: Optional[str] = None
    vorname: Optional[str] = None
    staatsangehoerigkeit: Optional[str] = None
    geb_datum: Optional[str] = None
    geschlecht: Optional[str] = None
    familienstand: Optional[str] = None
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    eintritt: Optional[str] = None
    austritt: Optional[str] = None
    teilzeit_vollzeit: Optional[str] = None
    sv_nr: Optional[str] = None
    steuer_id: Optional[str] = None
    steuerklasse: Optional[str] = None
    konfession: Optional[str] = None
    kinderfreibetrag: Optional[str] = None
    monatlicher_freibetrag: Optional[str] = None
    krankenkasse: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    geldinstitut: Optional[str] = None

    def get(self, field_name: str) -> Optional[str]:
        return getattr(self, field_name, None)

    def set(self, field_name: str, value: Optional[str]) -> None:
        setattr(self, field_name, value)


@dataclass
class PageResult:
    """Result of extracting + verifying a single PDF page."""
    page_number: int
    data: Stammdaten
    uncertain_fields: set[str] = field(default_factory=set)
    notes: dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class EmployeeRecord:
    """Aggregated record per Pers-Nr (one employee may appear on multiple pages)."""
    data: Stammdaten
    uncertain_fields: set[str] = field(default_factory=set)
    notes: dict[str, str] = field(default_factory=dict)
    source_pages: list[int] = field(default_factory=list)
