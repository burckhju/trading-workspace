# Instrumentbezug der Stop-/Zielprüfung

## Ursache und Entscheidung

Der bisherige Resolver übernahm Zahlen aus FT-010 oder dem historischen FT-007-Plan und verglich sie durchgehend mit dem Tief/Hoch des Basiswerts. FT-010 speicherte keinen Instrument- oder Währungsbezug. Damit konnte ein Optionsschein-Ziel von 2,50 fälschlich durch einen Basiswertkurs von 337 ausgelöst werden.

Jeder automatisch geprüfte Stop und jedes Ziel benötigt jetzt eine ausdrücklich bestätigte `price_binding`: `basis` (`WARRANT` oder `UNDERLYING`), `instrument_id` und `currency`. Die Bestätigung wird als neuer immutable FT-010-Managementeintrag gespeichert. Produkt- und Basiswertidentität müssen zum Trade gehören. Auch ein unveränderter Zahlenwert kann mit seinem Bezug erneut gespeichert werden. Es gibt keine Interpretation anhand der Größenordnung und keine automatische Währungsumrechnung.

Vorhandene ungebundene Managementwerte und die historische Plan-Rückfallquelle bleiben sichtbar, sind aber für die automatische Regelprüfung `RULE_PRICE_BASIS_UNCONFIRMED`. FT-007 bleibt produktneutral; sein numerischer Plan wird nicht nachträglich umgedeutet. Für eine automatische Basiswert-Regel muss der entsprechende Wert in FT-010 ausdrücklich als Basiswertpreis bestätigt werden.

## Auswertung

- `WARRANT`: bestehende `ProductPositionValuationService` und bestehender Quote-Resolver. Verifizierter Bid oder ausdrücklich ausgewiesener Last-/Close-Referenzpreis. Fehlende Basiswert-Mappings blockieren diese Prüfung nicht. Fehlende Produktprovenienz oder unpassende Instrument-/Währungsidentität bleiben gesperrt.
- `UNDERLYING`: aktives primäres Listing, bestehendes Mapping und abgeschlossene Tagesdaten. Stop gegen Tagestief, Ziel gegen Tageshoch. Listing, Währung, Qualität und Handelstag werden geprüft. Aktuelle, noch nicht abgeschlossene Handelstage sind ausgeschlossen. Die bisherige maximale Tagesdatenalter-Grenze bleibt bestehen.
- Veraltete/indikative Produktkurse dürfen gemäß vorhandener Bewertungsrichtlinie Hinweise erzeugen; Quelle, Kursart, Originalzeitpunkt, Abrufzeitpunkt und Warnung werden gespeichert. Es entsteht keine Orderfreigabe.
- Der Bezug gehört zur Identität des gespeicherten Regelzustands. Ein Wechsel des Instruments oder der Währung übernimmt keinen ausgelösten Zustand einer anders bezogenen Regel. Ältere Beobachtungen können einen neueren Regelzustand nicht überschreiben.
- Datenabruf und Regelprüfung behalten ihre konfigurierten Intervalle. Es werden keine zusätzlichen kostenpflichtigen Provider oder Abonnements eingerichtet. Die Prüfung nutzt die vorhandenen Provider und deren Zugangs-/Rate-Limit-Regeln.

## Alte Meldungen

Die additive Migration `20260914_0037` verändert keine Preise, Positionen oder Meldungsdaten. Beim ersten neuen Monitoring-Durchlauf werden noch offene Meldungen ohne gespeicherten Kursbezug auf `INVALIDATED` gesetzt, mit `invalidated_at` und `LEGACY_RULE_PRICE_BASIS_UNCONFIRMED`. Ihre ursprünglichen Werte, Gründe und Versandhistorien bleiben erhalten. Bereits versendete Benachrichtigungen können dadurch nicht zurückgerufen werden. Ausstehende Benachrichtigungen ungültiger Meldungen werden vom Versand ausgeschlossen. Diese Quarantäne ist idempotent und behauptet keine erfolgreiche Kursauflösung. Ein Schema-Downgrade verweigert die Rückkehr zu den alten Statuswerten, solange `INVALIDATED`-Historie vorhanden ist; diese wird nicht stillschweigend umgeschrieben.

## Lokales Deployment und Prüfung

```bash
git switch main
git pull --ff-only
bash scripts/start-linux.sh --frankfurt
```

Das Startskript baut Backend/Frontend und führt `alembic upgrade head` aus. Manuell entspricht dies (bestehende Umgebungsdateien beibehalten):

```bash
docker compose --env-file docker/.env -f docker/compose.yml -f docker/compose.frankfurt.yml build backend frontend
docker compose --env-file docker/.env -f docker/compose.yml -f docker/compose.frankfurt.yml up -d --wait database
docker compose --env-file docker/.env -f docker/compose.yml -f docker/compose.frankfurt.yml run --rm backend alembic upgrade head
docker compose --env-file docker/.env -f docker/compose.yml -f docker/compose.frankfurt.yml up -d --wait backend frontend
```

1. In **Trade verwalten → Aktueller Management-Zustand** für Stop und Ziel das Instrument sowie die Währung auswählen, Wert prüfen und speichern. Ein fehlender Bezug wird nicht vorbelegt. Bei Optionsscheinpreisen in EUR: **Optionsschein**, **EUR**. Kein gleichzeitiger Börsen- oder Basiswertwechsel nötig.
2. Einmalige Prüfung ohne Benachrichtigungsversand (der Befehl schreibt Regelzustände/Meldungen und quarantänisiert offene Alt-Meldungen):

```bash
docker compose --env-file docker/.env -f docker/compose.yml -f docker/compose.frankfurt.yml exec -T \
  -e TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=false backend \
  python -m app.features.position_monitoring.cli \
  --backend-url http://127.0.0.1:8000 --include-rule-checks
```

3. Automatik nach Prüfung bei Bedarf wieder aktivieren: `TRADING_WORKSPACE_POSITION_MONITORING__ENABLED=true` in `docker/.env`, anschließend Backend mit denselben Compose-Dateien neu erstellen. Ein beim Start bereits aktivierter Hintergrundlauf kann unabhängig vom obigen Einmalbefehl die konfigurierten Benachrichtigungen versenden.
4. Status und tatsächlichen Kursbezug im letzten Hintergrunddurchlauf kontrollieren:

```bash
curl -fsS http://localhost:8000/api/v1/position-monitoring/runtime/status \
  | jq '{price_basis, last_result, last_rule_checks}'

curl -fsS http://localhost:8000/api/v1/position-monitoring/runtime/status \
  | jq '[.last_rule_checks[] | select(.trade_id == "dd8338bd-a092-42c0-94c0-c068a9094f77")]'
```

`blocked_rules` muss als offene Aufgabe bewertet werden, auch wenn andere Regeln bereits ausgewertet wurden. `positions_checked` zählt Positionen mit mindestens einer erfolgreichen Regelprüfung, nicht zwingend mit allen Regeln. Fehlender Basiswertkurs bleibt im getrennten Datenzustand sichtbar. Für UNH mit bestätigtem Optionsschein-Ziel 2,50 und beobachtetem Produktkurs 0,24 muss das Ziel unausgelöst bleiben; ein Basiswertkurs von 337 ist für diese Regel ausgeschlossen. Die konkreten Live-Werte müssen lokal zum jeweiligen Prüfzeitpunkt kontrolliert werden.

## Sammelbestätigung vorhandener Optionsschein-Regeln

Wenn fachlich bestätigt ist, dass **alle vorhandenen Stop- und Zielwerte der ausgewählten offenen Positionen Optionsscheinpreise in der angegebenen Währung sind**, kann die Zuordnung gesammelt erfolgen. Die folgende Anleitung gilt für die bestätigten 52 Positionen mit EUR-Schwellen. Diese Anzahl und Währung sind Aufrufparameter; der Code enthält keine Benutzer- oder Produkt-IDs.

Zuerst aktualisieren und bauen:

```bash
git switch main
git pull --ff-only
bash scripts/start-linux.sh --frankfurt
```

Vorschau erzeugen. Sie enthält die konkreten Trades, Positionen, Optionsschein-IDs, ISINs, unveränderten Schwellen und bereits passende Zuordnungen. Es wird noch nichts gespeichert und kein Provider abgefragt:

```bash
mkdir -p docker/rule-confirmations
docker compose --env-file docker/.env \
  -f docker/compose.yml -f docker/compose.frankfurt.yml exec -T backend \
  python -m app.tools.confirm_warrant_rules preview \
  --workspace-id 00000000-0000-4000-8000-000000000001 \
  --currency EUR --expect-positions 52 \
  > docker/rule-confirmations/warrant-eur.json

jq '{workspace_id, basis, currency, positions_count,
     rules_count: (.rules | length),
     pending_rules: ([.rules[] | select(.already_confirmed == false)] | length)}' \
  docker/rule-confirmations/warrant-eur.json
```

Bei 52 bisher unbestätigten Positionen werden `positions_count: 52`, `rules_count: 104` und `pending_rules: 104` erwartet. Mit folgendem Befehl genau diese Vorschau anwenden; die lokale Actor-ID entspricht dem vorhandenen lokalen UI-Benutzer:

```bash
docker compose --env-file docker/.env \
  -f docker/compose.yml -f docker/compose.frankfurt.yml exec -T backend \
  python -m app.tools.confirm_warrant_rules apply \
  --workspace-id 00000000-0000-4000-8000-000000000001 \
  --currency EUR --expect-positions 52 \
  --actor-id 00000000-0000-4000-8000-000000000002 \
  < docker/rule-confirmations/warrant-eur.json
```

Erwartet: `status: APPLIED`, `events_created: 104` (abzüglich bereits passend bestätigter Regeln). Eine Wiederholung derselben Vorschau erzeugt keine weiteren Einträge: `ALREADY_CONFIRMED`, `events_created: 0`.

Die Anwendung prüft die gesamte Vorschau gegen den aktuellen Bestand. Geänderte Positionen, Instrumente, Schwellen, widersprechende Zuordnungen oder bereits geplante zukünftige Preisänderungen brechen den Vorgang ab. Eine neue Vorschau muss auf dem korrigierten Bestand erzeugt werden; die JSON-Datei nicht manuell zur Umgehung der Prüfung ändern. Geschlossene/stornierte Positionen und andere Workspaces sind ausgeschlossen. Bei fehlendem Stop oder Ziel wird keine Schwelle erfunden.

Alle Zuordnungen werden als neue FT-010-Management-Ereignisse in **einer Transaktion** geschrieben; bestehende Historie, TradePlan-Versionen, Mengen, Einstand und Kursquellen werden nicht umgeschrieben. Kurze Datenbanksperren verhindern parallele Änderungen während Prüfung und Anwendung. Andere Schreibvorgänge können kurz warten; kann die Sperre innerhalb von fünf Sekunden nicht erworben werden, wird abgebrochen. Die Vorschau ist lesend, die Anwendung ist ein einmaliger Wartungsvorgang.

Der Sammelbefehl erzeugt selbst weder Alerts noch Benachrichtigungen oder Orders. Der bereits aktive Hintergrundlauf prüft die bestätigten Regeln beim nächsten Durchlauf und kann entsprechend der bestehenden Konfiguration Benachrichtigungen erzeugen. Für eine sofortige Prüfung ohne Telegram kann der oben dokumentierte Einmalbefehl verwendet werden; dieser ersetzt nicht den Prozessstatus des Hintergrundlaufs.

Nach dem nächsten Hintergrunddurchlauf:

```bash
curl -fsS http://localhost:8000/api/v1/position-monitoring/runtime/status \
  | jq '{last_cycle_completed_at, last_result,
         unconfirmed: ([.last_rule_checks[]
           | select(.reason == "RULE_PRICE_BASIS_UNCONFIRMED")] | length),
         other_checks: [.last_rule_checks[]
           | select(.status == "BLOCKED" or .status == "MISSING"
                    or .status == "STALE" or .status == "ERROR")]}'
```

Die fehlenden Zuordnungen sollen auf null sinken. Das ist noch kein Beleg für vollständige Kursversorgung: anschließend verbleibende Identitäts-, Währungs-, Kurs- oder Mappingprobleme anhand der jeweiligen `last_rule_checks` prüfen. Das Bestätigen eines Optionsscheinpreises macht keinen fehlenden Kurs verfügbar und erteilt keine Orderfreigabe.

## Aussagekraft des Einmallaufs und Kursdiagnose

`docker compose exec … python -m app.features.position_monitoring.cli` startet einen **separaten Prozess**. Ohne `--backend-url` hat dieser Prozess einen eigenen, zunächst leeren Provider-Cache. Die im API-Backend durch den Refresh-Scheduler gespeicherten letzten Kurse sind dort nicht vorhanden. Frankfurt begrenzt gleichzeitig die zeitlich unmittelbar folgenden Abrufe. Dadurch können viele Regeln `MISSING` melden, obwohl der laufende Backend-Prozess die betreffenden Kurse bereits im Cache besitzt. Ein solcher Lauf belegt keine fehlende Börsenabdeckung. Er startet außerdem keinen dauerhaften Refresh-Scheduler.

Für die Kontrolle eines laufenden lokalen Depots deshalb `--backend-url http://127.0.0.1:8000` verwenden. Der CLI-Lauf liest die bestehende Produktbewertungs-API und teilt dadurch deren Provider-Cache, letzte erfolgreiche Beobachtungen und Abrufbegrenzung mit UI und Hintergrundlauf. Er senkt keine Abrufgrenze und erzeugt keinen neuen Produkt-Provider-Abrufhaushalt. Die Basiswert-Tagesdaten verwenden weiterhin den bestehenden EOD-Zugriff. Quelle, Kursart, Originalzeitstempel, Warnungen und Instrumentidentität werden vom API-Vertrag übernommen und durch dieselbe Regelprüfung validiert. Bei nicht erreichbarem Backend gibt es keinen stillen Rückfall auf einen separaten Produkt-Cache.

**Aktualisierung des Einmalwerkzeugs ohne Verlust des laufenden Kurs-Caches:** Ein Backend-Neustart leert auch dessen Prozess-Cache. Deshalb kann zunächst nur das neue Image gebaut und der neue CLI-Prozess als separater Compose-Container gestartet werden. `--no-deps` lässt das bestehende Backend laufen; dessen Adresse im Compose-Netz ist `http://backend:8000`:

```bash
git switch main
git pull --ff-only
docker compose --env-file docker/.env \
  -f docker/compose.yml -f docker/compose.frankfurt.yml build backend

mkdir -p docker/rule-confirmations
docker compose --env-file docker/.env \
  -f docker/compose.yml -f docker/compose.frankfurt.yml run --rm --no-deps -T \
  -e TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=false backend \
  python -m app.features.position_monitoring.cli \
  --backend-url http://backend:8000 --include-rule-checks \
  > docker/rule-confirmations/monitoring-check.json
```

Das aktualisiert das CLI-Werkzeug für diesen Lauf, nicht den bereits laufenden API-Prozess. Änderungen an dessen Quellen-Fehlercodes werden beim nächsten regulären Backend-Deployment aktiv. Nach einem regulären Neustart muss der Refresh-Scheduler die Kurse erst wieder aufbauen; ein kurz danach noch unvollständiges Ergebnis ist kein Abdeckungsnachweis. Der Modus liest vorhandene Bewertungen und kann fehlende Kurse nicht selbst herstellen.

Die Ausgabe nennt `quote_context: RUNNING_BACKEND` bzw. `ISOLATED_PROCESS_CACHE`. Mit `--include-rule-checks` enthält sie zusätzlich:

- `rule_checks`: Instrument, Währung, Schwelle, Status, tatsächlicher Vergleichskurs und Provenienz je Regel.
- `product_valuations`: Produktbewertungsstatus und tatsächlich versuchte Kursquellen je Trade bei Nutzung des Backends. Begrenzte technische Fehlercodes wie `FRANKFURT_REQUEST_THROTTLED` oder `FRANKFURT_HTTP_404` bleiben in `source_attempts` erhalten; beliebige Exception-Texte oder HTTP-Antworten werden nicht ausgegeben.

Zum Speichern und Auswerten eines aktuellen Prüflaufs (schreibt Regelzustände/Alerts, Telegram für diesen Prozess deaktiviert):

```bash
mkdir -p docker/rule-confirmations
docker compose --env-file docker/.env \
  -f docker/compose.yml -f docker/compose.frankfurt.yml exec -T \
  -e TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=false backend \
  python -m app.features.position_monitoring.cli \
  --backend-url http://127.0.0.1:8000 --include-rule-checks \
  > docker/rule-confirmations/monitoring-check.json

jq '{quote_context, positions_seen, positions_checked, rules_evaluated,
     blocked_rules, subject_errors, missing_market_data, market_data_errors,
     rules_by_status: ([.rule_checks[]] | group_by(.status)
       | map({status: .[0].status, count: length})),
     missing_products: [.product_valuations[]
       | select(.status == "MISSING" or .status == "UNAVAILABLE" or .status == "ERROR")]}' \
  docker/rule-confirmations/monitoring-check.json
```

Fehlende Marktdaten werden **pro Regel** gezählt: 92 fehlgeschlagene Preisprüfungen können bei je zwei Regeln 46 Positionen betreffen. `market_data_errors: 0` allein beweist keinen fehlerfreien Provider, weil eine Produktbewertung mehrere fehlgeschlagene Quellen zu `NO_USABLE_WARRANT_QUOTE` zusammenfassen kann. Die Quelle der Einschränkung steht in den Detaildaten. Der Einmallauf aktualisiert weiterhin nicht `runtime/status`; dort bleibt das letzte Ergebnis des separaten Hintergrund-Schedulers sichtbar. Ein bereits aktiver Hintergrundlauf kann unabhängig vom CLI-Aufruf konfigurierte Benachrichtigungen versenden.
