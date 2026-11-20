# Betrieb der Emittentenkurse ab Version 1.4.0

Diese Anleitung ersetzt die Installationsbefehle der früheren Einzelpakete.
Ein GitHub-Merge aktualisiert den laufenden Server nicht automatisch. Ein bereits
laufender JMBbot bleibt bis zu einem gesonderten Deployment auf seinem installierten
Stand. Bestehende Konfiguration, Datenbank und Zustimmungsspeicher erhalten.

## Quellenwahl bei neuen Optionsscheinen

1. Kanonische ISIN, Emittent und eine eindeutige aktive EUR-Notierung müssen in
   den Stammdaten vorhanden sein. Discovery erfindet oder repariert diese nicht.
2. Bei aktivierter Emittentensuche prüft die Hintergrund-Lane die offizielle
   Produktseite von JPMorgan oder Morgan Stanley. Nur exakte Produktidentität,
   Produkttyp, Bewertungstag, Währung und DOM-Streamkennung ergeben einen Nachweis.
3. Wenn die HTTP-Seite unvollständig ist, darf der private Renderer sie darstellen.
   Zugangssperren, Rate Limits und geänderte Bedingungen werden nicht umgangen.
4. Registrierung und spätere Auswahl prüfen die Stammdaten erneut unter Sperren.
   Der dedizierte Streamadapter holt Kurse; der Quellenabgleich bindet nur geeignete
   verifizierte Routen. Zulässige bestehende Quellen werden erhalten.
5. Bewertungsansicht und Monitoring zeigen Anbieter, Qualität, Kurszeittext und
   Empfangszeit. Ohne verifiziertes Datum/Zeitzone bleibt `quote_observed_at=null`.
   Indikative Regeln folgen ausschließlich der bestätigten Indikations-Policy.

Aktivierung erfolgt ausdrücklich über das optionale Compose-Overlay. Ohne diese
Konfiguration bleiben neue Provider, automatische Auswahl und Discovery aus.
Das Discovery-Intervall beträgt standardmäßig eine Stunde; Diagnose-GETs erzwingen
keinen sofortigen Wiederholungsabruf. `SELECTED` beweist keine neue oder handelbare Quote.

### JPMorgan-Produktseiten ohne DOM-Uhrzeitfeld (ab 1.4.5)

Die Routenerkennung verlangt Geld- und Briefbindung im `staticgrid` mit
`data-source=lightstreamer` und derselben exakten, ISIN-bezogenen Streamkennung.
Das JPMorgan-DOM-Feld `quotetime` ist optional: Ein am 04.10.2026 zurückgemeldeter
Serverlauf enthielt beide Preisbindungen, aber kein solches Zeitfeld. Ist eine
passende Zeitbindung vorhanden, darf sie der Preiskennung weiterhin nicht
widersprechen. Produktmetadaten, Währung und alle übrigen Identitätsgrenzen gelten
unverändert. Morgan Stanley verlangt weiterhin `lastquotetimestamp`.

Dies ist ausschließlich ein Seitennachweis für die technische Route, keine
Kursprüfung. Der Streamadapter behält sein eigenes Schema und seine Prüfungen.
Fehlende Kurszeit bleibt unbekannt; weder Empfangszeit, Bewertungstag noch
Basiswertzeit werden eingesetzt. `execution_usable=false` bleibt erhalten.

Auf älteren Ständen kann das Zustimmungs-Setup nach erfolgreicher Formularbedienung
mit `JPMORGAN_CONSENT_NOT_VERIFIED_NO_STATE_SAVED` und der Ursache
`ISSUER_STREAM_BINDING_UNVERIFIED` abbrechen. Erst die konkreten DOM-Bindungen
unterscheiden diesen Fehler von fehlenden oder widersprüchlichen Preisbindungen.
Keine Speicherung erzwingen, keine Zeitfelder synthetisch ergänzen und keine
Wartezeiten pauschal erhöhen. Backend und Renderer auf denselben korrigierten
Release-Stand bringen; ein neuer Diagnose-Checkout allein ersetzt deren Parser
nicht. Danach den bestehenden freigegebenen Setup-Ablauf mit weiterhin identischem
Bedingungshash erneut ausführen und die Wiederverwendung separat nachweisen.

## Reguläre Konfiguration

`docker/compose.issuer-monitoring.yml` bündelt die bisherigen Emittenten-,
Performance-, Auswahl-, Renderer- und Monitoring-Overlays. Bestehende Frankfurt-,
gettex- und Stuttgart-Konfiguration zusätzlich erhalten. Die neuen Dateien nicht
mit alten Paket-Overlays mischen, die dieselben Werte erneut überschreiben.

Ab 1.4.1 unterstützt der kanonische Starthelfer das Overlay ausdrücklich:

```bash
bash scripts/start-linux.sh --issuer-monitoring --check
bash scripts/start-linux.sh --issuer-monitoring
```

Der erste Aufruf ist rein prüfend; der zweite führt das Deployment aus. Vorhandenes
`docker/frankfurt.env` wird automatisch berücksichtigt. Weitere tatsächlich benötigte
Börsen-Overlays auf beiden Aufrufen in bisheriger Reihenfolge mit `--overlay DATEI`
angeben. Weggelassene oder umsortierte frühere Compose-Dateien führen vor Änderungen
zum Abbruch. Alte Paket-Overlays erst nach bewusster manueller Migrationsprüfung
ablösen, nicht zusätzlich mit dem kanonischen Overlay mischen. Details und Grenzen:
[Linux Deployment](LINUX_DEPLOYMENT.md#issuer-monitoring-and-existing-overlay-chains-141).

Der Helper baut auch den Renderer und verlangt dessen Sandbox-Healthcheck vor
Migration/Backend-Neustart. Der Migrationscontainer startet keine Abhängigkeiten.
Für manuelle Compose-Aufrufe im Projektverzeichnis weiterhin:

```bash
export ISSUER_RENDERER_SECCOMP_PATH="$PWD/docker/issuer-renderer/seccomp_profile.json"
```

Den Telegram-Schalter `TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=true`
in der bestehenden privaten `docker/.env` beibehalten, wenn der Versand bereits
freigegeben und eingerichtet ist. Bot-Token und Chat-ID bleiben ausschließlich dort.
Das Overlay versendet selbst keine Testnachricht. Vor einem Deployment die effektive
Compose-Konfiguration prüfen, ohne deren Geheimniswerte öffentlich auszugeben.

Die folgenden Diagnosebeispiele verwenden die Basiskonfiguration zur Auswahl des
bereits laufenden Containers; `exec` rekonstruiert oder ersetzt keinen Dienst:

```bash
docker compose --env-file docker/.env -f docker/compose.yml exec -T backend \
  python -m app.tools.audit_monitoring_performance --wait-seconds 0
```

Zusätzliche Prüfwerkzeuge: `audit_position_source_selection`,
`audit_issuer_route_discovery`, `audit_new_issuer_routes` und `monitoring_resume`.
Die jeweilige `--help`-Ausgabe zeigt Pflichtparameter. Die beiden Runtime-Hash-Audits
benötigen die Hashliste des tatsächlich deployten Commitstands, keine alten
Paket-Hashes. `audit_issuer_monitoring` kann über die normalen Bewertungs-GETs Kurse
aktualisieren; es verändert keine Regeln und versendet keine Meldungen.

Ab 1.4.2 zählt `audit_monitoring_performance` alle aktuellen `ISSUER_QUOTES`-Jobs,
auch für neu entdeckte Produkte. Eine historische ISIN-Liste begrenzt diese
Diagnose nicht mehr. Ein Regelcheck wird anhand seines expliziten Providers oder,
bei fehlender Providerangabe, seiner Instrument-ID in einem solchen Job zugeordnet.
Eine ausdrücklich andere Kursquelle bleibt maßgeblich. Diese Zuordnung ist keine
Änderung oder Bestätigung der benutzergebundenen Quellenentscheidung.

`issuer_refresh_success_isins` erfordert je Produkt einen verfügbaren Job mit
positivem endlichem Geldkurs eines unterstützten Emittenten, Empfangszeit und ohne
Retention/Abruffehler. `issuer_refresh_unverified_isins` nennt die übrigen Produkte.
Die Jobliste zeigt `positive_bid_evidenced` und kompakte Original-Kursfelder, damit
ein verfügbares Ergebnis ohne diesen Nachweis erklärbar bleibt. Empfangszeit ist
weiterhin keine Kurszeit; ein positiver Geldkurs beweist weder Aktualität noch
Ausführbarkeit. `rule_issues` umfasst auch indikative Regelchecks mit Abruffehlern
und erhält deren ursprünglichen Status.

`wait_completed=true` bestätigt Schedulerfortschritt und erfolgte Erstprüfungen
aller aktuellen Emittentenjobs, keine vollständige Kursabdeckung. Monitoring- und
Refresh-Status werden nacheinander gelesen. Ein späterer erfolgreicher Abruf kann
deshalb neben einem noch fehlgeschlagenen Check des letzten Monitoring-Zyklus
stehen. Der nächste reguläre Zyklus liefert den neuen Bewertungsnachweis.

## JPMorgan-Zustimmung

Der Renderer verwendet ausschließlich seinen eigenen privaten Zustand im Volume
`issuer-consent-state`. Eine Zustimmung im Cloud-Browser ist nicht dieser Zustand.
Die unbeaufsichtigte Discovery klickt keine rechtlichen Erklärungen an.

Zur Vorbereitung im laufenden Renderer:

```bash
docker compose --env-file docker/.env -f docker/compose.yml \
  -f docker/compose.issuer-monitoring.yml exec -T issuer-renderer \
  python -m app.tools.setup_jpmorgan_consent
```

Der Betreiber prüft den ausgegebenen aktuellen Text, Hash und seine Erklärungen.
Der explizite Zustimmungslauf benötigt `--accept-current-jpmorgan-terms`,
`--confirm-sha256`, `--confirm-de-at-residence-and-non-us-person` und bei gewünschter
Speicherung `--remember-30-days`. Er läuft unter der vorhandenen Setup-Sperre.
Ein geänderter Hash wird nicht automatisch freigegeben.

Vor erneuter Zustimmung wird ein vorhandener gültiger Zustand mit passendem Hash
in einem frischen Kontext produktgeprüft. Erfolg:
`EXISTING_CONSENT_REUSE_VERIFIED`, `new_acceptance_performed=false`.
Ohne gespeicherten Zustand wird der bestätigte Formularlauf ausgeführt; erst nach
verifizierter Wiederverwendung darf gespeichert werden. Erfolg:
`CONSENT_STORED_PRODUCT_VERIFIED`, `new_acceptance_performed=true`.
Ungültige oder nicht mehr verwendbare vorhandene Zustände werden nicht stillschweigend
überschrieben. Die Größenbegrenzung bleibt bestehen; eine kleinere Variante nur
mit den erfassten Cookies benötigt eine erneute Produktprüfung.

`setup_diagnostics` nennt Phasen, Laufzeiten, begrenzte Fehlerketten und reine
Speichermetadaten. Keine Cookies/Storage-Werte in Berichte kopieren. Wenn Speichern
bereits gelang und nur die Browserbereinigung fehlschlug, macht der Bericht dies
sichtbar; der nächste Lauf prüft die gespeicherte Zustimmung zuerst.

Der Setup-Erfolg erzeugt weder ein Mapping noch eine Testposition. Neue Routen
werden weiterhin durch die Hintergrund-Lane und deren Identitätsprüfungen angelegt.

## Release und Deployment auseinanderhalten

<a id="indicative-entry-operations"></a>
### Gesonderte automatische Einstandsbeobachtung

`INDICATIVE_ENTRY_V1` mit Regelversion `indicative-entry-review-v1` ist ein eigener
freigegebener Prüfumfang. Er nutzt gespeicherte Positionen, effektive Ausführungen,
Einstand und Währung sowie vorhandene Quellen-, Kalender- und Produktbelege.
Z1-Verkauf oder Target-Evidenz sind für diesen Umfang keine Voraussetzung. Neue
oder fehlende Belege werden gezielt als Datenproblem sichtbar; unveränderte
Belege innerhalb ihres Gültigkeitsbereichs werden nicht täglich neu bestätigt.

Der Hintergrundrunner erzeugt drei getrennte Hinweise im vorhandenen
Arbeitsbereich: Einstandsindikation unter persönlichem Bruttoeinstand,
Prüferinnerung nach 20 abgeschlossenen Basiswertsitzungen und Datenproblem.
Wiederholung und Neustart erzeugen keinen zweiten logischen Hinweis für dieselbe
Episode. Eine Datenlücke ist keine Kurserholung. Vollständiger Verkauf beendet
neue Hinweise und noch ausstehende Zustellungen dieser Typen; die Historie bleibt.
Die vorhandenen allgemeinen Stop-/Zielregeln bleiben erhalten.

Ein explizit belegter Original-BID benötigt seine eigene Seitenzeit und mindestens
20 abgeschlossene Sitzungen bereits zu dieser Zeit. Bestehende registrierte
Emittentenindikationen haben dagegen häufig keine verifizierte Originalzeit;
ihre bisherige 300-Sekunden-Grenze betrifft ausschließlich den erfolgreichen
Empfang. Eine fällige Positionsprüfung datiert diesen Preis nicht nachträglich.
Negative Originalstatuspunkte bleiben mit eigener Zeit sichtbar; ihre
Fortgeltung wird nicht erfunden. Die genaue Eingangsqualifikation steht im
[Regelvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-entry-review-v1).

Die einmalige [zentrale PC-Aktivierung](LINUX_LAUNCHER.md#einmaliger-übergang-auf-die-indikative-positionsprüfung)
schaltet den Umfang für bestehende offene Positionen gemeinsam ein.
`REVIEW_NOTIFICATIONS_ENABLED=false` hält neue externe Reviewzustellungen aus;
die Hinweise sind im Arbeitsbereich gespeichert. Vorhandene andere
Benachrichtigungen können gemäß ihrer bereits eingerichteten Konfiguration
weiterlaufen. Aktivierung und Softwareupdate erteilen keine neue Providerfreigabe
und versenden keine Testnachricht.

Die Betriebsanzeige unterscheidet konfigurierten Umfang, gestarteten Runner,
abgeschlossenen Zyklus und dessen tatsächliche Positions-/Datenproblemzähler.
Ein geladener Umfang mit null ausgewerteten Positionen belegt keine
Depotabdeckung; ein Fehler oder Datenproblem bleibt sichtbar. Die passive
Detailansicht liest vorhandene Bewertungen und löst weder Beschaffung noch
Regelauswertung aus. Nach Aktivierung wird der nächste reguläre Prüflauf
abgewartet; tägliche Prüfklicks sind nicht erforderlich.

Die strenge B04/B57-Strecke und `HEBELTRADER_CONFIRMED_BASELINE` werden dadurch
nicht aktiviert. B58 bleibt ohne geeignete reale Originalstatuslieferung offen.
B05 benötigt weiterhin seine eigenständigen belegten Produkttermine und das
feste Ausstiegslisting; ein fehlender BID ist für diese Fristregel kein Hindernis.

### Erweiterter eigener Umfang V2

`INDICATIVE_ENTRY_V2` / `indicative-entry-review-v2` ergänzt den
[V2-Regelvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-review-rule-v2)
mit den vorhandenen verzögerten Quellen (eigene gemeinsame Quellzeit,
höchstens 30 Minuten) und aktuellen Originalproduktbelegen mit sichtbar
angenommener historischer Kontinuität. Die strenge 900-Sekunden-BID-Grenze und
die weiterhin fehlende B58-Originalstatusversorgung bleiben unverändert.
Beschaffungsprobleme sind getrennte Betriebsdiagnosen und löschen weder alte
Originale noch eine bestehende Verlustepisode. Bekannte Rücknahmen oder
widersprüchliche Bindungen werden nicht durch schwächere Belege übergangen.

Die unabhängige Produktfristprüfung benötigt dokumentiertes Produktende,
letzten Handelstag und ausdrücklich gewähltes Ausstiegslisting. Vorliegende
Originalseiten können einmalig über den kontrollierten Dateiimport übernommen
werden. Ein Börsentagskalender liefert ausschließlich eine Datumserinnerung;
individuelle Handelszeiten/B20 und nicht belegte Kalenderjahre bleiben offen.
Einstands- und Fristergebnisse haben getrennte Zähler. Vorübergehend fehlende
Fristgrundlagen pausieren ausstehende Meldungen, während ein belegter Vollverkauf
diese beendet. Externe Reviewzustellung bleibt im vorbereiteten PC-Übergang aus.

Die [zentrale V2-Aktivierung](LINUX_LAUNCHER.md#erweiterung-der-vorhandenen-installation-auf-v2)
übernimmt vorhandene Positionen gemeinsam; tatsächliche Depotabdeckung wird
anschließend aus einem beobachteten PC-Zyklus beurteilt. Eine vollständige
Hebeltrader-Baseline, B06 oder B08 folgen daraus nicht.

### Softwarestand und Betriebsnachweis

Git-Tag und Paketversion kennzeichnen den Quellstand; Schema, Image und geladene
Konfiguration sind separate Betriebsnachweise. Vor Deployment sichern, beide
Migrationen prüfen, zuerst Renderer-Health bestätigen und anschließend die
vollständige bestehende Stack-Konfiguration verwenden. Keine Löschung von Volumes,
kein Datenbank-Stamp und kein stiller Rollback.

Der Release-PR enthält lokale Prüfergebnisse und GitHub-CI. Die noch offene
JPMorgan-Liveabnahme und fehlende neue Produktabdeckung sind dort ausdrücklich
aufgeführt und dürfen nicht aus grünen Unit-Tests abgeleitet werden.

<a id="lesende-depot-datenversorgungsdiagnose"></a>
## Lesende Diagnose der tatsächlichen Depotversorgung

Prüfstand: Main `c7db441de36297a98d47cdf28c64b4e5d9994692` / v1.5.52, 20.11.2026. [Fachlicher Datenvertrag und Einzelbelege](../reviews/DEPOT_DATA_SUPPLY_2026-11-20.md); [einziger nächster Arbeitsauftrag](../planning/PRODUCT_BACKLOG.md#naechster-schnitt). Diese Anleitung ist vorbereitet und lokal auf Syntax und Readerverträge geprüft; eine Ausführung auf dem Nutzer-PC ist damit nicht behauptet.

Es existiert bereits ein geeigneter GET-Inventarread: `/api/v1/market-data/positions/quote-coverage`. Er ermittelt alle offenen, nicht stornierten Positionen aus der DB, einschließlich Positionen ohne Quelle; es gibt keine feste Sechserliste und keinen Bezug nur auf letzte Rulechecks. Er liefert Produkt- und Listingidentitäten sowie source selection. Vor/nach Sammlung werden dessen IDs und Mapping-/Auswahlbezüge verglichen. Kein neuer API-Endpoint, Runner oder Produktionscode ist nötig.

Quellbelege: [Inventar-API](../../backend/app/features/market_data/api/quote_coverage.py), Z.51–60; [Projektion](../../backend/app/features/market_data/service/position_quote_coverage.py), Z.131–158; [Positionsinventur](../../backend/app/features/market_data/persistence/position_quote_coverage.py), Z.52–114; [Quellenread](../../backend/app/features/market_data/persistence/quote_coverage.py), Z.25–130. Ausschließlich SELECTs und reine Projektion, keine Provideraufrufe/flush/commit. Die Coverage-Projektion besitzt mehrere kurze Reads, keinen global atomaren Snapshot.

Die dortige Eigenschaft `monitoring_usable` ist **kein** Nachweis der B58-/V2-Regelqualität: sie schließt ausdrücklich STALE/REFERENCE_ONLY/TIMESTAMP_UNKNOWN ein (`service/position_quote_coverage.py:209–229`). Die tatsächlichen gespeicherten Regelbewertungen bleiben maßgeblich.

### Kopierbarer Abruf im vorhandenen Programmordner

Der Befehl wählt nur den bestehenden Backendcontainer; er startet/baut/ändert keinen Dienst. Keine Providerbestätigung, keine Regelausführung, kein Import. Der JSON-Bericht bleibt außerhalb des Repositories in einem privaten neuen Verzeichnis. Keine Rohdatei als PR-Anhang veröffentlichen. Falls Docker/Backend nicht läuft, ist das Ergebnis „Diagnose nicht zugänglich“; nicht für diese Diagnose einen neuen Stack starten.

```bash
(
set -euo pipefail
cd "$HOME/Boerse/trading-workspace-app"
umask 077
TW_DIAG_DIR=$(mktemp -d "$HOME/trading-workspace-diagnose.XXXXXX")
~/.local/bin/trading-workspace status > "$TW_DIAG_DIR/installation.txt" 2>&1
docker compose --env-file docker/.env -f docker/compose.yml exec -T backend \
  python - > "$TW_DIAG_DIR/monitoring-private.json" <<'PY'
import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

import httpx
from pydantic import TypeAdapter, ValidationError

from app.features.market_data.service.position_quote_coverage import PositionQuoteCoverageReport
from app.features.position_monitoring.service.hebeltrader_loss_read import LossStatusReport
from app.features.position_monitoring.service.hebeltrader_original_bid_contracts import (
    HebeltraderOriginalBidReport,
)
from app.features.position_monitoring.service.hebeltrader_target_contracts import (
    HebeltraderTargetsReport,
)
from app.features.position_monitoring.service.indicative_entry_read import IndicativeStatusReport
from app.features.position_monitoring.service.product_deadline_review_read import (
    ProductDeadlineStatusReport,
)
from app.features.trade_position.service.hebeltrader_coverage import HebeltraderCoverage

BASE = "/api/v1/position-monitoring"
INVENTORY = "/api/v1/market-data/positions/quote-coverage"
READS = (
    ("indicative-entry", BASE),
    ("product-deadline-review", BASE),
    ("hebeltrader-original-bid", BASE),
    ("hebeltrader-targets", BASE),
    ("hebeltrader-loss", BASE),
    ("hebeltrader-evidence", "/api/v1/trade-position"),
)
INVENTORY_RESPONSE = TypeAdapter(PositionQuoteCoverageReport)
POSITION_RESPONSES = {
    "indicative-entry": TypeAdapter(IndicativeStatusReport),
    "product-deadline-review": TypeAdapter(ProductDeadlineStatusReport),
    "hebeltrader-original-bid": TypeAdapter(HebeltraderOriginalBidReport),
    "hebeltrader-targets": TypeAdapter(HebeltraderTargetsReport),
    "hebeltrader-loss": TypeAdapter(LossStatusReport),
    "hebeltrader-evidence": TypeAdapter(HebeltraderCoverage),
}

def now():
    return datetime.now(UTC).isoformat()

async def get(client, path, params=None):
    started = now()
    try:
        response = await client.get(path, params=params)
        if response.status_code != 200:
            return {"read_at": started, "http_status": response.status_code,
                    "read_error": "DIAGNOSTIC_READ_UNAVAILABLE"}
        body = response.json()
        if not isinstance(body, dict):
            return {"read_at": started, "http_status": 200,
                    "read_error": "JSON_OBJECT_REQUIRED"}
        return {"read_at": started, "http_status": 200, "body": body}
    except (httpx.HTTPError, ValueError) as error:
        return {"read_at": started, "read_error": type(error).__name__}

def canonical_uuid(value):
    if not isinstance(value, str):
        raise ValueError("UUID_STRING_REQUIRED")
    parsed = UUID(value)
    if parsed.int == 0 or value.lower() != str(parsed):
        raise ValueError("CANONICAL_NONZERO_UUID_REQUIRED")
    return str(parsed)

def valid_time(value):
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value).utcoffset() is not None
    except ValueError:
        return False

def validate_inventory(snapshot):
    if snapshot.get("http_status") != 200 or snapshot.get("read_error"):
        return [], ["INVENTORY_READ_UNAVAILABLE"]
    body = snapshot.get("body", {})
    try:
        INVENTORY_RESPONSE.validate_python(body)
    except (ValidationError, ValueError, TypeError):
        return [], ["INVENTORY_RESPONSE_SCHEMA_INVALID"]
    summary, rows = body.get("summary"), body.get("items")
    if (not isinstance(summary, dict) or not isinstance(rows, list)
            or type(summary.get("open_positions")) is not int
            or summary["open_positions"] < 0
            or summary["open_positions"] != len(rows)
            or not valid_time(body.get("assessed_at"))
            or body.get("assessment_scope") != "STORED_OBSERVATIONS_NOT_LIVE_VALUATION"
            or body.get("execution_usable") is not False):
        return [], ["INVENTORY_SCHEMA_OR_COUNT_INVALID"]
    validated, position_ids, trade_ids = [], set(), set()
    for row in rows:
        if not isinstance(row, dict):
            return [], ["INVENTORY_ITEM_NOT_OBJECT"]
        try:
            clean = dict(row)
            for key in ("position_id", "trade_id", "warrant_id"):
                clean[key] = canonical_uuid(row.get(key))
            for key in ("selection_id", "warrant_listing_id", "mapping_id"):
                if key not in row:
                    raise ValueError("INVENTORY_FIELD_MISSING")
                clean[key] = canonical_uuid(row[key]) if row[key] is not None else None
            for key in ("selected_provider", "selection_status", "mic", "currency"):
                if key not in row or (row[key] is not None and not isinstance(row[key], str)):
                    raise ValueError("INVENTORY_FIELD_INVALID")
            if ("mapping_version" not in row or
                    (row["mapping_version"] is not None and
                     (type(row["mapping_version"]) is not int or row["mapping_version"] < 1))):
                raise ValueError("INVENTORY_MAPPING_VERSION_INVALID")
        except (ValueError, AttributeError, TypeError):
            return [], ["INVENTORY_IDENTITY_SCHEMA_INVALID"]
        if clean["position_id"] in position_ids or clean["trade_id"] in trade_ids:
            return [], ["INVENTORY_DUPLICATE_POSITION_OR_TRADE"]
        position_ids.add(clean["position_id"])
        trade_ids.add(clean["trade_id"])
        validated.append(clean)
    return sorted(validated, key=lambda row: row["position_id"]), []

def bindings(rows):
    keys = ("position_id", "trade_id", "warrant_id", "selection_id",
            "selected_provider", "warrant_listing_id", "mapping_id",
            "mapping_version", "selection_status", "mic", "currency")
    return sorted(tuple(str(row.get(key)) for key in keys) for row in rows)

def marker(snapshot):
    body = snapshot.get("body", {})
    if (snapshot.get("http_status") != 200 or snapshot.get("read_error")
            or type(body.get("cycle_running")) is not bool
            or not valid_time(body.get("last_cycle_started_at"))
            or not valid_time(body.get("last_cycle_completed_at"))):
        return None
    keys = ("last_cycle_started_at", "last_cycle_completed_at", "cycle_running")
    return tuple(body.get(key) for key in keys)

def validate_position_read(snapshot, row, name):
    if snapshot.get("http_status") != 200 or snapshot.get("read_error"):
        return
    body = snapshot.get("body", {})
    try:
        POSITION_RESPONSES[name].validate_python(body)
        if any(canonical_uuid(body.get(key)) != row[key]
               for key in ("trade_id", "position_id")):
            raise ValueError("WRONG_POSITION")
        clocks = ("read_at",) if name in {
            "indicative-entry", "product-deadline-review", "hebeltrader-loss"
        } else ("read_started_at", "read_completed_at")
        if name == "hebeltrader-original-bid":
            clocks += ("evaluated_at",)
        if any(not valid_time(body.get(key)) for key in clocks):
            raise ValueError("INVALID_READ_TIME")
        if name in {"indicative-entry", "product-deadline-review", "hebeltrader-loss"}:
            if "latest_assessment" not in body:
                raise ValueError("MISSING_ASSESSMENT_FIELD")
            assessment = body["latest_assessment"]
            if assessment is not None and (not isinstance(assessment, dict)
                    or not isinstance(assessment.get("reasons"), list)
                    or not all(isinstance(reason, str) for reason in assessment["reasons"])
                    or not valid_time(assessment.get("evaluated_at"))):
                raise ValueError("INVALID_ASSESSMENT")
    except (ValidationError, ValueError, AttributeError, TypeError):
        snapshot["read_error"] = "POSITION_RESPONSE_SCHEMA_OR_IDENTITY_INVALID"

async def main():
    result = {"schema": "PRIVATE_MONITORING_READBACK_2026_11_20",
              "started_at": now(), "requests": "GET_ONLY",
              "global_atomic_snapshot": False}
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000",
                               timeout=15, trust_env=False,
                               follow_redirects=False) as client:
        result["runtime_before"] = await get(client, BASE + "/runtime/status")
        result["refresh_before"] = await get(client, "/api/v1/market-data/refresh/status")
        result["inventory_before"] = await get(client, INVENTORY)
        initial, initial_errors = validate_inventory(result["inventory_before"])
        result["inventory_before_errors"] = initial_errors
        result["positions"] = []
        for number, row in enumerate(initial, 1):
            entry = {"label": f"P{number:02d}", "identity_private": row, "reads": {}}
            for name, prefix in READS:
                read = await get(
                    client, f"{prefix}/trades/{row['trade_id']}/{name}",
                    {"position_id": row["position_id"]})
                validate_position_read(read, row, name)
                entry["reads"][name] = read
            result["positions"].append(entry)
        result["inventory_after"] = await get(client, INVENTORY)
        result["refresh_after"] = await get(client, "/api/v1/market-data/refresh/status")
        result["runtime_after"] = await get(client, BASE + "/runtime/status")
    final, final_errors = validate_inventory(result["inventory_after"])
    result["inventory_after_errors"] = final_errors
    valid_inventory = not initial_errors and not final_errors
    before_marker = marker(result["runtime_before"])
    after_marker = marker(result["runtime_after"])
    result["coverage_checks"] = {
        "inventory_schema_ids_and_counts_valid": valid_inventory,
        "positions_requested": len(initial),
        "nonempty_portfolio_observed": valid_inventory and bool(initial),
        "same_inventory_and_bindings": valid_inventory and bindings(initial) == bindings(final),
        "same_idle_cycle_markers": (
            before_marker is not None and before_marker == after_marker
            and before_marker[2] is False),
        "auxiliary_reads_available": all(
            result[key].get("http_status") == 200 and not result[key].get("read_error")
            for key in ("runtime_before", "refresh_before", "refresh_after", "runtime_after")),
        "all_position_reads_available": valid_inventory and bool(initial) and all(
            read.get("http_status") == 200 and not read.get("read_error")
            for entry in result["positions"] for read in entry["reads"].values()),
    }
    checks = result["coverage_checks"]
    result["collection_status"] = (
        "INVENTORY_UNAVAILABLE_OR_INVALID" if not valid_inventory else
        "NO_OPEN_POSITIONS_NO_COVERAGE_EVIDENCE" if not initial else
        "AUXILIARY_READS_UNAVAILABLE" if not checks["auxiliary_reads_available"] else
        "POSITION_READS_INCOMPLETE" if not checks["all_position_reads_available"] else
        "CHANGED_OR_UNVERIFIED_COLLECTION_WINDOW" if not (
            checks["same_inventory_and_bindings"] and checks["same_idle_cycle_markers"]) else
        "COMPLETE_PASSIVE_READBACK_NOT_RULE_QUALIFICATION")
    result["completed_at"] = now()
    print(json.dumps(result, ensure_ascii=False, indent=2))

asyncio.run(main())
PY
printf '%s\n' "$TW_DIAG_DIR"
)
```

Quellcodeprüfung dieses Snippets ist möglich; seine Ausführung auf dem Nutzer-PC ist damit nicht behauptet. Der Launcherstatus enthält Installationsstand und prüft bestehende versiegelte Images; `/health` allein liefert keine Softwareversion.

Die Antwortprüfung verwendet mit `TypeAdapter` die vorhandenen Response-Dataclasses der installierten Anwendung. Die benannten Response-Dataclasses sind in v1.5.51 und v1.5.52 vorhanden; maßgeblich ist der jeweils installierte Vertrag. Die Imports definieren Typen, Funktionen und lokale SQLAlchemy-Metadaten, öffnen jedoch keine Datenbanksitzung und führen keinen Provider-/Commandpfad aus. Die Validierung ersetzt die Originalantwort nicht. Zulässige `null`-Bewertungen und fachliche MISSING-/UNSUITABLE-Befunde bleiben erhalten; ein unvollständiges HTTP-200-Objekt wird als Diagnosefehler markiert. Das ist eine Transport-/Strukturprüfung, keine fachliche Regelqualifikation.

### Auswertungsregeln

1. Beide Inventarreads erfolgreich und mit dem vorhandenen Responsevertrag validiert, vollständige Object-/List-/Countstruktur und kanonische nichtleere UUIDs, `summary.open_positions == len(items)`, keine doppelten Positions- oder Tradekennungen. Bei fehlerhaftem Inventar werden **keine** Einzelposition-URLs gebildet; IDs werden vor Verwendung validiert und kanonisiert. Jede Position bekommt alle **sechs** vorgesehenen, mit ihren Responseverträgen geprüften Read-Ergebnisse oder einen ausdrücklich benannten Diagnosefehler. Runtime- und Refreshstatus vor/nach der Sammlung müssen ebenfalls zugänglich sein; sonst lautet der Sammelstatus `AUXILIARY_READS_UNAVAILABLE`. Null offene Positionen erhält `NO_OPEN_POSITIONS_NO_COVERAGE_EVIDENCE`; `all_position_reads_available` bleibt false. `latest_assessment=null` kann ein gültiger Readerbefund sein, bedeutet aber fehlende Bewertung und keine Regelabdeckung.
2. Inventar/Bindings und idle Zyklusmarker unverändert: Sammlung ohne beobachteten Zykluswechsel. Das ist keine globale DB-Snapshotgarantie. Bei Wechsel den betroffenen Teil lesend wiederholen, keine laufenden Dienste pausieren. Persönliche Buchungs-/Belegänderungen und Kursrefresh können weiter stattfinden.
3. Für V2: `latest_assessment` vorhanden, `rule_version=indicative-entry-review-v2`, ausgewerteter Zeitpunkt/basis/source sichtbar. `latest_assessment.reasons`, `document_readiness` und aktive `DATA_UNAVAILABLE`-Episode gemeinsam lesen; Erwerbserfolg ist nicht Dokumenteignung. `document_readiness` enthält lediglich Versuchsergebnis/-zeit/-backoff. Es weist **keine** aktuelle KID-Revision, Parserfassung oder erfolgreiche lokale Neubewertung nach.
4. Für v1.5.52-Wirkung: installierten Stand bestätigen, letzte reguläre Bewertung nach Update heranziehen; wegfallender falscher Terms-Mismatch muss von weiter bestehendem echten Datums-/Underlying-Mismatch unterschieden werden. Keine Quote/Einstandsfreigabe allein aus verschwundenem Fehlercode.
5. Für strenge Regeln: Original-BID-/Maßstab-/Kalenderchecks und `hebeltrader-loss.activation_status`/Qualifikationsreferenzen auswerten. Ein reiner `FRESH_QUOTE` oder `monitoring_usable=true` ist keine B58-Eignung. Für B06 sind **beide Pflichtreads** nötig: `hebeltrader-targets` für historische Ziele/Targetzustand sowie `/api/v1/trade-position/trades/{id}/hebeltrader-evidence?position_id=...` für historischen persönlichen Basiswerteinstand, Währung, Ausführungsbezüge und Belegabdeckung. Der zweite Read liefert je Beitrag die Abdeckung/Verknüpfung in `items`/`execution_links` und die wirtschaftliche `valuation_basis`; er gibt die rohe `declaration.underlying_trades` nicht aus. Nur bei konkretem Bedarf an den originalen Einzel-BUY-Belegen zusätzlich dessen vorhandenen `/history`-GET lesen. Fehlende Grundbelege und bekannt unimplementierte Folgestopanteile getrennt ausweisen.
6. Öffentlich ausschließlich Tabelle `Pseudonym | Regel | belegt/teilweise/nicht auswertbar | konkrete Fehlcodes | Kategorie Quelle/Mapping/Import/Verarbeitung/Konfiguration/Fachentscheidung | Owner | Beschaffung`. Private `identity_private`-Map und vollständige Originalreadantworten im privaten Diagnoseverzeichnis belassen. Bei Unterstützung nur über einen ausdrücklich privaten Kanal bereitstellen; Beträge/IDs vor Repositoryübernahme entfernen.

Gezielt ergänzend, nur wenn die vorhandenen Reader eine Ursache nicht liefern: passiver `hebeltrader-targets/qualification-preview` für konkrete historischen Quellen-/Skalenprobleme; `hebeltrader-sessions` für genaue Zeitraumlücken; privater bereits vorhandener Logauszug zum dokumentierten Acquisitionversuch für HTTP403 versus Timeout. Diese sind kein unbedingter weiterer Dauerschritt.

### Grenze des vorhandenen Product-Readbacks bei unklarem Datumswiderspruch

**Genau ein bestehender GET enthält passende Product-Owner-Teilbelege:** der bereits verpflichtend gelesene `/api/v1/position-monitoring/trades/{id}/product-deadline-review?position_id=...`. Seine `latest_assessment.product_evidence` nennt `product_document_revision_id`, `product_end_on`, `payment_on`, `payment_qualifier` und `current_terms_date_role`. Diese Werte beschreiben die **damals ausgewertete** Product-Owner-Evidenz, nicht den unabhängig aktuellen KID-Head. `product_evidence.recorded_at` ist das Maximum von KID-, Exitwahl- und Listingterms-Speicherzeiten; es darf nicht als alleinige KID-Reparsezeit bezeichnet werden (`product/service/review_evidence.py:463–506`; `position_monitoring/service/product_deadline_review_read.py:85–99`).

Der aktuelle Main hat **keinen HTTP-GET**, der den aktuellen KID-Head einschließlich `parser_version`, originalem `retrieved_at` und eigenem `recorded_at` vollständig zurückgibt. `ProductReviewEvidenceReader.current_for_review` ist nur ein interner passiver Ownerread und enthält selbst kein Parserfeld. `latest_document` (`product/service/review_evidence.py:55–74`) liest per SELECT die passende `ProductReviewDocumentModel`-Revision samt Parserfassung, ist aber nicht als GET exponiert. Der vorhandene `deadline-listing-terms/current`-GET betrifft einen anderen Belegtyp und ersetzt diesen KID-Nachweis nicht.

Deshalb gilt: Bleibt nach bestätigt installiertem v1.5.52 und nachfolgendem regulärem Zyklus ein unklarer Terms-Mismatch bestehen, reicht diese GET-Sammlung für die **aktuelle Parserursache** nicht. Dann ist genau ein gezielter passiver KID-Metadatenread beim bestehenden Product-Owner erforderlich (nur Produkt-/Revision-/Terms-ID, Parserfassung, `recorded_at`, `retrieved_at`, Dokumenthash und begrenzte `facts.issues`/Datumsrollen; keine Originalbytes). Dieser Zusatz ist hier **weder ausgeführt noch als vorhandener API-Pfad erfunden**. Ohne ihn bleibt die konkrete Reparsefrage ausdrücklich offen. Kein neuer Spec-, Command-, Import- oder Beschaffungspfad ist Bestandteil des Snippets.

Der ergänzte B06-Reader ist anhand `trade_position/api/hebeltrader_evidence.py:165–175` und `service/hebeltrader_evidence.py:479–511` als `REPEATABLE READ READ ONLY`, ohne Netzwerk/Commands, mit abschließendem Rollback geprüft.

## Git-Versionierung

`VERSION`, `backend/pyproject.toml`, `frontend/package.json` und dessen Lockdatei
werden im Release-PR gemeinsam fortgeschrieben. Der Workflow `Version tag` setzt
`v<VERSION>` erst, wenn Backend, Frontend und End-to-End am selben aktuellen
`main`-Commit vollständig erfolgreich sind. Vorhandene Tags werden niemals
verschoben. Der Workflow übernimmt keine PRs und führt kein Deployment aus.

## Umstieg alter Paket-Overlays (1.4.3)

Ein bestehender Paket-Stack darf nicht allein durch Austausch seiner Compose-Liste
aktualisiert werden: Laufzeitwerte können von `.env` abweichen. Für die geprüfte
Vier-Service-Topologie beschreibt [Linux Deployment](LINUX_DEPLOYMENT.md#reviewed-legacy-issuer-migration-143)
die getrennte Vorbereitung und den Wechsel mit Erhalt tatsächlicher Einstellungen,
Volumes, absolutem Stuttgart-Pfad, Sicherungen und Sandbox. Der ursprüngliche
Checkout bleibt bestehen. Der private Erhaltungs-Overlay gehört anschließend zur
vollständigen Betriebskonfiguration; ihn nicht ins Repository oder Support kopieren.
Ein erfolgreicher Wechsel ersetzt keine JPMorgan-Produktprüfung und keinen
Nachweis vollständiger Monitoring-Zyklen nach dem Cacheaufbau.
