# FT-001 – Basiswertverwaltung

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Feature-ID | FT-001 |
| Technischer Name | `underlying` |
| Version | 1.1 |
| Status | 🟢 Implemented – Sprint 2 Complete |
| Letzte Änderung | 2026-08-04 |

## Ziel

Der Benutzer verwaltet Aktien als zentrale Basiswerte an genau einer Stelle. Andere Features referenzieren diese Daten und erfassen sie nicht erneut.

## Nutzen

- zentrale und eindeutige Stammdaten,
- keine doppelte Erfassung,
- nachvollziehbare Änderungen,
- stabile historische Referenzen,
- vorbereitete Trennung zwischen Basiswert und Marktpräsenz.

## Scope

- Aktie als Underlying anlegen,
- mindestens eine primäre Notierung erfassen,
- Basiswerte suchen, filtern und anzeigen,
- Stammdaten und Notierungen bearbeiten,
- aktivieren und deaktivieren,
- unbenutzte Fehleinträge endgültig löschen,
- Verwendungen vor Löschung transparent anzeigen,
- Dubletten anhand definierter Kennungen verhindern.

## Nicht-Scope

- Optionsscheinverwaltung,
- Emittentenverwaltung,
- Providerimport,
- Kursdaten,
- automatische Stammdatenergänzung,
- Indizes, ETFs, Rohstoffe oder Währungen,
- Zusammenführung von Dubletten,
- Handelsentscheidung oder Produktempfehlung.

## Benutzer

Version 1 besitzt genau einen Benutzer in einem unsichtbaren Workspace.

## Hauptanwendungsfälle

1. Basiswert mit primärer Notierung anlegen.
2. Basiswert über Name, Ticker, ISIN oder WKN finden.
3. Details und Notierungen anzeigen.
4. Basiswert- oder Notierungsdaten ändern.
5. Basiswert deaktivieren oder reaktivieren.
6. Unbenutzten Basiswert endgültig löschen.
7. Löschung bei vorhandenen Referenzen ablehnen und Verwendungen anzeigen.

## Fachliche Kernregeln

- Nur Aktien dürfen angelegt werden.
- Ein Optionsschein darf niemals als Basiswert angelegt werden.
- Underlying und Listing sind getrennte Objekte.
- Operative Nutzung erfordert genau eine aktive primäre Notierung.
- Ticker ist nur zusammen mit Markt eindeutig.
- ISIN und WKN sind optional, aber eindeutig, sobald vorhanden.
- Referenzierte Basiswerte dürfen nicht endgültig gelöscht werden.
- Deaktivierung verändert bestehende Referenzen nicht.
- Andere Features dürfen Underlying-Stammdaten nicht schreiben.

## Abhängigkeiten

- Workspace-Basis aus ADR-S1-004.
- Markt-/Handelsplatzreferenz; bis FT-002 muss eine kontrollierte Referenzliste genutzt werden.
- Währungsreferenz aus dem technischen/shared Bereich oder einer späteren fachlichen Referenzquelle.

## Bedienprinzip

Die Anlage erfolgt als geführter Ablauf mit Grunddaten und primärer Notierung. Da Version 1 nur Aktien unterstützt, ist der Typ nicht als frei wählbare Liste nötig; er wird sichtbar als „Aktie“ dargestellt.

## Freigabestatus

Alle fachlichen Grund- und Detailentscheidungen sind akzeptiert. FT-001 wurde in Sprint 2 vollständig über Backend, REST API, React-Frontend, Tests und Dokumentation umgesetzt. Die Implementierung bleibt an die akzeptierten ADRs und die Feature-Book-Verträge gebunden.
