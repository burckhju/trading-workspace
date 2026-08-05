# Architecture Review 1.0

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | ARCHITECTURE_REVIEW_1_0.md |
| Dokumenttyp | Architecture Review |
| Version | 1.1 |
| Status | 🟡 Proposed |
| Reviewdatum | 2026-08-03 |
| Bewerteter Stand | Sprint-0-Basis, Tag `sprint-0.0.0` und nachfolgende technische Korrekturen |

## 1. Zweck

Dieses Review bewertet, ob der nach Sprint 0 vorliegende Stand eine belastbare Grundlage für die fachliche Entwicklung des Trading Workspace bildet. Es legt außerdem die verbindliche Struktur für den Übergang von der technischen Basis zur Feature-Umsetzung fest.

Das Review trifft keine Aussage über die fachliche Qualität zukünftiger Handelsmodelle. Diese müssen jeweils separat spezifiziert, getestet, versioniert und freigegeben werden.

## 2. Gesamturteil

Der aktuelle Stand ist als technisches Entwicklungsfundament geeignet.

Die Architektur unterstützt insbesondere:

- fachlich getrennte Features,
- nachvollziehbare Daten- und Modellversionen,
- getrennte Backend- und Frontendverantwortlichkeiten,
- automatisierte Qualitätsprüfungen,
- dokumentationsgetriebene Umsetzung,
- spätere Erweiterung um Provider und Modelle.

Die nächste Entwicklungsphase darf daher beginnen. Vor der Implementierung komplexer Trading-Funktionen ist jedoch eine fachliche Architekturphase erforderlich. Sie schafft die eindeutige Zuordnung zwischen Domänenobjekten, Prozessen, Features, Anforderungen und Releases.

## 3. Stärken des aktuellen Stands

### 3.1 Klare technische Schichten

Backend, Frontend, Datenbank, Provider und Dokumentation sind strukturell getrennt. Die Feature-Architektur verhindert, dass Geschäftslogik in API-Routen oder UI-Komponenten verteilt wird.

### 3.2 Dokumentation vor Implementierung

Feature Lifecycle und Implementation Template geben einen kontrollierten Weg von der Idee bis zur Abnahme vor. Dies unterstützt die Projektziele Transparenz und Wiederholbarkeit.

### 3.3 Nachvollziehbarkeit als Architekturprinzip

Requirements, Traceability und Model Book verlangen Datenquelle, Modellversion, Eingaben und Ergebnis. Damit ist die Grundlage für reproduzierbare Berechnungen vorhanden.

### 3.4 Reproduzierbare Qualitätssicherung

Backend-, Frontend- und E2E-Workflows sowie lokale Prüfscripte sind vorhanden. Die Entwicklung kann damit auf einer einheitlichen Definition of Done aufbauen.

### 3.5 Keine autonome Handelsentscheidung

Die Projektgrenzen sind eindeutig dokumentiert: Das System unterstützt und bewertet, der Benutzer entscheidet. Dieses Prinzip muss in jeder Feature-Spezifikation als unveränderliche Randbedingung bestehen bleiben.

## 4. Festgestellte fachliche Lücken

### L-001 – Fehlende verbindliche Feature-Zuordnung

Die Roadmap beschreibt Meilensteine, während technische Dokumente auf FT-001 bis FT-013 verweisen. Eine zentrale, verbindliche Zuordnung der Feature-IDs zu fachlichen Verantwortlichkeiten fehlt.

**Maßnahme:** Einführung des Modul- und Feature-Katalogs `MODULE_AND_FEATURE_CATALOG.md`.

### L-002 – Fehlendes priorisiertes Product Backlog

Die Roadmap nennt Zielzustände, aber noch keine umsetzbaren Backlog-Elemente mit Abhängigkeiten, Ergebnissen und Abnahmekriterien.

**Maßnahme:** Einführung von `PRODUCT_BACKLOG.md`.

### L-003 – Domänenobjekte und Lebenszyklen nicht zentral zusammengeführt

Begriffe sind im Glossar enthalten, aber Aggregate, Ownership und Statusübergänge sind noch nicht in einem fachlichen Gesamtmodell zusammengeführt.

**Maßnahme:** Im ersten fachlichen Sprint werden Domain Map und Prozessmodell erstellt und freigegeben.

### L-004 – Stammdatenumfang zu breit für ein einzelnes erstes Feature

M1 umfasst Basiswerte, Börsen, Emittenten, Instrumente, Optionsscheine und Datenprovider. Eine gleichzeitige Umsetzung würde zu früh viele Schnittstellen und Änderungsabhängigkeiten erzeugen.

**Maßnahme:** M1 in vertikale, einzeln abnehmbare Features zerlegen. Erstes Referenzfeature ist `FT-001 Basiswertverwaltung`.

### L-005 – Modell- und Regelgovernance noch auf Baseline-Niveau

`MODEL_BOOK.md`, `REQUIREMENTS.md` und `TRACEABILITY.md` befinden sich noch im Review-Status. Die Mindestanforderungen sind vorhanden, aber der konkrete Freigabeprozess für Modellversionen muss vor dem ersten bewertenden Modell verbindlich werden.

**Maßnahme:** Governance spätestens vor Marktanalyse-Scoring oder Produktscore freigeben. Reine Stammdatenverwaltung darf vorher umgesetzt werden.

### L-006 – Benutzer- und Berechtigungsgrenze noch nicht fachlich entschieden

Das Projekt ist persönlich ausgerichtet. Dennoch muss entschieden werden, ob Daten technisch einem Benutzer beziehungsweise Workspace zugeordnet werden oder ob Version 1.0 bewusst Single-Workspace bleibt.

**Maßnahme:** ADR vor dem ersten persistenten Fachobjekt. Empfohlene Startentscheidung: Single-User/Single-Workspace mit vorbereiteter, aber nicht implementierter Mandantengrenze.

### L-007 – Datenprovider-Abgrenzung

Stammdaten können manuell erfasst oder von Providern geliefert werden. Ohne Ownership-Regel drohen Überschreibungen und doppelte Datenpflege.

**Maßnahme:** Für jedes Feld Herkunft, Aktualisierungsmodus und Überschreibungsregel definieren. Das erste Feature startet mit manueller Pflege; Provider-Import folgt separat.

## 5. Verbindliche Architekturentscheidungen für die nächste Phase

1. **Vertikale Feature-Slices:** Jedes Feature umfasst bei Bedarf Dokumentation, Datenmodell, API, Backend, Frontend und Tests.
2. **Ein fachlicher Owner pro Datenobjekt:** Ein Objekt wird nur durch sein zuständiges Feature geändert.
3. **Explizite Herkunft:** Importierte und manuell gepflegte Werte müssen unterscheidbar sein.
4. **Historie statt Überschreiben:** Fachlich relevante Modell- und Entscheidungsstände werden versioniert oder historisiert.
5. **Keine versteckten Defaults:** Fachliche Standardwerte müssen dokumentiert und testbar sein.
6. **API-Vertrag vor UI-Integration:** Frontend und Backend arbeiten gegen freigegebene Contracts.
7. **Referenzfeature zuerst:** `FT-001 Basiswertverwaltung` etabliert das Muster für folgende CRUD- und Stammdatenfeatures.
8. **Modelle später, Governance vorher:** Bewertungsmodelle werden erst umgesetzt, wenn Model Book und Traceability freigegeben sind.

## 6. Zielarchitektur der fachlichen Domäne

```text
Reference Data
  Basiswert · Börse · Emittent · Instrument · Optionsschein · Datenprovider
        ↓
Market Discovery
  Marktanalyse · Watchlist · Kandidat
        ↓
Trade Preparation
  Trade-Idee · TradePlan · Risiko · Ziel- und Stopregeln
        ↓
Product Selection
  Produktsuche · Produktvergleich · Produktauswahl
        ↓
Execution Record
  Ordererfassung · Position · Trade-Ereignisse
        ↓
Trade Management
  Stopanpassung · Teilverkauf · Produktwechsel · Abschluss
        ↓
Post Trade Learning
  Nachbeobachtung · Exit Review · Journal · Lessons Learned
        ↓
Evaluation & Models
  Performance · Modellvergleich · neue Modellversion
```

Die Pfeile beschreiben fachliche Abhängigkeiten, keine automatischen Handelsaktionen.

## 7. Empfohlene Umsetzungsreihenfolge

1. Fachliche Domain Map und Prozessmodell
2. FT-001 Basiswertverwaltung
3. FT-002 Börsen und Handelsplätze
4. FT-003 Emittenten und Datenprovider-Stammdaten
5. FT-004 Instrumente und Optionsscheine
6. FT-005 Watchlisten und Kandidaten
7. FT-006 Marktanalyse
8. FT-007 TradePlan
9. FT-008 Produktauswahl
10. FT-009 Trade und Position
11. FT-010 Trade Management
12. FT-011 Nachbeobachtung und Exit Review
13. FT-012 Journal, Lessons Learned und Performance
14. FT-013 Modellkatalog und Modellbewertung

Die IDs in diesem Review ersetzen ältere, nicht zentral dokumentierte Zuordnungen erst nach fachlicher Freigabe des Katalogs.

## 8. Qualitätsgates je Feature

Ein Feature darf nur implementiert werden, wenn:

- Zweck und Nicht-Zweck festgelegt sind,
- betroffene Domänenobjekte eindeutig sind,
- Abhängigkeiten bekannt sind,
- fachliche Regeln und Validierungen dokumentiert sind,
- Datenherkunft und Ownership geklärt sind,
- Akzeptanzkriterien vorliegen,
- Architekturreview bestanden ist.

Ein Feature darf nur freigegeben werden, wenn:

- Backend- und Frontendprüfungen erfolgreich sind,
- Migrationen vorwärts und rückwärts geprüft wurden,
- Contract-, Integrations- und E2E-Tests vorliegen,
- Traceability aktualisiert ist,
- Dokumentation und Changelog aktuell sind,
- keine autonome Handelsentscheidung eingeführt wurde.

## 9. Freigabeempfehlung

**Empfehlung:** Fachliche Architekturphase starten und `FT-001 Basiswertverwaltung` als erstes Referenzfeature spezifizieren.

**Noch nicht empfohlen:** Direkter Beginn mit Scanner, Produktscore, Trade Assistant oder anderen bewertenden Modellen.


## 10. Review-Fortschreibung 2026-08-03

Akzeptierte Entscheidungen:

- Aktien sind in Version 1 die einzigen Basiswerte.
- Optionsscheine sind getrennte Produkte.
- Underlying und Listing werden getrennt.
- FT-001 wird als eigenes Feature `underlying` geführt.
- Version 1 ist Single-User/Single-Workspace.
- Referenzierte Basiswerte werden deaktiviert statt gelöscht.
- Identifikatorregeln gemäß ADR-S1-006.

Die fachlichen Artefakte befinden sich weiterhin im Review; eine Implementierungsfreigabe ist damit noch nicht verbunden.


## 11. Abschließender Architekturreview 2026-08-03

### Ergebnis

Die ADRs S1-007 bis S1-013 schließen die verbliebenen Detailfragen. Die Dokumente Domain Map, Trading-Prozessmodell, Modulzuordnung und FT-001 Feature Book sind untereinander konsistent.

### Terminologische Korrekturen

- Die bestätigte Versionsprüfung ist optimistische, nicht pessimistische Nebenläufigkeitskontrolle.
- `ACTIVE/INACTIVE` beschreibt den Lebenszyklus; `DRAFT/COMPLETE/VERIFIED` beschreibt separat die Datenqualität.

### Freigabe

- Sprint 1 fachliche Architektur: **Approved**
- FT-001: **Architecture Approved – Approved for Build**
- Produktive Implementierung: **noch nicht begonnen; Start erst mit Sprint 2**

Es bestehen keine blockierenden fachlichen Inkonsistenzen für FT-001. Technische Detailentscheidungen dürfen die akzeptierten ADRs und Fachregeln nicht verändern.
