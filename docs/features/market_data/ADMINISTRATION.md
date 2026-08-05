# Provider-Mapping-Administration und Betriebsstatus

Provider-Mappings sind administrative Zuordnungen zwischen einem bestehenden Listing und einer externen Providerkennung. Sie ändern weder Listing-Stammdaten noch fachliche Identitäten.

## Lebenszyklus

1. Anlegen oder Ändern erzeugt ein deaktiviertes Mapping.
2. Validierung ist ein expliziter administrativer Schritt und aktiviert das Mapping.
3. Deaktivierung löscht keine Historie.
4. Jede Änderung wird als Audit Event am Aggregat `PROVIDER_MAPPING` dokumentiert.

## Betriebsstatus

Der Statusendpunkt zeigt ausschließlich nicht geheime Informationen: Aktivierung, Konfigurationszustand, Tageslimit, Sicherheitsreserve, lokale Nutzung, Restbudget, Minutenlimit und Burst-Kapazität. API-Key, URL-Parameter und Providerantworten werden niemals ausgegeben.

Der Status ist prozesslokal. Sprint 3 bleibt auf eine koordinierte Backendinstanz begrenzt.
