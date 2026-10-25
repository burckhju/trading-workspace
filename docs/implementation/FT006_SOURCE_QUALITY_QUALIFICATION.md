# FT-006: versionierte Quellenqualität — Runtimeanbindung und B07

## 25.10.2026: qualifizierter Vorhead und erneute Aufnahme des aktuellen Main

Der vollständige Folgehead
[`b1a3deb408cd868e5001577fb61c26b183f39643`](https://github.com/burckhju/trading-workspace/commit/b1a3deb408cd868e5001577fb61c26b183f39643),
Tree `873d3cede71a388e9617505a24bcc7d17bb90a68`, ist auf dem tatsächlichen
PR-Testmerge `785af46af8d495cca3e1ba6aedeee5ed93008991` vollständig qualifiziert:

- [Backend `40184070104` / quality `121141070094`](https://github.com/burckhju/trading-workspace/actions/runs/40184070104/job/121141070094),
  Versuch 1: **3377 passed, 1 bestehende Warnung, 797,33 Sekunden**, Coverage
  **87,56 %** bei unverändert 85 % Mindestwert. Alle **38** FT-006- und beide
  neuen nativen Candidate-PostgreSQL-Fälle sind vollständig bestanden.
  Damit ist auch der zuvor fehlerhafte Listing-Snapshotvergleich nach dem
  kanonischen Fixturefix nativ belegt. Ruff, Black, mypy und Migration bestanden.
- [Frontend `40184070110`](https://github.com/burckhju/trading-workspace/actions/runs/40184070110):
  **806 Tests / 124 Dateien**, vollständiges Gate und Produktionsbuild bestanden.
- [E2E `40184070115`](https://github.com/burckhju/trading-workspace/actions/runs/40184070115):
  Smoke **78 passed / 5 geschützte Skips**, dieselben fünf Testidentitäten in
  den separaten Finanz-/Lern-/Governanceownerfällen tatsächlich bestanden,
  jeweils ohne Retry/Skip/Flaky. Image, Renderer und Publikationsguards bestanden;
  der Tagjob ist beim PR erwartungsgemäß übersprungen.
- Das eigene GOOD-B07-Artefakt dieses Heads ist
  [`12595306781`](https://github.com/burckhju/trading-workspace/actions/runs/40184070115/artifacts/12595306781),
  ZIP-SHA256 `e9b0c56d52b566c11318f60f0ff1d627fd20e056fea6d6aa090304bee1045024`.
  Alle 26 Manifestdateien, drei echten GOOD-Quellen, A/A/B/A, Legacy-/Negativfälle,
  14 Verify-/vier GET-Fenster, sechs tatsächlich gesichteten Bilder und Cleanup
  sind erneut geprüft. Auch die vier anderen Ownerfälle besitzen vollständig
  geprüfte eigene Rohartefakte und unveränderte Lesefenster ohne Restressourcen.

Während dieses CI-Laufs wurde jedoch #279 in Main integriert. Beim Schlussabgleich
stand Main bereits auf
[`656cd84eb79831888db2d9b5301b95f43d901251`](https://github.com/burckhju/trading-workspace/commit/656cd84eb79831888db2d9b5301b95f43d901251),
Tree `bd0cb575eb3e10f4f4c53e3514e7abf281c0b940`. Der normale Zwei-Eltern-Merge
in den bestehenden #278-Branch erhält daher sowohl `b1a3deb4…` als auch diesen
neuen Main. Die feste EUR-Berichtswährung, ihre beiden bestehenden nativen
Ownerfälle, PB-019 und der bereits in Main enthaltene Versionsstand **1.5.17**
werden unverändert übernommen. Der einzige inhaltliche Mergekonflikt betrifft
zwei angehängte Traceability-Abschnitte; beide Nachträge bleiben vollständig
erhalten. PB-013/PB-020 und PB-019 werden nicht gegeneinander überschrieben.

Dies reserviert keine FT-006-Softwareversion, verändert keinen Dependency-Pin,
keinen Runner, Checker oder Workflow und führt keinen Main-Merge, Tag oder
PC-Schritt für #278 aus. Die gesonderte #279-Freigabe ist keine #278-Freigabe.
Der aktuelle [PR #278](https://github.com/burckhju/trading-workspace/pull/278)
bindet den neuen gemeinsamen Mergehead, seinen vollständigen Tree, tatsächlichen
CI-Checkout, sämtliche regulären Gates und eigene neue native Artefakte.
Die oben vollständig bestandene CI bleibt genau dem vorherigen Head und seiner
damaligen Main-Basis `7b70f0df…` zugeordnet.

## Fortsetzung 25.10.2026: vollständige Ownerstrecke und ausgeführter GOOD-B07

Aktualisierte Ausgangsbasis: Main und Tag `v1.5.16` zeigen unverändert auf
`7b70f0dfd5cbb81518c73d68d09bbad0c6a9ac2b`, Tree
`53ef549f7710508cbb14365b36a03a26d2843562`. Der gelesene offene Draft #278
stand bereits auf `cd395c9b8a1a864a2c91fd352343eaf3c4e94f7e`, Tree
`97d6fb647494ce3c1ffb8ff73c5d665ff609e667`. Sein Integrationscommit
`1e73a170f993138b0555b8d87f934aca66cd57ed` erhält den ursprünglichen Kernhead
`122224e3…` und den aktuellen Main als Eltern. Diese Fortsetzung erhält alle
Vorleistungen, #204/#274/#276 und die unveränderten fünf nativen Ownerfälle.
Kein neuer konkurrierender PR, Rebase, Main-Schreiben oder Release.

Der vollständige Clone gelang über den genehmigten Netzwerkzugang. Der eigene
Aufgabenbranch war sauber; der Vorhead ist zusätzlich in einem getrennten
detached Worktree als Rotreferenz vorhanden. Im Repository wurde kein
`AGENTS.md` gefunden. Entwicklungsleitfaden, Roadmap, PB-013/PB-020, FT-006,
ADR-S4-005, FT-019/020 und die bestehenden Qualifikationsverträge wurden gelesen.
Aktuelle PR-Kommentare enthalten keine zusätzliche Merge-/Releasefreigabe.

### Explizite Modellwahl und tatsächliche Integrationslücken

Der Entwicklungsauftrag legt für künftig bewusst gestartete neue Analysen den
festen Vertrag `EOD_TREND_MOMENTUM/1.0.1` fest. Maßgeblich sind
`NEW_RUN_MODEL_ID` und `NEW_RUN_MODEL_VERSION` im vorhandenen Dispatcher;
API und beide Services verwenden diese Auswahl auch ohne Requestoverride.
Die bestehende UI sendet die Version ausdrücklich und zeigt das gespeicherte
Analysemodell getrennt von der Runnummer. Explizites `1.0.0` bleibt verfügbar.
Diese Codeentscheidung ist keine produktive Modellaktivierung oder Fachabnahme.

Der Vorhead hatte bereits den Executor angebunden, aber vier Restlücken:

1. Normale neue Runs blieben beim alten Importdefault; die Referenz-HTTP-Route
   verwarf sogar das ausdrücklich übermittelte `model_version`.
2. Generische Detailantworten verlangten Listing-/Basiswert-UUIDs und konnten
   echte Referenzanalysen mit NULL-Ownerfeldern nicht ausgeben.
3. Warnungseinträge wurden beim Referenzreader gefiltert, beim Listingreader
   zusätzlich im TC-001-Domainobjekt getrimmt. Der neue Vertrag bewahrt den
   tatsächlichen nichtleeren Persistenztext einschließlich leerer Einträge.
4. Der bestehende Candidate-Resolver und dessen Readiness fanden Referenzquellen
   nur über die ältere Listing-Bridge. Sie lesen nun zuerst ein vorhandenes
   exaktes MARKET_REFERENCE-Instrument und dessen vollständigen abgeschlossenen
   Snapshot bis zum Cutoff. Fehlt eine native Identität, bleibt die historische
   Bridge erhalten; ein vorhandener unvollständiger nativer Owner fällt nicht
   still darauf zurück. Kein Read legt Identitäten oder Runs an.

Die [Consumer-/Vertragsmatrix](../features/FT-006_MARKET_ANALYSIS.md) benennt
Listing-Run, Referenz-Run, Retry, Verify, Snapshot/Hash, Provenienz und Handoff
mit ihren tatsächlichen Einstiegen. Alle Runs verwenden denselben
`_execute_snapshot`; Modell-ID und -Version sind dort zwingende Argumente.
Referenz-Retry und Verify bleiben die geerbten Methoden. Keine Verdopplung der
Ausführung, keine neue Candidate-Policy oder Aktivierungsengine.

### Originalquelle, Historie und Provenienz

`calculator.py`, seine Kennzahlen/Kriterien und der vorhandene 1.0.1-Kern bleiben
bytegleich. `VALID` wird nie in `GOOD` umgeschrieben. Neue 1.0.1-Reader verwenden
den gespeicherten Preistext: `""` ist die regulär serialisierte leere Sammlung;
jeder nichtleere Text wird nur an Newlines getrennt, ohne Filter oder Trimming.
Bereits vor der Persistenz verlorene Einträge sind nicht rekonstruierbar; eine
pauschal verlustfreie Ingestbehauptung wird nicht erhoben. Explizite neue Legacy-
Runs behalten ihre bisherigen Reader. Historische Retry-/Verify-Aufrufe lesen
in beiden Versionen ausschließlich den gespeicherten JSON-Snapshot.

Verify vergleicht Hash, numerische Ergebnisse, Kriterien einschließlich ihrer
Multiplizität, Qualität und Notes separat und mit ursprünglicher `analysis_time`.
Retry von FAILED/NOT_EVALUABLE ist kein Upgrade und lädt keine Preise nach.
Neue versionierte Hashes unterscheiden sich bei denselben Originalinputs;
historische Fakten und Hashes werden nicht geändert.

Die vorhandene exakte Provenienzauflösung wird erhalten und mit beiden Versionen
für 0/1/mehrere Treffer, DRAFT, fremden Workspace, falschen Modellschlüssel und
abweichenden Implementierungsbezug qualifiziert. Registrierungen/Genehmigungen
im isolierten Test verwenden bestehende Ownerbefehle. Neue 1.0.1-Provenienz
verweist auf den vorhandenen Commit `541fcad…`; beide Rechenartefakte sind dort
mit den aktuellen Blobs identisch. Der alte festgeschriebene Legacyref
`8dcead…` war beim exakten erneuten Abruf nicht auflösbar (GitHub 404); er wird
nicht erfunden oder nachträglich ersetzt. Details und Blobs stehen im
[Provenienzvertrag](../features/FT-006_GOVERNED_MODEL_PROVENANCE.md).

### Lokale Ausführung dieser Fortsetzung

Projektpins: Python 3.12.14, Node 22.16.0, npm 10.9.2; unveränderte Requirements
und npm-Lockdatei. Kein neuer Schema-/Dependency-/Versions-/Workflowstand.

- Gegen vollständigen Vorhead `cd395c9b…`: die neun neuen HTTP-Vertragsfälle
  ergeben **5 failed / 4 passed**. Es fehlen neue Defaultwahl, durchgereichte
  Referenzversionen und nullable Referenzreadback. Gegen die Integration:
  **15 passed**, einschließlich sechs bestehender Lifecycle-/Referenzfälle.
- Derselbe neue UI-Testinhalt gegen Vorhead: **2 failed / 6 passed**;
  mit Integration und Clientfällen **10 passed**.
- Erweiterte Service-/Versionsfälle: **52 passed**. Candidate-Resolverfälle:
  **22 passed**, darunter 13 neue. Bestehende native Runner-/Manifestguards:
  **62 passed**, Node-Requestguards **21 passed**.
- Repositoryweite Ruff-/Black-/mypy-Prüfung bestanden (995 formatierte
  Pythondateien geprüft, 558 mypy-Quellen). Der anfängliche Importformatfehler
  ist behoben; keine fachlichen Assertions wurden dafür geändert.
- Das unveränderte vollständige Frontendgate (`bash scripts/check-frontend.sh`)
  ist bestanden: **806 Tests / 124 Dateien**, TypeScript, ESLint, Prettier,
  Coverage und Produktionsbuild. Coverage Statements/Lines 93,87 %, Branches
  86,29 %, Functions 86,53 %. Bestehende React-act-/Chunkhinweise bleiben sichtbar.
- Strikte B07-TypeScript-Prüfung, Seederformat/-syntax, Bashsyntax, exakt eine
  unveränderte Playwright-Testidentität und strikter Discoveryprüfer bestanden.
  Collection ist kein nativer Testpass.
- Anschließend die vollständigen Analyse-/Candidate-Units samt bestehenden
  Referenz-HTTP-Fällen: **271 passed / 1 bestehende Warnung**. Diese überlappenden
  Prüfungen werden nicht zu einer künstlichen Gesamtzahl addiert.

Vier erste lokale HTTP-/Vitest-Ausführungen hingen in der eingeschränkten
Prozesssandbox und wurden abgebrochen. Ihre unvollständigen Logs bleiben
erhalten. Die danach genehmigt ausgeführten identischen Prüfungen liefern die
oben genannten vollständigen Ergebnisse; keine längeren Testtimeouts oder
Erfolgs-Retries wurden eingeführt.

### Tatsächlich ausgeführter nativer GOOD-B07 vom 25.10.2026

Der vorhandene geschützte Browserfall ist erweitert: zwei echte Referenzowner
und ein Listingowner, jeweils zunächst ein echter 1.0.0-LIMITED-Run, dann
1.0.1-GOOD mit gleichen Originalinputs, Zahlen und Kriterien. Alle vier
Candidatephasen verwenden dieselben drei neuen Quellen und Parameter.
Zusätzlich prüft der Fall getrennte 19-Zeilen-INSUFFICIENT-Snapshots samt
versionsgenauem Retry trotz 200 vorhandener aktueller Preise und eine eigene
Warnungsquelle mit LIMITED. Jeder Verify-POST ist mit vollständigen
DB-Fingerprints eingerahmt. Herkunftsmarker stehen außerhalb der positiven
Warnungsfelder; Kalenderabdeckung wird nicht aus 200 Werktagen abgeleitet.

Der erste vollständige Lauf des erweiterten Falls ist **bestanden**. B07 ist für
den technischen GOOD-Referenzumfang mit folgendem neuen Nachweis geschlossen:

| Identität | Geprüfter Wert |
| --- | --- |
| Entwicklungshead | [`18e3e1411b98d54812850ce006ce24c5ceab874d`](https://github.com/burckhju/trading-workspace/commit/18e3e1411b98d54812850ce006ce24c5ceab874d) |
| Vollständiger Tree | `4c0abfea18cc6fbe48dd647f25ceeb3f37d4a2f6` |
| Tatsächlicher PR-Testmerge | `71f167371e35e6ba5c5dc6432270c1fa3d259245`; Eltern `7b70f0df…` und `18e3e141…`, gleicher Tree |
| Event / Lauf / Job / Versuch | `pull_request` / [`40182968277`](https://github.com/burckhju/trading-workspace/actions/runs/40182968277) / [`121137734172`](https://github.com/burckhju/trading-workspace/actions/runs/40182968277/job/121137734172) / `1` |
| Native Toolchain | Python `3.12.15`, Node `22.16.0`, npm `10.9.2` gemäß unveränderten Projektpins |
| Ergebnis | Genau der erwartete Governancefall: **1 passed**, Retry `0`, Skip `0`, Flaky `0` |
| Rohartefakt | [`12594962453`](https://github.com/burckhju/trading-workspace/actions/runs/40182968277/artifacts/12594962453), ZIP SHA-256 `de432118369859eaf47807e033811f56522ed7e702ae46ac5d6d34d025aaac02` |
| Manifest | Alle 26 Inhaltsdateien mit Prüfsummen geprüft, einschließlich Rohantworten, Report, Trace, sechs Screenshots und Cleanup |

Die drei getrennten Analysen sind `acd0570a-9038-4158-850c-307e8a729d20` v2
(MARKET), `4eae4ad6-22fb-4d59-a895-4e9be0506f16` v2 (SECTOR) und
`b5343556-7513-4c27-acad-dcd37e0f1bcb` v6 (UNDERLYING). Alle verwenden tatsächlich
`EOD_TREND_MOMENTUM/1.0.1`, Status COMPLETED, Qualität GOOD und je 200 VALID-
Snapshotzeilen ohne Warnung. Markt und Sektor besitzen verschiedene eigene
MARKET_REFERENCE-Instrumente; `listing_id` und `underlying_id` sind jeweils NULL.
Nur die Basiswertquelle besitzt ein Listing. Letzter Preistag ist `2026-10-23`,
Analysezeit `2026-10-25`: zwei Tage bei unverändert maximal sieben Tagen.
Die tatsächlichen aufgelösten Parameter, Owner-UUIDs und versionsgetrennten
Hashes sind im [datierten B07-Nachtrag](CANDIDATE_GOVERNANCE_JOURNEY_QUALIFICATION.md)
und in `S0-analysis-owner-source-chain`/`B-CG-001-complete-source-version-chain`
des Originalreports vollständig gebunden. 200 abgeschlossene Werktage sind
ausdrücklich kein zertifizierter Börsenkalender- oder Providerqualitätsnachweis.

Vier Evaluationen auf denselben konkreten drei Quellen ergeben unter CAUTIOUS
**A/A/B/A → QUALIFIED / QUALIFIED / NOT_QUALIFIED / QUALIFIED**, jeweils GOOD.
Nur `TD-MARKET-001` wechselt entsprechend der bereits vorhandenen Policy;
die fünf anderen Required-Kriterien bleiben exakt gleich und erfüllt. Approval
von B lässt A zunächst aktiv; B und die Rückkehr zu A sind eigene ausdrückliche
Aktivierungen. Historische Evaluationen und die drei alten 1.0.0-LIMITED-Runs
bleiben unverändert; Snapshot, Parameter, Kennzahlen und Kriterien sind zwischen
den Runtimeversionen identisch, die Hashes absichtlich versionsgetrennt.

Alle **14 Verify-Fenster** haben sieben erfolgreiche Prüffelder und identische
DB-Fingerprints davor/danach; auch die vier reinen GET-Fenster sind unverändert.
Die separaten 19-Zeilen-Runs und Retries beider Versionen bleiben INSUFFICIENT,
die eigene Quelle mit echter Warnung bleibt LIMITED. 168 Requests, darunter
11 Browsercommands, sind protokolliert; keine Requestfailures. Der verifizierte
synthetische Stack wurde vollständig entfernt: **0 Container / 0 Netze / 0 Volumes**.
Alle sechs relevanten Desktop-/Mobilbilder wurden tatsächlich angesehen: exakte
L1-Basis, APPROVED-B bei aktivem A, aktives B, historisches B bei erneut aktivem A
und explizite A-Rückkehr. Sichtbare Modelle, Quellen, Qualität und Historie stimmen
mit den Rohantworten überein.

### Erster kombinierter CI-Stand und eng belegte Frontend-Testkorrektur

Der GOOD-B07-Pass ist kein pauschaler grüner Gesamthead: Im ersten Frontendlauf
[`40182968177` / Job `121137733384`](https://github.com/burckhju/trading-workspace/actions/runs/40182968177/job/121137733384)
auf `18e3e141…` bestanden 805 Tests; ein bisher unveränderter Test in
`WarrantSelectionRepair.test.tsx` scheiterte. Handelswährungsformular und
Handelsplatzoptionen laden unabhängig. Der Test wählte vor Eintreffen der Option
einen erforderlichen Selectwert; die native Formularvalidierung verhinderte den
Submit, daher fehlte der erwartete API-Fehleralert. Dies ist ein tatsächlicher
Fehlversuch und bleibt als solcher erhalten.

Eine kontrolliert zurückgehaltene Venue-Antwort reproduziert auf unverändertem
Produktcode exakt diese Reihenfolge und den ursprünglichen fehlgeschlagenen
Alert-Assert (**1 failed**, 11 nicht ausgewählte Fälle). Der enge Testfix wartet
auf dieselbe konkrete Antwort/Option und prüft den gewählten Wert sowie zusätzlich
den genauen POST-Payload. Auch der benachbarte Refreshfehlerfall erhält die
Optionsbarriere. Fehler-, Eingabeerhalt- und Keine-Autobewertung-Assertions bleiben
erhalten. Keine Sleeps, Erfolgs-Retries, Timeoutverlängerungen, Produktivänderungen
oder Gateabsenkungen. Mit dem Fix: **12/12 passed**, TypeScript, ESLint, Prettier
und `git diff --check` bestanden. Anschließend besteht auch das unveränderte
vollständige Frontendgate erneut mit **806/806 Tests in 124 Dateien**,
TypeScript, ESLint, Prettier und Produktionsbuild; Coverage Statements/Lines
93,87 %, Branches 86,34 %, Functions 86,53 %.

Während dieser Qualifikation ging parallel der normale Folgecommit
[`3efe5a94d68820f052db4408886d84cb2d46ad02`](https://github.com/burckhju/trading-workspace/commit/3efe5a94d68820f052db4408886d84cb2d46ad02)
mit der Optionsbarriere, den beiden Eingabewertprüfungen und dem genauen
POST-Payload ein. Er wird vollständig als Vorgänger erhalten; die kontrolliert
verspätete Antwort und die Barriere im benachbarten Refreshfall ergänzen ihn.
Sein Frontend-[Lauf `40183630489` / Job `121139703505`](https://github.com/burckhju/trading-workspace/actions/runs/40183630489/job/121139703505)
bestand ebenfalls mit 806 Tests / 124 Dateien und Build. Der erste Backendlauf
[`40182968208` / Job `121137733478`](https://github.com/burckhju/trading-workspace/actions/runs/40182968208/job/121137733478)
wurde durch den neuen Branchhead entsprechend der unveränderten
`cancel-in-progress`-Regel abgebrochen. Er ist **kein Backendpass**. Sein
Teilprotokoll zeigt für die 38 FT-006-PostgreSQL-Fälle 37 Erfolgsmeldungen und
einen Fehler beim ersten Listingfall; die beiden neuen nativen Candidatefälle
sind erfolgreich gemeldet. Wegen des Abbruchs fehlt der pytest-Abschluss mit
vollständigem Fehlertrace.

Der Snapshotvergleich des Listingfalls ließ sich anschließend mit den echten
Projektmappern kontrolliert reproduzieren: Die neue Testfixture verwendete
`SYNTHETIC-FT006-` mit kleingeschriebenen UUID-Buchstaben als Providersymbol.
Der unveränderte Legacy-Listingreader normalisiert diesen Code groß; der neue
Reader bewahrt den gespeicherten Originaltext. Der einzige Unterschied zwischen
beiden so erzeugten Snapshots ist daher `provider_symbol`. Mit einem von Anfang
an kanonischen synthetischen Providerschlüssel, wie ihn der reguläre TC-001-
Owner erzeugt, besteht dieselbe vollständige Gleichheitsassertion. Die Fixture
erhält ausschließlich `.upper()` für den UUID-Symbolteil; Originalflags,
Warnungen, numerische Inputs, sämtliche Assertions und Produktcode bleiben
erhalten. Ruff und Black bestehen. Dieser lokale Mappernachweis ist ausdrücklich
kein PostgreSQL-Testlauf; der native Abschluss gehört zum folgenden regulären
CI-Head mit diesem eng begründeten Fixturefix.

Die vier bisherigen Finanz-/Lernownerfälle sind auf `18e3e141…` ebenfalls nativ
bestanden, jeweils einmal ohne Retry/Skip/Flaky. Ihre drei vollständigen Manifeste
(16/20/25 Inhaltsdateien), neun weiteren Lesefenster und vollständigen Cleanups
sind geprüft. Finance-Artefakt `12595172144`, ZIP SHA-256
`487470ca3870356ffc29dd6ab3afe4df3d7ae2c01fe3d9cfdc8e14718e934266`;
Learning-Artefakt `12594593087`, ZIP SHA-256
`b79fae5a2ca5223d2a0282bbe80ad073eba534e5457aaee92b52ebad1226f798`.
Der abschließende reguläre CI-Lauf des Folgecommits wird mit seinem eigenen
Head/Tree/Checkout und seinen eigenen Rohartefakten im bestehenden
[PR #278](https://github.com/burckhju/trading-workspace/pull/278) gebunden;
das hier bezeichnete erste Artefakt wird keinem späteren Head zugeschrieben.
Lokal fehlen Docker/PostgreSQL; dafür werden echte reguläre Actions verwendet,
keine fingierten lokalen CI-Flags. B07-Abschluss, Fachabnahme, Merge, Release,
PC-Installation und produktive Modellaktivierung bleiben getrennte Aussagen.

## Historischer Zwischenstand: explizite Runtime-Anbindung am Vorhead


Der folgende Kernbericht bleibt als historischer Nachweis erhalten. Die aktuelle
Fortsetzung nimmt Main `7b70f0dfd5cbb81518c73d68d09bbad0c6a9ac2b` / 1.5.16
mit einem normalen Zwei-Eltern-Integrationscommit in #278 auf. #276 und die
Navigation aus #204 bleiben erhalten; kein Main-Schreiben oder Force-Push.

Erstellung, Retry und Verify verwenden nun denselben exakten Modellvertrag.
Der bestehende Run-Request erhaelt die optionale ausdrueckliche Auswahl
`model_version: "1.0.1"`; weggelassen bleibt sie kompatibel auf **1.0.0**.
Unbekannte Versionen werden vor Run-/Snapshot-Schreiben abgewiesen. Listing-
und Marktreferenzowner delegieren an denselben Executor. Retry liest weiterhin
nur den gespeicherten Snapshot und nimmt dessen gespeicherte Modell-ID/-Version;
Verify berechnet mit derselben Version und dem urspruenglichen Analysezeitpunkt.
Keine bestehende Auswahl wird automatisch auf 1.0.1 umgestellt.

Die Provenienzaufloesung verlangt fuer 1.0.1 genau deren eigenen unveraenderlichen
Vertrag und Implementation-Ref. Nur genau eine passende APPROVED-Definition im
Workspace wird verknuepft. Fehlend, DRAFT oder mehrdeutig bleibt NULL; eine alte
1.0.0-Genehmigung ist kein Ersatz. Es entsteht keine Genehmigung oder Aktivierung.

Zusaetzlicher reproduzierter Verify-Befund: Der Repositoryreader sortiert
Kriterien nach Code, der Rechner liefert Modellreihenfolge. Verify vergleicht nun
kanonisch nach Code, weiterhin alle vier Felder und die volle Multiplizitaet.
Fehlende, doppelte oder veraenderte Kriterien bleiben Fehler. Weder gespeicherte
Kriterien noch Hashes werden umgeschrieben.

### Lokaler Nachweis dieser Fortsetzung

Der lokale Quellbestand ist weiterhin eine anhand von Git-Blob-SHAs gepruefte
Teilmenge, kein vollstaendiger Checkout. Python 3.13.5 / pytest 9.0.2:

- 31 vorhandene Kernfaelle plus 12 neue Transport-/Vertragsfaelle: **43 passed**.
- 24 neue Servicefaelle im isolierten Import-Port-Harness: gegen unveraenderte
  Application-/Reference-Dateien **14 failed / 10 passed**, mit Fix **24 passed**.
  Derselbe Testinhalt und dieselben Assertions, keine Sleeps oder Retries.
- Der Harness fuehrt die tatsaechlichen Service-/Domainquellen aus, ersetzt aber
  nicht lokal verfuegbare Repository-/ORM-Importports. Er ist daher ausdruecklich
  **kein vollstaendiger Paketimport, SQLAlchemy- oder PostgreSQL-Nachweis**.
- AST- und Whitespacepruefung bestanden. Ruff/Black/mypy sowie Docker/PostgreSQL
  stehen lokal nicht zur Verfuegung; die unveraenderten Projektgates laufen in CI.

13 neue PostgreSQL-Faelle fuer beide Owner, exakte Provenienz, historische
Verifikation, Retry, negative Qualitaet und den echten HTTP-Runweg sind ergaenzt.
Sie verwenden nur die streng gepruefte `trading_workspace_test`, eigene UUIDs und
eine rueckgerollte aeussere Transaktion mit Savepoints. Kein externer Provider.
Ihr tatsaechliches Ergebnis wird erst nach dem aktuellen CI-Abruf berichtet.

**B07 ist in diesem Zwischenstand noch offen:** Der bestehende Governance-
Browserfall verwendet weiterhin 1.0.0 und markierte Warnungen. Die neue
GOOD-Referenz muss auf dem kombinierten Stand nativ nachgewiesen werden.
Keine Merge-, Release-, PC-, Fach- oder wirtschaftliche Freigabe aus diesem
Zwischenstand ableiten. Aktuelle Head-/Tree-/Checkout-/Runbelege stehen in #278.

---


25.10.2026. Dieser Bericht ist ein technischer Nachweis, kein zweites Backlog.
Aufgabenstatus bleiben im [Product Backlog](../planning/PRODUCT_BACKLOG.md).
Der abhaengige Gesamtweg ist [PR #276](https://github.com/burckhju/trading-workspace/pull/276).

## Ausgangspunkt und Parallelgrenze

Basis ist Main `27098f173caf56bd0fd11f2ff6bc600a7e8e633a`, Tree
`68065a3f8944e8ea9526d3b154f46c961662d1ef`, Softwareversion 1.5.15.
#276 wurde waehrend der Untersuchung unabhaengig mit Main integriert und fuer
v1.5.16 vorbereitet. Seine laufenden Commits werden hier nicht ueberschrieben.
Dieser getrennte Folgeschnitt aendert weder #276 noch Navigation, Runtime-Defaults,
API, Persistenz, Governancefreigaben, Migrationen, Dependencies oder Workflows.

## Reproduzierter Befund

Die bestehenden Owneradapter uebernehmen die Preisqualitaet unveraendert in den
Snapshot. Persistierte Preise verwenden VALID; der Rechner 1.0.0 vergleicht dort
jedoch mit GOOD, dem Wortschatz seiner Analyseausgabe. Vollstaendige synthetische
VALID-Reihen liefern deshalb LIMITED. Ein kuenstlicher GOOD-Quellwert liefert
hingegen GOOD. Quellenwarnungen sind im alten Rechner nicht in den Ergebnisnotes
sichtbar. Dies ist ein reproduzierter Rechenvertrag, kein Schadensnachweis am Depot.

Das historische Modell wird nicht repariert, indem gehashte Quellwerte in GOOD
umgeschrieben oder alte Ausgaben nachtraeglich aufgewertet werden.

## Implementierter, ausdruecklich begrenzter Zusatz

`calculator_v1_0_1.py` verwendet die unveraenderte 1.0.0-Arithmetik und berechnet
in der eigenstaendigen Modellversion 1.0.1 die Quellenqualitaet aus Originalfakten:
Nur ausreichend viele ausgewaehlte Preise, durchgehend VALID und ohne Warnungen
oder fehlende ausgewaehlte Preiswerte ergeben im Rechenkern GOOD. INSUFFICIENT hat
Vorrang; andere oder unbekannte Quellflags bleiben LIMITED. Quellenwarnungen und
abweichende Flags werden mit Datum in Notes erhalten. Auch fehlerhafte leere
Warnungseintraege werden nicht als sauberer Input ausgegeben.

Kennzahlen, Rundung, Kriterien, Schwellen und die Rohsnapshotzeilen bleiben gleich.
Zeitabhaengige Aktualitaet bleibt Aufgabe des vorhandenen Application Service;
dieser reine Rechenkern behauptet keine Kalenderabdeckung oder aktuelle Kurse.

`model_versions.py` dispatcht nur nach ausdruecklich uebergebener Modell-ID und
exakter Version. Es gibt keinen latest-Default und keinen Fallback unbekannter
Identitaeten. 1.0.0 ruft weiterhin unveraendert den alten Rechner auf. Der bisherige
produktiv verwendete Import, seine Versionskonstante und Governanceprovenienz
bleiben unberuehrt. Die Softwareversion wird nicht erhoeht.

## Tatsaechlich ausgefuehrte lokale Tests

Kein vollstaendiger Repositorycheckout: Git-Clone scheiterte an DNS-Aufloesung.
Die benoetigten fuenf Domainquelldateien wurden einzeln gelesen und ihre vollstaendigen
Bytes gegen die von GitHub gelieferten Git-Blob-Identitaeten abgeglichen:

| Datei unter `backend/app/features/analysis/domain/` | Git-Blob |
|---|---|
| calculator.py | `7ece74da68639cd26c5bbc73fcdf8b65dac426b8` |
| indicators.py | `4977db3f88aa666734bab16dc768c3315b16fa92` |
| models.py | `da35d64b8cf12000e63a7b251808a755fe4427ab` |
| enums.py | `8c6a105177466beb3941c28c8f6d1c5dad2ef170` |
| errors.py | `a37be4c3182010fabcca10ca04617fe940893933` |

Laufzeit: Python 3.13.5, pytest 9.0.2. Das ist kein Python-3.12-CI-Nachweis.
13 Quellenvertragsfaelle wurden zuerst mit unveraendertem 1.0.0-Rechner geprueft:
**6 fehlgeschlagen, 7 bestanden**. Gegenueber der finalen Testdatei wurde in der
isolierten Rotkopie ausschliesslich der Import des zu pruefenden Rechners auf den
alten Rechner umgebunden; die ausgefuehrten Assertions sind gleich.
Die sechs Fehler sind zwei VALID-Positivfaelle (CLOSE/ADJUSTED_CLOSE), der falsche
GOOD-Quellflag und drei fehlende Warnungsdiagnosen. Bei den Warnungsfaellen war
LIMITED bereits vorhanden; nur dessen Warnungsnachweis fehlte.

Mit dem Zusatz bestehen **31/31 Domainfaelle**, ohne Skip oder Retry. Darin sind die
13 obigen Faelle enthalten, nicht zusaetzlich zu zaehlen. Weitere Faelle sichern
Einzelfehler, fehlende Adjusted-Closes, INSUFFICIENT samt Warnung, unveraenderte
Kennzahlen/Kriterien/Inputs, historischen 1.0.0-Hash und getrennten 1.0.1-Hash sowie
den exakten Versionsdispatch und Ablehnung unbekannter Modelle/Versionen.
Python-AST-Pruefung und Whitespacepruefung bestanden. Ruff, Black und mypy sowie
die vollstaendigen Backend-/Frontend-/E2E-Gates wurden lokal nicht ausgefuehrt.
Aktuelle PR-CI muss separat an ihren tatsaechlichen Head/Checkout/Tree gebunden werden.

## Noch nicht geliefert — B07 bleibt offen

Dies ist nur der implementierte und lokal getestete versionierte Rechenkern,
**keine vollstaendige produktive FT-006-Korrektur**. Die bisherigen Owner verwenden
weiter 1.0.0. Es gab weder PostgreSQL- noch Browserausfuehrung dieses Zusatzes.

Vor Integration sind Run, Retry und Verify auf den gespeicherten exakten
Modellvertrag zu binden, fuer Listing- und Referenzowner gemeinsam. Der vorhandene
Provenienzlistener ist auf den alten Runtimevertrag zugeschnitten; 1.0.1 darf keine
falsche genehmigte 1.0.0-Referenz erhalten. Neue Snapshots muessen ihre wirkliche
Version hashen; historische Versionen, Hashes, Ergebnisse und Quellen bleiben
unveraendert. Kein impliziter Wechsel einer aktiven Governanceversion.

Erst der danach erneut ausgefuehrte reale Browser/API/PostgreSQL-Gesamtweg mit
GOOD-Referenz, Negativfaellen und allen unveraenderten Ownergates kann die offene
B07-Grenze aus #276 schliessen. Keine technische Gesamtuebergabereife, Fachabnahme,
wirtschaftliche Ueberlegenheit, Veroeffentlichung, Installation oder Aktivierung
wird aus diesen Domaintests abgeleitet.
