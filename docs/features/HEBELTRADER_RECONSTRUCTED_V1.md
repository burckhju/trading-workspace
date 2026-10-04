# Hebeltrader: rekonstruierte Regelvorschau V1

## Status und fachliche Grenze

Implementierter, **nicht automatisch aktivierter Vorschlagsrechner** unter
`HEBELTRADER_RECONSTRUCTED_V1`. Keine Behauptung, den unveröffentlichten
Originalalgorithmus des Herausgebers identisch reproduziert zu haben.

Die Oberfläche ergänzt den **manuellen** FT-007-TradePlan-Workflow. Sie berechnet
Aktienmarken und erstellt nur nach separater Benutzerbestätigung über den
bestehenden Create-Endpunkt einen neuen **DRAFT**. Review und Approval bleiben
unverändert. Candidate-Provenance wird nicht in einen manuellen Ursprung umgebogen.
Bestehende Pläne, Positionen, ATR-Stopps (`DYNAMIC_STOP_V1`), Alerts, Brokeraufträge
und Governed-Model-Aktivierungen werden nicht geändert.

Die übrigen Endpunkte sind zustandslose, manuell mit Daten zu versorgende
Prüfungen. Insbesondere gibt es **keinen automatisch laufenden Hebeltrader-
Positionsmonitor**, keinen neuen Marktdaten-/Kalenderprovider und keine
Orderausführung. Die Produktauswahl muss Vertragsdaten und Anbieterqualität
weiterhin separat verifizieren.

## Evidenz und ausdrücklich eigene Entscheidungen

Grundlage ist die Auswertung der 135 vom Benutzer bereitgestellten Empfehlungen
vom 07.01. bis 11.09.2026. Vollständige PDFs und Auswertungsdateien werden nicht in
das öffentliche Repository kopiert. Die Beispiele in Tests sind minimale
numerische Regressionen, keine Veröffentlichung der Börsenbriefe.

| Regel | Grundlage | Umsetzung |
| --- | --- | --- |
| Aktienziele um GD200 | Empirische Rekonstruktion; nicht ausnahmslos | T1 = GD200 + B; T2 = GD200 + 2B |
| Breite B | Originalfenster und Skalierung unbekannt | B ist ein expliziter, begründeter Eingabewert; kein erfundener Standardwert |
| Initialstopp | Technische Unterstützung, häufig GD50/GD200 | Unterstützung explizit wählen; optionalen Puffer offen angeben |
| Long-Filter | Kurs über GD200 in allen ausgewerteten Beispielen | Als rekonstruiertes Eingangskriterium implementiert, nicht als bewiesene allgemeine Verlagsregel |
| Fundamentale These | Methodentext | Manuelle Bestätigung; keine vorgetäuschte Fundamentalanalyse |
| Mindest-Stoppabstand | Veröffentlichte 2%-Regel, später Aktienbezug präzisiert | Immer auf der Aktienachse messen |
| T1 / T2 | Veröffentlichte Positionsführung | 50% der ursprünglichen Position / Rest |
| Zeitregeln | Späterer veröffentlichter Stand | Neuester Management-Stand ab 10.08.2026; keine automatische Rückübertragung |
| Nie sinkender Stopp | **Eigene Konsistenzentscheidung** | max(bisheriger Stopp, Einstand, 0,8 × T1) |
| Call OTM | Beobachtetes Auswahlmuster | Im separaten Call-Einstiegscheck als rekonstruiertes Kriterium |
| Kursalter / Analysealter | **Eigene Datenqualitätsgrenzen** | Höchstens 3600 Sekunden / 7 Kalendertage |
| Geld-/Briefseite, Fill-Bestätigung | **Eigene technische Präzisierung** | Einstieg zum Brief, Ausstiegssignal am Geld; kein erfundener Fill |

## Deterministische Regeln

### HT-01: Eingaben und Einheiten

Alle Preise sind endliche `Decimal`-Werte. Eine einzelne Preisachse verwendet
immer dieselbe Hauptwährungseinheit. GBp muss vor Übergabe in GBP umgerechnet
werden; Aktie, Basispreis und deren Ziele dürfen nicht unterschiedlich skaliert
sein. Das System konvertiert diese Einheiten nicht stillschweigend.

Es gilt `0 < L < E < T1 < T2`. Fehlende oder widersprüchliche Eingaben werden
zurückgewiesen. Quotes benötigen Geld, Brief, Quelle, ISO-Währung und einen
Zeitstempel mit Zeitzone. Geld darf null sein, aber nicht über Brief liegen.
Veraltete oder zukünftige Quotes ergeben keinen zulässigen Einstieg.

### HT-02: Technische Marken

Für generierte Aktienmarken:

```text
L  = floor_to_tick(Unterstützung × (1 − Puffer))
T1 = floor_to_tick(GD200 + B)
T2 = floor_to_tick(GD200 + 2 × B)
```

Unterstützung ist explizit GD200, GD50 oder über die API ein manuelles Niveau
unterhalb des Einstiegskurses. Der Puffer liegt zwischen 0 einschließlich und 1
ausschließlich; Standard 0 bedeutet **keinen angenommenen Verlags-Puffer**.
Gerundet wird auf ein echtes Tick-Vielfaches, auch bei Tickgrößen wie 0,05.

Alternativ akzeptiert `/preview` `published_levels`. Diese Originalwerte werden
nicht verändert. `abs((2*T1−T2)−GD200)/GD200 > 0,02` erzeugt einen Prüfhinweis,
keine heimliche Korrektur. B und veröffentlichte Marken sind alternative Eingaben.

### HT-03: Einstieg und CRV

Einstieg nur nach fundamentalem Review, bei Aktienkurs strikt über GD200,
Aktien-Stoppabstand `(Aktienkurs − Aktienstopp)/Aktienkurs >= 0,02`, positivem
Risiko und Ertrag und noch nicht ausgeschöpftem Ziel. Die 2%-Grenze wird niemals
auf das Optionsscheinpremium angewandt. Es wird **kein unbelegtes Mindest-CRV**
vorausgesetzt.

```text
CRV_normal = (((T1 + T2) / 2) − Brief) / (Brief − L)
```

Jeder geänderte Einstieg verändert das CRV. Es handelt sich um ein Brutto-
Szenarioverhältnis ohne Kosten oder Slippage, nicht um Erwartungswert,
Erfolgswahrscheinlichkeit oder garantierte Verlustgrenze.

Historisch bereits erreichtes T1 muss als `target1_seen` mitgegeben werden,
auch nach einem Rücksetzer. Ein aktueller Geldkurs ab T1 zählt ebenfalls.
Dann beträgt die vorgeschlagene Allokation 0,5, Stopp ist der ursprünglich
empfohlene Einstieg und nur T2 bleibt als Ziel:

```text
CRV_spaet = (T2 − Brief) / (Brief − ursprünglicher Einstieg)
```

Kein fiktiver T1-Verkauf wird gutgeschrieben. Bereits erreichtes T2 sperrt den
Einstieg. T2-Historie erfordert auch T1-Historie. Überschreitet nur der Brief T1,
nicht der Geldkurs, wird nicht automatisch ein verpasster T1-Verkauf angenommen.
Die generierte Markenvariante benötigt einen Einstieg unter T1; ein später
Einstieg wird anhand unveränderter `published_levels` geprüft.

### HT-04: Separate Call-Bewertung

`/entry-check` prüft separate Aktien- und Call-Marken. Für Calls sind Basispreis,
Handelskalender und verifizierter letzter Handelstag erforderlich. Der Basispreis
muss über dem Aktien-Empfehlungseinstieg liegen, die Restzeit über 20 Sitzungen.

`/call-scenario` berechnet ausschließlich einen **theoretischen europäischen
Call** nach Black-Scholes-Merton mit stetiger Dividendenrendite und ACT/365.
Jedes Szenario benötigt Aktienkurs, Basispreis, Bezugsverhältnis,
Bewertungsdatum, Ausübungsdatum, implizite Volatilität, Zins,
Dividendenrendite, FX und beide Währungen. FX ist die Zahl der Einheiten der
Optionsscheinwährung pro Einheit der Aktienwährung; bei gleicher Währung FX=1.
Historische Volatilität ersetzt die implizite Volatilität nicht automatisch.

Keine lineare Omega-Hochrechnung. Keine automatische Zuordnung zwischen
Aktienziel und garantiertem Call-Kurs. Für Stopp, T1 und T2 sind getrennte
Bewertungszeit-/IV-/FX-Szenarien aufzurufen. Amerikanische Ausübung, Quanto,
Barrieren, diskrete Dividenden, Emittentenausfall und Geld-/Briefaufschläge sind
nicht modelliert. Nicht unterstützte Vertragsformen werden zurückgewiesen.

### HT-05: Zustandslose Positionsführung

`/management-preview` liefert einen Prüfhinweis, **keine Ausführung**. Der Caller
muss den tatsächlichen Einstand, aktuellen Stopp, Restbestand und bestätigte
T1-Ausführung liefern. Unterstützte Restanteile sind 1, 0,5 und 0 der ursprünglich
vorgesehenen Position. Andere Teilfüllungen benötigen separate Bearbeitung und
werden nicht in ein angebliches Standardportfolio umgerechnet.

| Bedingung | Rückgabe |
| --- | --- |
| Position bereits geschlossen | NONE |
| Höchstens 20 Sitzungen bis letztem Handelstag | EXIT_REVIEW, gesamter Rest |
| Fehlender oder nicht aktueller Geldkurs | DATA_REQUIRED |
| Geldkurs am oder unter wirksamem Stopp | EXIT_REVIEW, gesamter Rest |
| Ab 20 Sitzungen Haltedauer und Geldkurs unter tatsächlichem Einstand | EXIT_REVIEW, gesamter Rest |
| Geldkurs ab T2 | EXIT_REVIEW, gesamter Rest |
| Geldkurs ab T1, T1-Verkauf noch nicht bestätigt | PARTIAL_EXIT_REVIEW, 0,5 der ursprünglichen Position |
| Sonst | HOLD_REVIEW |

Diese Reihenfolge ist die Priorität bei gleichzeitig erfüllten Bedingungen.
Ein Sprung über T2 erzeugt kein ausgedachtes T1-Fill zu einem anderen Kurs.
Ein T1-Signal ändert den Stopp nicht; erst ein extern bestätigter Verkauf führt
zum Einstandsstopp. Nach weiteren 20 Sitzungen gilt der nie sinkende Folgestopp.
Bei spätem Einstieg bleibt der ursprüngliche Empfehlungseinstieg die
Einstandsmarke der Regel; der Nachzieh-Timer startet am tatsächlichen Einstieg.
Gleiche Eingaben liefern gleiche Ergebnisse, keine versteckten Zustandsänderungen.

### HT-06: Handelstage und Gültigkeit

Kalender benötigen Handelsplatz, Zeitzone, Quelle, Abdeckungsgrenzen und eine
vollständige, streng aufsteigende Liste der tatsächlichen Börsensitzungen.
Der Rechner prüft Konsistenz und Abdeckung, **nicht die Wahrheit einer vom
Caller behaupteten Feiertagsliste**. Produktiv ist ein verifizierter Provider
anzuschließen. Er erzeugt selbst keine Montag-bis-Freitag-Ersatzkalender.

Gezählt wird `(Startdatum, Enddatum]`: Einstiegstag zählt als 0.
Das Bewertungsdatum wird in der angegebenen Börsenzeitzone bestimmt.
Fehlende Kalenderabdeckung führt zum Fehler statt zu vermeintlich null Tagen.
Für die Laufzeitregel zählt der letzte **Handelstag**, nicht der spätere Zahltag.
Management-Anfragen vor 10.08.2026 werden zurückgewiesen. Ein Backtest älterer
Fassungen erfordert eigene Policy-Versionen und Forward-Kursdaten.

## Verwendung in der Oberfläche

Im manuellen TradePlan-Workflow einen aktiven Basiswert auswählen und
**Hebeltrader-Regelvorschau** öffnen. Aktien-Geld/Brief, GD200, optional GD50,
explizite Bandbreite B, Puffer, Tickgröße, Zeitstempel und begründete Quelle
angeben. Fundamentale These separat bestätigen und Vorschau berechnen.

Erst die zusätzliche Bestätigung der Rekonstruktion und ein Klick auf
**Geprüften Entwurf anlegen** speichern den neuen Aktien-DRAFT. Anschließend
läuft der bestehende Review-/Approval-Prozess. Ein Wechsel des Basiswerts oder
der Eingaben verwirft die alte Vorschau. Call-Szenarien und Management-Prüfungen
sind in dieser Version über die API erreichbar, nicht als neue laufende
Überwachung oder Brokerfunktion in der Oberfläche.

## API und Beispiel

Basis: `/api/v1/trade-plans/strategies/hebeltrader`

- `GET /rules`: Regelmanifest und offengelegte Implementierungsentscheidungen.
- `POST /preview`: Aktienvorschau mit optionalem produktneutralem Draft-Inhalt.
- `POST /entry-check`: getrennter Aktien-/Call-Einstiegscheck.
- `POST /call-scenario`: explizite theoretische Call-Bewertung.
- `POST /management-preview`: zeitabhängiger, zustandsloser Management-Hinweis.

Synthetisches, historisch datiertes API-Beispiel, **keine aktuelle Notierung**:

```json
{
  "as_of": "2026-09-11T16:00:00+02:00",
  "analysis_date": "2026-09-11",
  "source_ref": "synthetisches Beispiel; B explizit mit 30 angesetzt",
  "quote": {
    "bid": "100", "ask": "101", "currency": "EUR",
    "observed_at": "2026-09-11T15:59:00+02:00", "source": "synthetisch"
  },
  "gd200": "95", "band_width": "30", "support_source": "GD200",
  "buffer_fraction": "0", "tick": "0.01", "fundamental_ok": true
}
```

Ergebnis: L=95, T1=125, T2=155; Aktien-Stoppdistanz=5%; CRV=(140−101)/(101−95)=6,5.
Alle Antworten kennzeichnen `execution_enabled=false`. Snapshot und SHA-256-
Digest im Draft-Risikotext ermöglichen Nachvollziehbarkeit, sind jedoch keine
kryptografische Quellenverifikation und keine registrierte Model-Aktivierung.

## Tests und Grenzen der Prüfung

Die mitgelieferten isolierten Backend-Tests decken BP-/MTU-CRV, Intel-Bandabweichung,
Geld-/Briefseite, Kursalter, Währungsachsen, 2%- und 20-Sitzungs-Grenzen,
Feiertagslücken, Fill-Bestätigung, Folgestopp-Monotonie und Call-Modellgrenzen ab.
Originalabweichungen werden nicht als vermeintlich bereinigte Daten versteckt.
Die Kurvenauswertung aus dem Vorlauf der Empfehlungen ist kein Forward-Backtest.

```bash
cd backend
PYTHONPATH=.:.. pytest ../tests/unit/backend/test_hebeltrader*.py
```

Die lokale Prüfung wurde gegen die neuen Module und einen Auszug der bestehenden
DTO-Verträge ausgeführt, nicht gegen eine vollständige PostgreSQL-Installation.
Repository-weite Lint-, Typ-, Frontend-, Integrations- und E2E-Prüfungen bleiben
separate Qualitätsstufen; eine isolierte grüne Testsuite ist keine Behauptung,
dass diese Stufen bereits bestanden sind.
