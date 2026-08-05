# FT-001 – Validierungen

## Zweck

Schritt 9 schließt die Validierung an der HTTP-Grenze, ohne fachliche Regeln aus der Domain zu duplizieren.

## Transportvalidierungen

- Namen werden getrimmt und müssen 1 bis 200 Zeichen enthalten.
- Ticker werden getrimmt und müssen 1 bis 32 Zeichen enthalten.
- Währungscodes müssen aus genau drei Buchstaben bestehen.
- Versionen müssen größer oder gleich 1 sein.
- Suchtexte dürfen höchstens 200 Zeichen enthalten.
- `offset` muss mindestens 0 sein; `limit` liegt zwischen 1 und 100.
- PATCH-Requests müssen neben der Version mindestens ein änderbares Feld enthalten.
- Unbekannte Request-Felder bleiben verboten.

## Abgrenzung

Die API prüft Form, Größe und sichere Wertebereiche. Kanonische Normalisierung, ISO-6166-Prüfziffer, WKN-Format, Dubletten, Referenzexistenz, Primärnotierungsregeln, Statusübergänge und Optimistic Locking verbleiben in Domain und Service Layer.

## Fehlerverhalten

Transportfehler werden vor einem Service-Aufruf als HTTP 422 zurückgegeben. Cross-Field-Verstöße verwenden serialisierbare Pydantic-Fehler und bleiben mit dem zentralen Fehlervertrag kompatibel.
