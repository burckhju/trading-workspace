# UX-3 — Einheitliche Hinweise und sichere nächste Aktionen

**Status: Dokumentierter Entwurf zur Prüfung. Keine produktive Hinweisarchitektur.**

Die Anwendung soll Zustand, Ursache, Auswirkung, bereits mögliche automatische
Lösung und tatsächlich notwendige Nutzerentscheidung zusammen erklären. UX-3
ordnet vorhandene Domaininformationen für die Darstellung; Entscheidungen und
Berechnungen bleiben bei ihren bisherigen Ownern.

## Lesereihenfolge und Lieferumfang

| Artefakt | Inhalt |
| --- | --- |
| [Hinweisinventur](inventory.md) | Tatsächlich gelesene Meldungen und Codes in A–E, normale Zustände, Dopplungen, konkrete Verbesserungen. |
| [Fachlicher Hinweisvertrag](notice-contract.md) | Identität, Ursachen, Auswirkungen, Semantik, Priorität, automatische Lösung, Kontextisolation und Recovery. |
| [Komponenten und Aktionen](components-and-actions.md) | Kompakte Darstellung, Details, sichere Navigation, mobile und barrierefreie Bedienung. |
| [Integration und Folgearbeiten](integration-and-rollout.md) | Owner, bestehende Verträge, UX-1-/UX-2-Schnittstellen, Entscheidungsbedarf und kleine Umsetzungsschritte. |
| [Tests und Abnahme](test-and-acceptance.md) | Positive und negative Beispiele, vorhandene Regressionen, geplante Abnahme und tatsächlich ausgeführte Prüfungen. |
| [TypeScript-Verträge](contracts.ts) | Ausschließlich Vorschlag: Präsentationstypen und Komponenten-Props, ohne Renderer, Resolver, Store oder API-Endpunkt. |
| [Typprüfungen](contracts.type-test.ts) | Positive Beispiele und erwartete Typfehler für fehlende Belege, falsche Aktionstypen und vertauschte Domainzustände. |

Alle Dateien dieses Schnitts liegen unter `docs/ui/ux-3/`. Sie werden nicht vom
Produktimportgraphen verwendet. Die Prüfskripte sind lokale Dokumentationswerkzeuge.

## 1. Tatsächlich geprüfter Repository-Stand

Abgleich am **31.10.2026** über GitHub-API und frischen Repository-Checkout.
Dateiinhalte und Tests wurden am folgenden Commit gelesen; frühere PR-Texte sind
keine Implementierungsnachweise.

| Gegenstand | Verifizierter Stand | Aussagegrenze |
| --- | --- | --- |
| Main | [`1883f7f330719453958f8be1dd51d48db816662e`](https://github.com/burckhju/trading-workspace/commit/1883f7f330719453958f8be1dd51d48db816662e) | Ausgangsstand dieses Entwurfs. |
| Main-Tree | `e90aa341805c71362df1cda1a9dc378b0af9c4fe` | Ausgangsbaum ohne UX-3. |
| Version | `VERSION`, Backend- und Frontend-Metadaten: `1.5.35` | Kein Beleg einer PC-Installation. |
| Veröffentlichungstag | [`v1.5.35`](https://github.com/burckhju/trading-workspace/tree/v1.5.35) zeigt auf denselben Main-Commit | Der vorhandene Version-Tag-Workflow publiziert Tags. |
| GitHub-Release-Eintrag | [`v1.0.0-product-selection`](https://github.com/burckhju/trading-workspace/releases/tag/v1.0.0-product-selection), veröffentlicht 16.08.2026 | Beim Abgleich einziger Release-Eintrag und Antwort von `releases/latest`; nicht mit dem neuesten Softwaretag verwechseln. |
| Backend Main-CI | [41171213873](https://github.com/burckhju/trading-workspace/actions/runs/41171213873), `push`, `success` | Belegt den genannten Main-Commit, nicht diesen Dokumentations-Head. |
| Frontend Main-CI | [41171213875](https://github.com/burckhju/trading-workspace/actions/runs/41171213875), `push`, `success` | Derselbe Commit. |
| E2E Main-CI | [41171214040](https://github.com/burckhju/trading-workspace/actions/runs/41171214040), `push`, `success` | Derselbe Commit. |

Die Workflows [Backend](../../../.github/workflows/backend.yml),
[Frontend](../../../.github/workflows/frontend.yml) und
[End-to-End](../../../.github/workflows/e2e.yml) prüfen PRs auf Main auch bei reinen
Dokumentationsänderungen. Bestehende Gates bleiben unverändert: Backend-Coverage
85 %, Frontend Lines/Functions/Statements 80 % und Branches 70 %.

## 2. Offene parallele Arbeiten

Die vollständige offene PR-Liste umfasste beim ersten Abgleich fünf Einträge.
Während der Analyse wurden UX-1 und UX-2 als weitere Drafts sichtbar. Beim
erneuten Abgleich blieb Main unverändert; die offene Liste umfasste sieben PRs:

| PR | Stand | Head | Abgrenzung |
| --- | --- | --- | --- |
| [#312 — UX-1](https://github.com/burckhju/trading-workspace/pull/312) | Draft | `74d29bb8197d4819f3edc948143a41f4cd7046c8` | Tatsächlicher 31-Dateien-Diff geprüft: Eingabewiederverwendung und lesende historische Währungsvorschau; nicht in Main. |
| [#311 — UX-2](https://github.com/burckhju/trading-workspace/pull/311) | Draft | `6782bc7a567ce24d480e3e7996f919399f28896f` | Tatsächlicher 25-Dateien-Diff geprüft: kontexterhaltende Trade-/Quellen-/Journalnavigation und Fokus; nicht in Main. |
| [#220](https://github.com/burckhju/trading-workspace/pull/220) | offen, kein Draft | `40da0f23dea50cf6c70f1232f61ffd83f825dd19` | Recherche weiterer Kursquellen, kein Aktivierungsnachweis. |
| [#207](https://github.com/burckhju/trading-workspace/pull/207) | Draft | `85921b9a6db30028a25b9c69a3e9a97a50482c10` | Eigenständige Monitoringarbeit; Beschreibung ersetzt keinen in Main gelesenen Code. |
| [#205](https://github.com/burckhju/trading-workspace/pull/205) | Draft | `ba7f442a027c55fd3bb15ed6f77271690c8a9055` | Älterer Historienentwurf; heute vorhandene Historie wird aus Main inventarisiert. |
| [#197](https://github.com/burckhju/trading-workspace/pull/197) | Draft | `08d2a5c9abe91ef518eb2c940eff9bbeceb073f8` | Historische Forschung, keine produktive Regelfreigabe. |
| [#187](https://github.com/burckhju/trading-workspace/pull/187) | Draft | `bad00a420f56994216ad1def6a580b00b0f5772f` | Eigenständiger Hebeltrader-Entwurf außerhalb Main. |

Beim ersten Abgleich gab es keinen eindeutig erkennbaren UX-1-/UX-2-Arbeitsstand;
die inzwischen vorhandenen Drafts wurden anschließend über ihre **tatsächlichen
Dateiänderungen an den oben genannten Heads** geprüft. Ihr Code wird separat im
[Parallelabgleich](integration-and-rollout.md#2a-nachtrag-zu-den-inzwischen-sichtbaren-parallel-prs)
beschrieben und nicht zur Main-Inventur gezählt. Spätere Heads brauchen einen
erneuten Abgleich. Eine Codeinspektion ist keine Abstimmung oder Freigabe durch
die anderen Owner. Kein fremder Feature-Branch wird übernommen oder gemergt.
Der eigene Branch lautet `docs/ux-3-notice-contract`.

## 3. Fachliche Grenzen

- Historische Ausführungswährung folgt dem bestehenden Resolver und zeitlich
  gültigen Belegen. Ein heutiges EUR-Listing beweist keinen historischen Kauf.
- Unbekannte Finanzbeträge bleiben unbekannt; kein `null → 0`, keine zusätzliche
  Währungsumrechnung und keine zweite Kostenbasisrechnung im Frontend.
- Abruf, verwendbarer Kurs, Originalzeit, Sitzungsfrische, Historienabdeckung und
  Persistenz sind getrennte Aussagen. Ein Ersatzkurs beweist keinen erfolgreichen Abruf.
- Historische Plan-, Review-, Journal- und Lesson-Versionen bleiben exakt gebunden.
  Eine fehlende Version wird nicht still durch die aktuelle ersetzt.
- Anzeigen, Aufklappen und Navigation erzeugen keine Bestätigung, Freigabe,
  Materialisierung, Order, Mengenentscheidung oder Strategieaktivierung.
- Der in Main vorhandene [Hebeltrader-Integrationsvertrag](../../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md)
  aus #309 ist Dokumentation historischer Anforderungen. Er aktiviert diese Regeln nicht.
- Fixtures sind synthetisch. Für diese Planung wurden keine produktiven
  Nutzerbestände, Providerkonten oder privaten Handelsdaten abgerufen.

## 4. Arbeits- und Freigabestatus

| Statuswort | Bedeutung für UX-3 in diesem Schnitt |
| --- | --- |
| Dokumentiert | Inventur und nachweisbare Main-Verträge liegen vor. |
| Konzipiert | Präsentationsvertrag, Komponenten-APIs, Aktionen und Folgearbeiten vorgeschlagen. |
| Implementiert | Nur Dokumente, typprüfbare Beispiele und deren Prüfwerkzeuge; keine produktive Architektur. |
| Getestet | Umfang und Ergebnis ausschließlich nach [Prüfprotokoll](test-and-acceptance.md). Ein Typcheck beweist keine fertige Oberfläche. |
| In Main integriert | Nein, dieser Schnitt bleibt ein eigenständiger Draft-PR. |
| Veröffentlicht | UX-3 nicht veröffentlicht. `v1.5.35` bezeichnet den bestehenden Ausgangsstand. |
| Auf dem PC installiert | Nicht geprüft und nicht ausgeführt. |
| Fachlich abgenommen | Offen; Draft und technische Tests ersetzen keine fachliche Abnahme. |

Die Planungsphase liefert einen reviewbaren Vertrag. Eine spätere Umsetzung oder
ein Merge benötigt einen eigenen Auftrag im jeweils abgegrenzten Umfang.
