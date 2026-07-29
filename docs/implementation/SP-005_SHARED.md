# SP-005 Shared

## Ziel

Bereitstellung fachlich neutraler, backendweit wiederverwendbarer Bausteine ohne Vorwegnahme eines Features.

## Umgesetzter Umfang

- rekursive Typdefinitionen für JSON-kompatible Werte
- unveränderlicher UUID-basierter `Identifier`
- UTC-sichere Zeitfunktionen
- testbarer `Clock`-Vertrag mit produktiver `SystemClock`
- zentrale Normalisierung und Validierung erforderlicher Texte
- Unit-Tests für alle implementierten Shared-Bausteine

## Architekturgrenzen

Nicht umgesetzt wurden:

- fachliche Enumerationen
- Geld- oder Währungsobjekte
- Feature-spezifische Value Objects
- API-, Repository- oder Event-Verträge
- Frontend-Shared-Komponenten

Für diese Komponenten fehlen in den verbindlichen Dokumenten konkrete fachliche beziehungsweise technische Verträge. Eine Implementierung würde Annahmen oder Platzhalter erzeugen.

## Verwendung

Shared-Code darf keine Abhängigkeit auf `features`, `providers`, `database` oder FastAPI besitzen. Feature-Code darf die hier definierten Bausteine verwenden, sofern sie den jeweiligen Feature-Verträgen entsprechen.
