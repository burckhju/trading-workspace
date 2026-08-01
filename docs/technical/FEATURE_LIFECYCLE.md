# Feature Lifecycle

> Verbindlicher Lebenszyklus für Features, Fehlerkorrekturen und fachliche Modelländerungen im Trading Workspace

---

# Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument-ID | DOC-017 |
| Dokument | FEATURE_LIFECYCLE.md |
| Dokumenttyp | Development Standard |
| Version | 1.1 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-08-01 |
| Freigegeben durch | noch offen |
| Freigabedatum | noch offen |

---

# Zweck

Dieses Dokument definiert den verbindlichen Lebenszyklus für

- neue Features,
- Erweiterungen bestehender Features,
- Fehlerkorrekturen,
- technische Verbesserungen,
- Änderungen an fachlichen Regeln,
- Änderungen an Handels- und Bewertungsmodellen.

Es stellt sicher, dass jede Änderung

- nachvollziehbar,
- reproduzierbar,
- überprüfbar,
- testbar,
- versioniert und
- kontrolliert freigegeben

wird.

Eine Implementierung allein bedeutet nicht, dass eine Änderung abgeschlossen ist.

---

# Grundsatz

Jede Änderung durchläuft einen kontrollierten Prozess von der Idee bis zur Beobachtung im Betrieb.

Trading Workspace trifft keine Handelsentscheidungen.

Auch ein Feature darf daher keine autonome Kauf-, Verkaufs-, Halte- oder Positionsgrößenentscheidung einführen.

---

# Geltungsbereich

Der Lebenszyklus gilt für Änderungen in:

```text
backend/
frontend/
docs/
tests/
scripts/
docker/
.github/
```

Er gilt außerdem für:

- Datenmodelle,
- APIs,
- Provider-Integrationen,
- Berechnungslogik,
- Regelwerke,
- Modellversionen,
- Benutzeroberflächen,
- Workflows,
- Betriebs- und Qualitätssicherung.

---

# Änderungskategorien

## Feature

Neue fachliche Funktion oder wesentliche Erweiterung.

Beispiele:

- neue Kandidatenbewertung,
- neue Trade-Plan-Funktion,
- neues Journalmodul,
- neue Performanceauswertung.

## Fehlerkorrektur

Korrektur eines nachweisbaren Fehlverhaltens.

## Technische Verbesserung

Änderung ohne beabsichtigte fachliche Verhaltensänderung.

Beispiele:

- Refactoring,
- Performanceverbesserung,
- Dependency-Update,
- CI-Anpassung.

## Fachliche Regeländerung

Änderung einer validierenden, bewertenden oder steuernden Fachregel.

## Modelländerung

Änderung an einem Handels-, Bewertungs-, Ranking- oder Analysemodell.

Eine Modelländerung erzeugt grundsätzlich eine neue Modellversion.

---

# Rollen

## Benutzer beziehungsweise Product Owner

Verantwortlich für:

- fachliche Zielsetzung,
- Priorisierung,
- fachliche Entscheidungen,
- Abnahme,
- Freigabe fachlicher Regeln und Modellversionen.

## Entwickler

Verantwortlich für:

- technische Analyse,
- Implementierung,
- Tests,
- technische Dokumentation,
- transparente Darstellung offener Punkte.

## Reviewer

Verantwortlich für:

- Prüfung von Architektur,
- Qualität,
- Nachvollziehbarkeit,
- Tests,
- Risiken und Abweichungen.

## Modellverantwortlicher

Verantwortlich für:

- fachliche Definition des Modells,
- Versionsentscheidung,
- Dokumentation von Eingaben, Annahmen und Ergebnissen,
- Freigabe neuer Modellversionen.

In einem kleinen Projekt können mehrere Rollen von derselben Person wahrgenommen werden. Die Verantwortlichkeiten bleiben dennoch getrennt zu betrachten.

---

# Lebenszyklus

Der verbindliche Ablauf besteht aus zwölf Phasen:

```text
1. Idee
2. Analyse
3. Spezifikation
4. Architekturprüfung
5. Freigabe zur Umsetzung
6. Implementierung
7. technische Prüfung
8. fachliche Prüfung
9. Abnahme
10. Veröffentlichung
11. Beobachtung
12. Verbesserungsvorschlag
```

Keine Phase darf stillschweigend übersprungen werden.

Bei kleinen Änderungen dürfen Phasen in einem Dokument zusammengefasst werden, ihre Kriterien müssen jedoch weiterhin erfüllt sein.

---

# Phase 1 – Idee

## Ziel

Eine mögliche Änderung wird als nachvollziehbarer Vorschlag erfasst.

## Erforderliche Angaben

- Titel,
- Problem oder Anlass,
- erwarteter Nutzen,
- betroffener Benutzerprozess,
- betroffene Features,
- grobe Priorität,
- bekannte Risiken.

## Eintrittskriterium

Ein konkreter Bedarf, Fehler oder Verbesserungsvorschlag liegt vor.

## Austrittskriterium

Die Idee ist dokumentiert und einer verantwortlichen Person zugeordnet.

## Nicht zulässig

- direkte Implementierung ohne erfassten Anlass,
- Lösungsvorgabe ohne beschriebenes Problem,
- Vermischung mehrerer unabhängiger Ziele.

---

# Phase 2 – Analyse

## Ziel

Problem, Ausgangszustand und Auswirkungen werden verstanden.

## Zu prüfen

- aktuelles Verhalten,
- fachliche Ursache,
- technische Ursache,
- betroffene Daten,
- betroffene Schnittstellen,
- betroffene Dokumente,
- Auswirkungen auf bestehende Trades,
- Auswirkungen auf historische Auswertungen,
- Sicherheits- und Datenschutzfolgen,
- Migrationsbedarf,
- Rückwärtskompatibilität.

## Ergebnis

Eine dokumentierte Analyse mit klarer Abgrenzung.

## Austrittskriterium

Es ist bekannt,

- was geändert werden soll,
- was ausdrücklich nicht geändert wird,
- welche Artefakte betroffen sind,
- welche Risiken bestehen.

---

# Phase 3 – Spezifikation

## Ziel

Die erwartete Änderung wird prüfbar beschrieben.

## Mindestinhalt

- fachliches Ziel,
- Benutzerablauf,
- Eingaben,
- Ausgaben,
- Regeln,
- Validierungen,
- Fehlerfälle,
- Akzeptanzkriterien,
- Datenquellen,
- Modell- oder Regelversion,
- Nachvollziehbarkeitsanforderungen,
- Testfälle.

## Akzeptanzkriterien

Akzeptanzkriterien müssen beobachtbar und überprüfbar sein.

Nicht ausreichend:

```text
Die Funktion soll gut funktionieren.
```

Ausreichend:

```text
Wenn Marktdaten älter als der konfigurierte Grenzwert sind,
zeigt das System eine Warnung und kennzeichnet das Ergebnis als veraltet.
```

## Austrittskriterium

Die Spezifikation ist vollständig genug, um Implementierung und Tests eindeutig abzuleiten.

---

# Phase 4 – Architekturprüfung

## Ziel

Die Änderung wird gegen die verbindliche Architektur geprüft.

## Zu prüfen

- zuständiges Feature,
- Abhängigkeitsrichtung,
- Datenmodell,
- API-Vertrag,
- Provider-Abhängigkeiten,
- Ereignisse und Contracts,
- Teststrategie,
- Migrationen,
- Logging und Audit,
- Sicherheitsfolgen,
- Deploymentfolgen.

## Architekturentscheidung

Eine dokumentierte Architekturentscheidung ist erforderlich, wenn

- neue Hauptkomponenten entstehen,
- bestehende Abhängigkeitsregeln geändert werden,
- neue externe Systeme angebunden werden,
- Datenverantwortung verschoben wird,
- ein bestehender Contract gebrochen wird.

## Austrittskriterium

Die technische Lösung ist freigegeben oder offene Architekturfragen sind ausdrücklich als Blocker dokumentiert.

---

# Phase 5 – Freigabe zur Umsetzung

## Ziel

Die Änderung wird bewusst für die Implementierung freigegeben.

## Erforderliche Voraussetzungen

- Analyse abgeschlossen,
- Spezifikation vorhanden,
- Architektur geprüft,
- Akzeptanzkriterien definiert,
- Risiken dokumentiert,
- Priorität bestätigt,
- Verantwortlichkeit festgelegt.

## Freigabeentscheidung

Die Freigabe beantwortet:

```text
Darf diese Änderung jetzt umgesetzt werden?
```

Sie ist keine fachliche Endabnahme.

## Austrittskriterium

Eine eindeutige Freigabe oder Ablehnung ist dokumentiert.

---

# Phase 6 – Implementierung

## Ziel

Die freigegebene Änderung wird umgesetzt.

## Regeln

- nur freigegebener Umfang,
- Coding Standards einhalten,
- bestehende Architektur einhalten,
- keine versteckten fachlichen Defaultwerte,
- keine unversionierte Modelländerung,
- Tests parallel erstellen,
- Dokumentation parallel aktualisieren,
- Migrationen prüfen,
- keine Zugangsdaten einchecken.

## Modelländerungen

Bei einer Modelländerung müssen mindestens dokumentiert werden:

- Modellname,
- bisherige Version,
- neue Version,
- Änderungsgrund,
- geänderte Regeln oder Parameter,
- erwartete Auswirkungen,
- bekannte Einschränkungen,
- Vergleich zur Vorgängerversion.

## Austrittskriterium

Implementierung, Tests, Migrationen und Dokumentation sind vollständig im Arbeitsstand enthalten.

---

# Phase 7 – Technische Prüfung

## Ziel

Die technische Qualität und Reproduzierbarkeit werden geprüft.

## Verbindliche Prüfungen

Je nach betroffenem Bereich:

```bash
bash scripts/check-backend.sh
bash scripts/check-frontend.sh
bash scripts/run-e2e.sh
bash scripts/verify-release-readiness.sh
```

Zusätzlich:

```bash
git diff --check
git diff
```

## Zu prüfen

- Typprüfung,
- Linting,
- Formatierung,
- Unit-Tests,
- Integrationstests,
- Contract-Tests,
- Workflow-Tests,
- E2E-Tests,
- Build,
- Migrationen,
- Docker-Konfiguration,
- Sicherheitsrisiken,
- Geheimnisse,
- Abhängigkeiten.

## Austrittskriterium

Alle erforderlichen technischen Prüfungen sind erfolgreich oder verbleibende Blocker sind ausdrücklich dokumentiert und verhindern die Freigabe.

---

# Phase 8 – Fachliche Prüfung

## Ziel

Es wird geprüft, ob die Implementierung die fachliche Spezifikation erfüllt.

## Zu prüfen

- Akzeptanzkriterien,
- Benutzerablauf,
- Eingaben und Ausgaben,
- fachliche Validierungen,
- Warnungen,
- Nachvollziehbarkeit,
- Modellversion,
- historische Zuordnung,
- keine autonome Handelsentscheidung,
- verständliche Darstellung.

## Für Berechnungen und Empfehlungen

Mindestens sichtbar beziehungsweise referenzierbar:

- Datenquelle,
- Datenstand,
- Modell,
- Version,
- Eingaben,
- Konfiguration,
- Ergebnis,
- Warnungen,
- Einschränkungen.

## Austrittskriterium

Die fachliche Prüfung ist bestanden oder konkrete Abweichungen sind dokumentiert und zur Korrektur zurückgegeben.

---

# Phase 9 – Abnahme

## Ziel

Der fachlich Verantwortliche entscheidet über die Annahme der Änderung.

## Mögliche Ergebnisse

```text
angenommen
angenommen mit dokumentierten Restpunkten
abgelehnt
zur Überarbeitung zurückgegeben
```

## Mindestvoraussetzungen

- Akzeptanzkriterien erfüllt,
- technische Prüfung erfolgreich,
- fachliche Prüfung erfolgreich,
- Dokumentation vollständig,
- Risiken bekannt,
- Modellversion freigegeben, falls betroffen,
- keine kritischen offenen Fehler.

## Austrittskriterium

Eine datierte und verantwortete Abnahmeentscheidung ist dokumentiert.

---

# Phase 10 – Veröffentlichung

## Ziel

Die abgenommene Änderung wird kontrolliert in die Zielumgebung übernommen.

## Zu dokumentieren

- Release oder Commit,
- Datum,
- enthaltene Änderungen,
- Migrationen,
- Konfigurationsänderungen,
- Rollback-Möglichkeit,
- bekannte Einschränkungen,
- verantwortliche Person.

## Vor Veröffentlichung

- erforderliche CI-Prüfungen erfolgreich,
- Branch Protection erfüllt,
- Zielkonfiguration geprüft,
- Backups und Migrationen bewertet,
- Release Notes vorhanden.

## Austrittskriterium

Die Änderung ist in der Zielumgebung verfügbar und technisch überprüft.

---

# Phase 11 – Beobachtung

## Ziel

Das Verhalten der Änderung wird nach Veröffentlichung kontrolliert.

## Zu beobachten

- technische Fehler,
- Datenqualität,
- Providerprobleme,
- Benutzerprobleme,
- Performance,
- unerwartete fachliche Ergebnisse,
- Abweichungen zwischen Erwartung und Realität.

## Trading-spezifisch

Abgeschlossene Trades und Berechnungsergebnisse werden weiterhin der verwendeten Modellversion zugeordnet.

Eine spätere Modelländerung verändert historische Zuordnungen nicht.

## Austrittskriterium

Die definierte Beobachtungsperiode ist beendet oder es wurde ein neuer Fehler- beziehungsweise Verbesserungsvorschlag erzeugt.

---

# Phase 12 – Verbesserungsvorschlag

## Ziel

Erkenntnisse werden kontrolliert in einen neuen Lebenszyklus überführt.

## Quellen

- abgeschlossene Trades,
- Journalinformationen,
- Performanceanalysen,
- Fehlerberichte,
- Benutzerfeedback,
- Provideränderungen,
- technische Messwerte.

## Grundregel

Erkenntnisse dürfen ein Modell oder Regelwerk nicht automatisch verändern.

Sie erzeugen ausschließlich einen neuen Vorschlag für

- Analyse,
- Regeländerung,
- Modelländerung,
- neues Feature oder
- Fehlerkorrektur.

Der neue Vorschlag beginnt wieder in Phase 1.

---

# Modellversionierung

## Wann ist eine neue Version erforderlich?

Eine neue Modellversion ist erforderlich bei Änderungen an:

- Regeln,
- Formeln,
- Gewichtungen,
- Schwellenwerten,
- Eingabefeldern,
- Datenquellen,
- Datenaufbereitung,
- Rankinglogik,
- Risikoermittlung,
- Produktauswahl,
- Ausstiegskriterien.

## Historische Stabilität

Bereits geplante, eröffnete oder abgeschlossene Trades bleiben mit der damals verwendeten Modellversion verknüpft.

Nicht zulässig:

- stillschweigendes Überschreiben alter Modellversionen,
- rückwirkende Neuberechnung ohne Kennzeichnung,
- Vermischung von Ergebnissen verschiedener Versionen.

## Vergleich neuer Versionen

Eine neue Modellversion soll vor Freigabe gegen die Vorgängerversion verglichen werden.

Zu dokumentieren:

- Testdatensatz,
- Eingaben,
- Ergebnisse beider Versionen,
- Abweichungen,
- fachliche Bewertung,
- Freigabeentscheidung.

---

# Fehlerkorrekturen

Fehlerkorrekturen durchlaufen denselben Lebenszyklus, dürfen aber kompakter dokumentiert werden.

Mindestanforderungen:

- Fehlerbeschreibung,
- Reproduktionsschritte,
- Ursache,
- Korrektur,
- Regressionstest,
- Auswirkungen,
- Review,
- Abnahme.

Ein Bugfix soll einen Test enthalten, der den Fehler vor der Korrektur nachweist.

---

# Technische Änderungen

Technische Änderungen ohne beabsichtigte Fachänderung müssen nachweisen, dass das fachliche Verhalten unverändert bleibt.

Beispiele:

- Refactoring,
- Bibliotheksupdate,
- Buildänderung,
- CI-Anpassung,
- Performanceoptimierung.

Erforderlich sind mindestens:

- technische Begründung,
- Risikoanalyse,
- passende Tests,
- Review,
- dokumentiertes Ergebnis.

---

# Dokumentationsartefakte

Je nach Änderung sind mindestens zu aktualisieren:

```text
docs/foundation/
docs/features/
docs/reference/
docs/architecture/
docs/technical/
docs/implementation/
```

Außerdem gegebenenfalls:

- API-Spezifikation,
- Datenmodell,
- Modellbuch,
- Traceability,
- Entscheidungsprotokoll,
- Release Notes,
- Betriebsanleitung.

Dokumentation wird im selben Pull Request wie die Änderung aktualisiert.

---

# Definition of Ready

Eine Änderung ist bereit zur Umsetzung, wenn:

```markdown
- [ ] Problem oder Ziel ist dokumentiert.
- [ ] Umfang und Nicht-Umfang sind definiert.
- [ ] Akzeptanzkriterien sind prüfbar.
- [ ] Betroffene Features und Dateien sind bekannt.
- [ ] Datenquellen und Modelle sind benannt.
- [ ] Architektur wurde geprüft.
- [ ] Risiken und Migrationen wurden bewertet.
- [ ] Verantwortlichkeit ist festgelegt.
- [ ] Umsetzung wurde freigegeben.
```

---

# Definition of Done

Eine Änderung ist abgeschlossen, wenn:

```markdown
- [ ] Implementierung entspricht der freigegebenen Spezifikation.
- [ ] Coding Standards sind eingehalten.
- [ ] Erforderliche Tests sind vorhanden und erfolgreich.
- [ ] Typprüfung, Linting und Formatprüfung sind erfolgreich.
- [ ] Build und gegebenenfalls Docker-Prüfung sind erfolgreich.
- [ ] Migrationen sind geprüft.
- [ ] Dokumentation ist aktualisiert.
- [ ] Datenquelle, Modellversion, Eingaben und Ergebnisse sind nachvollziehbar.
- [ ] Keine autonome Handelsentscheidung wurde eingeführt.
- [ ] Technisches Review ist abgeschlossen.
- [ ] Fachliche Prüfung ist abgeschlossen.
- [ ] Abnahme ist dokumentiert.
- [ ] Offene Restpunkte und Risiken sind dokumentiert.
- [ ] Veröffentlichung und Beobachtung sind vorbereitet.
```

---

# Rücksprungregeln

Eine Änderung geht in eine frühere Phase zurück, wenn

- Anforderungen unklar werden,
- neue Risiken auftreten,
- Architektur geändert werden muss,
- Akzeptanzkriterien nicht erfüllt sind,
- Tests fehlschlagen,
- fachliche Prüfung Abweichungen feststellt,
- Abnahme verweigert wird.

Rücksprünge sind normal und werden dokumentiert.

---

# Nicht zulässig

Nicht zulässig sind:

- Implementierung ohne dokumentierten Anlass,
- Freigabe ohne prüfbare Akzeptanzkriterien,
- Modelländerung ohne neue Version,
- automatische Modelländerung aus Performanceergebnissen,
- rückwirkendes Überschreiben historischer Ergebnisse,
- autonome Handelsentscheidungen,
- Überspringen von Tests und Review,
- Freigabe trotz kritischer offener Fehler,
- undokumentierte Architekturabweichung,
- Veröffentlichung ohne nachvollziehbare Abnahme.

---

# Freigabe dieses Dokuments

Dieses Dokument kann auf `🟢 Approved` gesetzt werden, wenn

- Rollen und Verantwortlichkeiten bestätigt sind,
- die Lebenszyklusphasen mit dem tatsächlichen Entwicklungsprozess übereinstimmen,
- Definition of Ready und Definition of Done akzeptiert sind,
- Modellversionierung und historische Zuordnung fachlich bestätigt sind,
- Freigabeverantwortung und Freigabedatum eingetragen wurden.

Bis dahin bleibt der Status `🔵 Review`.

---

# Siehe auch

- `docs/architecture/Source_Architecture.md`
- `docs/technical/CODING_STANDARDS.md`
- `docs/technical/DEVELOPMENT_GUIDE.md`
- `docs/foundation/MODEL_BOOK.md`
- `docs/foundation/TRACEABILITY.md`
- `docs/technical/FEATURE_IMPLEMENTATION_TEMPLATE.md`

---

# Änderungshistorie

| Version | Datum | Änderungen |
|---|---|---|
| 1.0 | 2026-07-22 | Erstversion |
| 1.1 | 2026-08-01 | Vollständige Definition der Lebenszyklusphasen, Rollen, Freigaben, Modellversionierung, Definition of Ready und Definition of Done |
