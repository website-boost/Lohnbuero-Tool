from __future__ import annotations

from .models import STAMMDATEN_FIELDS, EmployeeRecord, PageResult, Stammdaten


def _make_key(data: Stammdaten) -> str:
    """Key used to deduplicate employees across pages.

    Pers-Nr alone is not safe — the same Pers-Nr can be reused across different
    customers (Mandanten). We combine Pers-Nr with name+geb_datum as a fallback
    when Pers-Nr is missing, and use Pers-Nr+name when available.
    """
    pers = (data.pers_nr or "").strip()
    name = (data.name or "").strip().lower()
    vorname = (data.vorname or "").strip().lower()
    geb = (data.geb_datum or "").strip()
    if pers:
        return f"P:{pers}|{name}|{vorname}"
    return f"N:{name}|{vorname}|{geb}"


def aggregate_pages(pages: list[PageResult]) -> list[EmployeeRecord]:
    """Merge per-page extraction results into one record per employee.

    Strategy: group by key, then for each field pick the first non-empty value
    seen across all pages of that employee. If two pages disagree on a non-
    empty value, mark the field as uncertain on the merged record and record
    the conflict in notes.
    """
    by_key: dict[str, EmployeeRecord] = {}

    for page in pages:
        if page.error or not _has_any_data(page.data):
            continue
        key = _make_key(page.data)
        if key not in by_key:
            by_key[key] = EmployeeRecord(
                data=Stammdaten(),
                uncertain_fields=set(),
                notes={},
                source_pages=[],
            )
        record = by_key[key]
        record.source_pages.append(page.page_number)

        for field_name, _label in STAMMDATEN_FIELDS:
            new_val = (page.data.get(field_name) or "").strip()
            if not new_val:
                continue
            existing = (record.data.get(field_name) or "").strip()
            if not existing:
                record.data.set(field_name, new_val)
            elif existing != new_val:
                record.uncertain_fields.add(field_name)
                prior = record.notes.get(field_name, f"'{existing}'")
                record.notes[field_name] = f"{prior} vs '{new_val}' (Seite {page.page_number})"

        # Carry forward per-page uncertainty (mismatches between extract+verify).
        for field_name in page.uncertain_fields:
            record.uncertain_fields.add(field_name)
            note = page.notes.get(field_name)
            if note and field_name not in record.notes:
                record.notes[field_name] = f"Seite {page.page_number}: {note}"

    return list(by_key.values())


def _has_any_data(data: Stammdaten) -> bool:
    return any(data.get(f) for f, _ in STAMMDATEN_FIELDS)
