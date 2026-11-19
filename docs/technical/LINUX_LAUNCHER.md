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
Migrationshelfer und seine qualifizierte Validierung sind über Inhaltsprüfsummen
gebunden. Eine Änderung daran verlangt eine erneute Prüfung des Updatewegs.

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

Für den eng begrenzten Wechsel von ausgeschaltetem EODHD zu einem aktiven Provider
mit bereits vorhandenem Schlüssel gibt es einen separaten
[EODHD-Aktivierungsweg](EODHD_ACTIVATION.md). Er erstellt einen neuen geprüften
Zustand bei gleicher Programmversion und berücksichtigt ausdrücklich die bereits
eingerichtete Kurs-, Positions- und Telegramautomatik.

<a id="einmaliger-übergang-auf-die-indikative-positionsprüfung"></a>
### Ursprünglicher Übergang auf V1 (v1.5.49)

Der für v1.5.49 vorbereitete Updatevertrag ergänzt genau zwei bisher fehlende
Backendfelder mit ihren ausgeschalteten Werten: `REVIEW_SCOPE=DISABLED` und
`REVIEW_NOTIFICATIONS_ENABLED=false` im vorhandenen
`TRADING_WORKSPACE_POSITION_MONITORING__`-Namensraum. Das Softwareupdate aktiviert
keine neue Regel oder Zustellung. Vorhandene Werte müssen weiterhin gleich sein;
aktive Zielwerte, gelöschte Felder und jede andere Konfigurationsabweichung werden
verweigert. Der Migrationsablauf, die Datensicherung und seine Schutzparameter
bleiben wirksam.

Der bisher installierte Starter bindet die frühere Validator-Prüfsumme und lehnt
den neuen Stand deshalb ab. Vor diesem Releaseupdate wird einmalig der neu
qualifizierte Starter aus dem exakt veröffentlichten Tag außerhalb des
Programmordners gespeichert und mit `install` eingerichtet. Die Release-Übergabe
liefert die vollständig ausgefüllten Befehle samt überprüftem Commit. Der
Programmcheckout wird dadurch noch nicht gewechselt; erst anschließend folgt
das normale gepinnte `trading-workspace update`. Keine versiegelte Konfiguration
manuell bearbeiten und keinen Schutzschalter entfernen.

Nach erfolgreichem Update und `trading-workspace status` erfolgt die zentrale
Vorbereitung einmal für die bestehende Installation:

```bash
python3 ~/Boerse/trading-workspace-app/scripts/activate-indicative-monitoring.py prepare
```

Die Vorbereitung prüft den tatsächlich installierten Tag, Images, vollständige
Compose-Kette und den privaten Zustand. Sie erstellt einen konkreten Plan und
gibt den dazu passenden Anwendungsbefehl aus. Diesen Befehl übernehmen; eigene
IDs, Hashes oder Request-IDs sind nicht erforderlich. Er aktiviert den Umfang
`INDICATIVE_ENTRY_V1` und den vorhandenen Runner zentral. Externe Zustellungen
dieses Umfangs bleiben ausgeschaltet. Bereits eingerichtete Provider,
Kursaktualisierung und andere Meldungsarten behalten ihre Konfiguration.

Die Anwendung verwendet die vorhandenen Images, sichert Datenbank und
Zustimmungszustand und übernimmt erst nach erfolgreicher Prüfung den neuen
Zustand. Es gibt keinen Imagebuild, keine Migration und keine neue
Providerzustimmung in diesem Aktivierungsschritt. Ein geänderter Ausgangszustand
verlangt einen neuen konkreten Plan; ein Fehler nach Beginn behält `pending` und
die Diagnose. Die oben beschriebenen Wiederherstellungsregeln gelten weiter.

Der Abschluss trennt geladene Konfiguration, gestarteten Runner und tatsächlich
abgeschlossenen Prüflauf. Eine erfolgreiche Aktivierung belegt keine
B58-Qualifikation oder vollständige Depotabdeckung. Die
[Betriebsgrenzen der indikativen Prüfung](ISSUER_MONITORING_OPERATIONS.md#indicative-entry-operations)
und der versionierte Regelvertrag bleiben maßgeblich.

### Erweiterung der vorhandenen Installation auf V2

Nach Installation des dafür veröffentlichten Releases über den normalen,
Tag und vollständigen Commit bindenden `trading-workspace update` wird derselbe
Aktivierungsbefehl einmal aufgerufen. Der Betriebsvertrag
[indicative-review-linux-operation-v2](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-review-linux-operation-v2)
akzeptiert einen bisher ausgeschalteten Umfang oder die bestehende aktive V1.
Er erstellt eine neue private Vorbereitung für `INDICATIVE_ENTRY_V2` mit
Regelversion `indicative-entry-review-v2`. Erst der vollständig ausgegebene
`apply`-Befehl wendet diesen konkreten Zustand an.

Der V2-Wechsel benötigt keine neue Launcher-/Supportqualifikation: deren
bisherige Inhaltsbindung ist unverändert. Datenbank, vorhandene Images,
Providerfreigaben, Refresh und bestehende andere Telegramzustellungen bleiben
an den installierten Zustand gebunden. Die neue Reviewzustellung bleibt aus.
Einstands- und Fristläufe werden mit getrennten Ergebnissen angezeigt.

Vorhandene Originalseiten für letzte Handelstage können einmal übernommen
werden, ohne Depotdaten erneut einzugeben:

```bash
python3 ~/Boerse/trading-workspace-app/scripts/import-original-product-documents.py /pfad/zum/quellenpaket.zip
```

Dieser erste Aufruf ist eine Vorschau. Derselbe Aufruf mit `--apply` übernimmt
die erkannten Originale über die lokale API. Die tatsächliche Dateizuordnung
und sämtliche Importvoraussetzungen werden vor dem ersten Schreiben geprüft.
Es wird keine Internetquelle abgefragt, kein Produkt angelegt und kein
Ausstiegsplatz ausgewählt. Den festen Ausstiegsplatz anschließend einmal im
Positionsbereich unter **Produkttermine · fester Ausstiegshandelsplatz** aus den vorhandenen
Listings wählen.
Nicht abgedeckte Instrumente, Kalenderjahre und individuelle Produktschlusszeiten
bleiben ausdrücklich offen.

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
