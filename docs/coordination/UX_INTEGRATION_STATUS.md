# UX-Integrationsprotokoll

## Geltung und Nachweisgrenze

**Prüfsnapshot: 31.10.2026, 14:16 Uhr Europe/Vienna (13:16 UTC).** Technisches Integrationsprotokoll, keine zweite fachliche Aufgaben-/Abnahmestatusliste. Maßgeblich bleibt [PRODUCT_BACKLOG](../planning/PRODUCT_BACKLOG.md). Nach jeder Head-/Main-Änderung die betroffenen Nachweise erneuern; spätere CI anhand der verlinkten Runs und des aktuellen PR-Heads prüfen.

Geprüft: vollständiger Main-Baum (2.377 Einträge, nicht gekürzt), Architektur-/Ownership-/Backlogvorgaben, betroffene Code-/Testdateien, vollständige Dateilisten der sieben offenen PRs, Main-Abstand, aktuelle Workflow-/Jobergebnisse und fehlgeschlagene UX-Joblogs. Alle 294 sichtbaren Branches wurden erfasst. Auf Main existierten weder die fünf angeforderten Koordinationsdokumente noch `AGENTS.md` oder `CODEOWNERS`. UX-1 und UX-2 besitzen eigene Übergabedokumente; diese werden verlinkt.

Lokaler Git-Netzzugriff war nicht verfügbar; Prüfung über GitHub-Datei-/Tree-/Compare-/Actions-Zugriff. Kein vollständiger lokaler Anwendungsbuild und keine neue lokale Produkt-Testausführung. Die Alt-PR-Prüfung betrifft Umfang/Basis/CI, keine erneute vollständige fachliche Codeabnahme. Nicht veröffentlichte Arbeitsstände anderer Chats sind unbekannt.

## Main und Veröffentlichung

| Nachweis | Geprüfter Stand |
|---|---|
| Main | [`1883f7f330719453958f8be1dd51d48db816662e`](https://github.com/burckhju/trading-workspace/commit/1883f7f330719453958f8be1dd51d48db816662e) |
| Main-Tree | `e90aa341805c71362df1cda1a9dc378b0af9c4fe` |
| Version | `VERSION` und Frontendmanifest: `1.5.35`; [Tag `v1.5.35`](https://github.com/burckhju/trading-workspace/tree/v1.5.35) zeigt auf denselben Main-Commit. |
| Main-CI, Event `push` | [Backend 41171213873](https://github.com/burckhju/trading-workspace/actions/runs/41171213873): drei Jobs erfolgreich; [Frontend 41171213875](https://github.com/burckhju/trading-workspace/actions/runs/41171213875): ein Job erfolgreich; [E2E 41171214040](https://github.com/burckhju/trading-workspace/actions/runs/41171214040): vier Jobs erfolgreich. Alle am genannten Main-SHA. |
| Veröffentlichung | [Version tag 41172652775](https://github.com/burckhju/trading-workspace/actions/runs/41172652775): Publikationswächter und Tagjob erfolgreich. |
| GitHub-Release-Eintrag | `releases/latest` liefert [`v1.0.0-product-selection`](https://github.com/burckhju/trading-workspace/releases/tag/v1.0.0-product-selection). Laut [Veröffentlichungsvertrag](../releases/V1.5.35-HEBELTRADER-CONTRACT.md) ist kein separater Release-Eintrag erforderlich; Tag-/Updatervertrag ist maßgeblich. |
| PC und Fachabnahme | Hier nicht geprüft. Tag/Main-CI sind kein Installations- oder Gesamtfachabnahmebeleg. |

## Vier UX-Stränge: Lieferung und fehlende Übergabe

| Strang | Tatsächlicher Befund | Integrationsgrenze / offene Übergabe |
|---|---|---|
| UX-1 | [Draft #312](https://github.com/burckhju/trading-workspace/pull/312), zuletzt 33 Dateien: Currency-Preview aus bestehendem Resolver, eindeutigen Auswahlrun lesend öffnen, editierbarer Browserzonenvorschlag. [Leadbericht](https://github.com/burckhju/trading-workspace/blob/8f67442daac6879d7dfb28416f2171f67aead0e5/docs/implementation/UX1_INPUT_REUSE_QUALIFICATION.md). | Korrektur von Zeitfeedback/Testkontext gelesen; neue Frontend-CI grün, Backend/E2E laufen. API-/Importgrenze und gemeinsame Hostregression offen. Journal-/Lessonverknüpfung dort nur Bestandsaufnahme. |
| UX-2 | [Draft #311](https://github.com/burckhju/trading-workspace/pull/311), zuletzt 27 Dateien: UX2-A Navigation/Pins/Rückwege. [Leadbericht](https://github.com/burckhju/trading-workspace/blob/79e9b97e31d3bf80936fb5c026798bf8ebb10b33/docs/ui/ux2-trade-workspace.md). | Testkorrektur gelesen; neue Frontend-/E2E-CI grün, Backend läuft. Gemeinsame Importgrenze offen. UX2-B/C/D sind vorbereitet, nicht implementiert. |
| UX-3 | Vorhandene Alert-/Risk-/Runtime-/Feedbackkomponenten und getrennte Daten-/Zustellzustände im Main-Code geprüft. | Kein veröffentlichter eigener Programmhead/Leadbericht nachgewiesen. Übergabe gemäß [Auftragsblatt](UX_MASTER_PLAN.md#übergabepaket-ux-3--hinweise-und-sichere-folgeaktionen) angefordert; kein Rückschluss auf unveröffentlichte Arbeit. |
| UX-4 | Vorhandener Positionskursverlauf, Marktcharts, Evidenztabellen und serverseitige Abschlussstatistik im Main-Code geprüft. | Kein veröffentlichter eigener Programmhead/Leadbericht nachgewiesen. Übergabe gemäß [Auftragsblatt](UX_MASTER_PLAN.md#übergabepaket-ux-4--diagramme-und-kennzahlen) angefordert; #205 ist keine neue Chartimplementierung. |

## Exakte UX-Heads und aktuelle CI

Alle folgenden Runs: Versuch 1, Event `pull_request`. Erfolgreiches `Version tag` auf einem PR bestätigt nur die Publikationswächter; der Tagjob ist übersprungen und keine Veröffentlichung.

| PR | Head / Testmerge | CI am Prüfzeitpunkt |
|---|---|---|
| #311, aktueller Head | `79e9b97e31d3bf80936fb5c026798bf8ebb10b33`; Testmerge `dff5096ca5b7e7118596c16da8ed95804e44777d`; Main-Basis `1883f7f…`. | [Backend 41204251167](https://github.com/burckhju/trading-workspace/actions/runs/41204251167) läuft; [Frontend 41204251146](https://github.com/burckhju/trading-workspace/actions/runs/41204251146), [E2E 41204251248](https://github.com/burckhju/trading-workspace/actions/runs/41204251248) und [Wächter 41204251142](https://github.com/burckhju/trading-workspace/actions/runs/41204251142) erfolgreich. |
| #312, aktueller Head | `8f67442daac6879d7dfb28416f2171f67aead0e5`; Testmerge `817a6762de66444127e7640650904b3af7122875`; Main-Basis `1883f7f…`. | [Backend 41204565968](https://github.com/burckhju/trading-workspace/actions/runs/41204565968) und [E2E 41204565951](https://github.com/burckhju/trading-workspace/actions/runs/41204565951) laufen; [Frontend 41204566048](https://github.com/burckhju/trading-workspace/actions/runs/41204566048) und [Wächter 41204565967](https://github.com/burckhju/trading-workspace/actions/runs/41204565967) erfolgreich. |

Beide PRs haben gegenüber dieser Main-Basis keinen Rückstand und sind laut GitHub textuell mergebar; sie bleiben Draft. Bei der Reviewabfrage keine abgegebenen Reviews oder Reviewthreads gefunden; dies ist keine fachliche Zustimmung.

### #311: historischer Fehler und gelesene Korrektur

Am zuerst geprüften Head `6782bc7a567ce24d480e3e7996f919399f28896f` testete GitHub Merge `a0dfa28c4a12824056637870cac3d9eab722a01c` mit Main und diesem Head als Eltern. Frontend war erfolgreich; Backend wurde beim Fortschreiben abgebrochen. [E2E 41203752901](https://github.com/burckhju/trading-workspace/actions/runs/41203752901) scheiterte in zwei Jobs:

- [Smoke 124544558459](https://github.com/burckhju/trading-workspace/actions/runs/41203752901/job/124544558459): drei veraltete nackte Lessonlink-Erwartungen in `post-trade-handoff-pin.spec.ts`; 134 bestanden, fünf übersprungen.
- [Journal/Evidence 124544558258](https://github.com/burckhju/trading-workspace/actions/runs/41203752901/job/124544558258): `post-trade-journal-postgres.spec.ts` las die ID per Stringsplit aus dem gesamten neuen Link einschließlich Query/Hash. Der lokale Requestguard blockierte korrekt vor dem Request. Einer von zwei nativen Fällen bestanden.

[Delta zum aktuellen Head](https://github.com/burckhju/trading-workspace/compare/6782bc7a567ce24d480e3e7996f919399f28896f...79e9b97e31d3bf80936fb5c026798bf8ebb10b33): nur diese zwei Testdateien (+15/-9), genaue Kontext-URLs prüfen und ID aus `URL.pathname` lesen. Schutzprüfungen und Produktcode unverändert. Die Korrektur ist gelesen; neue Frontend-/E2E-CI ist erfolgreich, Backend läuft noch. Der Importgrenzenbefund besteht fort.

### #312: historische Fehler und gelesene Korrektur

Die folgenden Fehler gehören zu Head `74d29bb8197d4819f3edc948143a41f4cd7046c8`, tatsächlich ausgechecktem Testmerge `d5df27fe74f41542daacd0f0812ac8025af2050d`, Tree `297c483014dd6df4f5a700c203e2cfef8f27745e`. Sie werden nicht auf den neuen Head übertragen.

- [Frontend / quality 124544681820](https://github.com/burckhju/trading-workspace/actions/runs/41203796168/job/124544681820): TypeScript, ESLint und Prettier erfolgreich; 27 Tests fehlgeschlagen, 1.834 bestanden. `ClosedTradesPage.test.tsx` und `RealizedGrossPage.test.tsx` erwarten Berlin und liefern Berlin-Fixtures, während der neue Browserzonenvorschlag im Runner UTC ist. Berichtskontextschutz verwirft unpassende Antworten korrekt. Testzone explizit kontrollieren, Initial-/Fallbackvertrag prüfen, negative Kontextprüfungen erhalten. Build übersprungen.
- [E2E / smoke 124544681821](https://github.com/burckhju/trading-workspace/actions/runs/41203796149/job/124544681821): 129 bestanden, ein Fehler, fünf übersprungen. `trade-capture-dst.spec.ts` findet den DST-Fehlertext in Preview und Submitstatus; globaler Locator mehrdeutig. Formular-/Statusbezug präzisieren und vollständige Keine-POST-/Historien-/Date-only-Prüfung erhalten: Der Test brach vor diesen Nachweisen ab. Drei übrige E2E-Ownerjobs erfolgreich. UX-1 und UX-3 klären gewünschte doppelte Hinweisdarstellung.

Das [Delta zu `8f67442d…`](https://github.com/burckhju/trading-workspace/compare/74d29bb8197d4819f3edc948143a41f4cd7046c8...8f67442daac6879d7dfb28416f2171f67aead0e5) ändert fünf Dateien: beide Performance-Seitentests wählen ihre Berichtszone ausdrücklich und mocken eine abweichende Browserzone; die Preview zeigt bei ungültiger Zeit nur einen allgemeinen Eingabehinweis ohne wirkungslosen Retry. Präzise DST-Validierung bleibt beim Captureformular; neue Unitprüfung ergänzt. Der vorhandene DST-Browserfall, Capture-/API-/Domainlogik und sämtliche Workflows bleiben unverändert. Neue Frontend-CI ist erfolgreich; E2E/Backend laufen noch. Diagnose und Korrektur erlauben kein Lockern der Schutzprüfungen oder eine Integration.

## Schnittstellen- und Integrationshindernisse

1. **Gemeinsame Datei:** Dateischnittmenge #311/#312 ist genau `frontend/src/features/trade/pages/TradeManagementPage.tsx`. Dreiwegevergleich temporärer, blobverifizierter Kopien: Exitcode 0, keine Konfliktmarker. Mainblob `e0669aef8ee6080c52094e199ad382414f066fd3`, UX2blob `5362fe8d077c10341ddb2183468950fcb4fa8a09`, UX1blob `77d3e859c4265a53dded6bcd662eb33e26d685b3`; beide UX-Dateiblobs an den neuesten Heads unverändert. Kein Repositorybranch gemergt. Gemeinsames Runtime-/Form-/Async-Verhalten damit nicht qualifiziert.
2. **Importgrenze:** Neue Navigation aus `post_trade`/`learning` importiert interne Trade-Komponenten/Services. Die [gemeinsame Schnittstelle](UX_SHARED_CONTRACTS.md#kontext-navigation-und-gemeinsame-importgrenze--owner-ux-2) vor Integration konkret umsetzen oder per begrenzter Architekturentscheidung klären; Previewintegration entsprechend prüfen.
3. **API-/Domainprüfung:** Additive Currency-Preview-Reads bleiben TradePosition-Vertrag. Keine neue Priorität/Bestätigung aus Preview ableiten; historische Invalidierung mit Navigation/Charts gemeinsam qualifizieren.
4. **Fehlende Übergaben:** UX-3 und UX-4 liefern eigenen Repositorybericht und Dateiumfang, bevor konkrete parallele Arbeiten reserviert werden.
5. **Fach-/Mobil-/Barrierefreiheitsabnahme:** Automatisierte Beispiele und CI belegen keine vollständige menschliche Abnahme oder PC-Installation.

## Weitere offene PRs: tatsächlicher Umfang und Main-Abstand

Diese historischen Headläufe sind erfolgreich, qualifizieren aber keinen Integrationsstand mit aktuellem Main. Vollständige SHAs sind über Commitlinks gebunden.

| PR / Head | Tatsächlicher Diff | Abstand / Konflikt | Alte Head-CI / Einordnung |
|---|---|---|---|
| [#220](https://github.com/burckhju/trading-workspace/pull/220), [`40da0f23`](https://github.com/burckhju/trading-workspace/commit/40da0f23dea50cf6c70f1232f61ffd83f825dd19) | Drei Dokumente zu Emittentenquellen; keine Provideraktivierung. | 510 Commits zurück, `behind`. | [B](https://github.com/burckhju/trading-workspace/actions/runs/34885796940), [F](https://github.com/burckhju/trading-workspace/actions/runs/34885796699), [E](https://github.com/burckhju/trading-workspace/actions/runs/34885796621), 14.09.; separate Quellen-/Domainprüfung. |
| [#207](https://github.com/burckhju/trading-workspace/pull/207), [`85921b9a`](https://github.com/burckhju/trading-workspace/commit/85921b9a6db30028a25b9c69a3e9a97a50482c10) | Nur `.github/workflows/hebeltrader-baseline.yml`; Entwicklungs-/Exportworkflow, kein Regelcode. | 499 zurück, `behind`. | [B](https://github.com/burckhju/trading-workspace/actions/runs/35032404812), [F](https://github.com/burckhju/trading-workspace/actions/runs/35032404811), [E](https://github.com/burckhju/trading-workspace/actions/runs/35032404809), 15.09.; tatsächlichen Implementierungshead anfordern. |
| [#205](https://github.com/burckhju/trading-workspace/pull/205), [`ba7f442a`](https://github.com/burckhju/trading-workspace/commit/ba7f442a027c55fd3bb15ed6f77271690c8a9055) | Historischer Kursverlaufsentwurf plus zwei Entwicklungs-/Exportworkflows. | 548 zurück, `dirty` / nicht mergebar. | [B](https://github.com/burckhju/trading-workspace/actions/runs/34781508726), [F](https://github.com/burckhju/trading-workspace/actions/runs/34781508739), [E](https://github.com/burckhju/trading-workspace/actions/runs/34781508725), 13.09.; gegen vorhandenen Main-Historienpfad abgleichen, keine UX-4-Voraussetzung. |
| [#197](https://github.com/burckhju/trading-workspace/pull/197), [`08d2a5c9`](https://github.com/burckhju/trading-workspace/commit/08d2a5c9abe91ef518eb2c940eff9bbeceb073f8) | Sieben Dateien: Historiencollector, Reparaturskript, Tests, Researchdokument und Workflow. | 577 zurück, `behind`. | [B](https://github.com/burckhju/trading-workspace/actions/runs/34752894574), [F](https://github.com/burckhju/trading-workspace/actions/runs/34752894580), [E](https://github.com/burckhju/trading-workspace/actions/runs/34752894613), 13.09.; Research ist kein produktiver Historien-/Strategienachweis. |
| [#187](https://github.com/burckhju/trading-workspace/pull/187), [`bad00a42`](https://github.com/burckhju/trading-workspace/commit/bad00a420f56994216ad1def6a580b00b0f5772f) | 16 Dateien zu Hebeltrader-Regeln, API/Quelle, Preislogik, UI und Tests. | 630 zurück, `dirty` / nicht mergebar. | [B](https://github.com/burckhju/trading-workspace/actions/runs/34690488439), [F](https://github.com/burckhju/trading-workspace/actions/runs/34690488560), [E](https://github.com/burckhju/trading-workspace/actions/runs/34690488455), 12.09.; eigene Domain-/Regelfreigaben und aktueller Abgleich nötig. |

Für keine dieser Arbeiten folgt eine Merge- oder Schließfreigabe. UX-Reihenfolge: Koordination → UX2-A → UX1 → UX3 → UX4; unabhängige Parallelmöglichkeiten und Regressionen in [UX_DEPENDENCIES](UX_DEPENDENCIES.md).

## Wichtigster nächster Schritt

**UX-2 legt für #311 die konkrete gemeinsame Navigations-/Importgrenze vor und bindet sie an den aktuellen Head.** Damit wird die zuerst empfohlene Produktintegration architektonisch prüfbar; neue CI und anschließende gemeinsame UX-1-Regression bleiben notwendige Nachweise.
