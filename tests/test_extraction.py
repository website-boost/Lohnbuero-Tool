"""Smoke test against the two real sample PDFs.

Run with: pytest tests/test_extraction.py -v
Requires ANTHROPIC_API_KEY in the environment (or .env).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.aggregator import aggregate_pages
from src.extractor import extract_pages
from src.pdf_splitter import load_pages

load_dotenv()

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLES = [FIXTURES / "sample_1.pdf", FIXTURES / "sample_2.pdf"]


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping live API test",
)
def test_extracts_known_employee():
    """Both sample PDFs should yield Pers-Nr 4, Nitu, geb. 22.02.2002."""
    pages = load_pages(SAMPLES)

    results = extract_pages(
        pages,
        api_key=os.environ["ANTHROPIC_API_KEY"],
        model=os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7"),
        max_workers=2,
    )

    records = aggregate_pages(results)
    assert len(records) >= 1, "Expected at least one employee"

    nitu = next(
        (r for r in records if (r.data.name or "").lower() == "nitu"),
        None,
    )
    assert nitu is not None, f"Did not find employee 'Nitu' in {[r.data.name for r in records]}"
    assert nitu.data.pers_nr == "4"
    assert nitu.data.geb_datum == "22.02.2002"
    assert nitu.data.eintritt == "20.04.2023"
    assert (nitu.data.plz, nitu.data.ort) == ("56637", "Plaidt")
    # SV-Nr and Steuer-ID must be distinct (the easy-to-confuse fields)
    assert nitu.data.sv_nr and nitu.data.sv_nr != nitu.data.steuer_id
    assert nitu.data.steuer_id and len(nitu.data.steuer_id) == 11
