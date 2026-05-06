# Deployment & Updates

So bringst du das Tool auf den Windows-Rechner deines Vaters und kannst von deinem Mac aus später Updates ausspielen.

---

## Einmalig: GitHub Repo aufsetzen

1. Auf <https://github.com/new> ein **privates** Repo anlegen, z.B. `Lohnbuero-Tool`.
2. Lokal im Projekt-Ordner:

   ```bash
   cd ~/Desktop/Lohnbuero-Tool
   git init
   git add .
   git commit -m "v0.1.0 — initial release"
   git branch -M main
   git remote add origin git@github.com:DEIN-USERNAME/Lohnbuero-Tool.git
   git push -u origin main
   ```

3. **`src/version.py` öffnen** und `GITHUB_REPO` setzen:

   ```python
   GITHUB_REPO = "DEIN-USERNAME/Lohnbuero-Tool"
   ```

   Commit + Push:

   ```bash
   git commit -am "configure auto-update repo"
   git push
   ```

---

## Erstes Release bauen (für die Installation auf Vaters Rechner)

1. Tag erzeugen + pushen:

   ```bash
   git tag v0.1.0
   git push --tags
   ```

2. GitHub Actions baut automatisch die Windows-EXE und hängt sie an den Release.
   Status: <https://github.com/DEIN-USERNAME/Lohnbuero-Tool/actions>

3. Wenn der Build grün ist (~3 Min): auf <https://github.com/DEIN-USERNAME/Lohnbuero-Tool/releases>
   den Release `v0.1.0` öffnen → `Lohnbuero-Tool.exe` herunterladen.

---

## Installation auf Vaters Windows-Rechner

1. **Ordner anlegen**, z.B. `C:\Lohnbuero-Tool\`
   Wichtig: **NICHT** in `C:\Program Files\` legen — dann darf das Auto-Update sich
   nicht selbst überschreiben (Admin-Rechte). Ein normaler Benutzerordner ist ideal.

2. Die `Lohnbuero-Tool.exe` in den Ordner kopieren.

3. **Verknüpfung auf den Desktop:** Rechtsklick auf die EXE → Senden an → Desktop.

4. Doppelklick → das Tool startet (beim ersten Start fragt Windows evtl. ob du
   einer "unbekannten App" vertraust → "Weitere Informationen" → "Trotzdem ausführen").

5. **API-Key eintragen:** Button "🔑 API-Key" → Anthropic-Key reinkopieren →
   wird in der Windows-Registry gespeichert (überlebt Updates).

6. **Excel-Vorlage** auf dem Rechner ablegen, z.B. `C:\Lohnbuero-Tool\Vorlage.xlsx` —
   dein Vater wählt sie pro Insolvenzfall im Tool aus.

---

## Updates ausspielen — komplett aus dem Mac heraus

Workflow für jede neue Version:

1. **Code anpassen** (Bugs fixen, Features ergänzen).

2. **Versionsnummer hochzählen** in `src/version.py`:

   ```python
   __version__ = "0.2.0"   # vorher: "0.1.0"
   ```

3. **Commit + Tag + Push**:

   ```bash
   git commit -am "v0.2.0 — IBAN-Erkennung verbessert"
   git tag v0.2.0
   git push && git push --tags
   ```

4. GitHub Actions baut die neue `Lohnbuero-Tool.exe` und attached sie
   automatisch an den Release `v0.2.0`. Du musst nichts weiter tun.

5. **Auf Vaters Rechner:** Beim nächsten Start des Tools erscheint oben
   ein oranger Banner: *"🎉 Update verfügbar: Version 0.2.0"* → Button
   *"Jetzt installieren"* → das Tool lädt die neue EXE, ersetzt sich selbst,
   startet neu. Komplett automatisch, ohne Eingriff.

   Oder dein Vater wartet einfach — die nächste manuelle Aktion zeigt's auch.

> 💡 **Tipp:** Versionsnummern nach [SemVer](https://semver.org/lang/de/) wählen:
> Bugfix → Patch (`0.1.1`), neues Feature → Minor (`0.2.0`), Breaking → Major (`1.0.0`).

---

## Troubleshooting

**Update-Banner erscheint nicht obwohl neue Version draußen ist?**
- `GITHUB_REPO` in `src/version.py` korrekt gesetzt?
- Bei privatem Repo: GitHub API ist anonym aufrufbar bei *public*. Bei *private* Repo
  müsste man einen GitHub-Token einbauen (sag Bescheid, baue ich nach).
- Repo öffentlich machen ist die einfachste Lösung — oder zumindest die Releases
  öffentlich zugänglich (Settings → Actions → Workflow permissions).

**Update läuft, aber EXE wird nicht ersetzt?**
- Liegt die EXE in `C:\Program Files\` o.ä. ohne Schreibrechte? Dann nach
  `C:\Lohnbuero-Tool\` oder Desktop verschieben.
- Antivirus blockiert das Batch-Skript? Whitelist `_lohnbuero_update.bat`.

**Privates Repo statt öffentliches:**
Falls du das Repo privat halten willst, müssen wir einen GitHub Personal Access
Token einbauen. Sag Bescheid, dann erweitere ich `updater.py` entsprechend.
