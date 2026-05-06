from __future__ import annotations

import os
import random
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtCore import Qt, QThread, QTimer, Signal, QSettings, QUrl
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent, QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QPlainTextEdit, QVBoxLayout, QWidget,
)

from src.aggregator import aggregate_pages
from src.excel_writer import write_records
from src.extractor import extract_pages
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

QLabel {{
    color: {COLORS['text']};
    background: transparent;
}}

QLabel#title {{
    font-size: 22px;
    font-weight: 700;
    color: {COLORS['text']};
    padding: 0;
}}

QLabel#subtitle {{
    font-size: 12px;
    color: {COLORS['text_dim']};
}}

QLabel#sectionLabel {{
    font-size: 11px;
    font-weight: 600;
    color: {COLORS['text_dim']};
    text-transform: uppercase;
    letter-spacing: 1px;
}}

QLabel#pdfLabel {{
    font-size: 13px;
    color: {COLORS['cyan']};
    padding: 4px 0;
}}

QLabel#loadingMsg {{
    font-size: 14px;
    color: {COLORS['accent2']};
    font-style: italic;
    padding: 6px 0;
}}

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

QPushButton:pressed {{
    background-color: {COLORS['bg']};
}}

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

QPushButton#primary:hover {{
    background-color: {COLORS['cyan']};
}}

QPushButton#primary:disabled {{
    background-color: {COLORS['border']};
    color: {COLORS['text_dim']};
}}

QLineEdit {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {COLORS['accent']};
}}

QLineEdit:focus {{
    border-color: {COLORS['accent']};
}}

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
    selection-background-color: {COLORS['accent']};
}}

QCheckBox {{
    color: {COLORS['text']};
    spacing: 10px;
    padding: 4px 0;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {COLORS['border']};
    border-radius: 4px;
    background: {COLORS['bg']};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS['accent']};
}}

QCheckBox::indicator:checked {{
    background: {COLORS['accent']};
    border-color: {COLORS['accent']};
    image: none;
}}

QMessageBox {{
    background-color: {COLORS['bg_elevated']};
}}

QFrame#updateBanner {{
    background-color: {COLORS['warning']};
    border-radius: 10px;
}}

QPushButton#updateBtn {{
    background-color: {COLORS['bg']};
    color: {COLORS['warning']};
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 700;
}}

QPushButton#updateBtn:hover {{
    background-color: {COLORS['bg_card']};
}}
"""


def get_api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key.strip()
    settings = QSettings(ORG_NAME, APP_NAME)
    stored = settings.value("api_key")
    return stored.strip() if stored else None


def store_api_key(key: str) -> None:
    QSettings(ORG_NAME, APP_NAME).setValue("api_key", key.strip())


def verify_api_key(api_key: str) -> tuple[bool, str]:
    """Make a tiny API call to confirm the key works. Returns (ok, message)."""
    import anthropic
    try:
        client = anthropic.Anthropic(api_key=api_key)
        client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, "ok"
    except anthropic.AuthenticationError as exc:
        return False, f"API-Key ungültig: {exc}"
    except Exception as exc:
        return False, f"Verbindung fehlgeschlagen: {type(exc).__name__}: {exc}"


class DropZone(QLabel):
    """Big label that accepts dragged PDF files."""
    files_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setText(
            "<div style='font-size:32px; margin-bottom:8px;'>📄</div>"
            "<div style='font-size:15px; font-weight:600;'>"
            "Dokumente hierher ziehen</div>"
            "<div style='font-size:12px; color:#7a88b8; margin-top:4px;'>"
            "PDF, JPG, PNG, GIF, WEBP — oder klicken zum Auswählen</div>"
        )
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(180)
        self._set_style(active=False)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)

    def _set_style(self, active: bool) -> None:
        if active:
            self.setStyleSheet(
                f"QLabel {{ border: 2px solid {COLORS['accent2']}; "
                f"border-radius: 14px; background: {COLORS['bg_elevated']}; "
                f"color: {COLORS['text']}; }}"
            )
        else:
            self.setStyleSheet(
                f"QLabel {{ border: 2px dashed {COLORS['border']}; "
                f"border-radius: 14px; background: {COLORS['bg_card']}; "
                f"color: {COLORS['text']}; }}"
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
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
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


class UpdateCheckWorker(QThread):
    """Background thread that checks GitHub Releases without blocking the UI."""
    found = Signal(object)  # UpdateInfo

    def run(self) -> None:
        info = check_for_update()
        if info is not None:
            self.found.emit(info)


class ExtractionWorker(QThread):
    progress = Signal(int, int, str)
    log = Signal(str)
    # output_excel, records, num_uncertain, ib_dir|None, ib_count, antrag_dir|None, antrag_count
    finished_ok = Signal(Path, list, int, object, int, object, int)
    failed = Signal(str)

    def __init__(
        self,
        pdf_paths: list[Path],
        template_path: Path,
        output_path: Path,
        api_key: str,
        model: str,
        do_ib: bool,
        do_antrag: bool,
    ) -> None:
        super().__init__()
        self.pdf_paths = pdf_paths
        self.template_path = template_path
        self.output_path = output_path
        self.api_key = api_key
        self.model = model
        self.do_ib = do_ib
        self.do_antrag = do_antrag

    def run(self) -> None:
        try:
            self.log.emit(f"Lade {len(self.pdf_paths)} Datei(en)…")
            all_pages = load_pages(self.pdf_paths)
            for path in self.pdf_paths:
                if path.suffix.lower() == ".pdf":
                    from pypdf import PdfReader
                    n = len(PdfReader(str(path)).pages)
                    self.log.emit(f"  {path.name}: {n} Seite(n)")
                else:
                    self.log.emit(f"  {path.name}: 1 Bild")

            total = len(all_pages)
            self.log.emit(f"Starte Extraktion ({total} Seiten, je 2 API-Aufrufe = {total*2} Calls)…")

            def on_progress(done: int, _total: int) -> None:
                self.progress.emit(done, total, f"{done} / {total} Seiten")

            page_results = extract_pages(
                all_pages,
                api_key=self.api_key,
                model=self.model,
                max_workers=5,
                progress_cb=on_progress,
            )

            errors = [p for p in page_results if p.error]
            for p in errors:
                self.log.emit(f"  ⚠ Seite {p.page_number}: {p.error}")

            self.log.emit("Aggregiere Mitarbeiter…")
            records = aggregate_pages(page_results)
            num_uncertain = sum(1 for r in records if r.uncertain_fields)
            self.log.emit(f"  {len(records)} Mitarbeiter gefunden, {num_uncertain} mit unsicheren Feldern")

            self.log.emit(f"Schreibe Excel: {self.output_path.name}")
            write_records(self.template_path, self.output_path, records)

            ib_dir, ib_count = None, 0
            antrag_dir, antrag_count = None, 0

            if self.do_ib and records:
                ib_dir = self.output_path.parent / f"{self.output_path.stem}_IB"
                self.log.emit(f"Erstelle IB-Bescheinigungen → {ib_dir.name}/")
                paths = fill_ib_forms(records, ib_dir)
                ib_count = len(paths)

            if self.do_antrag and records:
                antrag_dir = self.output_path.parent / f"{self.output_path.stem}_Antrag"
                self.log.emit(f"Erstelle Anträge → {antrag_dir.name}/")
                paths = fill_antrag_forms(records, antrag_dir)
                antrag_count = len(paths)

            self.finished_ok.emit(
                self.output_path, records, num_uncertain,
                ib_dir, ib_count, antrag_dir, antrag_count,
            )
        except Exception:
            self.failed.emit(traceback.format_exc())


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Lohnbüro-Tool")
        self.resize(780, 720)
        self.setStyleSheet(STYLESHEET)

        self.pdf_paths: list[Path] = []
        self.template_path: Path | None = None
        self.worker: ExtractionWorker | None = None

        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self._rotate_loading_msg)
        self._used_messages: list[str] = []

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)

        # --- Header ---
        header = QFrame()
        header.setObjectName("header")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        title_row = QHBoxLayout()
        title = QLabel("✨ Lohnbüro-Tool")
        title.setObjectName("title")
        title_row.addWidget(title)
        title_row.addStretch(1)
        version_label = QLabel(f"v{__version__}")
        version_label.setObjectName("subtitle")
        title_row.addWidget(version_label)
        header_layout.addLayout(title_row)
        subtitle = QLabel("Stammdaten-Extraktion aus Lohnabrechnungen — powered by Claude AI")
        subtitle.setObjectName("subtitle")
        header_layout.addWidget(subtitle)
        outer.addWidget(header)

        # --- Update banner (hidden until a new version is found) ---
        self.update_banner = QFrame()
        self.update_banner.setObjectName("updateBanner")
        ub_layout = QHBoxLayout(self.update_banner)
        ub_layout.setContentsMargins(16, 10, 16, 10)
        self.update_label = QLabel("")
        self.update_label.setStyleSheet("color: #1a1b26; font-weight: 600;")
        ub_layout.addWidget(self.update_label, stretch=1)
        self.update_btn = QPushButton("Jetzt installieren")
        self.update_btn.setObjectName("updateBtn")
        self.update_btn.clicked.connect(self.install_update)
        ub_layout.addWidget(self.update_btn)
        self.update_banner.setVisible(False)
        outer.addWidget(self.update_banner)
        self._pending_update: UpdateInfo | None = None

        # --- Drop zone ---
        self.drop = DropZone()
        self.drop.files_dropped.connect(self.on_files_dropped)
        outer.addWidget(self.drop)

        self.pdf_label = QLabel("Noch keine Datei ausgewählt.")
        self.pdf_label.setObjectName("pdfLabel")
        self.pdf_label.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.pdf_label)

        # --- Template picker card ---
        tpl_card = QFrame()
        tpl_card.setObjectName("card")
        tpl_layout = QVBoxLayout(tpl_card)
        tpl_layout.setContentsMargins(16, 12, 16, 12)
        tpl_layout.setSpacing(8)
        tpl_label = QLabel("EXCEL-VORLAGE")
        tpl_label.setObjectName("sectionLabel")
        tpl_layout.addWidget(tpl_label)

        tpl_row = QHBoxLayout()
        self.tpl_edit = QLineEdit()
        self.tpl_edit.setReadOnly(True)
        self.tpl_edit.setPlaceholderText("Keine Vorlage ausgewählt")
        tpl_row.addWidget(self.tpl_edit, stretch=1)
        tpl_btn = QPushButton("Auswählen…")
        tpl_btn.clicked.connect(self.pick_template)
        tpl_row.addWidget(tpl_btn)
        tpl_layout.addLayout(tpl_row)
        outer.addWidget(tpl_card)

        # --- Action buttons ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.start_btn = QPushButton("🚀  Extraktion starten")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self.start_extraction)
        btn_row.addWidget(self.start_btn, stretch=1)
        self.api_btn = QPushButton("🔑  API-Key")
        self.api_btn.clicked.connect(self.set_api_key)
        btn_row.addWidget(self.api_btn)
        outer.addLayout(btn_row)

        # --- Optional outputs (checkboxes) ---
        opts_card = QFrame()
        opts_card.setObjectName("card")
        opts_layout = QVBoxLayout(opts_card)
        opts_layout.setContentsMargins(16, 12, 16, 12)
        opts_layout.setSpacing(8)
        opts_label = QLabel("ZUSÄTZLICH GENERIEREN")
        opts_label.setObjectName("sectionLabel")
        opts_layout.addWidget(opts_label)
        self.cb_ib = QCheckBox("📋  IB-Bescheinigungen vorbereiten (1 PDF pro Mitarbeiter)")
        self.cb_ib.setChecked(True)
        opts_layout.addWidget(self.cb_ib)
        self.cb_antrag = QCheckBox("📝  Anträge auf Insolvenzgeld vorbereiten (1 PDF pro Mitarbeiter)")
        self.cb_antrag.setChecked(True)
        opts_layout.addWidget(self.cb_antrag)
        outer.addWidget(opts_card)

        # --- Progress + loading message ---
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        outer.addWidget(self.progress)

        self.loading_msg = QLabel("")
        self.loading_msg.setObjectName("loadingMsg")
        self.loading_msg.setAlignment(Qt.AlignCenter)
        self.loading_msg.setVisible(False)
        outer.addWidget(self.loading_msg)

        # --- Log ---
        log_label = QLabel("PROTOKOLL")
        log_label.setObjectName("sectionLabel")
        outer.addWidget(log_label)
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        outer.addWidget(self.log_box, stretch=1)

        self.setCentralWidget(central)

        # Kick off update check in the background (silent on failure / no update).
        self._update_worker = UpdateCheckWorker(self)
        self._update_worker.found.connect(self._show_update_banner)
        self._update_worker.start()

    # --- Update flow ---

    def _show_update_banner(self, info: UpdateInfo) -> None:
        self._pending_update = info
        if is_frozen_exe():
            self.update_label.setText(
                f"🎉 Update verfügbar: Version {info.latest_version} (du nutzt {__version__})"
            )
            self.update_btn.setVisible(True)
        else:
            # Dev mode (running from source) — show info but no install button
            self.update_label.setText(
                f"🎉 Neue Version {info.latest_version} ist verfügbar (Dev-Modus — Update via git pull)"
            )
            self.update_btn.setVisible(False)
        self.update_banner.setVisible(True)

    def install_update(self) -> None:
        if not self._pending_update:
            return
        info = self._pending_update
        reply = QMessageBox.question(
            self, "Update installieren",
            f"Version {info.latest_version} wird heruntergeladen und installiert.\n"
            f"Das Programm startet danach automatisch neu.\n\nFortfahren?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.update_label.setText(f"⬇️  Lade Version {info.latest_version}…")
        self.update_btn.setEnabled(False)
        QApplication.processEvents()
        try:
            download_and_apply_update(info)
        except Exception as exc:
            self.update_btn.setEnabled(True)
            QMessageBox.critical(
                self, "Update fehlgeschlagen",
                f"Das Update konnte nicht installiert werden:\n\n{exc}",
            )

    # --- Loading message rotation ---

    def _rotate_loading_msg(self) -> None:
        available = [m for m in LOADING_MESSAGES if m not in self._used_messages]
        if not available:
            self._used_messages = []
            available = LOADING_MESSAGES[:]
        msg = random.choice(available)
        self._used_messages.append(msg)
        self.loading_msg.setText(msg)

    def _start_loading_animation(self) -> None:
        self.loading_msg.setVisible(True)
        self._used_messages = []
        self._rotate_loading_msg()
        self.loading_timer.start(3500)

    def _stop_loading_animation(self) -> None:
        self.loading_timer.stop()
        self.loading_msg.setVisible(False)

    # --- Slots ---

    def on_files_dropped(self, paths: list[Path]) -> None:
        self.pdf_paths = paths
        if len(paths) == 1:
            self.pdf_label.setText(f"📄  {paths[0].name}")
        else:
            self.pdf_label.setText(f"📄  {len(paths)} Dateien ausgewählt")

    def pick_template(self) -> None:
        f, _ = QFileDialog.getOpenFileName(
            self, "Excel-Vorlage auswählen", "", "Excel-Dateien (*.xlsx)"
        )
        if f:
            self.template_path = Path(f)
            self.tpl_edit.setText(f)

    def set_api_key(self) -> None:
        current = get_api_key() or ""
        key, ok = QInputDialog.getText(
            self, "Anthropic API-Key",
            "API-Key (sk-ant-…):",
            QLineEdit.Password,
            current,
        )
        if ok and key.strip():
            store_api_key(key.strip())
            self.log("🔑 API-Key gespeichert.")

    def log(self, msg: str) -> None:
        self.log_box.appendPlainText(msg)

    def start_extraction(self) -> None:
        if not self.pdf_paths:
            QMessageBox.warning(self, "Fehlende PDF", "Bitte zuerst PDF(s) auswählen.")
            return
        if not self.template_path:
            QMessageBox.warning(self, "Fehlende Vorlage", "Bitte Excel-Vorlage auswählen.")
            return
        api_key = get_api_key()
        if not api_key:
            QMessageBox.warning(self, "Fehlender API-Key", "Bitte API-Key über den Button setzen.")
            return

        self.log("Prüfe API-Key…")
        QApplication.processEvents()
        ok, msg = verify_api_key(api_key)
        if not ok:
            self.log(f"❌ {msg}")
            QMessageBox.critical(
                self, "API-Key Problem",
                f"{msg}\n\nBitte über den Button 'API-Key' einen gültigen Key setzen.\n"
                f"(Tipp: nur den Key kopieren, ohne Anführungszeichen oder Leerzeichen.)",
            )
            return
        self.log("✓ API-Key ok")

        suggested = self.pdf_paths[0].with_name(
            self.pdf_paths[0].stem + "_extrahiert.xlsx"
        )
        out, _ = QFileDialog.getSaveFileName(
            self, "Ergebnis speichern unter", str(suggested), "Excel-Dateien (*.xlsx)"
        )
        if not out:
            return
        output_path = Path(out)

        model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")
        self.start_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.log_box.clear()
        self._start_loading_animation()

        self.worker = ExtractionWorker(
            self.pdf_paths, self.template_path, output_path, api_key, model,
            do_ib=self.cb_ib.isChecked(),
            do_antrag=self.cb_antrag.isChecked(),
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.log.connect(self.log)
        self.worker.finished_ok.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_progress(self, done: int, total: int, msg: str) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.progress.setFormat(msg)

    def on_finished(
        self, output_path: Path, records: list, num_uncertain: int,
        ib_dir, ib_count: int, antrag_dir, antrag_count: int,
    ) -> None:
        self._stop_loading_animation()
        self.start_btn.setEnabled(True)
        num_records = len(records)
        lines = [
            f"✅ Fertig!",
            f"  • {num_records} Mitarbeiter ins Excel geschrieben "
            f"({num_uncertain} mit unsicheren Feldern, orange markiert)",
        ]
        if ib_dir:
            lines.append(f"  • {ib_count} IB-Bescheinigungen in {ib_dir.name}/")
        if antrag_dir:
            lines.append(f"  • {antrag_count} Anträge in {antrag_dir.name}/")
        self.log("\n" + "\n".join(lines))

        msg_lines = [f"{num_records} Mitarbeiter eingetragen."]
        if num_uncertain:
            msg_lines.append(f"{num_uncertain} mit unsicheren Feldern (orange — bitte prüfen).")
        if ib_dir:
            msg_lines.append(f"{ib_count} IB-Bescheinigungen erstellt.")
        if antrag_dir:
            msg_lines.append(f"{antrag_count} Anträge erstellt.")
        msg_lines.append("")
        msg_lines.append(f"Excel: {output_path.name}")
        msg_lines.append("")
        msg_lines.append("Ordner jetzt öffnen?")

        reply = QMessageBox.information(
            self, "Fertig",
            "\n".join(msg_lines),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            # Open the Excel parent folder so the user sees Excel + form folders together
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_path.parent)))

    def on_failed(self, error: str) -> None:
        self._stop_loading_animation()
        self.start_btn.setEnabled(True)
        self.log(f"\n❌ Fehler:\n{error}")
        QMessageBox.critical(self, "Fehler", f"Extraktion fehlgeschlagen:\n\n{error}")


def main() -> None:
    app = QApplication(sys.argv)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")  # consistent look across platforms
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
