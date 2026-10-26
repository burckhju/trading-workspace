# UI4 — Tradeübersicht und Buchungsansicht konsolidieren

## Auftrag, Basis und Übergabegrenze

UI4 führt die bestehende Trade-/Positionsübersicht und die Datums-/Währungsaktionen
in einer gemeinsamen Buchungsansicht zusammen. Vorhandene Werte werden gelesen,
wirksame Ausführungen einmal angezeigt und Änderungen an die genaue Buchung
gebunden. Ursprüngliche Fakten, Korrekturketten und Währungsquellen bleiben erhalten.

Geprüfte Ausgangsbasis vom **26.10.2026**: `main`
`f8f61a11f65e9b36735704a2fabc3e4e953d4a77`, **Version 1.5.21**. Die integrierten
Produkt-/Tradeplan-Schnitte #285 und #284 bleiben erhalten. UI4 arbeitet auf dem
eigenen Branch `refactor/trade-bookings-consolidation` in einem eigenen Worktree.
Der parallel gelesene UI3-Branch `refactor/lesson-detail-consolidation` hatte
zunächst den Implementierungshead `986f20a2`. Vor Übergabe wurde sein
[Draft-PR #286](https://github.com/burckhju/trading-workspace/pull/286) mit Head
`89bad2a4ecfb5915c78dacde150edea533f6b0f0` einschließlich Dokumentationsfortschreibung
erneut gelesen. Seine Learning-/Hypothesenänderungen und gemeinsamen
Journal-Browseranpassungen werden durch UI4 nicht übernommen oder verändert.
Backlogergänzungen bleiben in den getrennten Trade-Abschnitten; die UI4-Traceability
steht neben der vorhandenen Kaufwährungs-/Tradequellenzuordnung außerhalb des
unveränderten historischen Baselineblocks.

Die Übergabe ist ein **geprüfter Implementierungsstand als Draft-PR**. Der
abschließende PR bindet Implementierungscommit, tatsächlich geprüften Tree,
lokale Ergebnisse und reguläre CI-Läufe. Die Basis-SHA oben ist kein Testnachweis
für die Änderung. Arbeitsstatus bleibt ausschließlich im
[Product Backlog](../planning/PRODUCT_BACKLOG.md#pb-017-history).

## Zuständigkeiten und Datenfluss

| Bereich | Umsetzung und Verantwortungsgrenze |
|---|---|
| Trade und Position | `TradeManagementPage` zeigt Produktbezug, Status, offene Menge, Öffnungs-/Schlussdatum, Kostenbasis, durchschnittlichen Einstieg und realisiertes Bruttoergebnis in einer Übersicht. Mengen und Ergebnisse stammen aus `PositionResponse`; keine neue Frontendrechnung. Fehlende Beträge werden nicht zu Null. |
| Ein gemeinsamer Buchungsstand | `ExecutionDatesPanel` besitzt den Timeline-Read für „Aktuelle Buchungen“, „Historie“ und den ausgewählten Editor. Die aktuelle Liste verwendet unverändert `effectiveExecutions`. |
| Historie | `TradeTimelinePanel` ist eine rein lesende Darstellung der übergebenen Timeline. Es lädt keinen unabhängigen Stand. Originale, Nachfolger, Managementereignisse und Stornierung behalten vollständige IDs und Zeitangaben. |
| Alerts | Nur die Timeline-Einbettung wird aus `TradeAlertsPanel` entfernt. Monitoring-, Alert- und Notificationaktionen behalten ihre Owner und Verträge. Der zusätzliche Timeline-Zweig stornierter Trades entfällt ebenfalls. |
| Ein Editor | Ein ausgewählter Datum- oder Währungseditor ersetzt die Detaildarstellung genau dieser wirksamen Buchung. Unveränderliche Identität, Seite, Menge und vollständiger Preisstring bleiben als Orientierung sichtbar. |
| Navigation | Der tradebezogene `TradePendingChangesProvider` teilt genau einen vorhandenen `PendingNavigationGuard` zwischen Seitenkontext und Buchungseditor. Seine globale API und andere Featureoberflächen bleiben unverändert. |
| Quellen und Folgezustände | `TradeSourcesView`, Review-, Journal-, Lesson- und Modellowner behalten ihre fachlichen Zuständigkeiten. Die Konsolidierung finalisiert keine Review neu und bindet keine historische Quelle automatisch um. |

Die Ansichten ersetzen einander; unter den Alerts wird keine zweite vollständige
Liste gerendert. `#execution-dates` bleibt der Einstieg in den Buchungsbereich,
`#sale-capture` der Einstieg in die tatsächliche Verkaufserfassung.
`/trade-management?trade_id=…` und `view=sources` mit ihren genauen
Review-/Journal-/Lessonparametern behalten ihre Bedeutung. Die geladene Route
liefert die Trade-ID; ein bestehender Tradewechsel bleibt möglich.

## Zwei verschiedene Schreibverträge

### Ausführungsdatum korrigieren

`POST /api/v1/trade-position/trades/{tradeId}/executions/{executionId}/corrections`
erzeugt über den bestehenden Owner eine Ersatz-Execution. UI4 verwendet
`executionDateCorrection` und die vorhandenen Zeithelfer. Seite, Stückzahl und
vollständiger `price_per_unit`-Decimalstring stammen unverändert aus der
ausgewählten wirksamen Execution.

Das Formular übernimmt deren Datum und Zeitpräzision. Es sendet entweder
`executed_at` oder `executed_on` mit `execution_timezone`. Eine reine Datumsangabe
bleibt „Uhrzeit unbekannt“; ein interner Tagesanker wird nicht als bekannte Uhrzeit
angezeigt. Eine belegte Uhrzeit einschließlich Sekundenbruchteilen bleibt
erhalten, solange ihr Wegfall nicht ausdrücklich gewählt wird. DST-Lücken,
mehrdeutige lokale Uhrzeiten und zukünftige Ausführungen werden nicht automatisch
aufgelöst. Der ausdrückliche Datumsbestätigungsschritt bleibt erforderlich.

Der Request erhält **keinen `request_id`**, keinen erfundenen Idempotenzheader,
keine `expected_version` und kein neues Pflichtbegründungsfeld. Die Erfolgskontrolle
verbindet die zurückgegebene Execution-ID mit `supersedes_id` im neu gelesenen
Verlauf. Das Original und sein `recorded_at` bleiben unverändert.

Nach einem unklaren Transportabschluss werden zuerst Timeline und Position
gelesen. Der Schreibversuch wird nicht automatisch wiederholt; weitere Writes
bleiben bis zur bewussten Prüfung des Buchungsstands gesperrt. Ein inzwischen
ersetztes Ziel wird als veraltet gezeigt, ohne auf dessen Nachfolger umzuschalten.
Ein bestätigter Write mit anschließendem Lesefehler bleibt als bestätigter
Abschluss erkennbar und verlangt nur den erneuten Readback.

### Ausführungswährung bestätigen

`POST /api/v1/trade-position/trades/{tradeId}/executions/{executionId}/currency-confirmations`
verändert ausschließlich die Währungsbestätigung. Der Editor liest die eigene
History der gewählten Execution; `supersedes_confirmation_id` stammt aus
`history.current?.id` oder ist `null`. Eine geerbte BUY-Bestätigung ist kein eigener
Vorgänger des SELL.

Eine neue Erklärung verlangt einen ausdrücklich eingegebenen dreistelligen Code.
Vorhandene Belegnotizen und alte Bestätigungen werden nicht vorbefüllt und erneut
gespeichert. Die optionale Notiz bleibt auf 1000 Zeichen begrenzt. Der bestehende
`request_id` und dessen Replay-Vertrag bleiben erhalten: Ein unveränderter
manueller Retry verwendet denselben Key. Bei unklarem Abschluss ist nur dieser
unveränderte Versuch erneut zulässig; andere Angaben benötigen zunächst den
bewusst neu gelesenen Stand.

Auch ein erfolgreicher Replay wird erst nach einem neuen History-Read eingeordnet,
weil seine Quittung bereits historisch ersetzt sein kann. Bestätigter Write und
fehlgeschlagener Readback werden getrennt angezeigt. Nach Änderung einer
BUY-Bestätigung werden die abhängigen Währungsauflösungen neu gelesen; geöffnete
veraltete Quellenstände bleiben bis zur bewussten Prüfung gesperrt.

### Wiederverwendung und ausdrückliche Abweichung

`USER_CONFIRMED`, `PRIOR_BUYS`, `REPLACED_EXECUTION`, `UNKNOWN` und `MIXED`
bleiben mit ihren jeweiligen Quellen unterscheidbar. Die normale Datumsänderung
übernimmt die belegte Währung lesend, ohne eine weitere Erklärung zu erzeugen.
Report-EUR, Tradeplan, Strike, Listing und heutiger Marktquote werden nicht zu
Ausführungsfakten umgedeutet.

Eine reine Währungsbestätigung erzeugt keine Execution. Eine Datumsänderung mit
ausdrücklich abweichender Währung verwendet dagegen den vorhandenen optionalen
`currency_confirmation`-Teil **desselben Korrekturrequests**. Zwei verkettete POSTs
werden nicht als atomarer Speichervorgang angeboten.

## Kontext, Entwürfe und koordinierter Readback

Die Editorbasis besteht aus Trade-ID, genau ausgewählter Execution-ID und bei der
separaten Währungsaktion der selbst gelesenen Bestätigungs-ID. Ein Refresh wählt
weder die erste Buchung noch einen Nachfolger als neue Basis. Ladegenerationen,
Abbruchsignale und synchrone Locks verhindern, dass verspätete Antworten,
A→B→A-Wechsel oder ein Unmount fremde Daten oder Erfolgsmeldungen übernehmen.

Der gemeinsame Guard schützt Route-/Querywechsel, Browser-Zurück/Vor und das
Verlassen der Seite. Lokale Buchungs-, Editor- und Historiewechsel erfordern bei
ungespeicherten Eingaben eine Entscheidung mit Fokus auf „Hier bleiben“.
Während eines Writes gibt es keine Verwerfen-Navigation. Hashwechsel innerhalb
desselben Trades erhalten den Editor und die Eingaben. Die Navigationstests
verwenden `createMemoryRouter` und `RouterProvider`, damit der Routenschutz
tatsächlich aktiv ist.

Ein Reload desselben Trades aktualisiert den Lesestand ohne `readAttempt`-Remount.
Die Synchronisation der Managementformulare vergleicht jeden Entwurf mit seiner
zuletzt gelesenen Basis. Stop/Target und ihre jeweilige Preisbindung werden
zusammen erhalten; These, Notiz und Verkaufseingaben bleiben bei einem
Buchungsrefresh bestehen. Unveränderte Felder können den neuen Backendstand
übernehmen. Ein echter Tradewechsel erhält dagegen einen neuen Kontext.

Nach bestätigter Korrektur werden Timeline und Backendposition koordiniert neu
gelesen. Während eines Writes oder ungeklärten Buchungsstands sind die betroffenen
weiteren Schreibaktionen gesperrt. Es gibt keine optimistische lokale Änderung
von Bestand, Kostenbasis oder PnL. Die koordinierten GETs sind **kein neuer atomarer
Backend-Snapshot**; die bestehenden Owner entscheiden weiterhin Currentness und
zulässige Folgeaktionen.

Stornierte Trades bleiben lesbar und schreibgeschützt. Die Stornierung bleibt von
einem tatsächlichen Verkauf verschieden. Geschlossene Trades behalten die vom
Backend erlaubten faktischen Datums- und Währungsaktionen. Neue Käufe, Nachkäufe,
Teil-/Vollverkäufe und bestehende Managementaktionen behalten ihre Verträge.

## Akzeptanzfälle und konkrete Prüfeinstiege

Die folgende Zuordnung beschreibt den implementierten Umfang und dessen Tests.
Ein Testverweis allein ist kein bestandener Lauf; der abschließende Prüfstand
wird mit Commit-/Treebezug im Draft-PR festgehalten.

| Nr. | Anforderung | Konkreter Prüfeinstieg |
|---|---|---|
| 1 | Status und offene Menge einmal; Backendwerte bleiben erhalten | `TradeManagementPage.test.tsx`, `trade-execution-consolidation.spec.ts` |
| 2–3 | Jede wirksame Execution einmal; ersetzende Historie mit Originalen, Management und Stornierung | `ExecutionDatesPanel.test.tsx`, `TradeAlertsPanel.test.tsx`, `trade-timeline.spec.ts` |
| 4–6 | Genau gewählte Buchung, vorbefülltes Datum, vollständiger Decimalstring, Abbrechen, Zeitpräzision und DST | `ExecutionDatesPanel.test.tsx`, `executionDateCorrection.test.ts`, `executionTime.test.ts`, `capture.test.ts`, `trade-execution-dates.spec.ts`, `trade-capture-dst.spec.ts` |
| 7–8 | Währung ohne Neueingabe wiederverwenden; reine Bestätigung versus atomare Datum-/Währungsabweichung | `ExecutionDatesPanel.test.tsx`, `ExecutionCurrencyPanel.test.tsx`, `client.test.ts`, nativer Fall in `trade-execution-consolidation.spec.ts` |
| 9–10 | Original und Erfassungszeit erhalten; ersetztes Ziel nicht erneut korrigieren | `test_corrections_timeline.py`, `ExecutionDatesPanel.test.tsx`, native BUY-/SELL-Datumskorrekturen |
| 11–12 | Replay erst nach History-Read, unbekannte/gemischte Herkunft, veränderte BUY-Quellen | `ExecutionCurrencyPanel.test.tsx`, `test_currency_confirmations.py`, `test_currency_resolution.py`, PostgreSQL-Currency-Regressionsanker |
| 13 | Stornierte Trades schreibgeschützt, geschlossene Trades faktisch korrigierbar | `ExecutionDatesPanel.test.tsx`, `TradeManagementContext.test.tsx`, `TradeCancellationPanel.test.tsx` |
| 14 | Synchroner Doppelsubmit-Schutz, unklarer Transport, Replay und Readbackfehler | `ExecutionDatesPanel.test.tsx`, `ExecutionCurrencyPanel.test.tsx`, `TradeManagementContext.test.tsx`, `trade-capture-safety.spec.ts` |
| 15 | A→B→A, Same-Trade-Reload, Query/Hash/Zurück/Vor; Managemententwürfe bleiben erhalten | `TradeManagementContext.test.tsx`, `ExecutionDatesPanel.test.tsx`, `trade-management-context.spec.ts`, `trade-execution-consolidation.spec.ts` |
| 16 | Bestehende Quellenlinks, Nachkauf, Verkauf, Alerts und Management | unveränderte `TradeSourcesView.test.tsx`, gezielte AdditionalPurchase-/Alert-/Cancellation-Suiten sowie `ft010-trade-management.spec.ts` |
| 17 | Tastatur, Fokus, Fehlermeldungen und schmale Ansicht | Guard-/Editorfälle in Vitest; eigener Konsolidierungs-Browserfall bei 390 Pixeln mit Tastaturbedienung |

## Verifikation und Aussagegrenzen

### Ausführbare Prüfauswahl

Das unveränderte vollständige Frontendgate wird vom Repository-Stamm ausgeführt:

```bash
bash scripts/check-frontend.sh
```

Gezielte Frontendfälle sind insbesondere die beiden Seiten-/Kontextsuiten,
`ExecutionDatesPanel.test.tsx`, `ExecutionCurrencyPanel.test.tsx`,
`executionDateCorrection.test.ts`, `executionTime.test.ts`, `capture.test.ts`,
`client.test.ts` sowie die betroffenen Alert-, Nachkauf- und Stornierungssuiten.
Die vollständige Auswahl und der Gate-Abschluss werden im Draft-PR ausgewiesen,
ohne überlappende Teilmengen zu einer erfundenen Gesamtzahl zu addieren.

Die unveränderten Backendverträge werden gezielt geprüft:

```bash
PYTHONPATH=backend:. python -m pytest -c backend/pyproject.toml \
  tests/unit/backend/features/trade_position/test_corrections_timeline.py \
  tests/unit/backend/features/trade_position/test_currency_confirmations.py \
  tests/unit/backend/features/trade_position/test_currency_resolution.py \
  tests/integration/backend/test_execution_currency_confirmations_postgres.py \
  tests/integration/backend/test_execution_currency_reuse_postgres.py \
  tests/integration/backend/test_ft010_trade_management_e2e.py -q
```

Im vorhandenen, vorher identifizierten synthetischen E2E-Stack aus `frontend`:

```bash
npm run e2e -- trade-execution-consolidation.spec.ts \
  trade-execution-dates.spec.ts trade-management-context.spec.ts \
  trade-timeline.spec.ts ft010-trade-management.spec.ts \
  trade-capture-safety.spec.ts trade-capture-dst.spec.ts \
  --workers=1 --reporter=list,html
```

Die bestehenden Schreibfreigaben der Browserfälle dürfen ausschließlich für eine
vorher nachgewiesene Wegwerfdatenbank gesetzt werden. Der lokale UI4-Stack enthält
synthetische Produkte, Trades und Ausführungen; echte Provider-, Broker-,
Benachrichtigungs- oder Modellaktionen gehören nicht zur Prüfung. Die bestehenden
CI-only-Performance-/Journal-/Governance-Runner, ihre Identitätsprüfungen und festen
Ports werden nicht umgeschrieben oder durch eine behauptete CI-Identität umgangen.

### Nachweisregister dieses Schnitts

| Ebene | Nachweis und verbleibende Grenze |
|---|---|
| Lokale Frontendlaufzeit | Repository-Pin Node 22.16.0 / npm 10.9.2. Die vorinstallierte Node-24-Laufzeit war wegen `Request`-/`AbortSignal`-Inkompatibilität mit jsdom kein geeigneter Navigationstestnachweis. |
| Lokale Ausführung | Die Sandbox ließ Vitest nach abgeschlossenen Testkörpern ohne regulären Gesamtabschluss hängen. Nur regulär beendete Hostläufe werden als bestanden gezählt; keine Test-/Coveragegrenze wird dafür verändert. |
| Frontendgate | Abschließender vollständiger Prüfstand im Draft-PR mit Commit-/Treebezug. Frühere fokussierte Erfolge sind keine Qualifikation späterer Änderungen. |
| Backend-Owner | Gezielte bestehende Korrektur-/Currency-/FT010-Anker; abschließender Prüfstand und genaue Auswahl im Draft-PR. Keine Backendberechnungsänderung durch UI4. |
| Echte Persistenz | Lokaler nativer PostgreSQL-Stack **16.15** mit synthetischen Daten. Der reguläre Backendworkflow verwendet **PostgreSQL 17**; lokale native Ergebnisse ersetzen dieses reguläre PR-Gate nicht. |
| Browser | Geroutete UI-Mocks und echte Browser→API→PostgreSQL-Fälle werden getrennt ausgewiesen. Der neue native Fall prüft BUY-/SELL-Datumsänderung, direkte und geerbte Währungsquellen, Originalhistorie und erneut gelesene Position. Finale Pass-/Skip-/Retryzahlen und Bildnachweise stehen im Draft-PR. |
| CI, Merge und Betrieb | Reguläre Gates am finalen PR-Head separat lesen. Kein Merge, Versionssprung, Tag, Release, Deployment oder PC-Abnahmenachweis wird aus lokalen Tests abgeleitet. |

Eine allgemeine Mengen-, Preis-, BUY/SELL-Seiten- oder historische
Managementkorrektur-Oberfläche ist weiterhin außerhalb von UI4. Ebenso fehlen in
diesem Schnitt neue Endpunkte, Migrationen, Berechnungsmodelle und globale
Navigationsänderungen. Diese Grenze ändert nicht die vorhandenen weitergehenden
Backendverträge oder die ursprünglichen Backloganforderungen.

## Vertragsreferenzen

- [ADR-S10-002: effektive Execution-Historie und Position](../decisions/ADR-S10-002-EFFECTIVE-EXECUTION-HISTORY-AND-POSITION-PROJECTION.md)
- [ADR-S10-007: Execution- und Managementkorrekturen](../decisions/ADR-S10-007-EXECUTION-AND-MANAGEMENT-CORRECTIONS.md)
- [ADR-S10-008: Execution-Währung, einschließlich Wiederverwendungsnachträgen](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)
- [ADR-S11-005: Upstreamkorrekturen und Currentness](../decisions/ADR-S11-005-UPSTREAM-CORRECTIONS-STALENESS-AND-FINALIZATION.md)
- [Bestehende Qualifikation der Währungswiederverwendung](EXECUTION_CURRENCY_REUSE_QUALIFICATION.md)
- [Verbindliche Entwicklungsanleitung](../technical/DEVELOPMENT_GUIDE.md)
