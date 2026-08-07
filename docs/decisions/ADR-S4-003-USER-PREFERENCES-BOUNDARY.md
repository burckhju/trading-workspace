# ADR-S4-003: User Preferences als eigenständige Feature-Grenze

## Status
Angenommen

## Kontext
Benannte Analyseansichten sollen geräteübergreifend speicherbar sein, gehören jedoch nicht zur Marktanalyse-Domain. Im aktuellen System existiert noch keine Authentifizierung, aber ein etablierter Actor-Header-Vertrag.

## Entscheidung
Ein additives Feature `user_preferences` speichert benannte, workspace- und actor-scoped JSON-Präferenzen. Die Marktanalyse kennt dieses Modul nicht. Der REST-Vertrag verwendet `X-Actor-ID`; im aktuellen Single-User-Modus wird `local-user` als expliziter Fallback verwendet.

## Konsequenzen
- Keine Vermischung von Analysefachlogik und UI-Präferenzen.
- Spätere Authentifizierung kann die Actor-ID liefern, ohne das Preferences-Modell zu ändern.
- Der aktuelle Fallback ist nicht für einen Mehrbenutzerbetrieb geeignet und muss vor dessen Einführung entfernt werden.
