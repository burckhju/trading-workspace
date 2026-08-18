# ADR-S11-009 – Repository-, Unit-of-Work- und Transaktionsgrenzen

## Status

Accepted for Sprint 11 technical Definition of Ready.

## Kontext

FT-011 besitzt eigene persistente Aggregate:

- PostTradeObservation;
- ExitReview;
- ExitReviewVersion.

Gleichzeitig konsumiert FT-011 bestehende Fakten aus anderen Features:

- Trade und Position;
- effektive Execution-Historie;
- effektive TradeManagementEvents;
- historische TradePlanVersion;
- historische Product-Selection-Provenance;
- Warrant und WarrantTermsVersion;
- Underlying und Listing;
- DailyPrice.

FT-011 darf diese Ownership-Grenzen nicht durch ein übergreifendes
God-Repository auflösen.

Das Repository verwendet bereits explizite Unit-of-Work-Patterns mit
atomarem Commit und Rollback.

## Entscheidung

### Eigenes FT-011 Unit of Work

FT-011 erhält ein eigenes:

PostTradeLearningUnitOfWork

mit mindestens:

- observations;
- exit_reviews;
- exit_review_versions;
- flush();
- commit();
- rollback().

Die konkrete SQLAlchemy-Implementierung folgt dem bestehenden Repository-UoW-
Pattern.

## FT-011 Write-Repositories

### PostTradeObservationRepository

Mindestens:

- add(observation)
- get(workspace_id, observation_id)
- get_for_trade(workspace_id, trade_id)
- replace(observation)

get_for_trade unterstützt die One-Observation-per-Trade-Invariante.

### ExitReviewRepository

Mindestens:

- add(review)
- get(workspace_id, review_id)
- get_for_observation(workspace_id, observation_id)

Die stabile Review-Identität wird nicht für normale Inhaltsänderungen ersetzt.

### ExitReviewVersionRepository

Mindestens:

- add(version)
- get(version_id)
- list_for_review(exit_review_id)
- get_latest(exit_review_id)
- get_current_finalized(exit_review_id)
- get_open_draft(exit_review_id)

Finalisierte Versionen werden nicht in-place fachlich überschrieben.

## Upstream Reads über Ports / Resolver

FT-011 besitzt keine Write-Repositories für fremde Feature-Aggregate.

Stattdessen konsumiert die Service-Schicht schmale Read-Contracts.

Mindestens erforderlich:

### TradeExitContextReader

Liefert:

- Trade;
- aktuelle Position;
- effektive Execution-Historie;
- effektive Management-Historie;
- FT-011 Eligibility;
- Full-Exit-Kontext.

### HistoricalPlanningContextReader

Liefert, sofern vorhanden:

- TradePlanVersion;
- ursprüngliche Targets;
- ursprünglichen Stop;
- weitere benötigte Plan-Provenance.

### HistoricalProductContextReader

Liefert, sofern vorhanden:

- Warrant;
- historische WarrantTermsVersion;
- maturity_date;
- ProductEvaluation-/Listing-Provenance.

### UnderlyingListingResolver

Löst gemäß ADR-S11-002 genau eine geeignete Underlying-Listing-ID.

### ObservationMarketDataReader

Liest relevante DailyPrice-Daten für die gepinnte Listing-ID.

Diese Ports dürfen intern bestehende Feature-Repositories oder Services
adaptieren.

FT-011 schreibt jedoch nicht in deren Tabellen.

## Start PostTradeObservation ist atomar

Der Command:

start_post_trade_observation

führt fachlich aus:

1. Trade laden;
2. FT-010 Eligibility prüfen;
3. bestehende Observation für Trade prüfen;
4. Underlying-Kontext auflösen;
5. konkrete Underlying-Listing-ID auflösen;
6. Observation erzeugen;
7. persistieren;
8. committen.

Wenn ein Schritt fehlschlägt:

kein Commit

und damit:

keine teilweise Observation.

## Completion ist atomar

Beim Übergang:

ACTIVE -> COMPLETED

muss die Service-Schicht zunächst die tatsächlich verwendbare EOD-Evidenz
prüfen.

Nur wenn der definierte Horizon erreicht wurde, darf der Status persistiert
und committed werden.

Ein COMPLETED ohne erfüllte Completion-Regel darf nicht gespeichert werden.

## Draft-Erstellung ist atomar

Beim Erstellen eines ExitReview-Drafts gilt:

1. Observation laden;
2. Review-Kontext prüfen;
3. offenen DRAFT prüfen;
4. stabile ExitReview-Identität gegebenenfalls anlegen;
5. nächste Review-Version bestimmen;
6. DRAFT anlegen;
7. committen.

Es darf nicht passieren:

exit_reviews angelegt
aber keine zugehörige initiale Version

wenn der Command insgesamt fehlschlägt.

## Finalisierung ist atomar

Beim Finalisieren einer Review-Version gilt:

1. Observation muss COMPLETED sein;
2. Version muss DRAFT sein;
3. alle vier Bewertungsdimensionen müssen gesetzt sein;
4. rationale muss gültig sein;
5. aktueller semantischer Input wird aufgebaut;
6. input_fingerprint wird berechnet;
7. Version wird FINALIZED / CURRENT;
8. Actor und finalized_at werden gesetzt;
9. commit.

Schlägt ein Schritt fehl:

Review bleibt DRAFT.

## Stale-Markierung ist atomar

Wird bei Revalidation erkannt:

stored fingerprint != current fingerprint

darf die finale Version in derselben FT-011-Transaktion:

CURRENT -> STALE

wechseln.

Bewertungsinhalt und rationale bleiben unverändert.

## Neue Version nach Staleness

Beim erneuten Review gilt:

1. bisherigen FINALIZED/STALE-Stand laden;
2. sicherstellen, dass kein offener Draft existiert;
3. nächste Versionsnummer bestimmen;
4. neue DRAFT-Version mit supersedes_version_id erzeugen;
5. committen.

Die finalisierte alte Version wird nicht zurück auf DRAFT gesetzt.

## Keine Cross-Feature-Schreibtransaktion

FT-011 startet keine Transaktion, die gleichzeitig beispielsweise:

ExecutionRecord korrigiert
+
PostTradeObservation verändert
+
ExitReview finalisiert.

Upstream-Korrekturen bleiben im verantwortlichen Feature.

FT-011 reagiert anschließend auf die neue effektive Faktenlage.

## Reads und Revalidation

Reine Reads wie:

- Observation anzeigen;
- Observation Points laden;
- Metriken berechnen;
- Review-Historie anzeigen;

benötigen keinen Commit.

Fingerprint-Revalidation gehört in die Application-Service-Schicht und darf
nicht als versteckter Seiteneffekt eines Repository-get() erfolgen.

Favorisiert:

service.get_review_with_revalidation()

oder ein semantisch gleichwertiger expliziter Service-Flow.

## Concurrency

Die Service-/Repository-Schicht muss konkurrierende Commands gegen folgende
Invarianten schützen:

- höchstens eine Observation pro Trade;
- höchstens ein ExitReview-Kontext pro Observation;
- höchstens ein offener DRAFT pro Review;
- eindeutige Review-Versionsnummern.

Datenbank-Unique-Constraints bleiben die letzte Sicherheitslinie.

Concurrent Conflicts werden in kontrollierte fachliche Fehler übersetzt und
dürfen nicht als ungefangener IntegrityError beim Nutzer erscheinen.

## Auswirkungen für den Nutzer

Wenn "Nachbeobachtung starten" fehlschlägt, existiert danach keine halbe
Observation ohne Listing oder vollständigen Kontext.

Doppelklicks oder parallele Requests erzeugen keine zwei offenen Review-Drafts.

Bei Finalisierung gilt:

entweder vollständig FINALIZED inklusive Fingerprint und Actor
oder vollständig DRAFT.

Korrekturen eines SELL bleiben im Trade-Management-Feature und werden nicht mit
FT-011 in einer undurchsichtigen Super-Transaktion vermischt.

## Begründung

Das bestehende UoW-Pattern ist im Repository bereits etabliert.

Ein eigenes FT-011-UoW erhält klare Ownership und ermöglicht atomare Commands,
ohne fremde Feature-Repositories in einen gemeinsamen Persistence-Service zu
ziehen.

Schmale Read-Ports reduzieren Kopplung und erleichtern Unit Tests.

Explizite Transaktionsgrenzen machen sichtbar, welche Benutzeraktion welche
persistente Änderung verursacht.

## Invarianten

### INV-S11-071
FT-011 besitzt ein eigenes Unit of Work für eigene Write-Aggregate.

### INV-S11-072
FT-011 schreibt nicht über eigene Repositories in fremde Feature-Tabellen.

### INV-S11-073
Observation-Start ist atomar.

### INV-S11-074
Observation-Completion ist atomar und validiert den Horizon vor Commit.

### INV-S11-075
Review-Draft-Erstellung erzeugt keinen halbfertigen Review-Kontext.

### INV-S11-076
Review-Finalisierung ist atomar.

### INV-S11-077
Eine finalisierte Review-Version wird nie auf DRAFT zurückgesetzt.

### INV-S11-078
Neue Bewertung nach Staleness erzeugt eine neue Version.

### INV-S11-079
Fingerprint-Revalidation wird in einer expliziten Service-Grenze orchestriert.

### INV-S11-080
Datenbank-Constraints sichern konkurrierende One-per-Trade-, One-Draft- und
Versions-Invarianten zusätzlich ab.
