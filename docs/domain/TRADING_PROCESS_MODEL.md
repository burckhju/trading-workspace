# Trading Process Model

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokumenttyp | Fachliches Prozessmodell |
| Version | 1.0 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-08-03 |

## Grundsatz

Jeder Übergang, der eine Handelsentscheidung darstellt, wird ausschließlich durch den Benutzer ausgelöst. Das System darf prüfen, berechnen, warnen, vergleichen und dokumentieren, aber keine Handelsalternative verbindlich wählen.

## Prozessübersicht

```text
Referenzdaten pflegen
→ Markt beobachten
→ Kandidat qualifizieren
→ Trade planen
→ Optionsscheine vergleichen
→ Benutzer wählt Produkt
→ Trade manuell erfassen
→ Trade managen
→ Trade schließen
→ Nachbeobachten
→ Exit Review
→ Journal abschließen
→ Performance und Modelle bewerten
```

## Phasen

### 1. Referenzdaten pflegen

**Eintritt:** Ein Basiswert oder Produkt wird für einen späteren Prozess benötigt.
**Systemunterstützung:** Suche, Dublettenprüfung, Validierung, Statusverwaltung, Herkunftsnachweis.
**Benutzerentscheidung:** Anlage, Änderung, Deaktivierung oder Reaktivierung.
**Ergebnis:** Eindeutig referenzierbares Fachobjekt.
**Rücksprung:** Unvollständige oder widersprüchliche Daten bleiben im Bearbeitungsstatus; keine stille Ergänzung.

### 2. Markt beobachten

**Eintritt:** Markt- und Basiswertdaten stehen zur Verfügung.
**Systemunterstützung:** Darstellung und nachvollziehbare Analysen.
**Benutzerentscheidung:** Welche Märkte/Basiswerte weiter betrachtet werden.
**Ergebnis:** Beobachtete Basiswerte oder Analysen.

### 3. Kandidat qualifizieren

**Eintritt:** Ein aktiver Basiswert ist bekannt.
**Systemunterstützung:** Regeln, Scores und dokumentierte Hinweise.
**Benutzerentscheidung:** Kandidatenstatus und Priorität.
**Ergebnis:** Kandidat oder verworfene Beobachtung mit Begründung.

### 4. Trade planen

**Eintritt:** Kandidat oder manuell gewählter Basiswert.
**Systemunterstützung:** Strukturierte Erfassung, Risikoberechnung, Konsistenzprüfung.
**Benutzerentscheidung:** Annahmen, Einstieg, Stop, Ziele, Risiko und Freigabe des Plans.
**Ergebnis:** Entwurf, freigegebener oder verworfener TradePlan.

### 5. Produkt auswählen

**Eintritt:** Freigegebener TradePlan und geeignete Warrants.
**Systemunterstützung:** Filter, Vergleich, Berechnungen und dokumentierte Bewertung.
**Benutzerentscheidung:** Auswahl oder Ablehnung eines Warrants.
**Ergebnis:** Dokumentierte Benutzerauswahl; keine automatische Produktauswahl.

### 6. Trade erfassen

**Eintritt:** Benutzer hat außerhalb oder innerhalb des unterstützten Prozesses gehandelt.
**Systemunterstützung:** Erfassung und Validierung von Ausführungsdaten.
**Benutzerentscheidung:** Bestätigung der tatsächlichen Ausführung.
**Ergebnis:** Trade und Position.

### 7. Trade managen

**Eintritt:** Offene Position.
**Systemunterstützung:** Warnungen, Soll-Ist-Vergleich, Event-Historie.
**Benutzerentscheidung:** Stopänderung, Teilverkauf, Produktwechsel oder Abschluss.
**Ergebnis:** Unveränderbare Folge dokumentierter Trade Events.

### 8. Trade schließen

**Eintritt:** Position wird vollständig beendet.
**Systemunterstützung:** Vollständigkeits- und Ergebnisberechnung.
**Benutzerentscheidung:** Bestätigung des Abschlusses.
**Ergebnis:** Geschlossener Trade; Übergang zur Nachbeobachtung möglich.

### 9. Nachbeobachten und Exit Review

**Eintritt:** Geschlossener Trade.
**Systemunterstützung:** Virtuelle Weiterführung ohne reale Order, Vergleich tatsächlicher und hypothetischer Verläufe.
**Benutzerentscheidung:** Abschluss und Bewertung des Exit Reviews.
**Ergebnis:** Erkenntnisse zur Prozess- und Ausstiegsqualität.

### 10. Journal und Performance

**Eintritt:** Trade und erforderliche Reviews sind abgeschlossen.
**Systemunterstützung:** Zusammenführung, Kennzahlen und Vergleich.
**Benutzerentscheidung:** Bewertung, Kommentar und Lessons Learned.
**Ergebnis:** Finalisiertes Journal und auswertbare Performance Records.

### 11. Modelle verbessern

**Eintritt:** Ausreichende abgeschlossene und nachvollziehbare Fälle.
**Systemunterstützung:** Vergleich von Modellversionen und Ergebnissen.
**Benutzerentscheidung:** Vorschlag, Review, Freigabe oder Verwerfung einer neuen Modellversion.
**Ergebnis:** Kontrolliert versioniertes Modell; historische Ergebnisse bleiben ihrer ursprünglichen Version zugeordnet.

## Querschnittsregeln

- Keine Prozessphase führt automatisch eine Order aus.
- Keine Empfehlung wird als Benutzerentscheidung gespeichert.
- Jeder fachliche Statuswechsel besitzt Zeitpunkt und Auslöser.
- Historische Entscheidungen werden nicht durch spätere Stammdaten- oder Modelländerungen unkenntlich gemacht.
- Rücksprünge erzeugen keine parallelen Objekte, wenn dasselbe Fachobjekt weiterbearbeitet wird.


## Sprint 7A Low-input Venue Rule

TradingVenue is reference context rather than a recurring trader input. If exactly one valid venue is available for the current consumer context, the system uses or preselects it. A user choice is requested only when multiple valid venues make the choice materially relevant. Provider ambiguity is resolved through reference-data reconciliation/admin workflows rather than free-form MIC or exchange-code entry by the trader.

This rule does not add Venue fields to TradePlan and does not implement FT-004 Warrant or FT-008 Product Selection.
