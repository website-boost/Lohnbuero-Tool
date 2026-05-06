from __future__ import annotations

import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import Callable, Optional

import anthropic

from .models import STAMMDATEN_FIELDS, PageResult, Stammdaten


EXTRACTION_TOOL = {
    "name": "submit_stammdaten",
    "description": (
        "Submit the extracted employee master data (Stammdaten) from a single "
        "German payroll document (Lohn- und Gehaltsabrechnung). All fields are "
        "optional — if a field is not visible or not clearly readable on the "
        "document, return null for that field. Do NOT guess."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pers_nr": {
                "type": ["string", "null"],
                "description": "Personalnummer (Pers-Nr.). Usually a short number, e.g. '4', '15800'.",
            },
            "anrede": {
                "type": ["string", "null"],
                "description": "Anrede / salutation. Either 'Herr' or 'Frau'.",
            },
            "name": {
                "type": ["string", "null"],
                "description": "Nachname (last name only). E.g. for 'Alexandru-Paul Nitu' → 'Nitu'.",
            },
            "vorname": {
                "type": ["string", "null"],
                "description": "Vorname(n) (first name(s) only). E.g. for 'Alexandru-Paul Nitu' → 'Alexandru-Paul'.",
            },
            "staatsangehoerigkeit": {
                "type": ["string", "null"],
                "description": (
                    "Staatsangehörigkeit (nationality). Nur dann ausfüllen wenn EXPLIZIT als "
                    "'Staatsangehörigkeit', 'Nationalität', 'Staatsangeh.' oder mit Länderkürzel "
                    "(z.B. 'DE', 'RO', 'TR', 'PL') auf dem Dokument vermerkt. "
                    "WICHTIG: NIEMALS aus dem Namen, der Adresse oder anderem ableiten — auch nicht "
                    "wenn der Name nach einer bestimmten Herkunft klingt. Im Zweifel null zurückgeben. "
                    "Auf Standard-Lohnabrechnungen meist NICHT vorhanden."
                ),
            },
            "geb_datum": {
                "type": ["string", "null"],
                "description": "Geburtsdatum in German format DD.MM.YYYY (e.g. '22.02.2002').",
            },
            "geschlecht": {
                "type": ["string", "null"],
                "description": "Geschlecht. 'm' (male), 'w' (female), or 'd' (divers). Infer from Anrede if not explicitly stated.",
            },
            "familienstand": {
                "type": ["string", "null"],
                "description": "Familienstand (marital status). Often not on the document — return null if not present.",
            },
            "strasse": {
                "type": ["string", "null"],
                "description": "Straßenname OHNE Hausnummer. E.g. for 'Im Kürchen 18' → 'Im Kürchen'.",
            },
            "hausnummer": {
                "type": ["string", "null"],
                "description": "Nur die Hausnummer (kann Buchstaben enthalten). E.g. for 'Im Kürchen 18' → '18'.",
            },
            "plz": {
                "type": ["string", "null"],
                "description": "Postleitzahl (5 Ziffern). E.g. '56637'.",
            },
            "ort": {
                "type": ["string", "null"],
                "description": "Ort. E.g. 'Plaidt'.",
            },
            "eintritt": {
                "type": ["string", "null"],
                "description": "Eintrittsdatum in DD.MM.YYYY format.",
            },
            "austritt": {
                "type": ["string", "null"],
                "description": "Austrittsdatum in DD.MM.YYYY format. Usually empty/null if employee is still active.",
            },
            "teilzeit_vollzeit": {
                "type": ["string", "null"],
                "description": "'Vollzeit' or 'Teilzeit'. Often not explicit — return null if unclear.",
            },
            "sv_nr": {
                "type": ["string", "null"],
                "description": (
                    "Sozialversicherungsnummer (Versicherungsnr.). 12 characters: "
                    "8 digits + 1 letter + 3 digits, e.g. '16220202N003'. "
                    "On the document this is labeled 'Versicherungsnr.' — NOT to be confused with the Steuer-ID."
                ),
            },
            "steuer_id": {
                "type": ["string", "null"],
                "description": (
                    "Steuer-Identifikationsnummer (Steuer-ID / IdNr). Exactly 11 digits, e.g. '74452816401'. "
                    "On the document often labeled 'SteuerID' — distinct from the SV-Nr."
                ),
            },
            "steuerklasse": {
                "type": ["string", "null"],
                "description": (
                    "Lohnsteuerklasse. EINE einzelne Ziffer von 1 bis 6 — z.B. '1', '3', '4', '5'. "
                    "Steht im Kopfbereich der Lohnabrechnung in einer Tabelle direkt unter dem Header "
                    "'Steuer- klasse' oder 'Steuerklasse' (oft die linkeste Spalte des Steuermerkmal-Blocks). "
                    "WICHTIG: Nur die nackte Ziffer zurückgeben, OHNE Klasse-Präfix, OHNE Faktor, "
                    "OHNE römische Zahlen. Beispiel: wenn auf der Abrechnung '1' unter 'Steuerklasse' steht, "
                    "dann '1' zurückgeben — nicht 'Klasse 1', nicht 'I', nicht '1.0'."
                ),
            },
            "konfession": {
                "type": ["string", "null"],
                "description": (
                    "Konfession / Kirchensteuermerkmal. Steht im Kopfbereich in der "
                    "GLEICHEN Tabellenzeile wie Steuerklasse und Kinderfreibetrag, "
                    "typischerweise in einer Spalte mit Header 'Kon-fession', "
                    "'Konfession' oder 'Kirchen-steuer'. "
                    "Übliche Werte: 'rk' (römisch-katholisch), 'ev' (evangelisch), "
                    "'ak' (altkatholisch), '--' (keine Kirchensteuer). "
                    "Wichtig: WENN das Feld auf der Abrechnung sichtbar ist (egal ob mit Wert "
                    "oder mit '--'), dann den genauen Inhalt zurückgeben. Auch '--' ist eine "
                    "gültige Information ('keine Kirche'). Nur null wenn das Feld komplett fehlt."
                ),
            },
            "kinderfreibetrag": {
                "type": ["string", "null"],
                "description": (
                    "Kinderfreibetrag / Anzahl der Kinderfreibeträge. Meist als Zahl mit Komma, "
                    "z.B. '0,5', '1,0', '2,0'. Im Kopfbereich der Abrechnung. "
                    "'0' oder leer = keine Kinder berücksichtigt."
                ),
            },
            "monatlicher_freibetrag": {
                "type": ["string", "null"],
                "description": (
                    "Monatlicher Freibetrag (Lohnsteuer-Freibetrag) in Euro, falls auf der "
                    "Abrechnung ausgewiesen. Geldbetrag mit Komma. Sonst null."
                ),
            },
            "krankenkasse": {
                "type": ["string", "null"],
                "description": (
                    "Krankenkasse des Arbeitnehmers. Steht im Kopfbereich, oft direkt unter den "
                    "Steuermerkmalen, z.B. 'AOK Rheinland-Pfalz/Saarland', 'Techniker Krankenkasse', "
                    "'Barmer'. Vollständigen Namen zurückgeben."
                ),
            },
            "iban": {
                "type": ["string", "null"],
                "description": (
                    "IBAN des Arbeitnehmers (Bankverbindung). Steht auf den meisten Lohnabrechnungen "
                    "im UNTEREN Bereich (Zahlungs-/Überweisungsblock), oft mit Geldinstitut + BIC daneben. "
                    "Format: Deutschland 'DE' + 20 Ziffern (22 Zeichen total), evtl. mit Leerzeichen "
                    "in 4er-Gruppen — Leerzeichen entfernen und kompakt zurückgeben. "
                    "Genau lesen, jede Ziffer prüfen. Nur null wenn wirklich nicht zu sehen."
                ),
            },
            "bic": {
                "type": ["string", "null"],
                "description": (
                    "BIC / SWIFT-Code. 8 oder 11 Zeichen, nur Großbuchstaben + Ziffern, z.B. "
                    "'MALADE51KOB', 'COBADEFFXXX'. Steht meist direkt neben oder unter der IBAN."
                ),
            },
            "geldinstitut": {
                "type": ["string", "null"],
                "description": (
                    "Name der Bank / des Geldinstituts (z.B. 'Sparkasse Koblenz', 'Volksbank Mittelhessen'). "
                    "Steht im Zahlungsblock zusammen mit IBAN + BIC."
                ),
            },
        },
        "required": [
            "pers_nr", "anrede", "name", "vorname", "staatsangehoerigkeit",
            "geb_datum", "geschlecht", "familienstand", "strasse", "hausnummer",
            "plz", "ort", "eintritt", "austritt", "teilzeit_vollzeit",
            "sv_nr", "steuer_id",
            "steuerklasse", "konfession", "kinderfreibetrag",
            "monatlicher_freibetrag", "krankenkasse",
            "iban", "bic", "geldinstitut",
        ],
        "additionalProperties": False,
    },
}


SYSTEM_PROMPT = (
    "You are an expert at extracting structured employee master data (Stammdaten) "
    "from German payroll documents (Lohn- und Gehaltsabrechnungen). The documents "
    "you see may be high-quality digital PDFs OR low-quality scanned/pixelated "
    "images of paper printouts. Your job is to read every field carefully and "
    "submit the extracted data via the submit_stammdaten tool.\n\n"
    "CRITICAL RULES:\n"
    "1. Accuracy matters more than completeness. If a field is not clearly "
    "readable, return null — do NOT guess. Wrong data is worse than missing data.\n"
    "2. The Sozialversicherungsnummer (SV-Nr / Versicherungsnr) and the "
    "Steuer-Identifikationsnummer (Steuer-ID / IdNr) often appear next to each "
    "other in a single field labeled 'Versicherungsnr. SteuerID'. They are TWO "
    "DIFFERENT numbers. The SV-Nr has the format 8 digits + 1 letter + 3 digits "
    "(12 chars). The Steuer-ID is exactly 11 digits.\n"
    "3. Split the full name into Vorname (all given names, possibly hyphenated) "
    "and Name (last name only).\n"
    "4. Split the address into Straße (street name without number) and Hausnummer "
    "(house number, may include letters like '18a').\n"
    "5. Dates must be returned in German format DD.MM.YYYY exactly as shown on the document.\n"
    "6. IBAN, BIC und Geldinstitut findest du fast immer im UNTEREN Bereich der Lohnabrechnung "
    "(Zahlungs-/Überweisungsblock). Schau dort gezielt — diese Felder werden gerne übersehen.\n"
    "7. Always call the submit_stammdaten tool — never reply with plain text."
)


VERIFY_PROMPT = (
    "You previously extracted the following data from this payroll document:\n\n"
    "{json}\n\n"
    "Now look at the document AGAIN, very carefully, and verify each field. "
    "Pay special attention to:\n"
    "- digits that could be misread (0/O, 1/I/l, 5/S, 6/G, 8/B)\n"
    "- whether the SV-Nr and Steuer-ID were correctly distinguished\n"
    "- whether dates are correct\n"
    "- whether the name was split correctly into Vorname / Name\n\n"
    "Submit your VERIFIED extraction via submit_stammdaten. If you are not sure "
    "about a field, return null rather than guessing."
)


def _build_message_content(data: bytes, mime_type: str, text: str) -> list[dict]:
    """Build a Claude message with either a PDF document block or an image block.

    Claude handles OCR on scanned PDFs and images natively, so we don't need
    a separate OCR step for either format.
    """
    block_type = "image" if mime_type.startswith("image/") else "document"
    return [
        {
            "type": block_type,
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": base64.standard_b64encode(data).decode("ascii"),
            },
        },
        {"type": "text", "text": text},
    ]


def _call_extraction(
    client: anthropic.Anthropic,
    model: str,
    page_bytes: bytes,
    mime_type: str,
    user_text: str,
) -> dict:
    """Single Claude API call that returns the parsed tool-input dict."""
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[{**EXTRACTION_TOOL, "cache_control": {"type": "ephemeral"}}],
        tool_choice={"type": "tool", "name": "submit_stammdaten"},
        messages=[
            {
                "role": "user",
                "content": _build_message_content(page_bytes, mime_type, user_text),
            }
        ],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_stammdaten":
            return dict(block.input)
    raise RuntimeError("Model did not call submit_stammdaten tool")


def extract_and_verify_page(
    client: anthropic.Anthropic,
    model: str,
    page_bytes: bytes,
    mime_type: str,
    page_number: int,
) -> PageResult:
    """Run extraction + verification on a single page. Compare results.

    Fields that differ between extraction and verification are marked as
    uncertain. The verified value (pass 2) is the one we keep.
    """
    try:
        extract_text = (
            "Extract all employee master data (Stammdaten) from this German "
            "payroll document. Use the submit_stammdaten tool."
        )
        first = _call_extraction(client, model, page_bytes, mime_type, extract_text)

        verify_text = VERIFY_PROMPT.format(json=json.dumps(first, indent=2, ensure_ascii=False))
        second = _call_extraction(client, model, page_bytes, mime_type, verify_text)

        data = Stammdaten()
        uncertain: set[str] = set()
        notes: dict[str, str] = {}

        for field_name, _label in STAMMDATEN_FIELDS:
            v1 = first.get(field_name)
            v2 = second.get(field_name)
            v1_norm = (v1 or "").strip()
            v2_norm = (v2 or "").strip()
            data.set(field_name, v2 if v2_norm else v1)
            if v1_norm != v2_norm:
                uncertain.add(field_name)
                notes[field_name] = f"Pass1='{v1_norm}' / Pass2='{v2_norm}'"

        return PageResult(
            page_number=page_number,
            data=data,
            uncertain_fields=uncertain,
            notes=notes,
        )
    except Exception as exc:
        return PageResult(
            page_number=page_number,
            data=Stammdaten(),
            error=f"{type(exc).__name__}: {exc}",
        )


def extract_pages(
    pages: list[tuple[bytes, str]],
    api_key: str,
    model: str = "claude-opus-4-7",
    max_workers: int = 2,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    log_cb: Optional[Callable[[str], None]] = None,
) -> list[PageResult]:
    """Run extraction over a list of pages in parallel, with a sequential
    retry pass for any failures.

    Each page is `(bytes, mime_type)` — `application/pdf` or `image/*`.
    `progress_cb(done, total)` reports progress; `log_cb(msg)` lets the
    caller surface intermediate status (used to report the retry phase).

    Strategy:
    1. Parallel pass with `max_workers` workers, SDK auto-retries 429s with
       exponential backoff up to 8 times.
    2. If any pages still failed (typically per-minute token bucket
       exhausted), wait 30 s for the bucket to refill, then retry those
       pages SEQUENTIALLY one by one. Sequential = no concurrency stress,
       maximum chance of success.

    Results are returned in original page order.
    """
    client = anthropic.Anthropic(api_key=api_key, max_retries=8)
    total = len(pages)
    results: list[Optional[PageResult]] = [None] * total
    done = 0

    # Pass 1 — parallel
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {
            pool.submit(
                extract_and_verify_page, client, model, page_bytes, mime, idx + 1
            ): idx
            for idx, (page_bytes, mime) in enumerate(pages)
        }
        for fut in as_completed(future_to_idx):
            idx = future_to_idx[fut]
            results[idx] = fut.result()
            done += 1
            if progress_cb:
                progress_cb(done, total)

    # Pass 2 — sequential retry for failures
    failed_idx = [i for i, r in enumerate(results) if r is not None and r.error]
    if failed_idx:
        if log_cb:
            log_cb(
                f"\n⏳ {len(failed_idx)} Seite(n) gescheitert — warte 30 Sekunden, "
                f"dann Einzelversuch nacheinander…"
            )
        time.sleep(30)
        for i in failed_idx:
            page_bytes, mime = pages[i]
            if log_cb:
                log_cb(f"  → Wiederhole Seite {i+1}…")
            results[i] = extract_and_verify_page(
                client, model, page_bytes, mime, i + 1
            )
            if log_cb and results[i] is not None:
                if results[i].error:
                    log_cb(f"    ✗ Seite {i+1}: weiterhin Fehler")
                else:
                    log_cb(f"    ✓ Seite {i+1} jetzt erfolgreich")

    return [r for r in results if r is not None]
