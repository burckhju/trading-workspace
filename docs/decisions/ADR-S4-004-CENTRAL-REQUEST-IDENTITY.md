# ADR-S4-004 – Zentrale Request-Identity-Abstraktion

## Status

Angenommen – 2026-08-06

## Kontext

Feature-Clients und einzelne FastAPI-Router lösten `X-Actor-ID` bislang selbst auf. Dadurch war die technische Herkunft einer Actor-ID über mehrere Module verteilt. Gleichzeitig existiert noch keine Authentifizierung oder Benutzerverwaltung.

## Entscheidung

Die Request-Identity wird an den technischen Anwendungsgrenzen zentralisiert.

Backend:

- `app.core.identity.RequestIdentity` ist der einheitliche Request-Vertrag.
- `get_request_identity` normalisiert `X-Actor-ID` und `X-Actor-Name`.
- Ohne Identitätsheader wird explizit `local-user` verwendet.
- `authenticated` bleibt `false`, solange kein Authentifizierungsadapter existiert.
- Feature-Router konsumieren die Identity per Dependency Injection.

Frontend:

- Der gemeinsame HTTP-Transport bezieht die Identity aus einem zentral konfigurierbaren Provider.
- Feature-Clients setzen keine festen Identity-Header mehr.
- Der aktuelle lokale Provider liefert weiterhin `local-user`.

## Konsequenzen

- Eine spätere Authentifizierung kann den zentralen Provider beziehungsweise die Backend-Dependency ersetzen, ohne Feature-Verträge zu ändern.
- Actor-Scoping für User Preferences bleibt erhalten.
- Der aktuelle Header ist kein Beweis einer authentifizierten Identität.
- Vor Mehrbenutzerbetrieb muss eine vertrauenswürdige Authentifizierungs- und Autorisierungsschicht eingeführt werden.

## Verworfene Alternativen

### Feste Actor-ID in jedem Feature-Client

Verworfen wegen doppelter Infrastruktur- und Identitätslogik.

### Sofortige Einführung eines vollständigen Auth-Systems

Verworfen, weil Authentifizierung nicht Bestandteil von Sprint 4 ist und ohne abgestimmte Sicherheitsanforderungen eine voreilige Architekturentscheidung wäre.
