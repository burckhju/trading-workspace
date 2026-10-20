# Basiswert-Listennavigation: gemeinsame Qualifikation mit Formularschutz

Prüfdatum: 20.10.2026. Gegenstand ist die begrenzte Weiterführung von
[PR #204](https://github.com/burckhju/trading-workspace/pull/204) auf v1.5.11.
Die dokumentierten Ergebnisse sind lokale synthetische Entwicklungsnachweise
vor der anschließenden Aktualisierung des bestehenden PRs. Dieser Bericht erhebt
keinen neuen GitHub-PR-/Main-Lauf, Merge, Release, PC-Update oder menschliche
Fachabnahme als Nachweis. Der Aufgabenstatus bleibt im
[Product Backlog](../planning/PRODUCT_BACKLOG.md).

## Geprüfte Grundlage und Integration

| Bezug | Wert |
|---|---|
| Bestehender Branch | `fix/underlying-list-return` |
| Ursprünglicher PR-Head | `3a2dd4823aa2ff8b0b44d23655bab3a0e443efaa` |
| Integrierter Main-Elternstand | `5e9ede2dc29f52eaff601d30614df6bc9c25c426` |
| Main-Tree | `303e56c078efd578e6e147edcf2ebac6accf6ba5` |
| Geprüfter Frontend-Quelltree | `c8d98bc689b0cd57e5a32eb473a82a1adc6c27f8` |
| Geprüfter `tests/e2e`-Quelltree | `192ded7fb7e8b10a10cf6ec1710fc5ead4ba8db4` |
| Runtime | Node `22.16.0`, npm `10.9.2`, unverändertes Lockfile |
| Browser | Playwright `1.55.0`, Chromium `140.0.7339.16` / Build `1187` |

Die Quelltrees wurden aus dem gestageten Integrationsstand mit
`git write-tree --prefix=frontend/` beziehungsweise `--prefix=tests/e2e/`
ermittelt. Sie binden die ausführbaren Nachweise unabhängig von späteren reinen
Dokumentationsänderungen. Der lokale Merge war bei Durchführung der Prüfungen
noch nicht committet; ein späterer Commit muss diese Trees erhalten oder seine
Abweichung erneut qualifizieren.

Main wurde nichtdestruktiv in den vorhandenen Branch übernommen. Die beiden
Konflikte in `UnderlyingFormPage.tsx` und `FEATURE.md` wurden inhaltlich aufgelöst:
aktuelle Formularschutzmechanismen aus #249/#267 erhalten, gezielten
Listenrücksprung hinzufügen. Backend, Stammdatenvalidierung, API-/Versions- und
Auditverträge, Provider, Migrationen, Releases, Währungs-/Performancecode,
Workflows und Dependency-Pins sind gegenüber dem Main-Elternstand unverändert.

## Verhalten und Schutzgrenzen

| Anforderung | Umsetzung und konkreter Nachweis |
|---|---|
| Bestätigte Suche, Status, Markt, Währung, 25er-Seite | Gemeinsamer URL-Helfer; Liste liest und schreibt ausschließlich den URL-Kontext. Unit- und Browserfälle erhalten alle fünf Werte auf Seite 2 und 3. Neue Suche/Filter setzt den Offset auf 0. |
| Sichere Rücksprungziele | Nur `/underlyings` und bekannte eindeutige Listenparameter. Keine externen, protokollrelativen, fremden, verschachtelten, doppelten oder missverständlich kodierten Ziele. Korrekt kodierte Suchzeichen werden kanonisiert, nicht als zweite URL interpretiert. 39 Helfertests einschließlich Negativfällen; fünf ungültige Ziele zusätzlich im Browser. |
| Detail → Edit → Save/Abbrechen/Zurück | Bestehende Linkkette gibt validiertes `returnTo` weiter. Edit-Save lädt die ursprüngliche Liste neu; Fehler behält Eingaben und führt nicht zur Erfolgsnavigation. Direkte Bearbeitung bleibt bei ihrem Detailziel; Neuanlage öffnet den angelegten Basiswert. |
| Reload, Verlauf, Tabs | Browser reloadet Liste und Formular; echter Browser-Zurück-/Vorwärtsweg und zwei unabhängige Tabs sind geprüft. Keine globale oder sessionweite zweite Zustandsablage. |
| Leere letzte Seite | Der bestehende Löschweg kehrt mit allen Filtern zurück. Nach Entfernen des einzigen Eintrags auf Seite 3 wird Seite 2 geladen. Die beobachteten Offsets sind genau `50, 50, 25`, ohne Schleife. |
| Vorschlag und Navigation getrennt | `returnTo` ist vom stabilen fachlichen Parametersnapshot/Formularschlüssel ausgeschlossen. Eine reine Zieländerung erhält Eingaben, Identität/Version und laufende Sperre. Ein noch aktiver Erfolg verwendet das aktuelle validierte Ziel. |
| Aktuelle Formularintegrität | Alle bisherigen Isolationsfälle bleiben erhalten: A→B, Ladefehler, StrictMode, Unmount, Version/Payload, kein Edit→Create-Fallback, synchrone Doppelübermittlung. Zusätzliche Fälle prüfen diese Regeln mit Listenkontext und reine Rücksprungänderungen während Create/Edit. |
| Detailwechsel und alte Löschantwort | Detailzustand ist an die Datensatzidentität gebunden. Verspätete A-Daten ersetzen B nicht; eine alte DELETE-Antwort navigiert B nicht weg. Eine synchrone Aktionssperre verhindert zwei gleichzeitige Löschaufträge. |

Ein bereits abgesendeter Schreibauftrag kann serverseitig weiterlaufen.
Navigation ist kein Abbruch oder Rollback. Die Tests prüfen ausschließlich,
dass verlassene Ansichten keine fremden Daten oder nachträgliche Navigation
übernehmen. Kein allgemeiner Umbau aller Detail-Aktualisierungsrennen wird
behauptet.

Der unabhängige Read-only-Review hat eine bereits auf Main bestehende engere
Grenze im Detail reproduziert: Unter React StrictMode können zwei Ladeeffekte
derselben Datensatzinstanz laufen; eine späte erste Antwort kann dann die
neuere zweite Version überschreiben. Das betrifft weder den hier ergänzten
A→B-Instanzschutz noch den bestehenden eigenen Lade-Abbruchschutz des Formulars.
Der Befund ist keine neue Navigationsregression und bleibt außerhalb dieses
begrenzten Integrationsschnitts sichtbar.

Produktionsdateien: `UnderlyingListPage.tsx`, `UnderlyingDetailPage.tsx`,
`UnderlyingFormPage.tsx` und `underlyingListNavigation.ts` unter
`frontend/src/features/market/`. Die ergänzte Featurebeschreibung steht im
[FT-001 Feature Book](../features/underlying/FEATURE.md).

## Reproduktion und Frontend-Gate

Vor der Korrektur wurden die neuen Fälle gegen den zunächst zusammengeführten
Code ausgeführt. Die 79 Formular-/URL-Fälle ergaben 67 Erfolge und zwölf
reproduzierte Fehler: zwei ungewollte Formular-Neuinitialisierungen bei reiner
Rücksprungänderung und zehn zu permissive Rücksprungziele. Die zwei ergänzten
Detailfälle ergaben vor ihrer Korrektur elf erfolgreiche bestehende Fälle und
zwei Fehler: verspätetes A ersetzt B sowie doppelte DELETE-Übermittlung.

Der fokussierte gemeinsame Lauf umfasst 114 Tests in sieben Dateien:
`UnderlyingNavigation.test.tsx` (13), `UnderlyingFormIsolation.test.tsx` (43),
`underlyingListNavigation.test.ts` (39), `UnderlyingFormPage.test.tsx` (7),
`UnderlyingListPage.test.tsx` (7), `UnderlyingDetailPage.test.tsx` (3) und
`src/app/Application.test.tsx` (2). Alle bestanden. Diese Teilmenge wird nicht
auf die Gesamtzahl des folgenden Gates aufaddiert.

Der erste vollständige Gateversuch stoppte an zwei `require-await`-Lintfehlern
in den neuen Detailtests. Die Tests warten nun explizit auf ihre kontrollierten
Promises. Anschließend bestand das unveränderte Repository-Gate:

```bash
bash scripts/check-frontend.sh
```

| Prüfung | Ergebnis |
|---|---|
| TypeScript | bestanden |
| ESLint, maximal 0 Warnungen | bestanden |
| Prettier | bestanden |
| Vollständige Vitest-Coverage-Suite | **632 bestanden in 113 Dateien**, keine Skips/Fehler |
| Lines / Statements | **92,86 % / 92,86 %**, Grenzen unverändert jeweils 80 % |
| Functions | **85,42 %**, Grenze unverändert 80 % |
| Branches | **85,08 %**, Grenze unverändert 70 % |
| Produktionsbuild | bestanden; bestehende Vite-Hinweismeldung zu großen Chunks bleibt sichtbar |
| Diff-/Konfliktprüfung | `git diff --check` und `git diff --cached --check` bestanden; keine unaufgelösten Indexkonflikte |

Die Runtime musste lokal bereitgestellt werden. Dependencyinstallation erfolgte
zunächst mit vorhandener Node-24-Runtime und gepinntem npm `10.9.2`, ohne
Lockfileänderung. Ein früh versuchter Node-24-Testlauf ohne Ergebnis wurde
abgebrochen und gilt nicht als Erfolg. Sämtliche hier als bestanden genannten
Gates und Browserläufe verwenden das verifizierte vollständige Node-22.16.0-Binary
und npm 10.9.2. Es wurden keine CI-Variablen gefälscht oder Schutzregeln geändert.

## Gemeinsamer synthetischer Browserlauf

Vor dem Lauf wurden genau **22 Tests in drei Dateien** per Playwright `--list`
erfasst. Anschließend wurden dieselben drei Dateien zusammen mit einem Worker,
`--retries=0`, `--trace=on` und JSON-Report ausgeführt:

```bash
npm run e2e -- \
  underlying-list-return.spec.ts \
  underlying-form-isolation.spec.ts \
  ft001-underlyings.spec.ts \
  --workers=1 --retries=0 --trace=on --reporter=list,json
```

| Browserdatei | Tatsächlich ausgeführter Umfang |
|---|---|
| `underlying-list-return.spec.ts` | 6: Save/Rückkehr Seite 2 und 3 mit Reload und allen Filtern; zwei Tabs/Abbrechen; leere letzte Seite nach Löschung; echtes Back/Forward; ungültige Rücksprungziele. |
| `underlying-form-isolation.spec.ts` | 12: sechs bestehende Fälle jeweils bei 1440×1000 und 390×844 — beide Lade-Reihenfolgen A/B, Ladefehler ohne Create-Fallback, alte Save-Auflösung/-Ablehnung während B speichert, synchrone doppelte Neuanlage. |
| `ft001-underlyings.spec.ts` | 4 bestehende Abläufe: Suche/Filter; Neuanlage mit Primärlisting; Detailhistorie/Verifizieren mit geladener Version; Deaktivieren/Löschen/Neuanlage. |

**Ergebnis: 22 bestanden in 18,3 Sekunden, 0 Skips, 0 Flaky, 0 Fehler und
0 Testretries.** Der JSON-Report wurde zusätzlich strukturell geprüft: exakt 22
eindeutige Testidentitäten, je genau ein Ergebnis `passed`, `retry=0`, keine
unerwarteten Ergebnisse und keine Reporterfehler. Der Browserreport enthält
22 Traces und 16 angehängte Screenshots. Seite 2/3 und mobile aktuelle bzw.
gesperrte Formulare wurden zusätzlich visuell geprüft; die bestehenden
Formularbrowserfälle prüfen horizontalen Überlauf programmatisch.

### Echte Pfade, synthetische Schreibantworten

Der separate Browserbuild verwendet ausdrücklich
`VITE_API_BASE_URL=http://localhost:8080/api`. Derselbe Wert wurde als
`E2E_VITE_API_BASE_URL` übergeben; `PLAYWRIGHT_BASE_URL` ist
`http://localhost:8080`. Daraus folgt für diesen Build tatsächlich
`/api/api/v1`. Diese testbezogenen Variablen wurden erst nach dem allgemeinen
Frontend-Gate gesetzt.

Die Navigation-/Formfixtures fangen alle API-, Fetch/XHR-, Mutations- und fremden
Requests ab. Nur statische Frontenddateien erreichen den eigenen lokalen
Previewprozess. Unbekannte Requests werden mit Fehler beantwortet und lassen
die Vertragsprüfung scheitern. Alle **19 angehängten API-Verträge** enthalten das
erwartete Präfix und `unexpected=[]`. Die Navigation prüft vollständige
Update-Payload, ID, Version, tatsächlichen API-Pfad und Filterparameter; die
bestehende Formisolation prüft ihre vollständigen Create-/Update-Payloads ebenfalls.
Der eigene Previewprozess wurde nach dem Lauf beendet.

Die Browserinstallation verwendete den normalen Playwright-Download-Fallback
nach einem fehlerhaften CDN-Archiv. Das war vor Testbeginn und ist kein
fachlicher Testretry. Es war kein Backend/Test-DB-Stack angeschlossen; diese
Mock-Browsernachweise ersetzen keine native PostgreSQL-Prüfung und belegen
keine realen Nutzerbestandsänderungen.

## Sitzungsartefakte und weitere Freigabe

Die unveränderten Rohberichte liegen in den Sitzungsartefakten und sind für eine
spätere autorisierte PR-Übergabe aufzubewahren. Sie wurden nicht als neue externe
CI-Artefakte veröffentlicht.

| Datei | SHA256 |
|---|---|
| `frontend-gate.log` | `663f841ee8388dd92b43976c2e89f5def5d3976f5937cf86c8abb16b2ef64ad2` |
| `browser-report.json` | `2b979bc7522804ae011a9711fc194f25e83bdc2109b3017c3b6efd17c549ff7c` |
| `browser-api-contracts.json` | `f61e974914f0e3a347c2491b80a1996095073c65e808fb9db482c482ed77dd09` |

Die unabhängige Alt-PR-Prüfung mit konkreten Quellen steht unter
[Restprüfung #204/#225/#235/#90](../reviews/LEGACY_PR_REMAINDERS_2026-10-20.md).
Alte PRs wurden im Rahmen dieser lokalen Prüfung weder geschlossen noch gemergt.
Die Entwicklungsbranch-/PR-Übergabe ist durch den Startauftrag autorisiert. Die
nachfolgenden tatsächlich erforderlichen Checks am exakten neuen PR- beziehungsweise
Testmerge-Head sind gesondert im bestehenden PR #204 zu ergänzen; die lokalen
Nachweise ersetzen sie nicht. Ein späterer Main-Push-/Release-/Installationsnachweis
bleibt ein eigener Schritt.
