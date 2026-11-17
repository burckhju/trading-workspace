# F207: vorhandene PR-Kette erneut geprüft am 17.11.2026

Dieser lesende Integrationsbefund ist kein Aufgabenstatus. Maßgeblich bleibt
[`PRODUCT_BACKLOG.md`](../planning/PRODUCT_BACKLOG.md). Er dokumentiert die
unveränderte Grundlage für Folgearbeiten; weder Merge noch Veröffentlichung,
Installation oder produktiver Betrieb wurden damit ausgeführt.

## Exakter Ausgangsstand

- Main: `19a10ad484293995e200b5eb9a99b4ae11a49ee2`, Merge von #347.
- Main-Tree: `c51703185c713034245306b00bf17ce7e6d80cea`; identisch mit
  #347-Head `093e97899fd35a1f8f508518ebe606fad8e2e237`, auf dem #348 aufbaut.
- VERSION: `1.5.46`.
- Tag `v1.5.46`: `d01c259f4b79fdfbdcec8743ececda035b69f9d1`, Tree
  `2371c76ac02f747d1961494c011b4cccdb3ad651` (Merge #340). Der Tag enthält
  die späteren Main-Änderungen nicht.

Git-Referenzen, lokale Commit-/Treeobjekte und aktuelle GitHub-Metadaten stimmen
überein. Alle drei PRs sind offen, Draft und `mergeable=true`; ihre formale Base
ist jeweils unverändert `main` am oben genannten Stand. Die vorhandenen Branches
wurden nicht verändert.

| PR | Bestätigter Head | Branch | Eigener Zusatz |
| --- | --- | --- | --- |
| [#348](https://github.com/burckhju/trading-workspace/pull/348) | `9a6168c12eca72094fda925862819e49d5df7485` | `feat/f207-3-original-bid-evidence` | Gegen Main/#347-Tree: 37 Dateien, +6.171 / −26 |
| [#349](https://github.com/burckhju/trading-workspace/pull/349) | `c258101a490353468bd03a7bf0b531fa0a43b727` | `feat/f207-3-product-price-scale` | Gegen #348: 39 Dateien, +5.216 / −37 |
| [#350](https://github.com/burckhju/trading-workspace/pull/350) | `77b3312da20b83d207f1da9c9b5f379b705dc8bb` | `feat/f207-3-market-status-evidence` | Gegen #349: 32 Dateien, +2.562 / −55 |

#349 enthält #348 unverändert in seiner Abstammung; #350 ist ein einzelner
Commit direkt auf #349. Die eigenen Diffs wurden getrennt gelesen. #348 erhält
Original-BID-Seitenzeit und passive Eingangsvoraussetzungen; #349 ergänzt den
dokumentgebundenen Product-Maßstabsowner; #350 ergänzt Originalstatuspunkte und
deren begrenzte zeitliche Aussage. Diese Fähigkeiten werden wiederverwendet.

## Tatsächlich geprüfte Integrationsobjekte

Die aktuellen GitHub-Gitobjekte bestätigen jeweils Main und den genannten
PR-Head als beide Eltern. Jeder Testmerge hat denselben Tree wie sein PR-Head.

| PR | Testmerge | Identischer Head-/Testmerge-Tree |
| --- | --- | --- |
| #348 | `cd4f6c5989c25729e47b17ea10cfe3a84e8b3809` | `463eac3e5b859a8a6f4553741c52d7f6899c1f3e` |
| #349 | `3e3540690b9051160235d89225839ac6fca14909` | `cecbfc307442f681ebe01170da1b1d319c27a56f` |
| #350 | `6ceef819fa757a297a722cb5579b5743dcaead07` | `9b8abd0a8728a43caaf27ab857d4462977046f6a` |

Die Metadaten aller zwölf regulären Läufe wurden erneut gelesen: Ereignis
`pull_request`, jeweils Versuch 1, `completed/success`, exakt der jeweilige
PR-Head. Bestehende `.github`-Workflows, reguläre Backend-/Frontend-Prüfskripte
und VERSION wurden in der gesamten Kette gegenüber Main nicht verändert.

| PR | Backend | Frontend | End-to-End | Versionsguards |
| --- | --- | --- | --- | --- |
| #348 | [43760691233](https://github.com/burckhju/trading-workspace/actions/runs/43760691233) | [43760691296](https://github.com/burckhju/trading-workspace/actions/runs/43760691296) | [43760691195](https://github.com/burckhju/trading-workspace/actions/runs/43760691195) | [43760691202](https://github.com/burckhju/trading-workspace/actions/runs/43760691202) |
| #349 | [43809683766](https://github.com/burckhju/trading-workspace/actions/runs/43809683766) | [43809683779](https://github.com/burckhju/trading-workspace/actions/runs/43809683779) | [43809683798](https://github.com/burckhju/trading-workspace/actions/runs/43809683798) | [43809685492](https://github.com/burckhju/trading-workspace/actions/runs/43809685492) |
| #350 | [43820780012](https://github.com/burckhju/trading-workspace/actions/runs/43820780012) | [43820780078](https://github.com/burckhju/trading-workspace/actions/runs/43820780078) | [43820780036](https://github.com/burckhju/trading-workspace/actions/runs/43820780036) | [43820780031](https://github.com/burckhju/trading-workspace/actions/runs/43820780031) |

Zusätzlich erneut gelesene Original-Joblogs:

- Backend #348: Checkout des oben genannten Testmerge, 5.027 Tests bestanden,
  Coverage 89,32 %; Backend #349: 5.203 bestanden, Coverage 89,47 %.
- Backend #350: 5.339 bestanden, Coverage 89,51 % bei unverändertem 85-%-Gate.
  Die zwei Produktmaßstabs-PostgreSQL-Fälle und der gespeicherte
  Kurs-/Statusbeleg-PostgreSQL-Fall sind tatsächlich ausgeführt. Ruff, Black,
  Mypy, Migration und beide Imagejobs sind erfolgreich.
- Frontend #350: 2.621 Tests in 198 Dateien bestanden, Coverage Lines/Statements
  96,71 %, Branches 91,28 %, Functions 92,54 %.
- E2E #350: 206 Smokefälle bestanden, **5 ausdrücklich übersprungen**. Die
  entsprechenden Ownerjobs weisen Candidate 1, Journal/Evidence 2, Realized
  Gross 1 und Full-close 1 als bestanden aus. Ihre Checkoutlogs binden sie an
  denselben #350-Testmerge.
- Versionsguards #350: 9 Tests bestanden. Der separate Tagjob ist ausdrücklich
  **skipped**; das ist keine Veröffentlichung.

Diese erneute Prüfung führt keine Tests aus. Originalartefakte und deren
Digests wurden dabei nicht nochmals heruntergeladen/geprüft; die früheren
Detailnachweise in den PRs werden nicht als neu ausgeführte Prüfungen gezählt.
Es gibt aktuell keine GitHub-Reviewsubmissions oder Reviewthreads an den drei
PRs. In PR-Beschreibungen dokumentierte unabhängige Prüfungen sind keine
formalen GitHub-Approvals.

## Aussagegrenzen und Folgearbeit

Der unveränderte #350-Tree ist als gemeinsame Entwicklungsgrundlage exakt
wiederverwendbar. Die spätere Integration ist in der Reihenfolge
#348 → #349 → #350 vorzubereiten. Bis zur ausdrücklichen Mergefreigabe bleiben
Folgearbeiten auf eigenen, abhängig gekennzeichneten Branches; neue Änderungen
erhalten eigene head- und integrationsgebundene Nachweise.

#350 erlaubt bewusst keine positive B58-Qualifikation: sein Statusreader liefert
nur `MISSING`, `UNSUITABLE` oder `NOT_APPLICABLE`. Ein Originalstatuspunkt besitzt
die Bedeutung `OBSERVED_AT_INSTANT`, keine abgeleitete Gültigkeitsdauer.
`SAVED_QUOTE_LAST_SUCCESS_ONLY` und
`NOT_OBSERVED_BY_SAVED_QUOTE_READER` benennen die fehlende Erhaltung neuerer
preisloser/negativer Statusinformationen. Ein anwendungseigenes
`status_observed_at` im Frankfurt-JSON ist kein Nachweis eines tatsächlich
verfügbaren qualifizierten Datenlieferanten. Quellenqualifikation,
preisunabhängige Statuspersistenz und der B04/B57-Regel-/Betriebspfad bleiben
deshalb eigenständige Folgebeiträge.
