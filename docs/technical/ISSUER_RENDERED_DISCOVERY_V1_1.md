# Gerenderte Emittentensuche – v1.1

> Historischer Paketstand. Für den Git-Stand ab 1.4.0 gelten die
> [aktuelle Betriebsanleitung](ISSUER_MONITORING_OPERATIONS.md) und die
> [Release-Notizen](../releases/V1.4.0-ISSUER-MONITORING.md).

Stand: 29.09.2026. Ergänzt AUTOMATIC_ISSUER_ROUTE_DISCOVERY_V1 und setzt Schema
20260928_0042 voraus. Keine Migration. Maßgeblich bleiben CODING_STANDARDS,
ADR-S1-010-ISIN-WKN-VALIDATION und ADR-S7-004-WARRANT-LISTING-BOUNDARY.

## Anlass und Entscheidung

Die Diagnose vom 29.09.2026 zeigt zwei verschiedene Ursachen: fehlende oder ungültige
Stammdaten sowie unvollständige HTTP-Produktseiten bzw. Transportfehler. Die Produktseiten
DE000JZ91459 (JPMorgan) und DE000MN5Y1X9 (Morgan Stanley) waren im Cloud-Browser vollständig
darstellbar. Das belegt noch keinen erfolgreichen Abruf vom JMBbot.

Für beide Emittenten bleibt der vorhandene HTTP-Abruf der erste Versuch. Nur bei
Transportfehlern, fehlender Produkttabelle oder fehlenden Stream-Bindungen wird ein
separater, bedarfsgesteuerter Chromium-Dienst aufgerufen. Derselbe strenge Parser prüft
die gerenderte Seite im Browser-Dienst und erneut im Backend. ISIN, WKN soweit vorhanden,
Optionsschein-Typ, Bewertungstag, EUR und exakte DOM-Stream-Kennung müssen zusammenpassen.
Kein Rückschluss auf eine Kennung aus einem Präfix oder aus dem Basiswert.

Dies ergänzt die Prozessentscheidung von v1: Die Planung und alle Datenbankentscheidungen
bleiben beim bestehenden Refresh-Leader. Der zusätzliche Dienst besitzt keine eigene
Zeitplanung, keine Datenbankverbindung und keine Entscheidungsrechte über Kursquellen.
Es gibt keine Browser-Abhängigkeit im Backend-Image und keine Browsernutzung für bestehende
Stream-Kursabrufe. Playwright und Chromium werden gemeinsam auf 1.63.0 festgelegt.

## Stammdaten vor Netzwerkzugriff

Die ISIN muss exakt kanonisch sein (12 Zeichen, Länderpräfix, Prüfziffer). Der öffentliche
Marktvertrag verwendet die vorhandene fachliche Prüfziffernvalidierung. Er korrigiert keine
Kennung. Insbesondere wird aus `DE000MJK091` kein vermeintlich richtiges Produkt konstruiert.

| Reason | Bedeutung |
|---|---|
| ISSUER_ISIN_INVALID | Originalkennung prüfen und über bestehende Stammdatenverwaltung korrigieren |
| ISSUER_LISTING_MISSING | Keine Notierung vorhanden; belegten Handelsplatz und Handelswährung erfassen |
| ISSUER_NO_ACTIVE_EUR_LISTING | Vorhandene Notierungen/Währung/Handelsplatz sind nicht geeignet oder inaktiv |
| ISSUER_MULTIPLE_ACTIVE_EUR_LISTINGS | Mehrdeutige Zuordnung; fachliche Prüfung erforderlich |

Diese Fälle tragen `NEEDS_MASTER_DATA`. Es wird keine Notierung angelegt, kein XETR/XFRA
angenommen und keine bestehende Sperre übergangen. Zehn Produkte der vorliegenden Diagnose
haben keine Notierung; eines davon zusätzlich eine ungültige ISIN. Der Browser-Dienst
allein löst diese Stammdatenfälle nicht. DE000MN2ZUN2 bleibt ausgeschlossen.

## Privater Browser-Dienst

`issuer-renderer:8091` ist nur im eigenen Compose-Netz mit dem Backend verbunden. Kein
Host-Port, keine Datenbank-/Benutzerzugangsdaten, keine Host-Verzeichnisse. Das Image läuft
als `pwuser`, mit Chromium-Sandbox, unveränderlichem Root-Dateisystem, temporärem /tmp,
entfernten Linux-Capabilities und dem offiziellen Playwright-Seccomp-Profil. Ressourcen:
1 CPU, 1 GiB Speicher, 256 Prozesse, 256 MiB /tmp und 256 MiB Shared Memory.

Die API akzeptiert ausschließlich Anbieter und kanonische ISIN. Zieladressen werden intern
gebildet. Hauptnavigation ist auf den exakten offiziellen Produktpfad beschränkt. HTTPS-
Ressourcen sind auf den jeweiligen Emittentenhost sowie beobachtete Consent-Asset-Hosts
beschränkt (`cdn.cookielaw.org`, `c.evidon.com`, `geolocation.onetrust.com`). Nur GET/HEAD,
höchstens 128 Requests, keine Unterseiten-/Frame-Navigation, keine WebSockets, keine
Service Workers, keine Übernahme bestehender Browsersitzungen. Jeder Abruf erhält einen
neuen Browserkontext. Nutzungsbedingungen, Zugangssperren und Sicherheitsprüfungen werden
nicht automatisch bestätigt oder umgangen. 401/403/429 im HTTP-Abruf lösen keinen Browser-
Alternativversuch aus. Die JS-Schutzprüfung ist ergänzend; ein vollständiger fachlicher
Seitennachweis bleibt zwingend.

Eine Browserprüfung hat ein Arbeitsbudget von 35 Sekunden plus höchstens 3 Sekunden
Kontextbereinigung, davon höchstens 20 Sekunden bis zum DOM
und anschließend höchstens 12 Sekunden für Produktfelder. Es wird nicht auf `networkidle`
gewartet. Ein Dienst verarbeitet höchstens eine Seite gleichzeitig. Mindestabstand je
Anbieter 15 Sekunden; Fehlerpause mindestens 5 Minuten, erkannte Zugangs-/Bedingungssperren
eine Stunde. Die Refresh-Lane plant Wiederholungen mit den bisherigen Regeln. Vorhandene
Kurs-Lanes warten nicht auf die Suche.

Zurückgegeben wird ein bereinigter DOM-Ausschnitt (maximal 2 MB), ohne Scripts, Formulare,
URLs oder Ereignisattribute. Produkttext und die für die Identitätsprüfung erforderlichen
Klassen-/Datenattribute bleiben erhalten. Der Backend-Transport begrenzt auch die JSON-
Antwort und prüft Anbieter, ISIN, offizielle URL und Aufnahmezeit. Der Nachweis kennzeichnet
`acquisition_mode=RENDERED_DOM`; bisherige Nachweise ohne dieses Feld bleiben PUBLIC_HTTP.

## Registrierung, Kurse und Auswahl

Nach positivem Nachweis gelten die vorhandene zweite Stammdatenprüfung unter Datenbank-
sperren, eindeutige Registrierung, Adapter-Invalidierung, Kursabruf und Quellenabgleich.
Bestehende verifizierte Quellen bleiben erhalten. Widersprüche verlangen Prüfung.

Die Quote bleibt indikativ. Empfangszeit und Kurszeit werden getrennt. JPMorgan liefert
weiter eine Uhrzeit ohne verifiziertes Kursdatum/Zeitzone; Morgan Stanley einen lokalen
Datums-/Zeittext ohne verifizierte Zeitzone. `observed_at` bleibt null, `execution_usable`
false. Ein Produktbewertungstag oder eine Browser-Aufnahmezeit wird niemals zum Kursdatum.

## Installation und Nachweise

Der Installer verlangt bekannte Dateihashes und Schema 0042. Keine Freigabe unbekannter
Dateistände und kein Datenbank-Stamp. Nach Sicherung und Image-Build muss zuerst der gesunde
Chromium-Dienst starten. Erst dann werden Backend/Frontend mit der vollständigen bisherigen
Overlay-Kette ersetzt. Ein Startfehler des Renderers stoppt vor dem Backend-Neustart.
Dateiänderungen und gebaute Images können dann bereits vorhanden sein; Sicherungspfad und
Installationslog bleiben erhalten. Bei späteren Fehlern gibt es keinen stillen Rollback.

`run.sh verify` bestätigt installierte Backend-Dateien, Schema, aktive Konfiguration,
Refresh-Leader, vorhandene Quellenbindungen und Renderer-Health. Es erzeugt keine neuen
Mappings. `RUNTIME_VERIFIED` ist ausdrücklich keine Zusage neuer Kursversorgung.

`run.sh acceptance` wartet höchstens 90 Sekunden lesend auf gespeicherte Nachweise und
positive EUR-Geldkurse für DE000JZ91459/DE000MN5Y1X9. Fehlende Stufen liefern
`ACCEPTANCE_INCOMPLETE` und Exit 2. Die eigentliche Arbeit erledigt die Hintergrund-Lane.
Bei bestehenden offenen Positionen wird die zugehörige Quellenbindung geprüft. Ohne
offene Position erscheint `NOT_APPLICABLE_NO_OPEN_POSITION`; es wird kein Testkauf erzeugt.
Gespeicherte Kurse beweisen keine Ausführbarkeit oder verifizierte Kursfrische.

`run.sh pause` pausiert neue Emittentensuche und stoppt den Browser-Dienst. Bestehende
Kursadapter, Quellenbindungen und Monitoring bleiben aktiv. `resume` startet zuerst den
Browser-Dienst. Zum Dateirückbau auf v1 dient `restore.py` mit dem tatsächlich ausgegebenen
Sicherungspfad; spätere Änderungen werden geschützt. Keine Datenbankänderung/Rückmigration.

## Testgrenzen

Die automatisierten Tests prüfen beide Emittenten mit synthetischen DOMs/Streams und echten
SQL-Registrierungen, Quellenentscheidungen und Beobachtungsspeicherung (SQLite). Browser-
Lifecycle und Netzwerkgrenzen sind mit SDK-Testdoubles geprüft. Zugriff auf echte Seiten
erfolgte separat im Cloud-Browser. Docker-Deployment wird lokal simuliert, da hier Docker
nicht verfügbar ist. Healthcheck und Live-Abnahme auf JMBbot sind deshalb erforderlich.
SQLite ersetzt keine PostgreSQL-Sperrprüfung. Keine Behauptung eines produktiven Live-Erfolgs.

Referenzen: [Playwright Docker](https://playwright.dev/python/docs/docker),
[Netzwerkinterception](https://playwright.dev/python/docs/network),
[Page API](https://playwright.dev/python/docs/api/class-page).
