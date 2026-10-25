# FT-006 Marktanalyse

Die ursprüngliche V1-Beschreibung unten bleibt als historischer Vertrag erhalten.
Für neue Runs im Entwicklungsstand von PR #278 gilt die
[Fortschreibung vom 25.10.2026](#fortschreibung-2026-10-25-exakte-quellenqualität-und-runtimeversion).
Sie ersetzt keine Fachabnahme, Veröffentlichung oder produktive Modellaktivierung.

## Zweck

FT-006 erstellt reproduzierbare, beschreibende Marktanalysen auf Basis bereits persistierter, providerunabhängiger EOD-Marktdaten. Das Modul trifft keine Handelsentscheidung und lädt während einer Berechnung keine externen Daten nach.

## Architektur

`app/features/analysis` enthält Domain, Application Service, Persistence und REST API. Die Domain kennt weder EODHD noch SQLAlchemy oder HTTP. Der Application Service liest interne `DailyPrice`-Objekte über einen Analyse-Read-Adapter und persistiert jede Ausführung als unveränderliche Version.

## Modell V1

- Modell-ID: `EOD_TREND_MOMENTUM`
- Version: `1.0.0`
- Preisfeld: `CLOSE` oder `ADJUSTED_CLOSE`
- SMA kurz, mittel und lang
- Momentum über explizite Fenster
- annualisierte realisierte Volatilität
- Position in der beobachteten Handelsspanne
- Datenvollständigkeit und Aktualität

Klassifikationen sind `POSITIVE`, `NEUTRAL`, `NEGATIVE` und `NOT_EVALUABLE`. Sie sind keine Kauf-, Verkaufs- oder Halteempfehlungen.

## Reproduzierbarkeit

Jede Version speichert:

- Analyse-ID und Versionsnummer
- UTC-Analysezeitpunkt
- Basiswert und Listing
- Modell-ID und Modellversion
- vollständig aufgelöste Parameter
- verwendete Providerherkünfte
- jede verwendete Marktdatenzeile
- Kennzahlen und Einzelkriterien
- Hinweise und Qualitätsstatus
- SHA-256-Hash der kanonischen Eingaben
- technische Correlation-ID

## Lebenszyklus

V1 persistiert abgeschlossene Ausführungen mit `COMPLETED`, `COMPLETED_WITH_WARNINGS` oder `NOT_EVALUABLE`. `DRAFT`, `RUNNING`, `FAILED` und `SUPERSEDED` sind im Domain-Vertrag reserviert und werden bei späterer asynchroner Orchestrierung verwendet.

## REST API

- `POST /api/v1/market-analyses`
- `GET /api/v1/market-analyses`
- `GET /api/v1/market-analyses/{analysis_id}`
- `POST /api/v1/market-analyses/{analysis_id}/runs`
- `GET /api/v1/market-analyses/{analysis_id}/runs/{version}`

Die Run-API arbeitet ausschließlich mit bereits persistierten EOD-Daten im angeforderten Zeitraum.

## Lifecycle-Ergänzung Sprint 4

Der Lebenszyklus wird durch eine explizite State Machine erzwungen. Terminale Runs bleiben unveränderlich. Eine Ablösung wird append-only über `market_analysis_events` dokumentiert.

Retry ist nur für `FAILED` und `NOT_EVALUABLE` zulässig und verwendet ausschließlich den persistierten Snapshot der Quellversion. Der Retry liest keine aktuellen Marktdaten und verwendet exakt dieselbe Modell-ID/-Version sowie dieselben aufgelösten Parameter.

Die Reproduzierbarkeit einer Version kann über `POST /api/v1/market-analyses/{analysis_id}/runs/{version}/verify` technisch geprüft werden. Die Prüfung umfasst Eingabe-Hash, Modellversion, Kennzahlen, Kriterien, Qualitätsstatus und Hinweise.


## Ergänzung 2026-10-04: integrierte EOD-Diagramme

Der Chart-Arbeitszweig ergänzt echte ETF-Stammdaten und einen rein lesenden
Markt-/Sektor-/Aktienvergleich. Indexreferenzen bleiben ohne synthetische Listings.
Frühere STOCK-only-Aussagen gelten damit nicht mehr für die Stammdatenverwaltung.
Analyse-Runs, Candidate-Regeln und fachliche Freigaben bleiben unverändert.
Contracts, Preis-/Zeitsemantik, Einrichtung und Prüfstand:
[MARKET_CHARTS](../implementation/MARKET_CHARTS.md).

## Fortschreibung 2026-10-25: exakte Quellenqualität und Runtimeversion

### Bewusst gestartete neue Runs

Der feste Vertrag für neue Runs ist `EOD_TREND_MOMENTUM/1.0.1`.
`NEW_RUN_MODEL_ID` und `NEW_RUN_MODEL_VERSION` in
`backend/app/features/analysis/domain/model_versions.py` sind die zentrale
Auswahl. Listing- und Referenzservice sowie der optionale `model_version`-Wert
des Run-Requests verwenden diese Auswahl. Die Analyseoberfläche übergibt für
einen neu angeforderten Run ausdrücklich `model_version: "1.0.1"`.
Ein expliziter Request für `"1.0.0"` bleibt zulässig; er führt den historischen
Vertrag aus. Unbekannte Versionen werden abgewiesen. Es gibt keine Auswahl
anhand von „latest approved“, einer Candidate-Aktivierung oder der Importversion
eines Rechners. Der gemeinsame `_execute_snapshot` verlangt Modell-ID und
Modellversion als benannte Pflichtargumente.

Eine Analyse-Runtimeversion wie `1.0.1`, die fortlaufende Run-Nummer wie `2`,
die genehmigte FT-013-ModelVersion und die Softwareversion sind verschiedene
Identitäten. In API und Persistenz bleiben `model_id`, `model_version`,
Run-`version` und `governed_model_version_id` getrennt. Die neue Auswahl im
Aufgabenbranch ist weder ein Main-Merge noch eine Freigabe zum Betrieb einer
neuen Produktivversion.

`1.0.1` verwendet die numerischen Berechnungen des unveränderten `1.0.0`-Rechners.
Es ändert die technische Quellenqualitätsentscheidung: ausreichend viele
tatsächlich verwendbare Werte, ausschließlich originale `VALID`-Flags und
keine beeinträchtigenden Hinweise können `GOOD` ergeben. `INCOMPLETE`,
`SUSPICIOUS`, unbekannte oder leere Flags ergeben kein `GOOD`; auch ein
künstliches Quellflag `GOOD` ist kein TC-001-`VALID`. Warnungen und fehlende
ausgewählte Adjusted-Close-Werte bleiben in den Notes sichtbar.
`INSUFFICIENT` bleibt bei zu wenigen nutzbaren Beobachtungen vorrangig.
Aktualität prüft weiterhin der Application Service. Kalenderabdeckung wird
nicht aus einer bloßen Zeilenanzahl abgeleitet. Kennzahlen, Kriterien,
Parametergrenzen, Schwellen und Rundung bleiben unverändert.

`GOOD` beschreibt die technische Eignung der Analysegrundlage unter diesen
Prüfungen. Es ist keine Handelsfreigabe und kein wirtschaftlicher Erfolgsnachweis.

### Listing und echte Markt-/Sektorreferenz

Listinganalysen bleiben an ihren Basiswert, ihr Listing und ihre
`market_data_instrument_id` gebunden. Markt- und Sektorreferenzen verwenden
ihre echte `MARKET_REFERENCE`-Identität ohne Ersatzlisting. Für sie gelten die
bestehenden Commands:

- `POST /api/v1/top-down-reference-data/market-references/{reference_id}/analyses`
- `POST /api/v1/top-down-reference-data/market-reference-analyses/{analysis_id}/runs`

Der Referenz-Run reicht die exakte Modellversion an denselben Executor weiter.
Die allgemeinen Analyse-Readbacks, Snapshot-, Retry- und Verify-Endpunkte sind
auch für diese Owner verwendbar. `underlying_id` und `listing_id` sind dafür
nullable; `market_data_instrument_id` bezeichnet im Readback den wirklichen
Owner. Der Listing-Run-Endpunkt weist eine referenzeigene Analyse ab. Die
Analyseoberfläche wählt anhand des gespeicherten Owners den passenden
Run-Command.

### Originalwarnungen und Hash

Persistierte Preise speichern ihre Warnungen als durch Zeilenumbrüche
getrennten Text. `snapshot_from_price` bildet diesen Vertrag für neue
`1.0.1`-Runs beider Owner so ab:

| Persistierter Text | Snapshot-Warnungen | Bedeutung |
|---|---|---|
| `""` | `()` | Reguläre Transportdarstellung einer leeren Warnungsliste. |
| `"Hinweis"` | `("Hinweis",)` | Ein tatsächlicher Eintrag. |
| `"\n"` | `("", "")` | Nichtleerer Transport mit leeren Einträgen; bleibt diagnostizierbar und verhindert `GOOD`. |
| `" Hinweis \n\n"` | `(" Hinweis ", "", "")` | Leerzeichen und leere Einträge bleiben erhalten. |

Bei nichtleerem Text erfolgt ausschließlich `split("\n")`, ohne `strip` oder
Filter. Der Listingreader behält die vorhandene TC-001-Validierung von
Identität, Währung und Zahlenwerten bei, kopiert die Snapshotwerte aber aus
der gespeicherten Quelle. Neue explizite `1.0.0`-Runs verwenden weiterhin die
historischen Readersemantiken; Retry und Verify lesen für beide Versionen
ausschließlich ihren bereits gespeicherten Snapshot.

Diese Abbildung ist für den vorhandenen Persistenztext nachvollziehbar.
Ein bereits vor der Speicherung normalisierter oder verlorener Warnungseintrag
kann damit nicht rekonstruiert werden; insbesondere lassen sich `()` und ein
zuvor zu `""` serialisierter einzelner leerer Eintrag nachträglich nicht
unterscheiden. Es wird keine allgemeine Verlustfreiheit der vorgelagerten
Providerkette behauptet.

Rohflags werden nicht in `GOOD` umgeschrieben. `calculate_input_hash` bindet
Modell-ID, exakte Runtimeversion, vollständig aufgelöste Parameter und kanonische
Snapshotzeilen. Bei gleichen Preisen/Parametern unterscheiden sich die Hashes
neuer `1.0.0`- und `1.0.1`-Runs wegen der Runtimeversion. Vorhandene Hashes,
Originalinputs und terminale Ergebnisse werden nicht nachträglich verändert.

### Laufzeit- und Consumer-Matrix

| Strecke | Tatsächlicher Einstieg | Modellwahl und Originalquelle | Persistenz / Consumer | Zugeordneter Test |
|---|---|---|---|---|
| Listing-Run | Run-REST-Route → `MarketAnalysisService.run` | Feste neue `1.0.1`-Auswahl oder explizit `1.0.0`; persistierte `DailyPriceModel`-Zeilen des Listings. | Gemeinsamer `_execute_snapshot`; Run, Snapshot, Kriterien und Lifecycleevents. | `test_listing_new_run_uses_fixed_version_and_accepts_exact_legacy`; nativer HTTP-Fall `[listing]`. |
| Referenz-Run | Referenz-Run-Route → `run_market_reference` | Derselbe Versionsvertrag; aktive Referenz und ihre eigene `MARKET_REFERENCE`-Instrument-ID. | Derselbe Executor; kein synthetisches FT-001-Listing. | `test_reference_owner_uses_same_versioned_executor`; nativer HTTP-Fall `[reference]`. |
| Retry | Generische Retry-Route → geerbtes `retry` | Gespeicherte exakte Modell-ID/-Version, Parameter und Quellsnapshot; nur `FAILED`/`NOT_EVALUABLE`. | Neuer Run plus append-only Ablösungsereignis; alte terminale Fakten bleiben erhalten. | `test_failed_retry_reuses_exact_saved_version_and_snapshot`; `test_native_retry_cannot_upgrade_or_replace_source_snapshot`. |
| Verify | Verify-Route → geerbtes `verify_reproducibility` | Gespeicherte Identität und Snapshot; Aktualität zum ursprünglichen `analysis_time`. | Keine fachlichen Schreiboperationen; getrennte Teilprüfungen. | `test_verify_reports_each_changed_fact_independently`; `test_verify_uses_original_time_after_today_and_new_prices_change`. |
| Snapshot / Hash | `_execute_snapshot`, `calculate_input_hash`, Snapshot-Readback | Originalflags/-warnungen und aufgelöste Parameter; Runtimeversion im Hash. | Snapshot und terminale Runfakten unverändert. | `test_both_native_owners_preserve_history_and_exact_governed_contract`; `test_native_warning_transport_preserves_entries_and_empty_separator_diagnostics`. |
| Provenienz | PostgreSQL-`before_insert`-Listener | Exakter ausgeführter Runtimevertrag; genau eine passende genehmigte Baseline im selben Workspace. | `governed_model_version_id` oder `NULL`; keine Registrierung/Aktivierung. | `test_native_provenance_requires_exact_approved_workspace_contract`; `test_native_provenance_ambiguity_is_not_latest_wins_or_a_backfill`. |
| Candidate-Handoff | `SemanticTopDownSourceResolver` → `TopDownEvaluationOrchestrator` | Gespeicherte exakte Markt-/Sektor-/Basiswert-Runs und ihre Qualitätswerte. Native Referenzen werden mit Owner, Cutoff und vollständigem Snapshot geprüft. | Bestehender Candidate-Consumer speichert vollständige Quellreferenzen; keine Neuberechnung oder Clientübersteuerung. | Bestehender geschützter `candidate-governance-journey-postgres.spec.ts`; tatsächliche B07-Ergebnisse nur im Qualifikationsbericht. |

Die Unitfälle liegen unter `tests/unit/backend/features/analysis/`; die nativen
FT-006-Fälle unter
`tests/integration/backend/database/test_ft006_versioned_quality_postgres.py`.
Eine vorhandene Testdefinition oder erfolgreiche Collection ist kein Nachweis
ihrer Ausführung. CI, kombinierter Stand, Rohartefakte und noch offene
Abnahmegrenzen werden im
[FT-006-Qualifikationsbericht](../implementation/FT006_SOURCE_QUALITY_QUALIFICATION.md)
geführt. Der [B07-Bericht](../implementation/CANDIDATE_GOVERNANCE_JOURNEY_QUALIFICATION.md)
behält seinen historischen LIMITED-Nachweis und weist einen etwaigen neuen
GOOD-Nachweis getrennt aus.

### Historie und genaue Reproduktion

Der alte `1.0.0`-Rechner bleibt unverändert. Ein aus `VALID`-Preisen entstandener
historischer `LIMITED`-Run darf unverändert `LIMITED` reproduzieren und trotzdem
vollständig verifiziert sein. Retry ist kein Upgrade. Eine heute geänderte
Preiszeile oder neue Standardauswahl ersetzt weder seinen Snapshot noch seine
Modellidentität. Die ursprüngliche Zeit bleibt Maßstab der Verify-Frischeprüfung.

Verify vergleicht Modellverfügbarkeit, Eingabe-Hash, Kennzahlen, vollständige
Kriterien, Qualität und Notes getrennt. Der Kriterienvergleich normalisiert nur
die Reihenfolge, weil der Repositoryreader nach Code sortiert; Code,
Klassifikation, Wert, Erklärung und Multiplizität bleiben prüfpflichtig.
Unbekannte Modellidentitäten führen zum bestehenden Nichtverfügbarkeitsresultat
beziehungsweise zu einem abgewiesenen Run/Retry, ohne Ersatzrechner.
Der [Provenienzvertrag](FT-006_GOVERNED_MODEL_PROVENANCE.md) bindet genau die
ausgeführte Version und ist kein Runtime-Aktivierungssystem.
