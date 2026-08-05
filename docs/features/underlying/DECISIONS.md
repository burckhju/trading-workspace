# FT-001 Decisions

## Freigegebene Entscheidungen

- ADR-S1-001: Aktien als Basiswerte, Optionsscheine als Produkte.
- ADR-S1-002: Trennung Underlying und Listing.
- ADR-S1-003: eigenes Feature `underlying`.
- ADR-S1-004: Single-User/Single-Workspace.
- ADR-S1-005: Löschung nur ohne Referenzen, sonst Deaktivierung.
- ADR-S1-006: UUID sowie grundlegende Identifikatorregeln.
- ADR-S1-007: eigenständige kontrollierte Referenzen für Markt und Währung.
- ADR-S1-008: Eindeutigkeit von ISIN, WKN und Markt/Ticker innerhalb des Workspace.
- ADR-S1-009: kanonische Normalisierung aller Identifikatoren.
- ADR-S1-010: formale ISIN-Prüfziffer- und WKN-Formatvalidierung.
- ADR-S1-011: optimistische Nebenläufigkeitskontrolle über Versionsnummer.
- ADR-S1-012: unveränderliche feldbasierte Audit-Events für jede fachliche Änderung.
- ADR-S1-013: getrennte Lebenszyklus- und Datenqualitätsstatus.
- ADR-S2-001: persistierter, unsichtbarer Version-1-Workspace.
- ADR-S2-002: persistierte und migrationsseitig versionierte Handelsplatz- und Währungsreferenzen.
- ADR-S2-003: gemeinsame append-only Audit-Tabelle mit JSONB-Feldänderungen und logischen Aggregatreferenzen.

## Architektur-Normalisierungen

Die bestätigte Versionsprüfung wird fachlich korrekt als **optimistische Nebenläufigkeitskontrolle** bezeichnet. Die bestätigten Zustände `DRAFT`, `COMPLETE` und `VERIFIED` bilden die Datenqualität; `ACTIVE` und `INACTIVE` bilden getrennt davon den Lebenszyklus.

## Verbleibende Detailarbeit

Die physischen Tabellendetails für Schritt 1 sind in `PHYSICAL_DATA_MODEL.md` festgelegt. Sie konkretisieren die akzeptierten Fachregeln, ohne sie zu verändern. REST-Pfade und weitere Implementierungsdetails werden in ihren jeweiligen Sprint-2-Schritten entschieden.
