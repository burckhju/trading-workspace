# Hebeltrader: ausschließlich ablesbare Nutzereingaben

Stand: 12. September 2026. Diese Eingaberegel ersetzt den zuvor beschriebenen
manuellen Band-/Puffer-Workflow in `HEBELTRADER_RECONSTRUCTED_V1.md`.

## Bedienung

Nach der vorhandenen Basiswertauswahl lädt das Panel bestätigte Hebeltrader-
PDF-Importe dieses Basiswerts. Der Nutzer wählt nur die gewünschte Ausgabe.
Einstieg, Stopp, beide Ziele, GD200, GD50, Währungen und Dateinachweis werden aus
der konkreten ExternalObservationVersion übernommen und schreibgeschützt gezeigt.
Aktie und Optionsschein bleiben getrennte Preisachsen. Weitere Ausgaben werden
seitenweise geladen; es wird kein Nutzer zur Eingabe technischer IDs aufgefordert.

Es gibt keine Formulareingaben für B, Stopp-Puffer, Tickgröße, geschätzte IV,
Volatilitätsfenster, Wechselkursannahmen, Zinssätze oder Handelssitzungslisten.
Unbekannte Parameter werden weder als versteckte Konstanten ergänzt noch aus
Omega linear hochgerechnet. Auch ein Preissturz des Calls ersetzt keine Bewertung.

## Fehlende Daten

Fehlende oder widersprüchliche Quellenwerte bleiben sichtbar. Es wird keine
Ergänzung aus dem Gedächtnis verlangt. Das Quellen-CRV kann ohne GD200 berechnet
werden; die GD200-Diagnose und aktuelle Einstiegsprüfung sind dann nicht verfügbar.
Fehlen Originalmarken vollständig, entsteht kein automatisch berechneter Zielpreis.
Die nicht eindeutig rekonstruierte B-Formel wird nicht durch eine andere ersetzt.

Der Import muss bereits bestätigt sein. Unbestätigte Zeilen, andere Basiswerte,
andere Workspaces und überholte Beobachtungsversionen werden nicht übernommen.
Dateiname, Ausgabe, Quellenversion und Datei-Prüfwert sind in der Ansicht ersichtlich.
Vollständige Artikeltexte werden durch die neue Lese-API nicht ausgegeben.

## Aktuelle Kurse: optional, nur direkt ablesbar

Für die historische Prüfung sind keine zusätzlichen Eingaben nötig. Erst die
freiwillige aktuelle Einstiegsprüfung bietet Geldkurs, Briefkurs, die tatsächlich
angezeigte Kurszeit und den angezeigten Kursanbieter an. Alle Felder dürfen leer
bleiben. Keine Gleichsetzung von veröffentlichtem Kurs, letztem Trade und Geld-/
Briefkurs. Eine unvollständige Taxierung wird nicht mit geschätzten Werten ergänzt.
Die Zeit wird über ein normales Datum-/Uhrzeitfeld in Browser-Lokalzeit eingegeben;
ISO-Zeit, Prüfzeitpunkt, Währung und technische Referenzen ergänzt die Anwendung.

Auch die Zielhistorie darf unbekannt bleiben. Sie wird dann nicht als „noch kein
Ziel erreicht“ interpretiert. Die Auswahl ist nur anhand eines tatsächlich
sichtbaren, vollständigen Kursverlaufs zu treffen. Fehlende aktuelle Taxierung,
fehlende Zielhistorie oder ungeklärte Quellenwarnungen ergeben eine historische
Prüfung ohne aktuelle Einstiegsfreigabe und ohne vorgefertigten neuen TradePlan.
Eine frische Taxierung verjüngt keine alte Analyse: die vorhandene 7-Tage-Sperre
und die Quote-Freshness-Prüfung bleiben unverändert.

Ein zulässiger aktueller Entwurf benötigt weiterhin die separate fundamentale
Prüfung und die ausdrückliche Bestätigung des Nutzers. Kein automatisches Approval,
keine Brokerorder, kein Überschreiben vorhandener Positionen.

## API

- `GET /api/v1/trade-plans/strategies/hebeltrader/sources?underlying_id=...`
  liest bis zu 50 bestätigte Quellen; `next_offset` zeigt weitere Ergebnisse an.
- `POST /api/v1/trade-plans/strategies/hebeltrader/source-preview` benötigt nur
  `underlying_id` und `source_version_id` für die historische Prüfung. Die Server-
  Anwendung löst alle Originalmarken selbst auf. Modell-/Markenüberschreibungen
  werden mit HTTP 422 zurückgewiesen.

Die bisherigen mathematischen Low-level-Endpunkte bleiben kompatibel, sind aber
kein manuelles Benutzerformular. Künftige Oberflächen für Call-Szenarien oder
Management dürfen ihre nicht ablesbaren Eingaben ausschließlich aus belegten
Datenadaptern beziehen; ohne solche Daten bleibt die jeweilige Funktion unverfügbar.
Diese Änderung implementiert keinen neuen Livefeed und keinen Kalenderprovider.
