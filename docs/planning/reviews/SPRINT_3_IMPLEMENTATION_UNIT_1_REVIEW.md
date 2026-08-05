# Sprint 3 – Implementierungsreview Arbeitseinheit 1

## Status

🟢 Completed – 2026-08-05

## Erledigte Arbeiten

- Providerunabhängiges Paket `app.features.market_data` angelegt.
- Interne Enums und unveränderliche Domainmodelle implementiert.
- Capability-basierte Provider-Protocols implementiert.
- Requests, Resultatmodell und Mapping-Validierungsergebnis implementiert.
- Providerunabhängige Domain- und Servicefehler implementiert.
- 17 gezielte Unit-Tests ergänzt und erfolgreich ausgeführt.
- Ruff und Black für den neuen Scope erfolgreich ausgeführt.
- Python-Bytecode-Kompilierung erfolgreich geprüft.

## Offene Punkte

- MyPy muss in einer funktionsfähigen Python-3.12-Projektumgebung erneut ausgeführt werden. Die mit der Repositoryhistorie verfügbare virtuelle Umgebung ist nicht portabel und kann ihre Standardbibliothek beziehungsweise native Pakete nicht konsistent laden.
- Persistenz, Migration, Repositorycontracts und Unit-of-Work sind noch nicht implementiert.

## Risiken

- `MarketDataProvider` enthält zunächst nur EODHD. Weitere Enumwerte werden erst gemeinsam mit einem tatsächlich integrierten Provider ergänzt.
- Die strikte UTC-Regel setzt voraus, dass Adapter Zeitstempel vor dem Erzeugen interner Modelle normalisieren.

## Architekturentscheidungen

- Keine Änderung an den akzeptierten ADRs.
- Binäre Fließkommawerte werden an der internen Modellgrenze abgelehnt.
- Aktive Provider-Mappings benötigen einen erfolgreichen Validierungszeitpunkt.
- Das Resultatmodell macht Cachezustand, Qualität, Retries und Providerkosten sichtbar.

## Nächster empfohlener Schritt

Arbeitseinheit 2: Persistenzmodelle, Migration, Repositorycontracts und Unit-of-Work für Provider-Mappings und validierte EOD-Tageskurse.
