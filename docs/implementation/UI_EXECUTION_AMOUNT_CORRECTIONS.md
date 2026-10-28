# UI7 — Menge und Preis bestehender Buchungen korrigieren

## Auftrag, Ausgangsbasis und Freigabegrenze

UI7 erweitert den vorhandenen Fakteneditor in `ExecutionDatesPanel.tsx`, nicht
die Erfassung eines neuen Kaufs oder Verkaufs. Ausgangsbasis der ursprünglichen
Implementierung war `eff24912ebfc1499fcea2cbf32dc1dbf8b0975e4` (v1.5.23).
Der neun Dateien umfassende Code-/Teststand wurde nach einer unterbrochenen
Werkzeugfreigabe vollständig aus dem Arbeitsprotokoll wiederhergestellt.
Der auf GitHub erzeugte Wiederherstellungs-Tree ist exakt
`dfb5ecc71d4c2d5daa19ddd7bf50c4cd72ffd052`, identisch zum ursprünglich lokal
geprüften Staging-Tree auf Basis `a864274c4c050698e1fc61134a98dfb03dcf1441`.

Integrationsbasis vom 27.10.2026 ist `38cac1a0cda52e4e1e6c4e69bd38f1842e388acb`
mit Tree `1a27d70bab245ab3d8d47261dcf0031b6c8e052e` und Version 1.5.25.
Der tatsächliche Vergleich zur ursprünglichen Basis umfasst zehn Commits;
keine der neun UI7-Code-/Testdateien ist darin verändert. Insbesondere bleiben
die inzwischen integrierten Analyse- und UI6-Journaländerungen unverändert.
Arbeitsbranch: `feat/execution-amount-corrections`.

Der Nutzer hat die ursprüngliche Draft-Grenze anschließend ausdrücklich erweitert:
**„Wenn grün mergen und für den PC bereitstellen“.** Ein Merge und eine
versionierte Bereitstellung sind damit nur nach erfolgreicher Qualifikation des
tatsächlichen finalen Integrations-/Release-Heads zulässig. Eine PC-Installation
oder menschliche Fachabnahme wird dadurch nicht behauptet.

## Bedienweg vorher und nachher

Bisher bot die konsolidierte Buchungsansicht Datumskorrektur und separate
Währungsbestätigung; Menge und Preis waren nur lesbar. Jetzt öffnet
**Kauf korrigieren** beziehungsweise **Verkauf korrigieren** an der wirksamen
Buchung denselben Inline-Fakteneditor mit vorausgefüllter Menge, vollständigem
Preisstring und den bisherigen Datums-/Uhrzeitoptionen. Die Lesezeile wird ersetzt.
Trade, Produkt, Richtung und die genaue Execution-ID bleiben fest gebunden.

Eine kompakte Alt/Neu-Tabelle zeigt ausschließlich geänderte Fakten, keine zweite
vollständige Buchungskarte und keine finanzielle Vorabberechnung. Die ausdrückliche
Bestätigung wird bei jeder Eingabeänderung zurückgesetzt. Der Hinweis erläutert:
Die Korrektur berichtigt eine bestehende Buchung; das Original bleibt in der
Historie. Sie erfasst keinen zusätzlichen Kauf oder Verkauf.

Es bleibt höchstens ein aktiver Fakten- oder Währungseditor. Aktuelle Buchungen
und schreibgeschützte Historie ersetzen einander über den vorhandenen Ansichtswechsel.
Die Deep-Links `#execution-dates`, `#sale-capture` und genaue Quellenparameter
bleiben unverändert. Keine neuen Pflichtdaten, Begründungen oder Stammdateneingaben.

## Mengen-, Preis- und Zeitvertrag

`executionAmountCorrection.ts` ergänzt ausschließlich die Mengen-/Preisprüfung
und ruft für alle Zeitangaben die unveränderte `executionDateCorrection` auf.

- Menge: vollständige Ziffernfolge, positive ganze Zahl bis 2147483647, passend
  zum persistierten PostgreSQL-Integer. Keine Teilstringauswertung, Dezimalabschneidung
  oder erfundene fachliche Grenze. Null ist weder Löschung noch Storno.
- Preis: Eingabe, Vergleich und Transport als String. Ein einzelnes Dezimalkomma
  wird eindeutig normalisiert. Gemischte Separatoren, Gruppierungen, unvollständige
  Angaben und neue Exponentschreibweisen werden mit Feldfehler abgewiesen.
  Geänderte Preise müssen positiv und verlustfrei in Numeric(24,10) darstellbar
  sein: höchstens 14 Vorkomma- und zehn Nachkommastellen nach Entfernen wertgleicher
  Nullen. Es erfolgt keine Rundung. Die exakte Wertgleichheit wird mit Ziffern und
  ganzzahligem Dezimalexponenten geprüft, nicht mit Number/parseFloat für Geld.
- Gleichwertige Schreibweisen wie `0,55` und `0.5500000000` sind unverändert.
  Bei unverändertem Preis wird immer der ursprüngliche vollständige String gesendet,
  auch bei Mengen-/Datumsänderung. Die Tests langer Bestandsstrings belegen nur
  verlustfreien Frontendtransport, keine unbegrenzte Datenbankpräzision. Bereits
  gespeicherte Decimal-Exponentschreibweisen bleiben unverändert transportierbar.
- Bei reiner Mengen-/Preiskorrektur bleiben exakter Zeitpunkt, Offset und sämtliche
  Sekundenbruchteile unverändert. Date-only behält `executed_on` und ursprüngliche
  `execution_timezone`, ohne erfundene Uhrzeit. Kalender-, Zukunfts- und DST-Prüfung
  sowie bewusster Verzicht auf eine bekannte Uhrzeit bleiben im bestehenden Helper.

Ungültige Eingaben gelten ebenfalls als ungespeichert. Nur wirklich geänderte
Menge, Preis oder Zeit erlauben einen Korrekturrequest; ein reiner Währungsentwurf
verweist auf den eigenen Bestätigungseditor. Verständliche Feldfehler sind über
`aria-invalid` und `aria-describedby` zugeordnet. Eingaben und Tabelle passen in
die schmale Darstellung; Tab-, Enter-, Escape- und Fokusverhalten bleiben erhalten.

## Bestehender Backendvertrag und Position

Es wird ausschließlich der bestehende Endpoint verwendet:

```text
POST /api/v1/trade-position/trades/{tradeId}/executions/{executionId}/corrections
```

Der Request enthält unveränderte Richtung, validierte Menge und Preisstring sowie
entweder `executed_at` oder `executed_on`/`execution_timezone`. Nur ausdrücklich
zusätzlich gewählte Währungsbestätigung ergänzt `currency_confirmation`.
Kein Capture-`request_id`, Idempotency-Key, `expected_version` oder neues Feld.

Das Backend erzeugt die Ersatz-Execution mit `supersedes_execution_id`, projiziert
die gesamte wirksame Historie und speichert Ersatz, Position und gegebenenfalls
Bestätigung atomar. Die ursprüngliche Buchung bleibt gespeichert. Historischer
Überverkauf und ungültige Reihenfolge werden als Backendfehler gezeigt, nicht
mit einer Frontend-Höchstmenge oder künstlicher Zeitverschiebung umgangen.
Geschlossene Trades bleiben korrigierbar und können zulässig wieder öffnen;
stornierte Trades bleiben schreibgeschützt.

Offene Menge, Einstand, Durchschnittspreis, realisiertes Bruttoergebnis und Status
werden über den vorhandenen Refresh neu vom Backend gelesen. Die Position aus
einer Schreibquittung wird nicht als endgültiger Seitenlesestand übernommen.
Stop-, Ziel-, Preisbindungs-, These- und Notizentwürfe bleiben erhalten; kein
pauschaler Remount desselben Trades und keine doppelte Positionszusammenfassung.

## Währungsherkunft und nachgelagerte Quellen

Direkte beziehungsweise geerbte Währung wird weiterverwendet, ohne neue
Bestätigungszeile für eine reine Mengen-/Preisänderung. USER_CONFIRMED,
REPLACED_EXECUTION, PRIOR_BUYS, UNKNOWN und MIXED bleiben getrennt. Listing-, Plan-
und Berichtswährung werden nicht als Ausführungswährung eingesetzt.
Eine reine Währungsänderung verwendet weiterhin ausschließlich den vorhandenen
Currency-Confirmation-Endpoint. Abhängige Buchungen werden nach Korrekturen frisch
gelesen, nicht durch lokale Kopien ihrer Herkunft aktualisiert.

Geänderte Mengen/Preise können heute geprüfte Observation-/Reviewquellen veralten
lassen; Wiederöffnung kann den Abschlusskontext aufheben. Historische Review-,
Journal-, Evidence- und Lessonversionen behalten ihre genauen Identitäten.
Gespeicherte `currentness` und heute geprüfte `source_currentness` sind verschiedene
Aussagen. UI7 berechnet kein eigenes STALE und löst keine Revalidierung,
Reviewaktualisierung, Journalumbindung, Finalisierung, Materialisierung oder
Lessonänderung aus. Die vorhandene Quellenprüfung bleibt zuständig.

## Entwurfsschutz, Konkurrenz und Abschluss

`TradePendingChanges` und `PendingNavigationGuard` behalten ihre globalen Verträge.
Mengen-/Preiseingaben werden in Dirty- und No-op-Erkennung einbezogen. Lokale
Editor-/Ansichtswechsel, Trade-/Route-/Querywechsel, Browser Zurück/Vor und
Seitenverlassen sind geschützt. „Hier bleiben“ erhält Eingaben. Laufende Writes
lassen keine Verwerfung oder Kontextfreigabe zu.

Die Bearbeitungsbasis und Ziel-ID bleiben fest. Ein inzwischen ersetztes Ziel
wird als veraltet angezeigt, niemals still an seinen Nachfolger gebunden.
Veränderte Währungsquellen werden auch bei gleichem Währungstext über ihre genaue
Herkunft erkannt; ein bewusster neuer Abgleich erhält übrige Eingaben und verlangt
erneute Bestätigung. Der konkrete Request wird vor dem Await festgehalten;
eine synchrone Sperre verhindert Doppelklicks vor dem nächsten Render.
Read-Abbruch beziehungsweise Generationenprüfung schützen verspätete Antworten
auch über A→B→A.

Nach bestätigtem POST werden neue ID, Trade-Zugehörigkeit und tatsächliche
Vorgängerbeziehung in der Timeline geprüft. Ein bestätigter Write mit Readbackfehler
bietet **Lesestand erneut laden**: ausschließlich GETs, keinen erneuten POST.
Bei unklarem Transportausgang bleibt der Schreibabschluss unbekannt; zuerst wird
der aktuelle Verlauf geprüft. Kein automatischer Retry und kein erfundener Erfolg.
Mehrere koordinierte GETs sind kein atomarer Datenbanksnapshot. Die vorhandene
API besitzt keine zusätzliche Frontend-CAS-Garantie.

## Nachweiszuordnung

Die folgende Matrix benennt vorhandene konkrete Tests. Ihr aktueller Ausführungsstand
ist getrennt im anschließenden Prüfprotokoll ausgewiesen; ein implementierter Test
allein ist kein erfolgreicher Lauf.

| Abnahme | Konkreter Nachweis |
|---|---|
| 1–3: BUY/SELL, ein Editor, feste Identitäten | `ExecutionDatesPanel.test.tsx`: parametrisierte reine Mengen-/Preiskorrektur beider Richtungen, Inline-/Historie-/Editorwechsel; eigener Browserfall. |
| 4–6: Präzision, Validierung, No-op, Zeit | `executionAmountCorrection.test.ts`: Integer-/Numeric-Grenzen, fehlerhafte Formate, Wertgleichheit, lange Bestandsstrings, Exponenten, exakter Timestamp, date-only und DST; Panel-Feldfehler und direkte No-op-Submits. |
| 7–8: Datum und Währung | Bestehende Datum-/Currency-Panel-/Input-/Clienttests; Paneltests für zusätzliche atomare Bestätigung, reine Währung, geänderte Quellen-IDs und abhängige Reads; bestehende Browserfälle nur mit angepassten Beschriftungs-Locators. |
| 9–11: Historie, Position, Storno | Eigener realer Browserfall mit vier erfolgreichen Korrekturen und abgelehntem historischen Überverkauf; Panel-Storno-/Historientests; echte Page-Einbettung liest neue Position einschließlich Wiederöffnung. |
| 12–14: Konkurrenz, Recovery, Identität | Paneltests für stale target, unklaren Transport mit tatsächlich erzeugtem Nachfolger, bestätigten Write mit Readbackfehler, Supersession-Linkprüfung, Doppelsubmit, A→B→A-Read und verspäteten Write. |
| 15: Entwürfe und Navigation | `TradeManagementPage.test.tsx` verwendet `createMemoryRouter`/`RouterProvider` mit echten Buchungs-/Managementkomponenten: Route, Query, POP, Hash, beforeunload, lokale Verwerfung und Erhalt aller Managemententwürfe bei Refresh. |
| 16: Keine automatischen Folgeaktionen | Requestbeobachtung im echten Browserfall erfasst alle Browser-POSTs und erlaubt nur die fünf ausdrücklichen Korrekturversuche; unveränderte FT011-/Journal-/Evidence-Regressionen bleiben im regulären Gate. |
| 17: Bedienung und Deep-Links | Vorhandene Tastatur-/Fokus-/Historietests plus neuer echter 390-Pixel-Browserfall mit Enter, Escape, Fokus und Überlaufprüfung; bestehende Kontextregressionen unverändert. |
| 18: Echte Persistenz und UI6-Grenze | `tests/e2e/trade-execution-corrections.spec.ts`, ohne API-Mocks: Browserwrites, Timeline-/Positionsreads, JSON-Readbacks und Screenshot; UI6-Dateien im UI7-Diff unverändert. |

### Historischer lokaler Lauf, vor Wiederherstellung

Das Arbeitsprotokoll des identischen ursprünglichen Code-/Test-Trees dokumentiert
`bash scripts/check-frontend.sh` mit **1.315 Tests in 137 Dateien**, Typecheck,
ESLint, Prettier, Coverage und Produktionsbuild erfolgreich. Coverage:
Statements/Lines 95,19 %, Branches 89,02 %, Functions 89,61 %.
Gezielte Backendregressionen: 87 bestanden. Ein weiterer Capture-/API-/Integrationslauf
hatte 21 bestandene und 35 mangels Wegwerf-PostgreSQL-Verbindung übersprungene Tests.
Diese Zahlen sind historische lokale Nachweise, nicht die Qualifikation des neuen
kombinierten Main-Stands. Der echte UI7-Browser-/PostgreSQL-Fall war dort noch
nicht erfolgreich ausgeführt.

### Aktuelle Integrationsqualifikation

Der vollständige frühere lokale Checkout und seine Abhängigkeiten stehen in der
Wiederherstellungssitzung nicht zur Verfügung; der neue Clone scheitert an der
DNS-Auflösung. Docker/PostgreSQL sind lokal nicht vorhanden. Der unveränderte
vollständige lokale Frontendbefehl und der native Persistenzlauf wurden deshalb
hier nicht erneut ausgeführt. Keine fremde Datenbankfreigabe, keine vorgetäuschte
CI-Identität, keine Gate- oder Runneränderung.

Der neu veröffentlichte PR muss den tatsächlich integrierten Tree mit den
bestehenden regulären Frontend-, Backend-, E2E- und Versionsworkflows qualifizieren.
Die Frontend-CI führt die unveränderten einzelnen Quality-Gate-Befehle einschließlich
Coverage und Build aus. Der neue Browserfall nutzt die bestehende Schutzbedingung
`TRADE_E2E_WRITES_ALLOWED=1` ausschließlich im zugelassenen Wegwerfstack.
Aktuelle Head-/Testmerge-/Tree-Bindung, konkrete Runs und Ergebnisse werden im
PR-Prüfprotokoll festgehalten. Bis zu deren erfolgreichem Abschluss bleibt der PR
Draft und nicht zur Integration freigegeben.

## Parallelität und verbleibende Grenzen

UI7 verändert keine UI6-Journal-/Learning-/PostTrade-Datei und keine bestehenden
Journal-Browserfälle. Gemeinsame Backlog-/Traceability-Dokumente werden durch diese
Wiederherstellung nicht global überschrieben. Die vorhandenen UI1–UI6-Funktionen
werden aus aktuellem Main übernommen. Unabhängige offene PRs werden nicht
stellvertretend gemergt. Getrennte Worktrees ersetzen keine Isolation von Ports,
Compose-Projektnamen oder Testdatenbanken; verwendet werden nur die vorhandenen
isolierten Runner.

Keine neue Backend-API, Migration, Finanzprojektion, BUY/SELL-Richtungsänderung,
Bulk-Korrektur, Managementkorrektur oder globale Guardänderung. Versions-/Release-
änderungen sind allein durch die nachträgliche Nutzerfreigabe gedeckt und erfolgen
getrennt nachvollziehbar. Kein Zugriff auf PC oder reale Depotdaten.
