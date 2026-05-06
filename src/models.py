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

# Header-label aliases per field. Used by excel_writer.detect_column_map() to
# auto-discover which Excel column a field belongs to, so the same code works
# with templates that have extra columns (IBAN, Bankdaten, Steuerklasse, …)
# in different positions.
#
# Add more variants here whenever a customer template uses a label we don't
# recognize yet. Comparison is loose: case-insensitive, whitespace and punctuation
# stripped, ä→ae / ö→oe / ü→ue / ß→ss applied automatically — so "Pers.-Nr.",
# "pers nr", "PERSONALNUMMER" all collapse to the same key.
FIELD_LABEL_ALIASES: dict[str, list[str]] = {
    "pers_nr":              ["Pers-Nr", "Pers Nr", "Pers.-Nr.", "Personalnummer", "Personal-Nr", "Personal Nr", "Personal", "Personal #"],
    "anrede":               ["Anrede"],
    "name":                 ["Name", "Nachname", "Familienname", "Name (Nachname)"],
    "vorname":              ["Vorname", "Vornamen", "Vorname(n)"],
    "staatsangehoerigkeit": ["Staatsangehörigkeit", "Staatsangeh.", "Staatsangeh", "Nationalität", "Staat"],
    "geb_datum":            ["GebDatum", "Geb.Datum", "Geb. Datum", "Geb-Datum", "Geburtsdatum", "Geboren am", "Geb."],
    "geschlecht":           ["Geschlecht", "Geschl.", "Geschl", "G", "m/w", "m/w/d"],
    "familienstand":        ["Familienstand", "Fam.stand", "Fam. Stand"],
    "strasse":              ["Straße", "Strasse", "Str.", "Straßenname", "Strassenname"],
    "hausnummer":           ["H#", "Hausnummer", "Haus-Nr", "Haus.Nr", "Haus.-Nr.", "HNr", "H-Nr", "H.Nr", "Nr."],
    "plz":                  ["PLZ", "Postleitzahl", "Plz"],
    "ort":                  ["Ort", "Wohnort", "Stadt"],
    "eintritt":             ["Eintritt", "Eintrittsdatum", "Beginn", "Beschäftigungsbeginn", "Anstellungsdatum"],
    "austritt":             ["Austritt", "Austrittsdatum", "Ende", "Beschäftigungsende"],
    "teilzeit_vollzeit":    ["Teilzeit/Vollzeit", "Vollzeit", "TZ/VZ", "VZ/TZ", "Arbeitszeit", "TZ-VZ"],
    "sv_nr":                ["SV Nr.", "SV-Nr.", "SV Nr", "SV-Nr", "SVNr", "Sozialversicherungsnummer", "Versicherungsnr.", "Versicherungsnummer", "RV-Nr", "RV Nr.", "Rentenversicherungsnummer"],
    "steuer_id":            ["ID. Nr.", "ID.Nr.", "IdNr", "ID-Nr", "ID Nr", "Steuer-ID", "SteuerID", "Steueridentifikationsnummer", "Steuer-Id-Nr", "StID"],
    # Form-only fields — only land in the Excel if the template has matching columns.
    "steuerklasse":         ["Steuerklasse", "St.Kl.", "StKl", "Steuer-Klasse", "Lohnsteuerklasse", "Stkl"],
    "konfession":           ["Konfession", "Kirchensteuer", "Religion", "Konfess."],
    "kinderfreibetrag":     ["Kinderfreibetrag", "Kinderfreibeträge", "KFB", "Anzahl Kinder", "Kinder"],
    "monatlicher_freibetrag": ["Monatlicher Freibetrag", "Freibetrag", "Monatsfreibetrag", "Mtl. Freibetrag"],
    "krankenkasse":         ["Krankenkasse", "KK", "Krankenversicherung", "Kasse"],
    "iban":                 ["IBAN", "Iban"],
    "bic":                  ["BIC", "Bic", "SWIFT", "SWIFT/BIC"],
    "geldinstitut":         ["Geldinstitut", "Bank", "Kreditinstitut", "Bankname"],
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
