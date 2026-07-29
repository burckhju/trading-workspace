# Systemarchitektur

> Fachliche und technische Gesamtarchitektur des Trading Workspace

---

# Änderungshistorie

| Version | Datum | Änderungen |
|----------|------------|--------------------------------------------------------------|
| 1.0 | 2026-07-22 | Erstversion |
| 1.1 | 2026-07-22 | Nachbeobachtung, Exit Review und lernender Workflow ergänzt. Modulstruktur überarbeitet. |

---

# Dokumentinformationen

| Feld | Wert |
|------|------|
| Dokument-ID | DOC-006 |
| Dokument | 02_ARCHITECTURE.md |
| Dokumenttyp | Specification |
| Version | 1.1 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-07-22 |

---

# Zweck

Dieses Dokument beschreibt die Gesamtarchitektur des Trading Workspace.

Es definiert

- Systemgrenzen
- Module
- Verantwortlichkeiten
- Datenflüsse
- Kommunikationsregeln
- fachliche Abhängigkeiten

Es beschreibt **nicht**

- Datenbanktabellen
- REST-Endpunkte
- Algorithmen
- Berechnungen

---

# Architekturziele

Die Architektur verfolgt folgende Ziele.

- Klare Verantwortlichkeiten
- Geringe Kopplung
- Hohe Erweiterbarkeit
- Hohe Testbarkeit
- Nachvollziehbarkeit
- Versionierbarkeit
- Austauschbare Modelle
- Austauschbare Datenprovider

---

# Schichtenmodell

```text
┌─────────────────────────────────────┐
│ Benutzer                            │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ Frontend                            │
│ React                               │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ REST API                            │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ Business Layer                      │
└─────────────────────────────────────┘
      │        │        │
      ▼        ▼        ▼
 Rule Engine  Model Engine Workflow Engine
      │        │        │
      └────────┼────────┘
               ▼
        Domain Services
               │
      ┌────────┴─────────┐
      ▼                  ▼
 Repository         Provider Layer
      │                  │
      ▼                  ▼
 PostgreSQL       Externe Datenquellen
```

---

# Fachliche Module

## 1. Market Analysis

### Verantwortung

Analyse des Gesamtmarktes.

### Aufgaben

- Marktübersicht
- Marktbreite
- Sektoren
- Scanner
- Trends

---

## 2. Candidate Management

### Verantwortung

Verwaltung aller beobachteten Basiswerte.

### Aufgaben

- Watchlist
- Kandidaten
- Priorisierung

---

## 3. Trade Planning

### Verantwortung

Erstellung des TradePlans.

### Aufgaben

- Einstieg
- Stopstrategie
- Kursziele
- Risiko
- Annahmen

---

## 4. Product Selection

### Verantwortung

Auswahl des optimalen Optionsscheins.

### Aufgaben

- Produktsuche
- Produktscore
- Vergleich
- Produktwechsel

---

## 5. Trade Management

### Verantwortung

Verwaltung laufender Trades.

### Aufgaben

- Trade eröffnen
- Depot
- Stopmanagement
- Teilverkäufe
- Trade schließen

---

## 6. Post Trade Observation

### Verantwortung

Bewertung abgeschlossener Trades.

### Aufgaben

- Nachbeobachtung
- Virtuelle Weiterführung
- Exit Review
- Vergleich tatsächlicher und virtueller Ausstiege

Dieses Modul erzeugt keine Orders.

Es verändert keine Trades.

Es sammelt ausschließlich Erkenntnisse.

---

## 7. Journal

### Verantwortung

Dokumentation des vollständigen Entscheidungsprozesses.

### Aufgaben

- Journal
- Regelabweichungen
- Kommentare
- Bewertungen

---

## 8. Learning

### Verantwortung

Verbesserung zukünftiger Entscheidungen.

### Aufgaben

- Lessons Learned
- Modellbewertung
- Regelbewertung
- Optimierung

---

## 9. Performance

### Verantwortung

Objektive Leistungsbewertung.

### Aufgaben

- Kennzahlen
- Statistiken
- Dashboards

---

## 10. Rule Engine

### Verantwortung

Prüfung sämtlicher Tradingregeln.

Die Rule Engine

- bewertet Regeln,
- erzeugt Empfehlungen,
- dokumentiert Ergebnisse.

Sie trifft niemals Handelsentscheidungen.

---

## 11. Model Engine

### Verantwortung

Ausführung sämtlicher Berechnungsmodelle.

Beispiele

- Scanner
- Marktmodell
- Stopmodell
- Zielmodell
- Produktscore
- Nachbeobachtungsmodell

---

## 12. Provider Layer

### Verantwortung

Kommunikation mit externen Datenquellen.

Beispiele

- EODHD
- ING
- weitere Provider

Provider sind vollständig austauschbar.

---

# Fachlicher Gesamtworkflow

```text
Marktanalyse

↓

Kandidat

↓

TradePlan

↓

Produktauswahl

↓

Trade

↓

Trade geschlossen

↓

Nachbeobachtung

↓

Exit Review

↓

Journal

↓

Lessons Learned

↓

Performance

↓

Modellverbesserung
```

---

# Datenfluss

```text
Provider

↓

Market Analysis

↓

Candidate

↓

TradePlan

↓

Product Selection

↓

Trade

↓

Post Trade Observation

↓

Journal

↓

Learning

↓

Model Engine
```

---

# Verantwortlichkeiten

| Modul | Darf Entscheidungen treffen |
|---------|----------------------------|
| Frontend | Nein |
| API | Nein |
| Business Layer | Ja (fachlich) |
| Rule Engine | Nein |
| Model Engine | Nein |
| Provider | Nein |
| Repository | Nein |

Der Benutzer bestätigt sämtliche Handelsentscheidungen.

---

# Kommunikationsregeln

Module kommunizieren ausschließlich über definierte Schnittstellen.

Nicht zulässig

```text
Frontend

↓

Direkter Datenbankzugriff
```

Nicht zulässig

```text
Model Engine

↓

Direkte UI-Manipulation
```

Nicht zulässig

```text
Provider

↓

Direktes Schreiben in Fachobjekte
```

Zulässig

```text
Frontend

↓

REST API

↓

Business Layer

↓

Repository
```

---

# Lernarchitektur

Der Trading Workspace besitzt zwei voneinander getrennte Kreisläufe.

## Operativer Kreislauf

```text
Markt

↓

Trade

↓

Trade geschlossen
```

---

## Lernkreislauf

```text
Trade geschlossen

↓

Nachbeobachtung

↓

Exit Review

↓

Journal

↓

Lessons Learned

↓

Modellverbesserung

↓

Neue Modellversion
```

Die Trennung dieser beiden Kreisläufe ist ein grundlegendes Architekturprinzip.

---

# Architekturregeln

Für sämtliche Module gelten folgende Regeln.

1. Eine Verantwortung pro Modul.
2. Kommunikation ausschließlich über Schnittstellen.
3. Keine zyklischen Abhängigkeiten.
4. Keine Geschäftslogik im Frontend.
5. Keine Berechnungen im Repository.
6. Modelle bleiben austauschbar.
7. Regeln bleiben konfigurierbar.
8. Provider bleiben austauschbar.
9. Operativer Workflow und Lernworkflow bleiben getrennt.

---

# Nicht Bestandteil dieses Dokuments

Nicht beschrieben werden

- Datenbanktabellen
- SQL
- REST-Endpunkte
- JSON-Strukturen
- Algorithmen
- Modellparameter

Diese Themen werden in den jeweiligen Spezifikationen beschrieben.

---

# Zusammenfassung

Die Architektur trennt konsequent

- Benutzeroberfläche,
- Geschäftslogik,
- Berechnungsmodelle,
- Regeln,
- Datenhaltung,
- Nachbeobachtung,
- Lernsystem.

Der Trading Workspace besteht aus zwei gleichwertigen Bereichen:

1. **Operatives Trading** – Vorbereitung, Durchführung und Verwaltung von Trades.

2. **Kontinuierliches Lernen** – Bewertung abgeschlossener Entscheidungen und Verbesserung zukünftiger Modelle.

Diese Trennung macht den Trading Workspace zu einem lernenden Entscheidungsunterstützungssystem und bildet die Grundlage für alle weiteren Spezifikationen.

---

# Siehe auch

- DOC-003 – PROJECT
- DOC-004 – ROADMAP
- DOC-005 – TERMINOLOGY
- DOC-007 – DATABASE
- DOC-009 – RULEBOOK
- DOC-010 – MODEL_BOOK
- DOC-017 – MODULE_DEPENDENCIES
- DOC-019 – DECISIONS
