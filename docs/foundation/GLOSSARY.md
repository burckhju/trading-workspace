# Glossary

> Verbindliches Glossar des Trading Workspace

---

# Änderungshistorie

| Version | Datum | Änderungen |
|----------|------------|----------------|
| 1.0 | 2026-07-22 | Erstversion |

---

# Dokumentinformationen

| Feld | Wert |
|------|------|
| Dokument-ID | DOC-017 |
| Dokument | GLOSSARY.md |
| Dokumenttyp | Reference |
| Version | 1.0 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-07-22 |

---

# Zweck

Dieses Dokument definiert sämtliche fachlichen Begriffe des Trading Workspace.

Es stellt sicher, dass in Dokumentation, Entwicklung und Tests dieselben Begriffe mit derselben Bedeutung verwendet werden.

Ein Begriff besitzt genau eine Definition.

---

# Verwendung

Das Glossar ist verbindlich für

- Foundation
- Feature Books
- Reference Library
- Quellcode
- Tests
- Benutzeroberfläche

---

# Aufbau

Jeder Begriff besitzt denselben Aufbau.

```text
Begriff

Definition

Verwendet von

Verwandte Begriffe
```

---

# A

## Ask Price

Verkaufskurs eines Wertpapiers.

Verwendet von

- FT-004
- FT-005

Siehe auch

- Bid Price
- Product

---

# B

## Bid Price

Ankaufskurs eines Wertpapiers.

Beim Trading Workspace werden Zielerreichungen eines Optionsscheins grundsätzlich anhand des Bid-Preises bewertet.

Verwendet von

- FT-004
- FT-005

Siehe auch

- Ask Price

---

# C

## Candidate

Ein beobachteter Basiswert mit Handelsinteresse.

Ein Candidate ist noch kein Trade.

Verwendet von

- FT-002

---

# D

## Decision Quality

Bewertung der Handelsentscheidung unabhängig vom finanziellen Ergebnis.

Verwendet von

- FT-006
- FT-008

---

# E

## Exit Review

Bewertung der tatsächlichen Ausstiegsentscheidung nach Abschluss der Nachbeobachtung.

Verwendet von

- FT-006
- FT-007

---

# F

## Feature

Fachlich abgeschlossener Funktionsbereich.

Beispiele

- Market Analysis
- Trade Management
- Journal

---

# H

## Historical Data

Historische Kursdaten eines Basiswerts oder Produkts.

Verwendet von

- FT-001
- FT-010

---

# J

## Journal

Dokumentation eines vollständig abgeschlossenen Trades.

Ein Journal wird erst nach Abschluss der Post Trade Observation finalisiert.

Verwendet von

- FT-007

---

# L

## Lessons Learned

Erkenntnisse aus abgeschlossenen Trades zur Verbesserung von Regeln und Modellen.

Verwendet von

- FT-007
- FT-009

---

# M

## Market Analysis

Analyse des Gesamtmarktes ohne konkrete Handelsentscheidung.

Verwendet von

- FT-001

---

## Model

Berechnungs- oder Bewertungslogik zur Unterstützung fachlicher Entscheidungen.

Verwendet von

- FT-009

---

## Model Version

Version eines Modells mit nachvollziehbarer Historie.

---

# N

## Notification

Systemgenerierte Erinnerung oder Warnung.

Das System führt niemals automatisch Orders aus.

Verwendet von

- FT-011

---

# O

## Observation

Nachbeobachtung eines bereits geschlossenen Trades.

Dient ausschließlich der Bewertung der Entscheidungsqualität.

Verwendet von

- FT-006

---

# P

## Performance

Gesamtauswertung aller abgeschlossenen Trades.

Umfasst

- finanzielle Performance
- virtuelle Performance
- Entscheidungsqualität

Verwendet von

- FT-008

---

## Post Trade Observation

Zeitraum nach Schließung eines Trades, in dem die weitere Entwicklung beobachtet wird.

Verwendet von

- FT-006

---

## Product

Handelbares Finanzinstrument zur Umsetzung eines TradePlans.

Beispielsweise

- Optionsschein
- Knock-Out
- Faktorzertifikat

Verwendet von

- FT-004
- FT-005

---

## Product Switch

Austausch des gehandelten Produkts bei unverändertem TradePlan.

Verwendet von

- FT-004
- FT-005

---

# R

## Requirement

Verbindliche fachliche Anforderung an das System.

Dokumentiert im REQUIREMENTS-Dokument.

---

## Rule

Fachliche Geschäftsregel.

Dokumentiert im RULEBOOK.

---

# T

## Target

Kursziel eines TradePlans.

Ein TradePlan kann mehrere Targets besitzen.

---

## Trade

Tatsächlich eröffnete Position.

Ein Trade entsteht erst nach Ausführung eines TradePlans.

---

## Trade Event

Unveränderbares Ereignis innerhalb des Lebenszyklus eines Trades.

Beispiele

- eröffnet
- Stop geändert
- Teilverkauf
- geschlossen

---

## Trade Management

Verwaltung eines laufenden Trades.

Verwendet von

- FT-005

---

## TradePlan

Beschreibung einer geplanten Handelsidee.

Ein TradePlan ist produktunabhängig.

Verwendet von

- FT-003

---

# U

## Underlying

Basiswert eines Handelsprodukts.

Beispiele

- Aktie
- ETF
- Index

---

# V

## Virtual Performance

Ergebnis eines virtuellen Verlaufs nach Trade-Schließung.

Dient ausschließlich der Analyse.

Verwendet von

- FT-006
- FT-008

---

# W

## Watchlist

Sammlung beobachteter Candidates.

Verwendet von

- FT-002

---

# Zusammenfassung

Dieses Glossar definiert die verbindliche Fachsprache des Trading Workspace.

Alle Dokumente, Features, Modelle, APIs und Implementierungen verwenden ausschließlich die hier definierten Begriffe.

---

# Siehe auch

## Foundation

- PROJECT
- TERMINOLOGY
- ARCHITECTURE

## Feature Books

- FT-001 bis FT-013

## Reference

- REQUIREMENTS
- RULEBOOK
- MODEL_BOOK
- DATABASE
- API
- TRACEABILITY
