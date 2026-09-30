# Betrieb der Emittentenkurse ab Version 1.4.0

Diese Anleitung ersetzt die Installationsbefehle der früheren Einzelpakete.
Ein GitHub-Merge aktualisiert den laufenden Server nicht automatisch. Ein bereits
laufender JMBbot bleibt bis zu einem gesonderten Deployment auf seinem installierten
Stand. Bestehende Konfiguration, Datenbank und Zustimmungsspeicher erhalten.

## Quellenwahl bei neuen Optionsscheinen

1. Kanonische ISIN, Emittent und eine eindeutige aktive EUR-Notierung müssen in
   den Stammdaten vorhanden sein. Discovery erfindet oder repariert diese nicht.
2. Bei aktivierter Emittentensuche prüft die Hintergrund-Lane die offizielle
   Produktseite von JPMorgan oder Morgan Stanley. Nur exakte Produktidentität,
   Produkttyp, Bewertungstag, Währung und DOM-Streamkennung ergeben einen Nachweis.
3. Wenn die HTTP-Seite unvollständig ist, darf der private Renderer sie darstellen.
   Zugangssperren, Rate Limits und geänderte Bedingungen werden nicht umgangen.
4. Registrierung und spätere Auswahl prüfen die Stammdaten erneut unter Sperren.
   Der dedizierte Streamadapter holt Kurse; der Quellenabgleich bindet nur geeignete
   verifizierte Routen. Zulässige bestehende Quellen werden erhalten.
5. Bewertungsansicht und Monitoring zeigen Anbieter, Qualität, Kurszeittext und
   Empfangszeit. Ohne verifiziertes Datum/Zeitzone bleibt `quote_observed_at=null`.
   Indikative Regeln folgen ausschließlich der bestätigten Indikations-Policy.

Aktivierung erfolgt ausdrücklich über das optionale Compose-Overlay. Ohne diese
Konfiguration bleiben neue Provider, automatische Auswahl und Discovery aus.
Das Discovery-Intervall beträgt standardmäßig eine Stunde; Diagnose-GETs erzwingen
keinen sofortigen Wiederholungsabruf. `SELECTED` beweist keine neue oder handelbare Quote.

## Reguläre Konfiguration

`docker/compose.issuer-monitoring.yml` bündelt die bisherigen Emittenten-,
Performance-, Auswahl-, Renderer- und Monitoring-Overlays. Bestehende Frankfurt-,
gettex- und Stuttgart-Konfiguration zusätzlich erhalten. Die neuen Dateien nicht
mit alten Paket-Overlays mischen, die dieselben Werte erneut überschreiben.

Im Projektverzeichnis:

```bash
export ISSUER_RENDERER_SECCOMP_PATH="$PWD/docker/issuer-renderer/seccomp_profile.json"
```

Den Telegram-Schalter `TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=true`
in der bestehenden privaten `docker/.env` beibehalten, wenn der Versand bereits
freigegeben und eingerichtet ist. Bot-Token und Chat-ID bleiben ausschließlich dort.
Das Overlay versendet selbst keine Testnachricht. Vor einem Deployment die effektive
Compose-Konfiguration prüfen, ohne deren Geheimniswerte öffentlich auszugeben.

Die folgenden Diagnosebeispiele verwenden die Basiskonfiguration zur Auswahl des
bereits laufenden Containers; `exec` rekonstruiert oder ersetzt keinen Dienst:

```bash
docker compose --env-file docker/.env -f docker/compose.yml exec -T backend \
  python -m app.tools.audit_monitoring_performance --wait-seconds 0
```

Zusätzliche Prüfwerkzeuge: `audit_position_source_selection`,
`audit_issuer_route_discovery`, `audit_new_issuer_routes` und `monitoring_resume`.
Die jeweilige `--help`-Ausgabe zeigt Pflichtparameter. Die beiden Runtime-Hash-Audits
benötigen die Hashliste des tatsächlich deployten Commitstands, keine alten
Paket-Hashes. `audit_issuer_monitoring` kann über die normalen Bewertungs-GETs Kurse
aktualisieren; es verändert keine Regeln und versendet keine Meldungen.

## JPMorgan-Zustimmung

Der Renderer verwendet ausschließlich seinen eigenen privaten Zustand im Volume
`issuer-consent-state`. Eine Zustimmung im Cloud-Browser ist nicht dieser Zustand.
Die unbeaufsichtigte Discovery klickt keine rechtlichen Erklärungen an.

Zur Vorbereitung im laufenden Renderer:

```bash
docker compose --env-file docker/.env -f docker/compose.yml \
  -f docker/compose.issuer-monitoring.yml exec -T issuer-renderer \
  python -m app.tools.setup_jpmorgan_consent
```

Der Betreiber prüft den ausgegebenen aktuellen Text, Hash und seine Erklärungen.
Der explizite Zustimmungslauf benötigt `--accept-current-jpmorgan-terms`,
`--confirm-sha256`, `--confirm-de-at-residence-and-non-us-person` und bei gewünschter
Speicherung `--remember-30-days`. Er läuft unter der vorhandenen Setup-Sperre.
Ein geänderter Hash wird nicht automatisch freigegeben.

Vor erneuter Zustimmung wird ein vorhandener gültiger Zustand mit passendem Hash
in einem frischen Kontext produktgeprüft. Erfolg:
`EXISTING_CONSENT_REUSE_VERIFIED`, `new_acceptance_performed=false`.
Ohne gespeicherten Zustand wird der bestätigte Formularlauf ausgeführt; erst nach
verifizierter Wiederverwendung darf gespeichert werden. Erfolg:
`CONSENT_STORED_PRODUCT_VERIFIED`, `new_acceptance_performed=true`.
Ungültige oder nicht mehr verwendbare vorhandene Zustände werden nicht stillschweigend
überschrieben. Die Größenbegrenzung bleibt bestehen; eine kleinere Variante nur
mit den erfassten Cookies benötigt eine erneute Produktprüfung.

`setup_diagnostics` nennt Phasen, Laufzeiten, begrenzte Fehlerketten und reine
Speichermetadaten. Keine Cookies/Storage-Werte in Berichte kopieren. Wenn Speichern
bereits gelang und nur die Browserbereinigung fehlschlug, macht der Bericht dies
sichtbar; der nächste Lauf prüft die gespeicherte Zustimmung zuerst.

Der Setup-Erfolg erzeugt weder ein Mapping noch eine Testposition. Neue Routen
werden weiterhin durch die Hintergrund-Lane und deren Identitätsprüfungen angelegt.

## Release und Deployment auseinanderhalten

Git-Tag und Paketversion kennzeichnen den Quellstand; Schema, Image und geladene
Konfiguration sind separate Betriebsnachweise. Vor Deployment sichern, beide
Migrationen prüfen, zuerst Renderer-Health bestätigen und anschließend die
vollständige bestehende Stack-Konfiguration verwenden. Keine Löschung von Volumes,
kein Datenbank-Stamp und kein stiller Rollback.

Der Release-PR enthält lokale Prüfergebnisse und GitHub-CI. Die noch offene
JPMorgan-Liveabnahme und fehlende neue Produktabdeckung sind dort ausdrücklich
aufgeführt und dürfen nicht aus grünen Unit-Tests abgeleitet werden.

## Git-Versionierung

`VERSION`, `backend/pyproject.toml`, `frontend/package.json` und dessen Lockdatei
werden im Release-PR gemeinsam fortgeschrieben. Der Workflow `Version tag` setzt
`v<VERSION>` erst, wenn Backend, Frontend und End-to-End am selben aktuellen
`main`-Commit vollständig erfolgreich sind. Vorhandene Tags werden niemals
verschoben. Der Workflow übernimmt keine PRs und führt kein Deployment aus.
