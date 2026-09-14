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
  python -m app.features.position_monitoring.cli
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
