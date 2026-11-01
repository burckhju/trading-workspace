# UX-3 — Einheitliche Hinweise und sichere nächste Aktionen

**Ein kanonischer Hinweisvertrag mit einem begrenzten B1/F1-Produktpiloten.**

UX-3 erklärt vorhandene Feststellung, Ursache, Auswirkung, belegte Systemleistung
und verbleibende Nutzerentscheidung. Fachliche Zustände, Geldberechnung,
Quellenqualifikation, erlaubte Commands und Recovery bleiben bei ihren bestehenden
Ownern. Dieser Einstieg bündelt die zwei zuvor parallelen Entwürfe gemäß der
[integrierten Masterentscheidung](../../coordination/UX_SHARED_CONTRACTS.md#kanonischer-ux3-hinweisvertrag--masterentscheidung-phase-1).

UX3-K wurde als Konsolidierung in [#314](https://github.com/burckhju/trading-workspace/pull/314)
integriert. Die Quellen- und Parallelstände unten dokumentieren diesen historischen
Schnitt. Der gesonderte [B1/F1-Pilot in #320](https://github.com/burckhju/trading-workspace/pull/320)
implementiert eine passive Hinweiskarte in `RealizedGrossSources`. Sein Umfang und
seine Prüfgrenzen stehen in der [Pilotqualifikation](../../implementation/UX3_B1_CURRENCY_NOTICE.md).
Der aktuelle Auftrag endet beim Draft-PR; die parallele Releasevorbereitung
wird auf ausdrückliche Nutzerentscheidung zurückgenommen.

Die [produktiven Props](../../../frontend/src/shared/notices/types.ts) sind eine
schmale Textprojektion für diesen Pilot. Die fünf Hinweisarten und die vollständige
Semantik des [Gesamtvertrags](notice-contract.md) bleiben maßgeblich. Die
[Komponentenbeschreibung](components-and-actions.md#6-exemplarische-komponenten-apis)
trennt tatsächliche B1-Exports und konzeptionelle APIs; es entsteht kein zweiter
Normvertrag. Die 42 Dokumenttypgegenfälle prüfen das vollständige Dokumentmodell,
nicht unmittelbar die produktiven `NoticeView`-Props oder die UI-Abnahme.

## Lesereihenfolge und Lieferumfang

| Artefakt | Inhalt |
| --- | --- |
| [Hinweisinventur](inventory.md) | Ein führender Katalog mit 80 Bestandszeilen in A–E und Zuordnung der ergänzenden Befunde. |
| [Ergänzende Detailinventur](detail-inventory.md) | Die 79 detaillierten Bestandszeilen aus #315 über acht Bereiche, Quellen und Owner; überlappende Nachweise, keine weiteren 79 unabhängigen Fehler und kein zweiter Vertrag. |
| [Fachlicher Hinweisvertrag](notice-contract.md) | Einziger semantischer Vertrag: Identität, Wirkung, Nutzerbedarf, Priorität, Kontextisolation, Schreiben/Readback und Recovery. |
| [Komponenten und Aktionen](components-and-actions.md) | Kompakte Darstellung, Details, Quellen und sichere Navigation; Reader und Commands bleiben beim Owner. |
| [Integration und Folgearbeiten](integration-and-rollout.md) | Pflichtübernahmen, Owner, Typpräzisierungen, Abhängigkeiten und genau ein getrennter B1/F1-Pilot. |
| [Tests und Abnahme](test-and-acceptance.md) | Erhaltene und ergänzte fachliche Gegenfälle, Zuordnung der 24 Fälle aus #315, vorhandene Regressionen und datierte tatsächliche Prüfungen. |
| [TypeScript-Vertrag](contracts.ts) | Vollständiges konzeptionelles Dokumentationstypmodell mit bestehenden Owner-DTOs; die begrenzte B1-Renderer-API ist gesondert dokumentiert. |
| [Typgegenfälle](contracts.type-test.ts) | Positive und negative Beispiele für Belege, Objektidentität, Schreibausgänge, Governance-Reads und Berichtspopulationen. |

Die kanonischen Dateien liegen ausschließlich unter `docs/ui/ux-3/`. Der bestehende
Workspace-Statuskatalog und das maßgebliche Product Backlog erhalten nur Verweise.
`docs/ui/ux3-notice-contract.md` und die parallele B/C/D-Auftragsdatei aus #315 werden
nicht als zweite normative Fassung integriert. Der ursprüngliche PR bleibt als
nachvollziehbare Quelle erhalten; seine Schließung ist kein Bestandteil von UX3-K.

## 1. Geprüfte Quellen und Ausgangsbasis

| Gegenstand | Exakter Bezug | Aussagegrenze |
| --- | --- | --- |
| Produktcode der ursprünglichen Inventuren | [`1883f7f330719453958f8be1dd51d48db816662e`](https://github.com/burckhju/trading-workspace/commit/1883f7f330719453958f8be1dd51d48db816662e), v1.5.35 | Code-/Testbestand vom 31.10.2026; kein Befund über persönliche Depotdaten oder eine PC-Installation. |
| Ausgangsmain der Konsolidierung am 01.11.2026 | [`35f3ab2133fa40beb4ab2e502a08fa3bf5b44e35`](https://github.com/burckhju/trading-workspace/commit/35f3ab2133fa40beb4ab2e502a08fa3bf5b44e35) | #313 integriert; der Delta zur Inventurbasis betrifft fünf Koordinationsdokumente, keinen Produktcode. |
| Führender eingehender UX3-Entwurf | [#314](https://github.com/burckhju/trading-workspace/pull/314), `52a24266dce1ec048b23360b4b75d5b3f54d746b` | Zehn Dokumentations-/Typdateien, 80 Katalogzeilen und 48 ursprüngliche Abnahmefälle. Historische Tests bleiben an diesen Head gebunden. |
| Verpflichtende Ergänzungen | [#315](https://github.com/burckhju/trading-workspace/pull/315), `d9d85f1af3159c4356c8773d076decbf1dc604e4` | 79 Detailzeilen, fachliche Präzisierungen und 24 Fälle; nachvollziehbar in den kanonischen Vertrag übernommen. |
| Verbindliche Koordination | [Shared Contracts](../../coordination/UX_SHARED_CONTRACTS.md), [Ownership](../../coordination/UX_OWNERSHIP.md), [Abhängigkeiten](../../coordination/UX_DEPENDENCIES.md) | Ein Owner je gemeinsamer Grenze, vier Typpräzisierungen und vollständige Pflichtübernahmen. |

Die damalige Dateiliste, der Head, die Mainbasis, der Testmerge/Tree und die
zugehörigen Run-/Jobnachweise der Konsolidierung stehen in
[PR #314](https://github.com/burckhju/trading-workspace/pull/314). Ein späterer
Main- oder Headwechsel benötigt die betroffene erneute Prüfung; ältere CI wird
nicht als Nachweis des konsolidierten Vertrags ausgegeben.

## 2. Parallelstände und abgegrenzte Zuständigkeit

Beim Start der Konsolidierung am 01.11.2026 wurden diese Remote-Heads aufgelöst:

| Strang | Sichtbarer Head | Bedeutung für UX3-K |
| --- | --- | --- |
| UX-1 / [#312](https://github.com/burckhju/trading-workspace/pull/312) | `8f67442daac6879d7dfb28416f2171f67aead0e5` | Herkunft/Preview bleiben beim TradePosition-Owner; dessen Produktänderungen werden nicht übernommen. |
| UX-2 / [#311](https://github.com/burckhju/trading-workspace/pull/311) | `55072f8e90c00d309c3bd6ed6dd17f61ab33bd32` | Shared-Navigation ist im Draft vorhanden. Hostintegration, Fokus und Readback gehören UX-2; dessen Quellcode wird nicht mit UX3-K gemergt. |
| UX-4 / [#316](https://github.com/burckhju/trading-workspace/pull/316) | `ae8c792f3e3ad74994894fac581cb4cf81ba5de7` | Eigener Dokumentationsschnitt, kein fehlender Qualitätsowner. Spätere Darstellung konsumiert den kanonischen UX3-Vertrag. |
| Koordinationsrelease / [#317](https://github.com/burckhju/trading-workspace/pull/317) | `b6123628b4e608ad737b91d4ee4f9e2d3c31f434` | Bereitet v1.5.36 separat vor. UX3-K beansprucht diese Version nicht; eine eigene Bereitstellung prüft den dann tatsächlichen Main-/Tagstand. |

Die integrierte Koordination ordnete die unabhängige UX4-A-Dokumentation vor der
UX3-K-Vertragsintegration ein und verlangte anschließend UX2-A vor der gezielten
UX1-Integration. B1/F1 setzt auf deren gemeinsam integriertem Stand aus #318 auf.
Fremde Featurebranches, Alt-PRs oder fachliche Freigaben wurden durch UX3-K nicht
übernommen. Ein veröffentlichter Querverweis ist kein Beleg
eines bestätigten Empfangs oder einer Abnahme durch einen anderen Lead.

## 3. Fachliche Grenzen

- Historische Ausführungswährung folgt dem bestehenden Resolver und zeitlich
  gültigen Belegen. Heutiges Listing, Browserzone und Berichtswährung sind kein Ersatz.
- Unbekannte Finanzbeträge bleiben unbekannt. Report-/Itemstatus und vorhandene
  Verwendbarkeitsflags bestimmen die Wirkung; ein Reason allein erfindet keine Sperre.
- Abruf, Kursverwendbarkeit, Originalzeit, Historienabdeckung und Persistenz bleiben
  getrennt. Ein alternativer qualifizierter Kurs behebt keine fremde Providerstörung.
- Historische Plan-, Review-, Journal- und Lessonpins bleiben exakt. Aktuelle
  Ableitungen dürfen eine neue Grundlage erhalten, ohne historische Fakten umzuschreiben.
- Eine stabile Ursachenidentität erlaubt keine veralteten Werte oder Aktionen.
  Requestgeneration und Berichtsbasis sichern die Gültigkeit, erzeugen allein aber
  keine neue Ursache oder erneute Alarmansage.
- Anzeigen, Aufklappen und Links führen keinen Fachcommand aus. Readbuttons,
  Dirty-Guards, Idempotenz, Versionsschutz und bewusste Writes bleiben beim Owner.
- Eine verlorene Speicherantwort beweist keine Ablehnung. Ein bestätigter Receipt
  bleibt auch bei anschließendem Readfehler eine Bestätigung des Schreibvorgangs.
- Die [Hebeltrader-Anforderungen](../../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md)
  dokumentieren ihren tatsächlichen Umfang; UX3-K aktiviert keine weiteren Regeln.

## 4. Autorisierung, Prüfung und Liefergrenzen

UX3-K erfüllte den konkret festgelegten Konsolidierungsauftrag ohne neue
Produktkomponente. Der anschließende B1/F1-Produktschnitt wird in #320 mit eigenen
Prüfbelegen geführt. Für diesen Pilot autorisiert der Nutzerauftrag vom
**01.11.2026** Implementierung, Tests, Feature-Branch und Draft-PR. Auf die
konkret vorgeschlagene Rücknahme der parallelen Versions- und Releasevorbereitung
hat der Nutzer ausdrücklich mit „Zurücknehmen“ geantwortet. Version 1.5.37 bleibt
erhalten; Merge, Release, Installation und produktive Datenmutation sind durch
diesen Auftrag nicht freigegeben. Technische Prüfungen ersetzen keine menschliche
Fachabnahme. Weitere Produktaufträge bleiben eigenständige Schnitte.

Die Dokumentprüfung und der strict/noEmit-Typcheck qualifizieren den Vertrag.
Die unveränderten [Backend](../../../.github/workflows/backend.yml)-,
[Frontend](../../../.github/workflows/frontend.yml)-,
[End-to-End](../../../.github/workflows/e2e.yml)- und
[Veröffentlichungsgates](../../../.github/workflows/version-tag.yml) prüfen den
tatsächlichen PR-/Releasehead. Alte Einzelerfolge ersetzen diese Nachweise nicht.
Historische Vertragsprüfungen stehen im [Prüfprotokoll](test-and-acceptance.md),
aktuelle Produktnachweise in der Pilotqualifikation und am tatsächlichen PR-Head.

Dokumentation, bestandene Prüfung, Main-Integration, veröffentlichter Tag,
PC-Installation und menschliche Fachabnahme sind getrennte Nachweise. Der vorhandene
[PC-Updater](../../technical/LINUX_LAUNCHER.md) verwendet einen verifizierten Tag und
vollständigen Commit-SHA; eine Bereitstellung behauptet keine bereits ausgeführte
Installation auf dem Nutzerrechner. Der Arbeits- und Abnahmestatus bleibt allein
im [Product Backlog](../../planning/PRODUCT_BACKLOG.md).
