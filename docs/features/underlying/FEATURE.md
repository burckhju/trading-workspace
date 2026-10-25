# FT-001 – Basiswertverwaltung

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Feature-ID | FT-001 |
| Technischer Name | `underlying` |
| Version | 1.1 |
| Status | 🟢 Implemented – Sprint 2 Complete |
| Letzte Änderung | 2026-08-04 |

Die folgenden ursprünglichen Scope- und Freigabeangaben beschreiben den
Sprint-2-Stand. ETF wurde später durch
[ADR-CHARTS-001](../../decisions/ADR-CHARTS-001-EOD-COMPARISON-AND-ETF-IDENTITY.md)
additiv aufgenommen. Der aktuelle Aufgaben- und Abnahmestatus steht ausschließlich
im [Product Backlog](../../planning/PRODUCT_BACKLOG.md), insbesondere PB-007.

## Ziel

Der Benutzer verwaltet Aktien als zentrale Basiswerte an genau einer Stelle. Andere Features referenzieren diese Daten und erfassen sie nicht erneut.

## Nutzen

- zentrale und eindeutige Stammdaten,
- keine doppelte Erfassung,
- nachvollziehbare Änderungen,
- stabile historische Referenzen,
- vorbereitete Trennung zwischen Basiswert und Marktpräsenz.

## Scope

- Aktie als Underlying anlegen,
- mindestens eine primäre Notierung erfassen,
- Basiswerte suchen, filtern und anzeigen,
- Stammdaten und Notierungen bearbeiten,
- aktivieren und deaktivieren,
- unbenutzte Fehleinträge endgültig löschen,
- Verwendungen vor Löschung transparent anzeigen,
- Dubletten anhand definierter Kennungen verhindern.

## Nicht-Scope

- Optionsscheinverwaltung,
- Emittentenverwaltung,
- Providerimport,
- Kursdaten,
- automatische Stammdatenergänzung,
- Indizes, ETFs, Rohstoffe oder Währungen,
- Zusammenführung von Dubletten,
- Handelsentscheidung oder Produktempfehlung.

## Benutzer

Version 1 besitzt genau einen Benutzer in einem unsichtbaren Workspace.

## Hauptanwendungsfälle

1. Basiswert mit primärer Notierung anlegen.
2. Basiswert über Name, Ticker, ISIN oder WKN finden.
3. Details und Notierungen anzeigen.
4. Basiswert- oder Notierungsdaten ändern.
5. Basiswert deaktivieren oder reaktivieren.
6. Unbenutzten Basiswert endgültig löschen.
7. Löschung bei vorhandenen Referenzen ablehnen und Verwendungen anzeigen.

## Fachliche Kernregeln

- Nur Aktien dürfen angelegt werden.
- Ein Optionsschein darf niemals als Basiswert angelegt werden.
- Underlying und Listing sind getrennte Objekte.
- Operative Nutzung erfordert genau eine aktive primäre Notierung.
- Ticker ist nur zusammen mit Markt eindeutig.
- ISIN und WKN sind optional, aber eindeutig, sobald vorhanden.
- Referenzierte Basiswerte dürfen nicht endgültig gelöscht werden.
- Deaktivierung verändert bestehende Referenzen nicht.
- Andere Features dürfen Underlying-Stammdaten nicht schreiben.

## Abhängigkeiten

- Workspace-Basis aus ADR-S1-004.
- Markt-/Handelsplatzreferenz; bis FT-002 muss eine kontrollierte Referenzliste genutzt werden.
- Währungsreferenz aus dem technischen/shared Bereich oder einer späteren fachlichen Referenzquelle.

## Bedienprinzip

Die Anlage erfolgt als geführter Ablauf mit Grunddaten und primärer Notierung. Da Version 1 nur Aktien unterstützt, ist der Typ nicht als frei wählbare Liste nötig; er wird sichtbar als „Aktie“ dargestellt.

## Freigabestatus

Alle fachlichen Grund- und Detailentscheidungen sind akzeptiert. FT-001 wurde in Sprint 2 vollständig über Backend, REST API, React-Frontend, Tests und Dokumentation umgesetzt. Die Implementierung bleibt an die akzeptierten ADRs und die Feature-Book-Verträge gebunden.

## Rückkehr nach der Stammdatenpflege

Die Basiswertliste hält ihre bestätigte Suche, Status-/Markt-/Währungsfilter und
25er-Paginierung in der URL. Beim Öffnen von Details oder Bearbeitung wird dieser
Listenkontext als auf `/underlyings` begrenztes `returnTo` weitergegeben. Nach
**erfolgreichem Speichern**, **Abbrechen** oder dem Formular-Zurücklink geht es
direkt auf die ursprüngliche Listenseite; der Detail-Zurücklink erhält sie ebenfalls.
Die Liste lädt ihre Daten dort erneut. Ein Speicherfehler bleibt mit den Eingaben
im Formular. Direkte Bearbeitungslinks ohne Listenkontext führen wie bisher zur
Detailansicht; Neuanlage führt weiterhin zum neu angelegten Basiswert.

Reload und Browser-Zurück/Vorwärts erhalten den URL-Kontext, getrennt je Tab.
Neue Suche oder Filteränderungen beginnen auf Seite 1. Existiert die gemerkte
letzte Seite nach einer Änderung/Löschung nicht mehr, wird die letzte vorhandene
Seite derselben gefilterten Liste geladen. Ungültige Seitenwerte fallen auf
Seite 1 zurück; externe oder fremde Rücksprungziele werden nicht verwendet.
Keine Backend-, Datenmodell-, Stammdatenvalidierungs- oder Provideränderung.

Ein Rücksprungziel enthält ausschließlich den Pfad `/underlyings` und die
bekannten, eindeutigen Listenparameter. Protokollrelative, verschachtelte,
doppelte oder missverständlich kodierte Ziele werden verworfen; korrekt kodierte
Suchzeichen bleiben normale Suchdaten. Ein verworfenes Ziel verwendet den
bestehenden Direktaufruf ohne Listenherkunft.

Die Detailansicht bindet Laden und Aktionen an die aktuelle Basiswertidentität.
Verspätete Daten oder die Antwort einer früher abgesendeten Löschung dürfen nach
einem Datensatzwechsel weder den neuen Basiswert ersetzen noch zurücknavigieren.
Zwei synchrone Auslösungen derselben Aktion senden nur einen Auftrag. Eine bereits
abgesendete Löschung kann serverseitig trotzdem abgeschlossen werden.

Prüfweg: Liste auf Seite 2/3 öffnen, Basiswert → Bearbeiten → Abbrechen oder
Detail → Basiswerte: Rückkehr zu derselben Seite mit denselben Filtern (lesend).
Speichern/Löschen und Fehlerfälle nur mit synthetischen Daten in der Testumgebung
prüfen; diese Aktionen verändern Stammdaten. Regressionen: `UnderlyingNavigation.test.tsx`,
`underlyingListNavigation.test.ts`, `tests/e2e/underlying-list-return.spec.ts`.
Die neuen Browserfälle verwenden vollständig abgefangene synthetische API-Antworten;
sie sind kein zusätzlicher Datenbank-Schreibnachweis.

## Sicheres Formular bei Navigation und Ladefehlern

Beim Wechsel des Basiswerts oder des Anlagevorschlags erhält das Formular einen
eigenen Zustand. Eingaben, Fehlermeldungen und verspätete Ladeantworten des
vorherigen Formulars werden nicht übernommen. Während des Ladens sind keine alten
Eingaben speicherbar; nach einem Ladefehler bleiben Eingaben und Speichern gesperrt.
Der Benutzer kann zurückgehen oder die Seite neu laden.

Bearbeiten setzt erfolgreich geladene Daten mit der Identität der aktuellen
Bearbeitungsadresse voraus. Fehlende Bearbeitungsdaten lösen niemals eine Neuanlage
aus. Die geladene Version bleibt Bestandteil des bestehenden Update-Vertrags.
Während eines Speichervorgangs sind die Eingaben gesperrt und doppelte
Formularübermittlungen werden abgefangen. Schlägt das aktuelle Speichern fehl,
bleiben die Eingaben für eine bewusste erneute Übermittlung erhalten.

Ein bereits abgesendeter Schreibauftrag kann nach Verlassen des Formulars auf dem
Server noch abgeschlossen werden. Seine Antwort darf jedoch weder das neue
Formular verändern noch eine nachträgliche Navigation auslösen. Navigation ist
kein Abbruch oder Rückgängigmachen des ursprünglichen Schreibauftrags.

### Ergänzung nach PR #249: stabile Vorschläge und sofortige Deaktivierung

Der in [PR #249](https://github.com/burckhju/trading-workspace/pull/249) gemergte
Schutz wird um zwei zeitliche Randfälle ergänzt. Gleichwertige Suchparameter wie
`name=Test+ETF` und `name=Test%20ETF` gehören zur selben Formularinstanz. Sie dürfen
keinen erneuten Ladevorgang auslösen, der bereits bearbeitete Eingaben während
eines Speicherns überschreibt. Der Formularschlüssel und der einmalig erzeugte
Parameter-Snapshot verwenden deshalb dieselbe serialisierte Suchzeichenfolge.

`returnTo` ist davon getrennte Navigation und gehört nicht zur fachlichen
Vorschlagsidentität. Ändert sich nur dieses gültige Rücksprungziel, bleiben
bewusste Eingaben, geladene Identität/Version und ein laufender Schreibauftrag
erhalten. Ein erfolgreicher noch aktiver Auftrag verwendet das aktuelle
validierte Ziel. Ein tatsächlicher Datensatz- oder Vorschlagswechsel deaktiviert
weiterhin die alte Formularinstanz.

Beim Verlassen wird die alte Formularinstanz bereits in der React-Commit-Phase
deaktiviert. Eine Speicherantwort zwischen dem Einhängen der Zielansicht und dem
späteren Aufräumen des Ladeeffekts darf nicht mehr navigieren. Dafür verwaltet ein
Layout-Effekt ausschließlich die Aktivitätsreferenz; Netzwerkladen bleibt im
normalen Effekt mit eigenem Abbruchkennzeichen.

Identität und geladene Version eines Updates bleiben unverändert gebunden. Auch
nach HTTP 409 wird keine neuere Version automatisch übernommen oder ohne bewusste
Übermittlung erneut geschrieben. STOCK, ETF, EODHD-Vorschläge sowie die genaue
MIC-/Währungsauswahl behalten ihre bestehenden Verträge.

Die Regressionen prüfen folgende beobachtbare Ergebnisse mit kontrollierten
Antworten und ohne zeitgesteuerte Sleeps:

| Bereich | Prüferwartung |
|---|---|
| A – Lade-Reihenfolge | A→B in beiden Antwortreihenfolgen: nur B mit seiner Version und vollständigen Update-Payload speichern. |
| B – Bereits geladenes A | Während B lädt oder dessen Laden scheitert, ist kein Schreibauftrag für A möglich. |
| C – Lebensdauer | A→B→A, StrictMode und Unmount übernehmen keine alten Antworten oder Fehler. |
| D – Ladefehler | Fehler bei Detail oder Referenzdaten sowie falsche Antwortidentität sperren auch programmgesteuerte Übermittlung; Edit fällt nicht in CREATE. |
| E – Formularwechsel | Edit, Neuanlage und verschiedene Vorschläge teilen keine Eingaben, Notierungen oder Fehler; gleichwertige URL-Codierungen erhalten bewusste Eingaben. |
| F – Alte Schreibantwort | Erfolg, Fehler und Abschluss eines alten UPDATE/CREATE beeinflussen weder Zielnavigation noch Sperre oder Fehler eines dort bereits laufenden Speicherns. |
| G – Doppelübermittlung | Zwei synchrone Submit-Ereignisse erzeugen genau einen Auftrag; ein bewusster neuer Versuch erhält Payload und Versionsbindung. |
| H – Bestehender Ablauf | Normale Anlage/Bearbeitung, Validierung und Zieladresse bleiben erhalten; Abbrechen und Zurück schreiben nichts. |

Die Browserprüfung ergänzt die Unit-Regressionen bei 1440×1000 und 390×844 um
beide Lade-Reihenfolgen, Ladefehler, alte UPDATE-Antworten während des Speicherns
von B und doppelte CREATE-Übermittlung. Sie prüft tatsächliche API-Pfade,
vollständige Payloads, Sperrzustände, Navigation und horizontalen Überlauf mit
synthetisch abgefangenen Requests. Das belegt keine Datenbankschreibvorgänge auf
dem Nutzer-PC. Exakte Prüfstände, Ergebnisse, Screenshots und CI-Läufe gehören in
den zugehörigen Folge-PR; frühere Läufe sind kein Nachweis für einen neueren Head.

Der getrennte Listen-Navigations-PR #204 führt diesen Schutz mit dem Rücksprung
zusammen. Die gemeinsame Prüfung einschließlich alter Schreibantworten mit
Listenkontext ist in der
[Navigationsqualifikation](../../implementation/UNDERLYING_NAVIGATION_QUALIFICATION.md)
belegt. Diese Ergänzung erklärt weder PB-007 insgesamt für abgenommen noch eine
Installation oder Veröffentlichung für erfolgt.
