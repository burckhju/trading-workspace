# UX4-B — Quellenwahl und eindeutige Originalbelege

## Aktueller Integrationsauftrag

Am 01.11.2026 wurde anschließend ausdrücklich beauftragt: „Falls vorhanden
Widersprüche aufzeigen, ansonsten wenn grün mergen“. Diese bedingte Freigabe
ersetzt für PR #322 die ursprüngliche Beschränkung auf einen Draft. Release,
Deployment, PC-Installation und menschliche Fach-/Screenreaderabnahme bleiben
getrennte, hier nicht behauptete Nachweise.

Der zur Mergeprüfung erneut aufgelöste Main ist
`e681c79e0c46a6efb9e4eeb7cd18d959ad99ea97`, Tree
`cbae4ba7e9c030e0c7e2db3a5374e88fc8d3ac8f`. Er integriert #321 am bereits
gelesenen Head `f90ba2c1baebbe530af536348bc71d73ca0e0108` und ergänzt gegenüber
dem ursprünglichen Ausgangs-Main ausschließlich die fünf Koordinationsdokumente.
Der Abgleich bestätigt weiterhin den lokalen UX4-B-Korridor, den vorhandenen
UX2-Hostvertrag und die kanonische UX3-Sprache. Es entsteht keine neue Abhängigkeit
vom offenen UX3-Piloten und keine Überschneidung seiner Produktdateien mit #322.

Zusätzlich gelesen wurde der aktuelle #320-Head
`9e725563a5f09a6601bbe1aceee85ef32f7b7d18`: dessen Produkt-/Testumfang bleibt
gegenüber dem zuvor geprüften Piloten unverändert; Version 1.5.37 wurde erhalten,
die Releasevorbereitung entfernt und B2 lediglich als getrennter Folgeauftrag
dokumentiert. Dieser fremde Featurebranch wird nicht übernommen.

Die Main-Aktualisierung ist konfliktfrei und verändert gegenüber dem bereits
qualifizierten UX4-B-Head `9e4f8460e3d3d69262e907eed21fbae536ebe9b8` keinen
Produktcode, Test, Workflow, Reader oder Versionswert. Die beiden eigenen
Dokumente kennzeichnen lediglich den neuen Auftrag und die aktualisierte Basis.
Die bisherigen grünen Runs bleiben Nachweise ihres exakten früheren Stands;
der neue kombinierte Head benötigt gemäß aktivem Main-Ruleset aktuelle normale
CI. Finaler Head, Tree, tatsächlicher Testmerge, Runs und gegebenenfalls der
ausgeführte Merge werden im PR dokumentiert. Schutzregeln werden nicht umgangen.

## Ursprünglicher Auftrag und Ausgangsstand

Datum: 01.11.2026. Ursprünglicher Implementierungsauftrag für den vorhandenen
Positionskursverlauf: Draft-PR, kein Merge, Release, Deployment oder PC-Update.
Die anschließende bedingte Mergefreigabe steht oben. Repository- und Testdaten
sind kein Nachweis tatsächlich gespeicherter Kurshistorie auf dem Nutzer-PC.

Der tatsächliche Main zu Beginn ist
`484143d33aa5f2d443da6b2edf097ae1cb5aee3a`, Tree
`08aaa9d41e64abd5021a391a9e6a1ebb6fbc8778`. `VERSION`,
`frontend/package.json`, Frontendlockdatei und `backend/pyproject.toml` enthalten
`1.5.37` und bleiben unverändert. Der historische Promptstand
`1883f7f330719453958f8be1dd51d48db816662e` wurde nicht wiederhergestellt.

Zu Beginn existiert bereits [Draft #322](https://github.com/burckhju/trading-workspace/pull/322),
Branch `feat/ux4-b-position-price-visibility-20261101`, Head
`e3365df7afc70ec52fe6fb19aabc4050250091e3`, mit einem ersten Quellenfilter und
zwei Tests. Dieser eigene Arbeitsstrang wird vervollständigt. Seine drei
veröffentlichten Commits bleiben erhalten; ausschließlich der aktuelle Main
wird in einem eigenen lokalen Checkout einbezogen. Kein fremder Featurebranch
wird zur Vorbereitung gemergt und keine fremde lokale Änderung überschrieben.
Der finale Head, Tree, tatsächliche CI-Testmerge und Run-Links stehen im PR;
ein Dokument kann seine eigene spätere Commit-SHA nicht vorwegnehmen.

Keine `AGENTS.md` im Repository. Gelesen wurden README, Entwicklungsanleitung,
Coding Standards, Product Backlog, Frontendarchitektur, Teststrategie,
Positionshistorienvertrag sowie UX4-Inventur, V01–V07/V12–V14 und Prüfmatrix.
Reader, Composer und lokale Chartbausteine auf Main entsprechen weiterhin dem
historischen UX4-A-Ausgangsstand. Bestehende automatische Reads, geschlossene
Positionen, UTC-Achsen, getrennte Währungen, Markerqualifikation, Retention und
50-zeilige Originaltabelle werden wiederverwendet.

## Koordination und tatsächliche Integration

| Bezug | Exakt geprüfter Head | Integrationsstand auf dem Ausgangs-Main |
| --- | --- | --- |
| Master #313 | `958bf9e9e554953bbb7a465c1dfdc863abd6ebed` | Gemergt als `35f3ab2133fa40beb4ab2e502a08fa3bf5b44e35` |
| UX2-A #311 | `55072f8e90c00d309c3bd6ed6dd17f61ab33bd32` | Über #318 integriert |
| UX1 #312 | `b1df1c1000815786a6623d35bf3f8631661a9543` | Über #318 integriert |
| Kanonischer UX3-Vertrag #314 | `cc547ef662d1bc28315d25df1930c32b94278d6b` | Gemergt als `d80bd45d84d845aa920a7eac5b19a7fe6cd63307` |
| Ergänzungsquelle #315 | `d9d85f1af3159c4356c8773d076decbf1dc604e4` | Offen/Draft; kein zweiter normativer Hinweisvertrag |
| UX4-A #316 | `82b11711a70aacf39fddf59a6545662fb7102b92` | Gemergt als `5f2e12667759bfb54eb14f39c6d8426c9cd8080f` |
| Gemeinsame UX1-/UX2-Integration #318 | `54eaba19fc626194237e8280af2e6cc315b1bac7` | Gemergt als `bb49ffe781933270746b9f86f4aee99b6f8144c2` |
| UX1-Dokumentnachtrag #319 | `5e58fc49781e0b944d94edcf2b298336051955c8` | Gemergt als aktueller Main `484143d33aa5f2d443da6b2edf097ae1cb5aee3a` |
| UX3-B1/F1 #320 | `71e971a67be7f1ca10192e04e3832f843b8099bd` | Offen/Draft; dessen Notice-Presenter ist kein Mainbestand |
| Masterfortschreibung #321 | `f90ba2c1baebbe530af536348bc71d73ca0e0108` | Offen/Draft; nur Koordinationsdokumente |

Die historischen Masterreferenzen `2312abfe…` und UX3-Referenzen `52a24266…`
sind durch integrierte, konkretere Verträge ergänzt. Die Shared-Navigation,
UX2-Chartstelle und UX1-Währungsübergaben sind inzwischen vorhanden. UX3 präzisiert
unter anderem unbekannt/leer/Fehler, Gültigkeit eines Snapshots, beleggebundene
Aktionen und Recovery im genauen Geltungsbereich. Die Dokumentintegration macht
die vorgeschlagenen `Notice*`-Bausteine nicht automatisch zu verfügbaren Imports.
Die spätere Masterfortschreibung bestätigt den bestehenden lokalen Chartkorridor.

Relevante offene Arbeiten wurden erneut geprüft: #320/#321/#315, eigener #322
sowie #205/#220/#197/#187/#207. #205 ist weiterhin ein historischer Vorschlag;
die vorhandene Chartimplementierung stammt aus bereits integrierten Folge-PRs.
Quellenforschung und Monitoringarbeit liefern keine zusätzliche produktive
Historienabdeckung für diese Darstellung.

## Konkreter Nutzerweg und Dateischnitt

1. Eine vorhandene Position oder die bestehende Tradeverwaltung öffnen. Die
   vorhandene Historienantwort liefert alle Marktquellen und effektiven Ereignisse.
2. Provider, Preisarten, Währung, historischen Handelsplatz, Quellenmodus und
   belegte Zeiten lesen. Bei mehr als sechs Quellen die zunächst kompakte Legende
   aufklappen; ausschließlich nach exakter Serien-ID lokal ein-/ausblenden.
3. Einen Punkt anklicken oder **Punkte und Buchungen auswählen** mit der Tastatur
   öffnen. Auch 16 oder mehr überlagerte Originalbelege bleiben einzeln anwählbar.
4. **Originalbeleg anzeigen** öffnet die richtige Evidenzseite und fokussiert die
   kompakte Originalkarte beziehungsweise die konkrete Kauf-/Verkaufsbuchung.

Produktdateien: `PositionPriceHistory`, `PositionPricePlot`,
`PositionPriceHistoryEvidence`, der unmittelbare lokale Präsentationsbaustein
`PositionPricePointAccess` und `priceHistoryPresentation`. Hinzu kommen deren
lokale Tests, zwei vorhandene Browser-Testdateien, der aktualisierte
Positionshistorienvertrag und dieser Nachweis mit synthetischen Screenshots.

Die ursprüngliche Quellenwahl in #322 bleibt erhalten; ergänzt werden stabile
Quellenkennzeichnung, jederzeit erreichbare Wiederherstellung auch bei nur noch
einer ausgeblendeten Serie, unveränderte Marker bei ausgeblendeten Marktquellen,
überlagerte Belege, paginierter Tastaturzugang und kompakte mobile Evidenz.
Bekannte tatsächliche Producer-/Moduscodes erhalten lesbare Labels und behalten
den Rohcode. Unbekannte Codes bleiben unverändert.

Es gibt keine neue Datenpopulation, Kursableitung, FX, lokale finanzielle Rechnung,
Historyrekonstruktion, Interpolation, Deduplizierung oder zusätzliche Stichprobe.
Originalstrings und Zeitzuständigkeiten bleiben erhalten. Die Auswahl zählt
Marktpunkte separat von Stichproben und Ausführungen; `report.events` und die
serverseitige Markerzulässigkeit werden durch Sichtbarkeitswahl nicht verändert.
Die 20-zeilige Belegauswahl paginiert Bedienelemente, die 50-zeilige Tabelle
weiterhin sämtliche Originalwerte. Alle Diagrammpunkte werden unverändert
berücksichtigt, soweit endliche JavaScript-Koordinaten darstellbar sind.

## Bestehende UX2-Einbindung und öffentliche Grenze

| Feld | Bestehender, unveränderter Vertrag |
| --- | --- |
| Hoststelle | `TradeManagementPage`, vorhandener Anker `#position-price-history` innerhalb von „Trade und Position“ |
| Weitere Verwendung | Bestehende `PositionDetails` im Operational Workspace; kein zweiter Positionsbereich |
| Öffentliche Grenze | Bereits vorhandener öffentlicher `PositionPriceHistory`-Export aus `features/operational_workspace`; keine neuen Querimporte oder Barrelumwege |
| Props | `tradeId`, `positionId`, in der Tradeverwaltung `reloadToken={historyReloadToken}` |
| Read-Lebensdauer | Vorhandene lokale Historyinstanz, gebunden an Trade/Position/Reload; `days` und Retry lösen den bestehenden GET aus |
| Readback | UX2-Host erhöht `historyReloadToken` erst nach vollständig qualifiziertem erfolgreichen Refresh; fehlgeschlagener Readback ist kein neuer Historienstand |
| Timeline | `ExecutionDatesPanel` behält seinen eigenen Read und seinen bestehenden `onChanged`-Ablauf |
| Abschnittswechsel | Bestehende Shared-Navigation; gleicher Trade/anderer Hash ändert keinen Historienrequestschlüssel |
| Neue Fokusziele | Rein lokal: Originalkarte beziehungsweise Ereignis-ID in vorhandener Evidenz; kein neuer Hash oder angeblicher Fokus auf eine fremde Buchungsoberfläche |
| Konfliktdateien | `TradeManagementPage`, `PositionDetails`, `OpenPositionsPanel`, Navigation, Routing, Lade-/Invalidierungsowner bleiben unverändert |
| Owner/Integrationsfolge | UX2-A #311 und gemeinsame #318-Integration bereits auf Main; darauf lokaler UX4-B-Draft. UX2 bleibt einziger Hostintegrator. |

Damit ist der konkrete vorhandene Schnitt technisch geprüft. Eine neue
Ownerfreigabe für gemeinsame Dateien ist nicht erforderlich, weil keine solche
Datei geändert wird. Das ist keine behauptete persönliche UX2-Abnahme oder ein
gemeinsamer Laufzeitnachweis mit offenen UX3-/UX4-C-/UX4-D-Arbeiten.

## UX1-/UX3-Abhängigkeiten und Qualitätstexte

UX1 behält Währungs-/Quellenauflösung, Capture, Kostenbasis und Performance.
UX4-B verwendet ausschließlich die gelieferten historischen Belege. UX3 behält
den kanonischen Hinweisvertrag; fachliche Codes und ihre Qualifikation bleiben
beim Domain-Owner. Kein neues Notice-Framework oder globale Qualitätsampel.

| Zustand | Konkrete Darstellung und Vertragsabgleich |
| --- | --- |
| Alle Quellen ausgeblendet | „Das ist Ihre Darstellungswahl“ und lokale Wiederherstellung; keine Datenfehlerbehauptung |
| Bestätigte leere Antwort | Bestehender Text „Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.“ |
| Technischer Readfehler | Bestehendes Alert und „Kursverlauf erneut laden“ beim bisherigen Readowner |
| Gekürzte Samples | Unveränderte Zahlen und Warnung „Begrenzter Ausschnitt … Ältere Belege können fehlen“ nahe der Grafik |
| Unvollständige Zeitabdeckung | „Zwischen den Punkten ist kein Kursverlauf belegt“ und „Eine vollständige Handelszeitabdeckung ist nicht belegt“ |
| Historische Qualität | Bestehende Reasonlabels wie „Bei Erfassung veraltet“; keine heutige Frische-/Recovery-/Handelbarkeitsfreigabe |
| Nicht plottbare Buchung | Unveränderter gelieferter Reason, Date-only-Datum, Zeitzone und Präzision in der Ereignisliste |
| Lazy-Chartfehler | Technischer Chartfehler und weiter nutzbare Kursevidenz/Ereignisliste; kein Ersatz durch leere Daten |

Neue statische Hinweise verwenden keine zusätzliche Live-Ankündigung. Einziger
Auswahlstatus ist der lokale Alle-ausgeblendet-Status; bestehende Lade-/Readfehler
bleiben getrennt. Der technische Wortlautabgleich wurde gegen die gelesenen
UX3-Verträge durchgeführt. Eine neue persönliche Fach-/UX3-Abnahme wurde nicht
erteilt und wird nicht als abgeschlossen ausgewiesen.

## Tatsächlich ausgeführte lokale Prüfung

Node `22.16.0`, npm `10.9.2` gemäß Repository; unveränderte Lockdatei. Python
`3.12.14` in isolierter Virtualenv aus unveränderten Requirements.

| Prüfung | Ergebnis |
| --- | --- |
| `bash scripts/check-frontend.sh` | Bestanden: TypeScript, ESLint ohne Warnungen, Prettier, **1.995 Tests in 165 Dateien**, Coverage und Produktionsbuild |
| Frontend-Coverage | Statements **96,00 %**, Lines **96,00 %**, Branches **90,34 %**, Functions **91,46 %**; bestehende Gates 80/80/70/80 unverändert |
| Fokussierte Backend-Ownerregressionen | **71 bestanden**, eine Starlette/AnyIO-Deprecationwarnung |
| PostgreSQL-Historienintegration lokal | **2 übersprungen**, Grund `Disposable PostgreSQL test URL required`; keine Testdatenbank, PostgreSQL-/Docker-Binaries lokal nicht verfügbar |
| Browser, Produktionsbuild | **33 bestanden** in 45,2 Sekunden: komplette `position-price-history.spec.ts` und `trade-workspace-navigation.spec.ts`, einschließlich sieben neuer UX4-B-Fälle; keine Retries im lokalen Lauf |
| Finanz-/Reader-/Hostgrenze | `git diff origin/main -- backend frontend/src/shared frontend/src/features/trade frontend/src/features/performance VERSION frontend/package.json frontend/package-lock.json .github/workflows` leer |

Backendbefehl (mit deaktivierten externen Provider-/Nachrichtenpfaden):

```bash
PYTHONPATH=backend:. \
TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED=false \
TRADING_WORKSPACE_MARKET_DATA__EODHD__API_KEY= \
TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__ENABLED=false \
TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=false \
backend/.venv/bin/python -m pytest -c backend/pyproject.toml \
  tests/unit/backend/features/market_data/test_warrant_price_history.py \
  tests/unit/backend/features/trade_position/test_position_price_history.py -q
```

Der erste Backendversuch unter eingeschränktem Prozess-/Socketzugriff hing und
wurde beendet; dieselben unveränderten Tests bestanden anschließend mit erlaubtem
lokalem Prozesszugriff. Ein Entwicklungsserverlauf der Browserfälle wurde wegen
der React-StrictMode-Doppelmounts nicht als Produktionsnachweis gewertet. Die
abschließende Browserprüfung läuft gegen `npm run build` / `npm run preview`;
die exakten GET-Zahlassertionen wurden nicht abgeschwächt.

Die Frontendsuite gibt React-`act`-Hinweise aus; der Produktionsbuild meldet
weiterhin große Chunks. Erfolgreicher Exit ist nicht gleich Warnungsfreiheit.
Keine Schwelle, bestehende Assertion, Retrykonfiguration oder Workflow wurde
abgesenkt oder übersprungen, um einen unerwarteten Befund zu verdecken.

## Mobil, Tastatur und Screenshots

Die neuen Fälle prüfen 320, 390 und 1280 CSS-Pixel, mehr als zwölf Marktserien,
verschiedene Preisarten/Modi/MICs, sichtbaren Fokus, native Tab-/Shift-Tab-/Enter-/
Leertastenbedienung, Wiederherstellung, unveränderte Reads/Writes, 16 überlagerte
Originalbelege und den exakten Originalbeleg auf Tabellenseite 2.

Der 200-%-Fall setzt echten Browserzoom über eine ausschließlich für den
Browser-Test erzeugte MV3-Extension und `chrome.tabs.setZoom`. `getZoom() === 2`,
CSS-Breite 1280 → 640 und `devicePixelRatio` 1 → 2 werden gemessen. Das ist keine
CSS-`zoom`-/Viewportsimulation. Die temporäre Extension wird nicht in Produktcode
oder eine Nutzerinstallation übernommen. Der Screenshot wird über die native
CDP-Oberfläche aufgenommen, da elementbezogenes Screenshot-Clipping bei diesem
Zoom einen schwarzen Ausschnitt lieferte; der endgültige Beleg wird visuell geprüft.

Recharts-Pfeiltests verifizieren konkret einen Tooltipwechsel und erhaltenen
Chartfokus, keine vollständige Scatter- oder Screenreader-Navigation. Der native
Belegwähler ist die vollständige Tastaturalternative. Dieselbe-Trade-Hashnavigation
erhält lokale Quellenwahl, Evidenzseite und manuelle Formularentwürfe ohne neue
Historien-, Positions- oder Timeline-Reads. Echte Identitätswechsel, A→B→A sowie
alte Erfolge/Fehler und Korrekturantworten bleiben isoliert.

Screenshots und Zoommessung sind ausdrücklich synthetische Testdaten:

| Nachweis | Datei |
| --- | --- |
| Kompakte Grafik, 320 CSS-Pixel | [320 px](evidence/ux4-b/ux4-b-compact-chart-320-synthetic.png) |
| Kompakte Grafik, 390 CSS-Pixel | [390 px](evidence/ux4-b/ux4-b-compact-chart-390-synthetic.png) |
| Kompakte Grafik, 1280 CSS-Pixel | [1280 px](evidence/ux4-b/ux4-b-compact-chart-1280-synthetic.png) |
| Quellenwahl und Tastaturfokus, 390 CSS-Pixel | [Quellenwahl](evidence/ux4-b/ux4-b-many-sources-390-synthetic.png) |
| Überlagerte Originalbelege (Auswahlliste) | [Originalbelege](evidence/ux4-b/ux4-b-overlap-originals-390-synthetic.png) |
| Nativer Browserzoom 200 % | [Zoom-Screenshot](evidence/ux4-b/ux4-b-native-200-percent-synthetic.png) und [gemessene Werte](evidence/ux4-b/ux4-b-native-zoom-measurements.json) |
| Begrenzte konkrete Kontrastprüfung | [Farben und Kontrastverhältnisse](evidence/ux4-b/contrast-check.json) |

Die Screenshots wurden visuell geprüft. Die Marktsymbolpalette erreicht auf dem
gemessenen Diagrammhintergrund `#070c20` mindestens **7,21:1**, die Achsenfarbe
**13,07:1**. Die separat erfasste Sekundärtextfarbe bleibt ebenfalls über 4,5:1.
Native Fokusumrisse sind im Quellen- und Zoombeleg sichtbar. Formen, Quellnummern,
Preisart-/Währungstext und Kauf-/Verkaufsbezeichnungen ergänzen die Farben.
Diese begrenzte konkrete Prüfung ist keine vollständige WCAG- oder Screenreaderabnahme.

Die separat gehaltene vollständige Tabelle darf in ihrer eigenen beschrifteten
Region horizontal scrollen; horizontale Dokumentrolle ist in den genannten
Breiten ausgeschlossen. Manuelle Screenreader- und menschliche Fachabnahme
bleiben offen.

## Nachweisstufen und genau ein nächster Schritt

| Stufe | Einordnung |
| --- | --- |
| Implementiert | Vollständiger lokaler UX4-B-Darstellungsschnitt im bestehenden Draft |
| Lokal geprüft | Frontendgate und Backend-Units bestanden; Browsernachweis siehe oben; PostgreSQL lokal übersprungen |
| CI-geprüft | Der erste vollständige Head `9e4f846…` ist mit neun erfolgreichen regulären Jobs qualifiziert. Die neue CI nach Main-Aktualisierung steht bei Erstellung dieses Nachtrags noch aus; maßgeblich sind ihre Runs am finalen Head bzw. dessen tatsächlichem Testmerge. Exakte Links/Ergebnisse stehen im PR. |
| Fachlich abgestimmt | Technischer Abgleich mit exakten kanonischen Verträgen erfolgt; neue persönliche Domain-/UX-/Screenreaderabnahme offen |
| Integriert/ausgeliefert | Main-Integration bedingt freigegeben, bei Erstellung dieses Nachtrags noch ausstehend; tatsächlicher Merge-/Main-SHA wird im PR dokumentiert. Release, Deployment und PC-Update sind damit nicht nachgewiesen. |

**Nächster Schritt:** Den aktualisierten PR #322 nach widerspruchsfreiem Abgleich
und erfolgreicher Standard-CI am aktuellen Main gemäß Nutzerfreigabe mergen.
