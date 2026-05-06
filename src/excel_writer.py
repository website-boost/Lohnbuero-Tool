from __future__ import annotations

import shutil
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import PatternFill

from .models import EXCEL_COLUMN_MAP, EmployeeRecord


# First data row in the template (rows 1–15 are header band).
FIRST_DATA_ROW = 16
SHEET_NAME = "Arbeitnehmer"

ORANGE_FILL = PatternFill(start_color="FFD9A0", end_color="FFD9A0", fill_type="solid")


def write_records(
    template_path: Path,
    output_path: Path,
    records: list[EmployeeRecord],
) -> None:
    """Copy the template, then fill rows 16+ with employee data.

    Cells where extraction was uncertain are filled orange and get a comment
    showing the conflicting values, so the user knows where to double-check.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template_path, output_path)

    wb = load_workbook(output_path)
    if SHEET_NAME not in wb.sheetnames:
        raise ValueError(f"Template missing expected sheet '{SHEET_NAME}'")
    ws = wb[SHEET_NAME]

    for offset, record in enumerate(records):
        row = FIRST_DATA_ROW + offset
        for field_name, column_letter in EXCEL_COLUMN_MAP.items():
            value = record.data.get(field_name)
            if value is None or value == "":
                continue
            cell = ws[f"{column_letter}{row}"]
            cell.value = value
            if field_name in record.uncertain_fields:
                cell.fill = ORANGE_FILL
                note = record.notes.get(field_name, "Bitte prüfen — unsicher extrahiert.")
                cell.comment = Comment(note, "Lohnbuero-Tool")

    wb.save(output_path)
