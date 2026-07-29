# Projekt

> Vision, Ziele und Grundprinzipien des Trading Workspace

---

# Änderungshistorie

| Version | Datum | Änderungen |
|----------|------------|--------------------------------------------------------------|
| 1.0 | 2026-07-22 | Erstversion |
| 1.1 | 2026-07-22 | Nachbeobachtung und Exit Review ergänzt. Projektvision geschärft. Workflow erweitert. Lernphilosophie überarbeitet. |

---

# Dokumentinformationen

| Feld | Wert |
|------|------|
| Dokument-ID | DOC-003 |
| Dokument | 00_PROJECT.md |
| Dokumenttyp | Policy |
| Version | 1.1 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-07-22 |

---

# Zweck

Dieses Dokument beschreibt die Vision, Ziele und grundlegenden Prinzipien des Trading Workspace.

Es definiert den fachlichen Rahmen, innerhalb dessen alle Architektur-, Spezifikations- und Implementierungsentscheidungen getroffen werden.

Dieses Dokument enthält **keine technischen Details**.

---

# Vision

Trading Workspace ist ein persönlicher, regelbasierter und lernender Trading-Arbeitsplatz.

Er unterstützt den Benutzer dabei,

- Märkte zu analysieren,
- fundierte Handelsentscheidungen vorzubereiten,
- Trades nachvollziehbar durchzuführen,
- Entscheidungen objektiv zu bewerten,
- und zukünftige Entscheidungen kontinuierlich zu verbessern.

Der Benutzer entscheidet.

Das System unterstützt, dokumentiert, bewertet und lernt.

---

# Mission

Trading Workspace verfolgt das Ziel, die Qualität von Handelsentscheidungen nachhaltig zu verbessern.

Dabei steht nicht ausschließlich das finanzielle Ergebnis im Mittelpunkt.

Ebenso wichtig sind

- Qualität der Analyse,
- Qualität des TradePlans,
- Qualität der Produktauswahl,
- Qualität des Risikomanagements,
- Qualität des Ausstiegs,
- Qualität des Lernprozesses.

---

# Zielgruppe

Trading Workspace richtet sich an private Trader, die

- regelbasiert handeln,
- deutsche Optionsscheine einsetzen,
- ihre Entscheidungen dokumentieren möchten,
- ihre Handelsstrategie kontinuierlich verbessern wollen.

---

# Projektziele

## Transparenz

Jede Empfehlung muss nachvollziehbar sein.

Zu jedem Ergebnis gehören mindestens

- Datenquelle
- Modell
- Modellversion
- Eingabedaten
- Berechnungszeitpunkt

---

## Nachvollziehbarkeit

Alle relevanten Entscheidungen werden dokumentiert.

Beispiele

- Trade eröffnet
- Produkt gewechselt
- Stop angepasst
- Teilverkauf durchgeführt
- Trade geschlossen
- Exit Review abgeschlossen

---

## Wiederholbarkeit

Gleiche Eingaben führen zu denselben Ergebnissen.

Berechnungen dürfen nicht vom Zufall abhängen.

---

## Kontinuierliche Verbesserung

Jeder abgeschlossene Trade liefert Erkenntnisse.

Diese fließen kontrolliert in

- Regelverbesserungen,
- Modellverbesserungen,
- Prozessverbesserungen

ein.

---

## Entscheidungsqualität

Nicht nur Gewinne werden bewertet.

Ebenso bewertet werden

- Einstieg
- Stop
- Kursziele
- Ausstieg
- Haltedauer
- Einhaltung des TradePlans

---

# Nicht-Ziele

Trading Workspace ist

- keine Brokerplattform,
- kein automatischer Trading-Bot,
- keine Blackbox-KI,
- keine Anlageberatung,
- kein Hochfrequenzhandelssystem.

Orders werden niemals automatisch ausgeführt.

---

# Grundprinzipien

## Dokumentation vor Implementierung

Jede Funktion wird zunächst fachlich beschrieben.

Danach folgen

- Spezifikation,
- Implementierung,
- Tests.

---

## Single Source of Truth

Jede Information besitzt genau eine fachliche Quelle.

Doppelte Definitionen sind nicht zulässig.

---

## Trennung der Verantwortlichkeiten

Der Tradingprozess wird in fachlich getrennte Bereiche gegliedert.

- Marktanalyse
- Kandidaten
- TradePlan
- Produktauswahl
- Trade Management
- Nachbeobachtung
- Journal
- Modellbewertung

Jeder Bereich besitzt eine klar definierte Verantwortung.

---

## Trennung von TradePlan und Produkt

Der TradePlan beschreibt ausschließlich die Handelsidee.

Das Produkt beschreibt ausschließlich deren technische Umsetzung.

Ein Produktwechsel verändert niemals den TradePlan.

---

## Lernen aus Entscheidungen

Das Projekt bewertet nicht ausschließlich Gewinne oder Verluste.

Bewertet werden insbesondere

- Qualität der Analyse,
- Qualität der Entscheidung,
- Qualität des Timings,
- Qualität des Ausstiegs.

---

## Nachbeobachtung

Ein Trade endet fachlich nicht mit dem Verkauf.

Nach dem Tradeabschluss beginnt die Phase der Nachbeobachtung.

Sie dient ausschließlich der Bewertung der ursprünglichen Handelsentscheidung.

Während dieser Phase

- existiert keine Position,
- besteht kein Risiko,
- werden keine Orders erzeugt.

---

## Versionierte Modelle

Alle Berechnungsmodelle werden versioniert.

Eine Modellversion bleibt nach ihrer Freigabe unverändert.

Neue Berechnungen erfolgen ausschließlich über neue Modellversionen.

---

## Datenqualität

Jede Information besitzt mindestens

- Quelle,
- Zeitstempel,
- Qualitätsstatus.

Fehlende oder veraltete Daten führen zu Warnungen.

---

## Benutzerkontrolle

Das System unterstützt Entscheidungen.

Das System trifft keine Entscheidungen.

Die Verantwortung verbleibt vollständig beim Benutzer.

---

# Trading-Lebenszyklus

```text
Marktanalyse
      │
      ▼
Kandidat
      │
      ▼
Analyse
      │
      ▼
TradePlan
      │
      ▼
Produktauswahl
      │
      ▼
Trade
      │
      ▼
Trade geschlossen
      │
      ▼
Nachbeobachtung
      │
      ▼
Exit Review
      │
      ▼
Journal
      │
      ▼
Lessons Learned
      │
      ▼
Modellverbesserung
```

---

# Datenphilosophie

Alle Informationen besitzen genau eine Herkunft.

| Herkunft | Beschreibung |
|-----------|--------------|
| Manuell | Benutzer |
| Importiert | Datenprovider |
| Berechnet | Modelle |

Die Herkunft bleibt dauerhaft nachvollziehbar.

---

# Modellphilosophie

Modelle unterstützen Entscheidungen.

Modelle

- analysieren,
- bewerten,
- priorisieren,
- berechnen.

Modelle treffen niemals Handelsentscheidungen.

---

# Lernphilosophie

Trading Workspace lernt nicht ausschließlich aus abgeschlossenen Trades.

Er bewertet zusätzlich die Qualität der Entscheidung.

Dazu werden

- tatsächlicher Verlauf,
- virtuelle Weiterführung,
- Exit Review

miteinander verglichen.

Dadurch können

- Stopmodelle,
- Kurszielmodelle,
- Haltedauern,
- TradePläne,
- Regeln

kontinuierlich verbessert werden.

---

# Qualitätsprinzipien

Vor jeder Berechnung werden geprüft

- Vollständigkeit,
- Aktualität,
- Plausibilität,
- Datenqualität.

Ungültige Daten werden niemals stillschweigend ersetzt.

---

# Erfolgsdefinition

Trading Workspace ist erfolgreich, wenn

- der tägliche Analyseaufwand sinkt,
- Entscheidungen nachvollziehbarer werden,
- Regeln konsequent eingehalten werden,
- Modelle kontinuierlich verbessert werden,
- die Qualität der Handelsentscheidungen langfristig steigt.

---

# Projektleitbild

> **Eine gute Trading-Entscheidung wird nicht ausschließlich am Gewinn gemessen.**

Sie wird daran gemessen,

- ob sie auf einer fundierten Analyse basiert,
- einem nachvollziehbaren TradePlan folgt,
- konsequent umgesetzt wurde,
- und ob aus ihrem Ergebnis gelernt wurde.

Trading Workspace unterstützt den Benutzer dabei, genau diese Qualität systematisch zu erreichen.

---

# Zusammenfassung

Trading Workspace verbindet

- Marktanalyse,
- TradePlanung,
- Produktauswahl,
- Trade Management,
- Nachbeobachtung,
- Exit Review,
- Journal,
- Lessons Learned
- und kontinuierliche Modellverbesserung

zu einem gemeinsamen, nachvollziehbaren Entscheidungsprozess.

Der Benutzer trifft die Entscheidungen.

Das System sorgt dafür, dass diese Entscheidungen transparent, reproduzierbar und kontinuierlich verbessert werden können.

---

# Siehe auch

- DOC-002 – INDEX
- DOC-004 – ROADMAP
- DOC-005 – TERMINOLOGY
- DOC-006 – ARCHITECTURE
- DOC-009 – RULEBOOK
- DOC-010 – MODEL_BOOK
- DOC-019 – DECISIONS
