# Position Monitoring, Alerting and Outbound Notifications

## Status und Feature-Zuordnung

Status: **Technical Review**.

Für diese Capability ist im aktuell gepflegten zentralen Feature-Katalog keine freigegebene FT-Nummer reserviert. Daher wird bewusst keine neue FT-Nummer erfunden. Die spätere Produktplanung kann den Schnitt entweder als ein Feature oder als getrennte Features für Monitoring/Alerting und Notification Delivery aufnehmen.

## Zielarchitektur

```text
Trade / Position / TradePlan / Trade Management
                    |
                    v
            Position Monitoring
                    |
                    v
                Alert Domain
                    |
                    v
           Notification Domain
                    |
                    v
             Delivery Adapter
                    |
                 Telegram
```

Telegram ist ausschließlich outbound Delivery Adapter. Monitoring kennt weder Telegram noch einen konkreten Market-Data-Provider. Alert Detection, Notification Creation und Delivery besitzen getrennte Verantwortungen und Persistenz-/Transaktionsgrenzen.

## V1 Scope

V1 überwacht offene beziehungsweise überwachungsrelevante Positionen deterministisch auf den aktuellen Stop und Target 1. Die effektiven Schwellen werden aus dem bestehenden Trade-Management-Zustand übernommen; falls keine Management-Änderung existiert, dient die zugehörige TradePlan-Version als Fallback. Es wird keine Trading-Regel dupliziert.

Plan- und Management-Schwellen sind Underlying-Preisniveaus. Die vorhandene providerneutrale Market-Data-Abstraktion bietet hierfür aktuell completed-daily Underlying-Daten. V1 bewertet deshalb abgeschlossene Daily-Low/High-Beobachtungen. Intraday- oder Minutenüberwachung wird nicht durch Warrant-Quotes vorgetäuscht.

Missing, stale oder technisch fehlerhafte Market Data erzeugen keinen fachlichen Stop-/Target-Alert. Diese Fälle werden als Monitoring-/Observability-Ergebnis behandelt.

## Alert- und Deduplication-Semantik

Alerts sind persistierte fachliche Entitäten mit Position-/Trade-Bezug, Alert-Typ, Severity, Rule-Key, Reason, beobachtetem Wert, Schwelle, Market-Data-Zeitpunkt und Detection-Zeitpunkt.

Der persistierte Rule-State bildet die Edge-Semantik ab:

```text
clear -> triggered    : genau ein neuer Alert
triggered -> triggered: kein Duplikat
triggered -> clear    : aktiver Alert wird resolved
clear -> triggered    : neuer Alert ist wieder möglich
```

Eine Änderung der fachlichen Schwelle beendet den bisherigen aktiven Zustand und startet die Evaluation für die neue Schwellenidentität nachvollziehbar neu.

## Notification und Delivery

Aus einem Alert wird pro `Alert + Channel + Destination` höchstens eine Notification erzeugt. Alert-Status und Delivery-Status sind getrennt.

Die persistente Delivery-Sequenz lautet:

1. Alert/Rule-State committen.
2. Notification in separater Transaktion erzeugen und committen.
3. Delivery Attempt als `IN_PROGRESS` persistieren und committen.
4. Erst danach den externen Adapter aufrufen.
5. Delivery-Ergebnis separat persistieren.
6. Stale `IN_PROGRESS` Attempts nach Restart als retryable failure übernehmen und Pending Notifications später erneut zustellen.

Retries erzeugen weder einen neuen Alert noch eine zweite Notification. Die Anzahl der Versuche ist begrenzt.

## Telegram

Telegram ist outbound-only. Keine Commands, Callback-Buttons, Kauf-/Verkaufsaktionen oder Trade-/Execution-Änderungen werden angenommen.

Konfiguration erfolgt über bestehende Pydantic-Settings/Environment-Mechanismen. Das Bot Token ist `SecretStr` und wird nicht persistiert oder geloggt. Relevante Variablen sind in `backend/.env.example` dokumentiert.

Telegram 429, Timeout und 5xx werden als retryable behandelt; permanente Konfigurations-/4xx-Fehler sind non-retryable. Tests verwenden ausschließlich Fake-/Mock-Adapter und senden keine realen Telegram-Nachrichten.

## Scheduling und Betrieb

Der Monitoring-Service ist trigger-unabhängig. Ein schlanker opt-in Background Runner wird im FastAPI-Lifespan gestartet, wenn `TRADING_WORKSPACE_POSITION_MONITORING__ENABLED=true` gesetzt ist. Er verwendet die bestehende EODHD-Implementierung nur über den providerneutralen `LatestCompletedDailyPriceProvider`-Contract.

Der Runner isoliert Cycle-Fehler, unterstützt graceful shutdown und loggt unter anderem geprüfte Positionen, erzeugte/deduplizierte/resolved Alerts, Market-Data-Fehler sowie Notification-/Delivery-Ergebnisse.

Für kontrollierte Produktions-Smoke-Tests steht zusätzlich der One-shot-Entry-Point `monitor-positions-once` zur Verfügung. Er führt exakt einen persistenten Runtime-Zyklus aus und gibt ausschließlich nicht-sensitive Betriebszähler als JSON aus. Wenn Telegram aktiviert ist, verweigert der Befehl standardmäßig die Ausführung; ein realer Versand muss mit `--allow-telegram` ausdrücklich freigegeben werden. Erwartungsparameter (`--expect-alerts`, `--expect-deliveries`, `--expect-delivery-failures`) machen Success-, Dedup- und Failure-Smoke-Checks automatisiert auswertbar.

Beispiel für einen bewusst freigegebenen ersten Trigger:

```bash
monitor-positions-once --allow-telegram --expect-alerts 1 --expect-deliveries 1
```

Der unveränderte zweite Lauf kann anschließend mit `--expect-alerts 0 --expect-deliveries 0` die Edge-Deduplication qualifizieren. Der Befehl enthält und loggt keine Bot Tokens oder Chat IDs.

## Workspace-Sichtbarkeit

Das Trade Management besitzt eine read-only Alert-Sicht. `GET /api/v1/alerts/trades/{trade_id}` liefert persistierte fachliche Alerts inklusive der zugehörigen channel-neutralen Notification- und letzten Delivery-Zustände. Der Endpoint erzeugt oder verändert weder Alerts noch Notifications.

Die Trade-Management-Seite zeigt diese Informationen direkt an der betroffenen Position: Alert-Typ, OPEN/RESOLVED, beobachteter Wert, Schwelle, Market-Data- und Detection-Zeitpunkt sowie den Delivery-Zustand pro Notification. Ein fehlgeschlagener Telegram-Versand wird daher sichtbar, ohne den fachlichen Alert als fehlgeschlagen darzustellen.

Die UI bietet bewusst keine Buy-/Sell-Aktion und keine Telegram-Steuerung. Der nächste Nutzerschritt bleibt die fachliche Prüfung im Trade Management.

## Persistenz

Alembic-Migrationen `20260903_0030` und `20260903_0031` führen Alert-, Monitoring-State-, Notification- und Delivery-Attempt-Persistenz inklusive Recovery-Status ein. Die Migrationen laufen in der bestehenden PostgreSQL-Migrationskette.

## Verifikation / Definition of Done

Automatisiert qualifiziert sind insbesondere:

- kein Trigger -> kein Alert,
- erster Trigger -> Alert,
- unveränderter Triggerzustand -> kein zweiter Alert,
- clear/reset und erneuter Trigger -> neuer Alert möglich,
- fehlende/stale Market Data -> kein Trading-Alert,
- Alert -> genau eine Notification,
- Delivery Success und Failure,
- retryable Failure und begrenzte Retries,
- persistiertes `IN_PROGRESS` vor externem Call sowie Restart-Recovery,
- Telegram Request-/Error-Mapping ohne echten API-Aufruf,
- expliziter End-to-End-Qualifikationstest `tests/integration/backend/test_position_monitoring_notification_e2e.py`: Detection -> Alert -> Notification -> Delivery und Wiederholung ohne Duplikat sowie Failure bei erhaltenem Alert,
- read-only Alert-API und Trade-Management-Darstellung von fachlichem Alert- und getrenntem Delivery-Zustand.

## Expliziter Nicht-Scope

- Intraday-Underlying-Monitoring ohne providerneutralen Underlying-Quote-Contract,
- Near-Threshold-/beliebige Kursbewegungsregeln,
- Rule Builder,
- globale Alert-Inbox, Acknowledge-/Resolve-Aktionen durch den Nutzer und zusätzliche Notification-Provider,
- Telegram inbound/bidirektional,
- Order Execution oder automatische Kauf-/Verkaufsentscheidung,
- Kafka/RabbitMQ oder ein generischer Message Bus.
