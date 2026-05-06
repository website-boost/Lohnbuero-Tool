from __future__ import annotations

import os
import random
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtCore import Qt, QThread, QTimer, Signal, QSettings, QUrl
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QPlainTextEdit, QStackedWidget, QVBoxLayout, QWidget,
)

from src.aggregator import aggregate_pages
from src.excel_writer import write_records
from src.extractor import extract_pages
from src.models import EmployeeRecord
from src.pdf_filler import fill_antrag_forms, fill_ib_forms
from src.pdf_splitter import SUPPORTED_EXTENSIONS, load_pages
from src.updater import (
    UpdateInfo, check_for_update, download_and_apply_update, is_frozen_exe,
)
from src.version import __version__


load_dotenv()

ORG_NAME = "Lohnbuero"
APP_NAME = "Lohnbuero-Tool"

# Tokyo-Night-inspired palette
COLORS = {
    "bg":          "#1a1b26",
    "bg_elevated": "#24283b",
    "bg_card":     "#1f2335",
    "border":      "#414868",
    "text":        "#c0caf5",
    "text_dim":    "#7a88b8",
    "accent":      "#7aa2f7",  # blue
    "accent2":     "#bb9af7",  # purple
    "success":     "#9ece6a",
    "warning":     "#e0af68",
    "error":       "#f7768e",
    "cyan":        "#7dcfff",
}

LOADING_MESSAGES = [
    "🤖 Die KI schaut sich die Daten an…",
    "☕ Zeit für einen Kaffee — das dauert ein paar Minuten",
    "🔍 Lese Personalnummern…",
    "🧐 Doppelt prüfen schadet nie…",
    "🤹 Jongliere mit Versicherungsnummern…",
    "📐 Vergleiche Pass 1 mit Pass 2…",
    "✏️ Notiere Geburtsdaten…",
    "🔎 Entwirre SV-Nr und Steuer-ID…",
    "🧠 Künstliche Intelligenz, echte Konzentration…",
    "📦 Pack die Stammdaten in Schachteln…",
    "☕ Noch ein Schluck Kaffee?",
    "🛠️ Zähle Pixel auf den Scans…",
    "🎯 Treffe ins Schwarze…",
    "🚀 Bin gleich da, versprochen!",
    "🎩 Tausche Name und Vorname richtigrum…",
    "✨ Mache dein Excel hübsch…",
    "🐢 Gut Ding will Weile haben…",
    "🔥 Tippmaschine läuft heiß…",
]


STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: -apple-system, "SF Pro Display", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QLabel {{ color: {COLORS['text']}; background: transparent; }}
QLabel#title {{ font-size: 22px; font-weight: 700; }}
QLabel#subtitle {{ font-size: 12px; color: {COLORS['text_dim']}; }}
QLabel#stepTitle {{ font-size: 18px; font-weight: 700; color: {COLORS['text']}; }}
QLabel#stepHint {{ font-size: 12px; color: {COLORS['text_dim']}; }}
QLabel#sectionLabel {{
    font-size: 11px; font-weight: 600;
    color: {COLORS['text_dim']};
    text-transform: uppercase; letter-spacing: 1px;
}}
QLabel#pdfLabel {{ font-size: 13px; color: {COLORS['cyan']}; padding: 4px 0; }}
QLabel#loadingMsg {{
    font-size: 16px; color: {COLORS['accent2']};
    font-style: italic; padding: 8px 0;
}}
QLabel#bigCheck {{ font-size: 14px; padding: 4px 0; }}
QLabel#stepIndicator {{ font-size: 11px; color: {COLORS['text_dim']}; }}

QFrame#card {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
}}
QFrame#header {{
    background-color: {COLORS['bg_elevated']};
    border-radius: 12px;
    border: 1px solid {COLORS['border']};
}}
QFrame#updateBanner {{
    background-color: {COLORS['warning']};
    border-radius: 10px;
}}

QPushButton {{
    background-color: {COLORS['bg_elevated']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {COLORS['border']};
    border-color: {COLORS['accent']};
}}
QPushButton:pressed {{ background-color: {COLORS['bg']}; }}
QPushButton:disabled {{
    color: {COLORS['text_dim']};
    background-color: {COLORS['bg_card']};
}}
QPushButton#primary {{
    background-color: {COLORS['accent']};
    color: {COLORS['bg']};
    border: none;
    font-weight: 700;
    font-size: 14px;
    padding: 12px 24px;
}}
QPushButton#primary:hover {{ background-color: {COLORS['cyan']}; }}
QPushButton#primary:disabled {{
    background-color: {COLORS['border']};
    color: {COLORS['text_dim']};
}}
QPushButton#updateBtn {{
    background-color: {COLORS['bg']};
    color: {COLORS['warning']};
    border: none; border-radius: 6px;
    padding: 6px 14px; font-weight: 700;
}}
QPushButton#updateBtn:hover {{ background-color: {COLORS['bg_card']}; }}

QLineEdit {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {COLORS['accent']};
}}
QLineEdit:focus {{ border-color: {COLORS['accent']}; }}

QProgressBar {{
    background-color: {COLORS['bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    height: 22px;
    text-align: center;
    color: {COLORS['text']};
    font-weight: 600;
}}
QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 7px;
}}

QPlainTextEdit {{
    background-color: {COLORS['bg']};
    color: {COLORS['text_dim']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 10px;
    font-family: "SF Mono", "Cascadia Code", "Menlo", monospace;
    font-size: 11px;
}}

QCheckBox {{
    color: {COLORS['text']}; padding: 8px 0; spacing: 12px;
    font-size: 14px;
}}
QCheckBox::indicator {{
    width: 24px; height: 24px;
    border: 2px solid {COLORS['border']};
    border-radius: 5px; background: {COLORS['bg']};
}}
QCheckBox::indicator:hover {{ border-color: {COLORS['accent']}; }}
QCheckBox::indicator:checked {{
    background: {COLORS['success']};
    border: 2px solid {COLORS['success']};
}}
QCheckBox::indicator:checked:hover {{
    background: {COLORS['success']};
    border-color: {COLORS['success']};
}}
QMessageBox {{ background-color: {COLORS['bg_elevated']}; }}
"""


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def get_api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key.strip()
    stored = QSettings(ORG_NAME, APP_NAME).value("api_key")
    return stored.strip() if stored else None


def store_api_key(key: str) -> None:
    QSettings(ORG_NAME, APP_NAME).setValue("api_key", key.strip())


def verify_api_key(api_key: str) -> tuple[bool, str]:
    """Tiny ping to confirm the key works."""
    import anthropic
    try:
        anthropic.Anthropic(api_key=api_key).messages.create(
            model="claude-haiku-4-5", max_tokens=4,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, "ok"
    except anthropic.AuthenticationError as exc:
        return False, f"API-Key ungültig: {exc}"
    except Exception as exc:
        return False, f"Verbindung fehlgeschlagen: {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Wizard state
# ---------------------------------------------------------------------------

@dataclass
class WizardState:
    # Step 1: what to do
    do_excel: bool = True
    do_ib: bool = True
    do_antrag: bool = True
    # Step 2: templates + output location
    excel_template: Path | None = None
    ib_schema_f: Path | None = None       # optional pre-filled IB
    antrag_schema_f: Path | None = None   # optional pre-filled Antrag
    output_dir: Path | None = None
    # Step 3: input files
    input_files: list[Path] = field(default_factory=list)
    # Results (Step 5)
    last_records: list[EmployeeRecord] = field(default_factory=list)
    last_excel_path: Path | None = None
    last_uncertain: int = 0
    last_ib_dir: Path | None = None
    last_ib_count: int = 0
    last_antrag_dir: Path | None = None
    last_antrag_count: int = 0


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------

class UpdateCheckWorker(QThread):
    found = Signal(object)

    def run(self) -> None:
        info = check_for_update()
        if info is not None:
            self.found.emit(info)


class ExtractionWorker(QThread):
    progress = Signal(int, int, str)
    log = Signal(str)
    # excel_path|None, records, num_uncertain, ib_dir|None, ib_count, antrag_dir|None, antrag_count
    finished_ok = Signal(object, list, int, object, int, object, int)
    failed = Signal(str)

    def __init__(self, state: WizardState, api_key: str, model: str) -> None:
        super().__init__()
        self.state = state
        self.api_key = api_key
        self.model = model

    def run(self) -> None:
        s = self.state
        try:
            self.log.emit(f"Lade {len(s.input_files)} Datei(en)…")
            all_pages = load_pages(s.input_files)
            for path in s.input_files:
                if path.suffix.lower() == ".pdf":
                    from pypdf import PdfReader
                    n = len(PdfReader(str(path)).pages)
                    self.log.emit(f"  {path.name}: {n} Seite(n)")
                else:
                    self.log.emit(f"  {path.name}: 1 Bild")

            total = len(all_pages)
            self.log.emit(
                f"Starte Extraktion ({total} Seiten, je 2 API-Aufrufe = "
                f"{total*2} Calls)…"
            )

            def on_progress(done: int, _total: int) -> None:
                self.progress.emit(done, total, f"{done} / {total} Seiten")

            page_results = extract_pages(
                all_pages, api_key=self.api_key, model=self.model,
                max_workers=5, progress_cb=on_progress,
            )
            for p in page_results:
                if p.error:
                    self.log.emit(f"  ⚠ Seite {p.page_number}: {p.error}")

            self.log.emit("Aggregiere Mitarbeiter…")
            records = aggregate_pages(page_results)
            num_uncertain = sum(1 for r in records if r.uncertain_fields)
            self.log.emit(
                f"  {len(records)} Mitarbeiter gefunden, "
                f"{num_uncertain} mit unsicheren Feldern"
            )

            stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            excel_path: Path | None = None
            if s.do_excel and records and s.excel_template and s.output_dir:
                excel_path = s.output_dir / f"{stamp}_Stammdaten.xlsx"
                self.log.emit(f"Schreibe Excel: {excel_path.name}")
                wr = write_records(s.excel_template, excel_path, records)
                self.log.emit(
                    f"  → {len(wr.detected_columns)} Spalten erkannt: "
                    f"{', '.join(sorted(wr.detected_columns.keys()))}"
                )
                if wr.fields_without_column:
                    self.log.emit(
                        f"  ⚠ Felder ohne passende Excel-Spalte: "
                        f"{', '.join(wr.fields_without_column)} "
                        f"(stehen aber in IB/Antrag falls aktiviert)"
                    )

            ib_dir, ib_count = None, 0
            if s.do_ib and records and s.output_dir:
                ib_dir = s.output_dir / f"{stamp}_IB"
                schema_note = " (mit Schema-F)" if s.ib_schema_f else ""
                self.log.emit(f"Erstelle IB-Bescheinigungen{schema_note} → {ib_dir.name}/")
                paths = fill_ib_forms(records, ib_dir, schema_f_pdf=s.ib_schema_f)
                ib_count = len(paths)

            antrag_dir, antrag_count = None, 0
            if s.do_antrag and records and s.output_dir:
                antrag_dir = s.output_dir / f"{stamp}_Antraege"
                schema_note = " (mit Schema-F)" if s.antrag_schema_f else ""
                self.log.emit(f"Erstelle Anträge{schema_note} → {antrag_dir.name}/")
                paths = fill_antrag_forms(records, antrag_dir, schema_f_pdf=s.antrag_schema_f)
                antrag_count = len(paths)

            self.finished_ok.emit(
                excel_path, records, num_uncertain,
                ib_dir, ib_count, antrag_dir, antrag_count,
            )
        except Exception:
            self.failed.emit(traceback.format_exc())


# ---------------------------------------------------------------------------
# Drop zone widget (used in Step 3)
# ---------------------------------------------------------------------------

class DropZone(QLabel):
    files_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setText(
            "<div style='font-size:38px; margin-bottom:8px;'>📄</div>"
            "<div style='font-size:15px; font-weight:600;'>"
            "Lohnabrechnungen hierher ziehen</div>"
            "<div style='font-size:12px; color:#7a88b8; margin-top:6px;'>"
            "PDF, JPG, PNG, GIF, WEBP — oder klicken zum Auswählen</div>"
        )
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(220)
        self._set_style(active=False)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)

    def _set_style(self, active: bool) -> None:
        border = COLORS['accent2'] if active else COLORS['border']
        bg = COLORS['bg_elevated'] if active else COLORS['bg_card']
        self.setStyleSheet(
            f"QLabel {{ border: 2px {'solid' if active else 'dashed'} {border}; "
            f"border-radius: 14px; background: {bg}; color: {COLORS['text']}; }}"
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_style(active=True)

    def dragLeaveEvent(self, event) -> None:
        self._set_style(active=False)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_style(active=False)
        paths = [
            Path(url.toLocalFile()) for url in event.mimeData().urls()
            if Path(url.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        if paths:
            self.files_dropped.emit(paths)

    def mousePressEvent(self, event) -> None:
        exts = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        files, _ = QFileDialog.getOpenFileNames(
            self, "Dokumente auswählen", "",
            f"Dokumente ({exts});;PDF (*.pdf);;Bilder (*.jpg *.jpeg *.png *.gif *.webp)",
        )
        if files:
            self.files_dropped.emit([Path(f) for f in files])


# ---------------------------------------------------------------------------
# Wizard step base + concrete steps
# ---------------------------------------------------------------------------

class StepBase(QWidget):
    """Each wizard slide. on_enter is called when the step is shown."""
    def __init__(self, parent: "MainWindow") -> None:
        super().__init__(parent)
        self.win = parent
        self.state = parent.state

    def on_enter(self) -> None:
        pass


def _step_header(title: str, hint: str) -> QVBoxLayout:
    box = QVBoxLayout()
    t = QLabel(title); t.setObjectName("stepTitle")
    h = QLabel(hint); h.setObjectName("stepHint"); h.setWordWrap(True)
    box.addWidget(t); box.addWidget(h)
    box.addSpacing(8)
    return box


def _file_picker_row(line_edit: QLineEdit, btn_label: str, on_clear=None) -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(line_edit, stretch=1)
    btn = QPushButton(btn_label)
    btn.setProperty("picker", True)
    row.addWidget(btn)
    if on_clear is not None:
        clear = QPushButton("✕")
        clear.setMaximumWidth(36)
        clear.clicked.connect(on_clear)
        row.addWidget(clear)
    return row, btn


# ---- Step 1 ---------------------------------------------------------------

class Step1_What(StepBase):
    def __init__(self, parent: "MainWindow") -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.addLayout(_step_header(
            "Schritt 1 — Was soll erstellt werden?",
            "Wähle aus, welche Dateien für diesen Insolvenzfall erzeugt werden sollen. "
            "Du kannst alles oder nur Teile auswählen.",
        ))

        card = QFrame(); card.setObjectName("card")
        cl = QVBoxLayout(card); cl.setContentsMargins(20, 16, 20, 16); cl.setSpacing(4)
        self.cb_excel = QCheckBox("📊  Excel-Liste (Arbeitnehmer-Stammdaten)")
        self.cb_ib    = QCheckBox("📋  IB-Bescheinigungen (1 PDF pro Mitarbeiter)")
        self.cb_antrag= QCheckBox("📝  Anträge auf Insolvenzgeld (1 PDF pro Mitarbeiter)")
        for cb, attr in [(self.cb_excel, "do_excel"), (self.cb_ib, "do_ib"), (self.cb_antrag, "do_antrag")]:
            cb.setChecked(getattr(self.state, attr))
            cl.addWidget(cb)
        outer.addWidget(card)
        outer.addStretch(1)

        nav = QHBoxLayout()
        nav.addStretch(1)
        nxt = QPushButton("Weiter →"); nxt.setObjectName("primary")
        nxt.clicked.connect(self._next)
        nav.addWidget(nxt)
        outer.addLayout(nav)

    def on_enter(self) -> None:
        # Defensive sync: state may have been reset by "Neuer Durchlauf"
        self.cb_excel.setChecked(self.state.do_excel)
        self.cb_ib.setChecked(self.state.do_ib)
        self.cb_antrag.setChecked(self.state.do_antrag)

    def _next(self) -> None:
        self.state.do_excel = self.cb_excel.isChecked()
        self.state.do_ib    = self.cb_ib.isChecked()
        self.state.do_antrag= self.cb_antrag.isChecked()
        if not (self.state.do_excel or self.state.do_ib or self.state.do_antrag):
            QMessageBox.warning(self, "Auswahl fehlt", "Bitte mindestens eine Option ankreuzen.")
            return
        self.win.go_next()


# ---- Step 2 ---------------------------------------------------------------

class Step2_Templates(StepBase):
    def __init__(self, parent: "MainWindow") -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self); outer.setSpacing(12)
        outer.addLayout(_step_header(
            "Schritt 2 — Vorlagen & Speicherort",
            "Wähle die Excel-Vorlage, den Ausgabe-Ordner und optional vorausgefüllte "
            "PDF-Vorlagen ('Schema F'), aus denen die ja/nein-Antworten und Fall-Info "
            "in jede neue Bescheinigung übernommen werden.",
        ))

        # --- Output folder ---
        out_card = QFrame(); out_card.setObjectName("card")
        ol = QVBoxLayout(out_card); ol.setContentsMargins(16, 12, 16, 12); ol.setSpacing(6)
        ol.addWidget(self._mklabel("AUSGABE-ORDNER"))
        ol.addWidget(self._mksub("Hier landen Excel + alle PDFs (mit Zeitstempel im Dateinamen)."))
        self.out_edit = QLineEdit(); self.out_edit.setReadOnly(True)
        self.out_edit.setPlaceholderText("Kein Ordner ausgewählt")
        out_row, out_btn = _file_picker_row(self.out_edit, "Auswählen…")
        out_btn.clicked.connect(self._pick_out)
        ol.addLayout(out_row)
        outer.addWidget(out_card)

        # --- Excel template ---
        self.xl_card = QFrame(); self.xl_card.setObjectName("card")
        xl = QVBoxLayout(self.xl_card); xl.setContentsMargins(16, 12, 16, 12); xl.setSpacing(6)
        xl.addWidget(self._mklabel("EXCEL-VORLAGE"))
        xl.addWidget(self._mksub("Die leere Arbeitnehmer-Liste, die befüllt werden soll."))
        self.xl_edit = QLineEdit(); self.xl_edit.setReadOnly(True)
        self.xl_edit.setPlaceholderText("Keine Vorlage ausgewählt")
        xl_row, xl_btn = _file_picker_row(self.xl_edit, "Auswählen…", on_clear=self._clear_xl)
        xl_btn.clicked.connect(self._pick_xl)
        xl.addLayout(xl_row)
        outer.addWidget(self.xl_card)

        # --- IB Schema-F ---
        self.ib_card = QFrame(); self.ib_card.setObjectName("card")
        ib = QVBoxLayout(self.ib_card); ib.setContentsMargins(16, 12, 16, 12); ib.setSpacing(6)
        ib.addWidget(self._mklabel("IB-VORLAGE (OPTIONAL)"))
        ib.addWidget(self._mksub(
            "Eine bereits ausgefüllte IB-Bescheinigung mit den ja/nein-Antworten und "
            "Fall-Daten für diesen Insolvenzfall. Wird auf jede neue IB übertragen."
        ))
        self.ib_edit = QLineEdit(); self.ib_edit.setReadOnly(True)
        self.ib_edit.setPlaceholderText("Optional — ohne werden alle IB-Felder leer gelassen")
        ib_row, ib_btn = _file_picker_row(self.ib_edit, "Auswählen…", on_clear=self._clear_ib)
        ib_btn.clicked.connect(self._pick_ib)
        ib.addLayout(ib_row)
        outer.addWidget(self.ib_card)

        # --- Antrag Schema-F ---
        self.an_card = QFrame(); self.an_card.setObjectName("card")
        an = QVBoxLayout(self.an_card); an.setContentsMargins(16, 12, 16, 12); an.setSpacing(6)
        an.addWidget(self._mklabel("ANTRAG-VORLAGE (OPTIONAL)"))
        an.addWidget(self._mksub(
            "Ein bereits ausgefüllter Antrag mit den ja/nein-Antworten und Fall-Daten."
        ))
        self.an_edit = QLineEdit(); self.an_edit.setReadOnly(True)
        self.an_edit.setPlaceholderText("Optional — ohne werden alle Antrag-Felder leer gelassen")
        an_row, an_btn = _file_picker_row(self.an_edit, "Auswählen…", on_clear=self._clear_an)
        an_btn.clicked.connect(self._pick_an)
        an.addLayout(an_row)
        outer.addWidget(self.an_card)

        outer.addStretch(1)

        nav = QHBoxLayout()
        back = QPushButton("← Zurück"); back.clicked.connect(self.win.go_back)
        nav.addWidget(back); nav.addStretch(1)
        nxt = QPushButton("Weiter →"); nxt.setObjectName("primary")
        nxt.clicked.connect(self._next)
        nav.addWidget(nxt)
        outer.addLayout(nav)

    def _mklabel(self, t: str) -> QLabel:
        l = QLabel(t); l.setObjectName("sectionLabel"); return l
    def _mksub(self, t: str) -> QLabel:
        l = QLabel(t); l.setObjectName("stepHint"); l.setWordWrap(True); return l

    def on_enter(self) -> None:
        # Show only the cards relevant to chosen outputs
        self.xl_card.setVisible(self.state.do_excel)
        self.ib_card.setVisible(self.state.do_ib)
        self.an_card.setVisible(self.state.do_antrag)
        # Restore previously chosen values
        if self.state.output_dir: self.out_edit.setText(str(self.state.output_dir))
        if self.state.excel_template: self.xl_edit.setText(str(self.state.excel_template))
        if self.state.ib_schema_f: self.ib_edit.setText(str(self.state.ib_schema_f))
        if self.state.antrag_schema_f: self.an_edit.setText(str(self.state.antrag_schema_f))

    def _pick_out(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Ausgabe-Ordner wählen", str(Path.home() / "Desktop"))
        if d:
            self.state.output_dir = Path(d); self.out_edit.setText(d)

    def _pick_xl(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Excel-Vorlage", "", "Excel (*.xlsx)")
        if f: self.state.excel_template = Path(f); self.xl_edit.setText(f)
    def _clear_xl(self) -> None: self.state.excel_template = None; self.xl_edit.clear()

    def _pick_ib(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "IB Schema-F", "", "PDF (*.pdf)")
        if f: self.state.ib_schema_f = Path(f); self.ib_edit.setText(f)
    def _clear_ib(self) -> None: self.state.ib_schema_f = None; self.ib_edit.clear()

    def _pick_an(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Antrag Schema-F", "", "PDF (*.pdf)")
        if f: self.state.antrag_schema_f = Path(f); self.an_edit.setText(f)
    def _clear_an(self) -> None: self.state.antrag_schema_f = None; self.an_edit.clear()

    def _next(self) -> None:
        if not self.state.output_dir:
            QMessageBox.warning(self, "Speicherort fehlt", "Bitte einen Ausgabe-Ordner auswählen.")
            return
        if self.state.do_excel and not self.state.excel_template:
            QMessageBox.warning(self, "Excel-Vorlage fehlt", "Du hast Excel ausgewählt — bitte eine Vorlage angeben.")
            return
        self.win.go_next()


# ---- Step 3 ---------------------------------------------------------------

class Step3_Files(StepBase):
    def __init__(self, parent: "MainWindow") -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self); outer.setSpacing(12)
        outer.addLayout(_step_header(
            "Schritt 3 — Lohnabrechnungen einlesen",
            "Zieh alle Lohnabrechnungen für diesen Insolvenzfall hier rein. "
            "Eine PDF mit mehreren Seiten oder mehrere einzelne Dateien — beides geht.",
        ))

        self.drop = DropZone()
        self.drop.files_dropped.connect(self._on_files)
        outer.addWidget(self.drop)

        self.file_label = QLabel(""); self.file_label.setObjectName("pdfLabel")
        self.file_label.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.file_label)

        outer.addStretch(1)

        nav = QHBoxLayout()
        back = QPushButton("← Zurück"); back.clicked.connect(self.win.go_back)
        nav.addWidget(back); nav.addStretch(1)
        self.go_btn = QPushButton("🚀  Los geht's"); self.go_btn.setObjectName("primary")
        self.go_btn.clicked.connect(self._start)
        nav.addWidget(self.go_btn)
        outer.addLayout(nav)

    def on_enter(self) -> None:
        self._refresh_label()

    def _on_files(self, paths: list[Path]) -> None:
        self.state.input_files = paths
        self._refresh_label()

    def _refresh_label(self) -> None:
        n = len(self.state.input_files)
        if n == 0:
            self.file_label.setText("Noch keine Datei ausgewählt.")
        elif n == 1:
            self.file_label.setText(f"📄  {self.state.input_files[0].name}")
        else:
            self.file_label.setText(f"📄  {n} Dateien ausgewählt")

    def _start(self) -> None:
        if not self.state.input_files:
            QMessageBox.warning(self, "Keine Dokumente", "Bitte zuerst Dokumente reinziehen.")
            return
        self.win.start_extraction()


# ---- Step 4 ---------------------------------------------------------------

class Step4_Loading(StepBase):
    def __init__(self, parent: "MainWindow") -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self); outer.setSpacing(14)
        outer.addLayout(_step_header(
            "Schritt 4 — Bin am Werk…",
            "Das kann ein paar Minuten dauern, je nach Anzahl der Seiten. "
            "Du kannst dem Fortschritt unten zuschauen oder eine Pause machen.",
        ))

        self.spinner = QLabel("✨")
        self.spinner.setAlignment(Qt.AlignCenter)
        self.spinner.setStyleSheet("font-size: 48px; padding: 16px 0;")
        outer.addWidget(self.spinner)

        self.loading_msg = QLabel("")
        self.loading_msg.setObjectName("loadingMsg")
        self.loading_msg.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.loading_msg)

        self.progress = QProgressBar()
        outer.addWidget(self.progress)

        log_label = QLabel("PROTOKOLL"); log_label.setObjectName("sectionLabel")
        outer.addWidget(log_label)
        self.log_box = QPlainTextEdit(); self.log_box.setReadOnly(True)
        outer.addWidget(self.log_box, stretch=1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate_msg)
        self._used: list[str] = []

    def on_enter(self) -> None:
        self.log_box.clear()
        self.progress.setValue(0)
        self.progress.setFormat("Starte…")
        self._used = []
        self._rotate_msg()
        self.timer.start(3500)

    def stop(self) -> None:
        self.timer.stop()

    def append_log(self, msg: str) -> None:
        self.log_box.appendPlainText(msg)

    def set_progress(self, done: int, total: int, fmt: str) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.progress.setFormat(fmt)

    def _rotate_msg(self) -> None:
        avail = [m for m in LOADING_MESSAGES if m not in self._used]
        if not avail:
            self._used = []; avail = LOADING_MESSAGES[:]
        msg = random.choice(avail)
        self._used.append(msg)
        self.loading_msg.setText(msg)


# ---- Step 5 ---------------------------------------------------------------

class Step5_Done(StepBase):
    def __init__(self, parent: "MainWindow") -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self); outer.setSpacing(12)
        outer.addLayout(_step_header(
            "Fertig! 🎉",
            "Alles erledigt. Hier eine Übersicht, was geschafft wurde.",
        ))

        self.results_card = QFrame(); self.results_card.setObjectName("card")
        self.results_layout = QVBoxLayout(self.results_card)
        self.results_layout.setContentsMargins(20, 16, 20, 16)
        self.results_layout.setSpacing(8)
        outer.addWidget(self.results_card)

        outer.addStretch(1)

        nav = QHBoxLayout()
        self.open_folder_btn = QPushButton("📂  Ergebnis-Ordner öffnen")
        self.open_folder_btn.clicked.connect(self._open_folder)
        nav.addWidget(self.open_folder_btn)
        nav.addStretch(1)
        new_btn = QPushButton("🔄  Neuer Durchlauf"); new_btn.setObjectName("primary")
        new_btn.clicked.connect(self.win.reset_for_new_run)
        nav.addWidget(new_btn)
        outer.addLayout(nav)

    def on_enter(self) -> None:
        # Clear previous results
        while self.results_layout.count():
            it = self.results_layout.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        s = self.state
        n = len(s.last_records)
        if n == 0:
            self._add_warn(
                "Keine Mitarbeiter erkannt — schau ins Protokoll auf der vorigen Seite "
                "(z.B. Schritt zurück), ob die Extraktion gescheitert ist."
            )
        else:
            self._add_check(f"{n} Mitarbeiter aus den Lohnabrechnungen extrahiert")
        if s.last_uncertain:
            self._add_warn(
                f"{s.last_uncertain} davon mit unsicheren Feldern (im Excel orange markiert)"
            )

        if s.last_excel_path:
            self._add_check(f"Excel-Liste erstellt: {s.last_excel_path.name}")
        if s.last_ib_dir:
            note = " mit Schema-F-Übernahme" if s.ib_schema_f else ""
            self._add_check(f"{s.last_ib_count} IB-Bescheinigungen erstellt{note}")
        if s.last_antrag_dir:
            note = " mit Schema-F-Übernahme" if s.antrag_schema_f else ""
            self._add_check(f"{s.last_antrag_count} Anträge erstellt{note}")

        self.open_folder_btn.setEnabled(s.output_dir is not None)

    def _add_check(self, text: str) -> None:
        l = QLabel(f"<span style='color:{COLORS['success']}; font-size:16px;'>✓</span>  {text}")
        l.setObjectName("bigCheck")
        l.setWordWrap(True)
        self.results_layout.addWidget(l)

    def _add_warn(self, text: str) -> None:
        l = QLabel(f"<span style='color:{COLORS['warning']}; font-size:16px;'>⚠</span>  {text}")
        l.setObjectName("bigCheck")
        l.setWordWrap(True)
        self.results_layout.addWidget(l)

    def _open_folder(self) -> None:
        if self.state.output_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.state.output_dir)))


# ---------------------------------------------------------------------------
# Main window with stacked wizard
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Lohnbüro-Tool")
        self.resize(820, 760)
        self.setStyleSheet(STYLESHEET)

        self.state = WizardState()
        self.worker: ExtractionWorker | None = None
        self._pending_update: UpdateInfo | None = None

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)

        # --- Header ---
        header = QFrame(); header.setObjectName("header")
        hl = QVBoxLayout(header); hl.setContentsMargins(20, 14, 20, 14)
        title_row = QHBoxLayout()
        title = QLabel("✨ Lohnbüro-Tool"); title.setObjectName("title")
        title_row.addWidget(title); title_row.addStretch(1)
        api_btn = QPushButton("🔑 API-Key"); api_btn.clicked.connect(self.set_api_key)
        title_row.addWidget(api_btn)
        ver = QLabel(f"v{__version__}"); ver.setObjectName("subtitle")
        title_row.addWidget(ver)
        hl.addLayout(title_row)
        self.step_indicator = QLabel(""); self.step_indicator.setObjectName("stepIndicator")
        hl.addWidget(self.step_indicator)
        outer.addWidget(header)

        # --- Update banner ---
        self.update_banner = QFrame(); self.update_banner.setObjectName("updateBanner")
        ub = QHBoxLayout(self.update_banner); ub.setContentsMargins(16, 10, 16, 10)
        self.update_label = QLabel("")
        self.update_label.setStyleSheet("color: #1a1b26; font-weight: 600;")
        ub.addWidget(self.update_label, stretch=1)
        self.update_btn = QPushButton("Jetzt installieren"); self.update_btn.setObjectName("updateBtn")
        self.update_btn.clicked.connect(self.install_update)
        ub.addWidget(self.update_btn)
        self.update_banner.setVisible(False)
        outer.addWidget(self.update_banner)

        # --- Wizard stack ---
        self.stack = QStackedWidget()
        self.steps = [
            Step1_What(self),
            Step2_Templates(self),
            Step3_Files(self),
            Step4_Loading(self),
            Step5_Done(self),
        ]
        for step in self.steps:
            self.stack.addWidget(step)
        outer.addWidget(self.stack, stretch=1)

        self.setCentralWidget(central)
        self._goto(0)

        # Background update check
        self._update_worker = UpdateCheckWorker(self)
        self._update_worker.found.connect(self._show_update_banner)
        self._update_worker.start()

    # --- Navigation ---

    def _goto(self, idx: int) -> None:
        idx = max(0, min(idx, len(self.steps) - 1))
        self.stack.setCurrentIndex(idx)
        names = ["1. Auswahl", "2. Vorlagen", "3. Dokumente", "4. Verarbeitung", "5. Fertig"]
        self.step_indicator.setText(" → ".join(
            f"<b style='color:{COLORS['accent']}'>{n}</b>" if i == idx else n
            for i, n in enumerate(names)
        ))
        self.steps[idx].on_enter()

    def go_next(self) -> None:
        self._goto(self.stack.currentIndex() + 1)

    def go_back(self) -> None:
        self._goto(self.stack.currentIndex() - 1)

    def reset_for_new_run(self) -> None:
        # Keep templates + output dir for convenience; reset inputs + results
        self.state.input_files = []
        self.state.last_records = []
        self.state.last_excel_path = None
        self.state.last_uncertain = 0
        self.state.last_ib_dir = None
        self.state.last_ib_count = 0
        self.state.last_antrag_dir = None
        self.state.last_antrag_count = 0
        self._goto(0)

    # --- API key ---

    def set_api_key(self) -> None:
        current = get_api_key() or ""
        key, ok = QInputDialog.getText(
            self, "Anthropic API-Key", "API-Key (sk-ant-…):",
            QLineEdit.Password, current,
        )
        if ok and key.strip():
            store_api_key(key.strip())
            QMessageBox.information(self, "Gespeichert", "API-Key wurde gespeichert.")

    # --- Update flow ---

    def _show_update_banner(self, info: UpdateInfo) -> None:
        self._pending_update = info
        if is_frozen_exe():
            self.update_label.setText(
                f"🎉 Update verfügbar: Version {info.latest_version} "
                f"(du nutzt {__version__})"
            )
            self.update_btn.setVisible(True)
        else:
            self.update_label.setText(
                f"🎉 Neue Version {info.latest_version} verfügbar "
                f"(Dev-Modus — Update via git pull)"
            )
            self.update_btn.setVisible(False)
        self.update_banner.setVisible(True)

    def install_update(self) -> None:
        if not self._pending_update: return
        info = self._pending_update
        reply = QMessageBox.question(
            self, "Update installieren",
            f"Version {info.latest_version} wird heruntergeladen und installiert.\n"
            f"Das Programm startet danach automatisch neu.\n\nFortfahren?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes: return
        self.update_label.setText(f"⬇️  Lade Version {info.latest_version}…")
        self.update_btn.setEnabled(False)
        QApplication.processEvents()
        try:
            download_and_apply_update(info)
        except Exception as exc:
            self.update_btn.setEnabled(True)
            QMessageBox.critical(self, "Update fehlgeschlagen", str(exc))

    # --- Extraction ---

    def start_extraction(self) -> None:
        api_key = get_api_key()
        if not api_key:
            QMessageBox.warning(
                self, "API-Key fehlt",
                "Bitte zuerst oben rechts den API-Key setzen.",
            )
            return

        # Quick ping to fail fast on bad key
        ok, msg = verify_api_key(api_key)
        if not ok:
            QMessageBox.critical(
                self, "API-Key Problem",
                f"{msg}\n\nBitte über den Button 'API-Key' oben einen gültigen Key setzen.",
            )
            return

        self._goto(3)  # loading slide
        loading = self.steps[3]
        assert isinstance(loading, Step4_Loading)
        loading.append_log(f"✓ API-Key ok (Modell: {os.environ.get('ANTHROPIC_MODEL', 'claude-opus-4-7')})")

        model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")
        self.worker = ExtractionWorker(self.state, api_key, model)
        self.worker.progress.connect(loading.set_progress)
        self.worker.log.connect(loading.append_log)
        self.worker.finished_ok.connect(self._on_extraction_done)
        self.worker.failed.connect(self._on_extraction_failed)
        self.worker.start()

    def _on_extraction_done(
        self, excel_path, records, num_uncertain,
        ib_dir, ib_count, antrag_dir, antrag_count,
    ) -> None:
        loading = self.steps[3]
        if isinstance(loading, Step4_Loading): loading.stop()

        self.state.last_records = records
        self.state.last_excel_path = excel_path
        self.state.last_uncertain = num_uncertain
        self.state.last_ib_dir = ib_dir
        self.state.last_ib_count = ib_count
        self.state.last_antrag_dir = antrag_dir
        self.state.last_antrag_count = antrag_count
        self._goto(4)

    def _on_extraction_failed(self, error: str) -> None:
        loading = self.steps[3]
        if isinstance(loading, Step4_Loading):
            loading.stop()
            loading.append_log(f"\n❌ Fehler:\n{error}")
        QMessageBox.critical(self, "Fehler", f"Extraktion fehlgeschlagen:\n\n{error}")
        # Don't strand the user on the loading slide — go back to file selection
        # so they can adjust and retry without restarting the wizard.
        self._goto(2)


def main() -> None:
    app = QApplication(sys.argv)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
