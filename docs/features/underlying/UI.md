# FT-001 UI Specification

## Navigation

```text
Stammdaten
└── Basiswerte
```

## Listenansicht

Spalten:

- Name,
- primäre Notierung: Ticker · Markt · Währung,
- ISIN,
- WKN,
- Status,
- letzte Änderung.

Funktionen:

- gemeinsames Suchfeld für Name, Ticker, ISIN und WKN,
- Filter aktiv/deaktiviert,
- Filter Markt und Währung,
- deaktivierte Basiswerte standardmäßig ausblenden.

## Anlage

Geführter Ablauf:

1. Grunddaten: Basiswertart „Aktie“, Name, ISIN, WKN.
2. Primäre Notierung: Markt, Ticker, Handelswährung.
3. Prüfung und Speichern.

Die Anlage von Underlying und primärer Notierung erfolgt atomar. Bei Fehlern bleibt der eingegebene Inhalt erhalten.

## Detailseite

Register oder Abschnitte:

- Übersicht,
- Identifikatoren,
- Notierungen,
- Verwendungen,
- Änderungshistorie.

## Deaktivierung

Die Bestätigung erklärt, dass der Basiswert in neuen Auswahllisten verborgen, historisch aber erhalten bleibt.

## Löschung

Bei Referenzen zeigt die UI mindestens Anzahl und Typ der Verwendungen und bietet Deaktivierung statt Löschung an.

## Auswahl in anderen Features

Darstellung:

```text
Siemens AG
SIE · Xetra · EUR
```

Andere Features dürfen Stammdaten nur anzeigen und über einen Link zur zentralen Detailseite führen.

## Bedienregeln

- UUID wird nicht regulär angezeigt.
- Fehlermeldungen benennen fachliche Ursache und Lösung.
- Keine gemeinsame Auswahlliste für Aktien und Optionsscheine.

## Datenqualität und Verifikation

Liste und Detailseite zeigen Lebenszyklus und Datenqualität getrennt. `DRAFT`, `COMPLETE` und `VERIFIED` werden nicht mit `INACTIVE` vermischt. Die Aktion „Verifizieren“ ist nur bei vollständigen Datensätzen verfügbar. Nach einer relevanten Stammdatenänderung wird eine bestehende Verifikation sichtbar zurückgesetzt.

## Nebenläufigkeitskonflikt

Bei einem Versionskonflikt überschreibt die UI keine Serverdaten. Sie zeigt die inzwischen gespeicherte Version und bietet Neuladen, Verwerfen oder erneutes Anwenden nach Sichtprüfung an.

## Referenzauswahl

Markt und Währung werden über durchsuchbare kontrollierte Auswahllisten erfasst; Freitexteingaben sind ausgeschlossen.
