# Einfacher Linux-Start im festen Programmordner

Für die bereits installierte, verwaltete Vier-Dienste-Installation gibt es einen
eigenen täglichen Starter. Der Programmordner bleibt
`~/Boerse/trading-workspace-app`; der Installationszustand liegt unter
`~/Boerse/trading-workspace-state/current-state`.

## Einmalig einrichten

Die geprüfte Datei `scripts/trading-workspace.sh` außerhalb des installierten
Git-Checkouts speichern, beispielsweise unter `~/Downloads/trading-workspace.sh`.
So kann der Starter auch für eine vorhandene v1.5.2-Installation eingerichtet
werden, ohne den versiegelten Programmstand zu ändern:

```bash
bash ~/Downloads/trading-workspace.sh install
```

Bei einer späteren Veröffentlichung, die den Starter bereits enthält, ist auch
`bash scripts/trading-workspace.sh install` aus deren Programmordner möglich.
Es werden nur `~/.local/bin/trading-workspace` und der Menüeintrag
`~/.local/share/applications/trading-workspace.desktop` installiert. Wiederholen
aktualisiert diese beiden Dateien. Die Installation benötigt `python3`, Bash und
Coreutils; für den Betrieb kommen Git, Docker/Compose und `flock` hinzu.
Als bisheriger Linux-Benutzer ausführen, ohne `sudo`.

## Täglich verwenden

Im Linux-Anwendungsmenü **Trading Workspace** auswählen. Alternativ:

```bash
~/.local/bin/trading-workspace
```

Der Starter prüft die gespeicherte Installation, startet nur angehaltene Container,
wartet auf deren Gesundheit und prüft die Backend-Bereitschaft. Danach öffnet er
bei vorhandener grafischer Sitzung und `xdg-open` die Oberfläche unter
<http://localhost:8080>. Sonst zeigt er die Adresse an. Bereits gesunde Dienste
bleiben unverändert. Ohne laufenden Docker-Dienst erscheint ein Hinweis.

Falls `~/.local/bin` im `PATH` steht, reicht der kurze Name:

| Befehl | Wirkung |
|---|---|
| `trading-workspace` | Starten und Oberfläche öffnen |
| `trading-workspace status` | Alle vier Dienste und Bereitschaft prüfen |
| `trading-workspace stop` | Anwendung und Renderer, danach Datenbank geordnet anhalten |
| `trading-workspace logs` | Letzte 100 Backend-Logzeilen lokal anzeigen |
| `trading-workspace --help` | Befehle anzeigen |

Status und Stop stehen außerdem als Aktionen des Menüeintrags zur Verfügung,
soweit die Desktopumgebung diese unterstützt. Status und Fehler bleiben im
Terminalfenster sichtbar, bis Enter gedrückt wird. Der Menüeintrag setzt keinen
Autostart bei der Anmeldung auf. Lokale Logs können private Details enthalten.

## Updates bleiben ein eigener Schritt

Nach Prüfung eines veröffentlichten Releases:

```text
trading-workspace update vX.Y.Z GEPRUEFTER_VOLLSTAENDIGER_COMMIT_SHA
```

Kein automatischer Wechsel auf `main` oder einen ungeprüften neuesten Tag.
Der Tag muss genau zum angegebenen Commit und dessen `VERSION` passen. Der
unveränderte, bereits qualifizierte Migrationshelfer und seine Validierung sind
über Inhaltsprüfsummen gebunden. Eine Änderung daran verlangt eine erneute
Prüfung des Updatewegs.

Das Update verwendet denselben Programmordner und legt Sicherungen unter
`trading-workspace-state/runs/` ab. Es archiviert den vorherigen Quellstand und
übernimmt die vorhandene private Konfiguration. Der Migrationshelfer baut,
sichert Datenbank und Zustimmungszustand und führt das Deployment aus. Es werden
keine weiteren dauerhaften Programmordner pro Version angelegt.

Ein fehlgeschlagener Versuch behält seinen `pending`-Marker und seine Diagnose.
Dann nicht blind erneut starten und keine Marker löschen. Der vorherige Zustand
bleibt nachvollziehbar; es erfolgt kein automatischer Rollback. Nach erfolgreichem
Update Provider-Kurse und Monitoring gesondert prüfen.

## Warum nicht einfach start-linux.sh?

`start-linux.sh` ist der bestehende Compose-Build-/Deployment-Einstieg. Ein nackter
Aufruf kennt die zusätzliche private `preserve.json` dieser verwalteten
Installation nicht. Selbst `--issuer-monitoring` ergänzt nicht deren vollständige
Dateireihenfolge. Die Schutzprüfung darf deshalb nicht entfernt werden.

Der tägliche Starter verwendet `current-state`, kontrolliert die versiegelten
Dateien, den Quellstand, die vorhandenen Images, die Datenbankidentität und die
Compose-Herkunft der drei Anwendungscontainer. Der unverändert beibehaltene
Datenbankcontainer darf seine ursprünglichen Compose-Labels behalten; seine
Identität muss mit dem versiegelten Zustand übereinstimmen. Der Migrationshelfer prüft
zusätzlich die effektive Konfiguration. Ein gemeinsames `update.lock` verhindert
überlappende Start-/Stop-/Update-Vorgänge, auch mit dem bisherigen Update-Skript.

Ein normaler Start baut keine Images, erzeugt keine Container oder Volumes, führt
keine Migration aus und ändert keine Provider-Einstellungen. Fehlende Container
oder abweichende Zustände erfordern eine gezielte Reparatur. Normale Hintergrund-
aufgaben laufen nach dem Start gemäß der bereits gespeicherten Konfiguration.

Die drei Entwicklungsskripte `check-backend.sh`, `check-frontend.sh` und
`run-e2e.sh` sind für den täglichen Programmstart nicht erforderlich.

## Prüfung

`tests/unit/backend/test_linux_launcher.py` führt den tatsächlichen Starter mit
temporären Git-Repositories, echten Prüfsummen und simuliertem Docker aus. Es
prüft unter anderem wiederholten Start, Stop/Start-Reihenfolge, Konfigurations-
abweichungen, fehlende Container, Sperren, Installation, gepinnte Updates und
abgebrochene Vorbereitung. Das ist kein Ersatz für einen Docker-Test.

`tests/deployment/legacy-issuer-migration.sh` prüft zusätzlich Stop/Start mit dem
echten Migrationshelfer, vier entbehrlichen CI-Containern, PostgreSQL-Daten und
Renderer-Zustand. Container-IDs, Images, Konfiguration und Prüfdatensätze müssen
erhalten bleiben. Es werden dabei keine externen Provider oder Telegram getestet.

Für einen abweichenden Basisordner kann `TRADING_WORKSPACE_BASE` gesetzt werden;
dieser wird beim Installieren im Menüeintrag festgehalten. `XDG_DATA_HOME` und
`TRADING_WORKSPACE_BIN_DIR` steuern nur die Installationsziele. Der normale
JMBbot-Aufruf benötigt keine dieser Variablen.
