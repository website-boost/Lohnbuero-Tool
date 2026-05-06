# Lohnbüro-Tool

Lokales Tool zur automatischen Extraktion von **Stammdaten** aus deutschen Lohn-
und Gehaltsabrechnungen (PDF) und zum Eintrag in eine Excel-Vorlage
("Arbeitnehmer-Liste" für Insolvenzgeld-Verfahren).

- Drag-and-Drop für PDFs (auch eingescannte, verpixelte Dokumente)
- Verarbeitet auch große PDFs mit hunderten Seiten
- **Doppelte Verifikation** jeder Seite: jede Seite läuft 2× durch Claude;
  abweichende Werte werden im Excel **orange markiert** und bekommen einen
  Kommentar mit den beiden Lesungen, damit der Bediener sie prüfen kann
- Aggregiert mehrere Seiten desselben Mitarbeiters (gleiche Pers-Nr) zu
  einem Datensatz
- Bestehende Excel-Vorlage wird kopiert; Formatierung und Formeln
  (Alter, Summen) bleiben erhalten

## Setup auf dem Mac (Entwicklung & Test)

```bash
cd ~/Desktop/Lohnbuero-Tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env öffnen und ANTHROPIC_API_KEY eintragen
python app.py
```

API-Key besorgen: <https://console.anthropic.com> → API Keys → Create Key.
Kosten ca. 1–3 Cent pro Seite (Claude Opus 4.7 mit Vision-PDF).

## Tests

```bash
pytest tests/test_extraction.py -v
```

Macht echte API-Calls gegen die zwei Beispiel-PDFs in `tests/fixtures/` und
prüft, dass Pers-Nr 4 (Nitu) korrekt erkannt wird (Geburtsdatum, Eintritt,
Adresse, SV-Nr ≠ Steuer-ID).

## Build der Windows-EXE (für den Rechner deines Vaters)

Du musst nichts auf Windows bauen — das macht GitHub Actions automatisch.

1. Repo auf GitHub pushen (privat ist ok).
2. `.github/workflows/build-windows.yml` läuft bei jedem Push auf `main`.
3. Im Repo unter **Actions → Build Windows EXE → letzter Run → Artifacts**
   die `Lohnbuero-Tool-Windows.zip` herunterladen, entpacken → fertige
   `Lohnbuero-Tool.exe`.
4. EXE auf den Windows-Rechner kopieren, Doppelklick.
5. Beim ersten Start: Button **API-Key…** klicken und den Anthropic-Key
   einmalig eintragen (wird in der Windows-Registry gespeichert).

Für eine offizielle Version mit Tag (`git tag v0.1 && git push --tags`)
wird die EXE automatisch an einen GitHub Release angehängt.

## Projektstruktur

```
Lohnbuero-Tool/
├── app.py                 # PySide6 GUI Entry-Point
├── src/
│   ├── pdf_splitter.py    # PDF → einzelne Seiten
│   ├── extractor.py       # Claude API: Extraktion + Verifikation
│   ├── aggregator.py      # Mehrere Seiten pro Mitarbeiter zusammenführen
│   ├── excel_writer.py    # Template befüllen + Orange-Markierung
│   └── models.py          # Datenklassen + Excel-Spalten-Mapping
├── tests/
│   ├── fixtures/          # 2 Beispiel-PDFs + Excel-Template
│   └── test_extraction.py
├── .github/workflows/build-windows.yml
├── requirements.txt
└── .env.example
```

## Wie der Double-Check funktioniert

Pro PDF-Seite:

1. **Pass 1 (Extract):** Claude liest das PDF, gibt strukturiertes JSON zurück.
2. **Pass 2 (Verify):** Claude bekommt das PDF *und* das JSON aus Pass 1,
   wird aufgefordert, jedes Feld erneut zu prüfen, gibt eigenes JSON zurück.
3. Felder, bei denen Pass 1 ≠ Pass 2 → **als unsicher markiert**.

Beim Schreiben ins Excel:
- Sichere Felder → normal
- Unsichere Felder → **orange Hintergrund** + Kommentar mit beiden Werten

Bei Mitarbeitern, die auf mehreren Abrechnungen vorkommen (z.B. 3 Monate),
werden zusätzlich die Lesungen über die Seiten hinweg verglichen — auch hier
führen Konflikte zu einer Orange-Markierung.

## Sicherheit / Datenschutz

- API-Key wird lokal gespeichert (Mac: `.env`; Windows: Registry).
- PDFs werden zur Verarbeitung an die Anthropic API gesendet (USA/EU).
  Anthropic bietet einen DSGVO-konformen DPA an.
- Keine Daten werden persistent bei Anthropic gespeichert (Standard-Policy).

## Bekannte Einschränkungen Phase 1

- Nur Stammdaten (keine Monats-Brutto-Werte). Das kommt in Phase 2.
- Datumswerte werden als Text im DD.MM.YYYY-Format ins Excel geschrieben.
- Keine OCR-Fallback-Strategie ohne API (Internet auf dem Windows-Rechner
  nötig).
