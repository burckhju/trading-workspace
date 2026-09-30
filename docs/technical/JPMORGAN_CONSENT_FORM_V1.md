# JPMorgan: verifiziertes Bestätigungsformular

> Historischer Paketstand. Für den Git-Stand ab 1.4.0 gelten die
> [aktuelle Betriebsanleitung](ISSUER_MONITORING_OPERATIONS.md) und die
> [Release-Notizen](../releases/V1.4.0-ISSUER-MONITORING.md).

Stand 30.09.2026. Paket `jpmorgan-consent-form/1.1.0-rc.1`.
Ersetzt den Einrichtungsablauf aus `monitoring-resume/1.0.0-rc.1`.
Keine Datenbankmigration und keine Änderung der Kurs-/Handelsregeln.

## Belegte Ursache

Der Serverbericht `jpmorgan-setup-diagnose-v1.1-VMqyDuB5.json` vom
30.09.2026 10:48:59 UTC zeigt diese Elemente:

| Element | Belegte Bedeutung |
|---|---|
| `CheckBoxNotUsResidential` | Wohnsitz Deutschland/Österreich, kein Wohnsitz USA, keine US-Person |
| `CheckBoxTermsOfService` | Kenntnisnahme und Zustimmung zu den Bedingungen |
| `CheckBoxSaveSettings` | Einstellungen merken, laut Beschriftung für 30 Tage |
| `a#AcceptButton` | „Einverstanden“, anfangs unsichtbar |

Die Checkbox-Inputs sind ebenfalls visuell verborgen. Der neue Ablauf prüft
Typ, eindeutige ID und exakten zugeordneten Erklärungstext. Er klickt nur auf
das tatsächlich zugeordnete sichtbare Label und prüft danach den nativen
Auswahlzustand. Kein `force=True`, keine DOM-Manipulation, kein direktes Setzen
von Zustimmungs-Cookies. Der frühere Rollenfilter für „Akzeptieren“ war für
dieses Formular ungeeignet.

Der 2,416 Sekunden dauernde Diagnoseabruf enthielt keinen OOM-/Prozesslimitfehler.
Der vorherige einmalige Timeout ist damit nicht abschließend erklärt. Es werden
keine Zeitlimits, Browserkennungen oder Netzwerkregeln gelockert.

## Installation

Archiv im Projektverzeichnis entpacken und ausführen:

```bash
bash jpmorgan-consent-form-v1.1/run.sh install
```

Versionsgeprüfte Dateien werden gesichert und ersetzt. Backend und Renderer
werden gebaut und kurz neu gestartet; alle neun bestehenden Compose-Overlays
bleiben aktiv. Das bestehende Zustandsvolume bleibt erhalten. Überwachung und
Telegram bleiben konfiguriert; nach dem Neustart wird ein abgeschlossener
Überwachungszyklus geprüft. Dieser Patch sendet keine weitere Testnachricht.
Er führt anschließend nur die Vorbereitung durch und akzeptiert nichts.

Der Audit prüft neue Backend-Modulhashes sowie die direkt im Renderer
installierten Einrichtungs- und Hilfsmodule. Bei lokalen Abweichungen stoppt
der Installer. Für diese Paketversion ausschließlich diesen neuen Installer
und dessen `verify` benutzen; alte Pakete nicht erneut darüber entpacken.

Erwartete Ausgaben: `RUNTIME_VERIFIED`, `MONITORING_ACTIVE`,
`FORM_VERIFIED=JPMORGAN_CHECKBOX_FORM_V1`, `ACCEPT_CONTROL_COUNT=1` und
`ACCEPT_TEXT=Einverstanden`. Eine vor Auswahl der Erklärungen unsichtbare
Schaltfläche ist im Vorschau-Bericht zulässig.

## Explizite Zustimmung durch den Betreiber

Den gesamten bei `TERMS_TEXT` angegebenen Text lesen. Nur wenn der Betreiber
die Bedingungen akzeptieren möchte und **sämtliche** Angaben der
Wohnsitz-/US-Person-Erklärung auf ihn zutreffen, führt er selbst aus:

```bash
bash jpmorgan-consent-form-v1.1/run.sh accept \
  --confirm-sha256 HASH_DES_GEPRUEFTEN_TEXTES \
  --confirm-de-at-residence-and-non-us-person \
  --remember-30-days
```

Der letzte Schalter ist eine ausdrückliche Auswahl von „Einstellungen merken
(für 30 Tage)“. Er darf weggelassen werden; dann wird das Feld nicht ausgewählt.
Die tatsächliche Gültigkeit des Zustands bestimmt weiterhin die Website.
Der Code darf keine Wohnsitz-/Personeneigenschaften aus Sprache, Hostname oder
IP-Adresse ableiten. Ohne den Erklärungsschalter stoppt er vor dem Browserstart.
Die Installation oder ein hochgeladener Text ist keine Zustimmung.

Der Hash wird vor allen Erklärungen und erneut vor „Einverstanden“ geprüft.
Der ursprüngliche Filter in v1 erfasste die tatsächlich gerenderte Großschreibung
und das verzögert erscheinende Cookie-Banner nicht. Die folgende Korrektur v1.1
ist für den Betrieb erforderlich; die Zustimmung mit v1 wurde nicht gespeichert.

Nach dem Klick muss die Produktidentität auf der Seite stimmen. Ein zweiter,
frischer Browserkontext muss dieselbe Produktidentität mit dem erhaltenen
Zustand erneut verifizieren. Erst danach wird der Zustand atomar und privat
unter `/state` gespeichert. Erfolg:
`CONSENT_STORED_PRODUCT_VERIFIED`, `accepted=true`,
`eligibility_confirmed_by_operator=true`. Keine Cookies oder Sessiondaten
als Bericht weitergeben.

## Route und Kurs danach separat prüfen

Die Speicherung erzeugt noch keine Kursroute. Der nächste reguläre Discovery-
Versuch nutzt den gespeicherten Zustand. Bisher betrug das Retry-Intervall eine
Stunde. `bash jpmorgan-consent-form-v1.1/run.sh acceptance` liest den Stand,
erzwingt aber keinen Retry. Für DE000JZ91459 gibt es keine Testposition; niemals
eine künstliche Position zur Abnahme anlegen.

JPMorgan-Kurse bleiben indikativ, Datum/Zeitzone werden nicht erfunden.
Morgan-Stanley-Seitenzugriff bleibt ein eigener offener Punkt.

## Prüfstand und Release

Für den ursprünglichen Formularstand bestanden 91 gezielte Tests; diese waren
bezüglich der dynamischen Textdarstellung unvollständig. Siehe Livebefund und
erweiterten Prüfstand für v1.1 unten.
Regressionen umfassen geänderte Erklärungstexte, fehlende Betreiberbestätigung,
versteckte native Checkboxen, überprüfte Auswahlzustände, geänderte Terms-Hashes
und Zustandsverifikation in einem zweiten Kontext. Paketprüfungen simulieren
Docker; echte Zustimmungs-/Produktprüfung steht auf JMBbot noch aus. Vollständige
Projektgates und Git-Release bleiben getrennt von diesen gezielten Prüfungen.
Black/Mypy sind in der lokalen Testumgebung weiterhin nicht installiert.

## Korrektur v1.1: nachgewiesene dynamische Anzeigeelemente

Livebericht `jpmorgan-consent-trace-v1-mGTX8lwP.json`, 30.09.2026 13:42 MESZ:
Die ersten beiden Textprüfungen bestanden; die dritte Prüfung nach Setzen der
Häkchen stoppte vor dem finalen Klick. Zusätzlich erschienen ausschließlich
`EINVERSTANDEN` sowie der öffentliche Cookie-Bannertext hinter `Back to top`.
Kein finaler Klick, kein neu gespeicherter Zustimmungszustand.

Version `jpmorgan-consent-form/1.1.0-rc.1` berücksichtigt nur die beiden
nachgewiesenen Button-Schreibweisen am Formularende und den exakt beobachteten
Cookie-Bannertext unmittelbar nach den unveränderten Erklärungen und dem Footer.
Alle anderen Textzusätze, Änderungen in Bedingungen/Erklärungen sowie unbekannte
Bannertexte bleiben Bestandteil des Hashes. Es wird kein anderer Hash freigegeben.
Ein nachladendes sichtbares Cookie-Banner wird über „Alle ablehnen“ geschlossen;
bleibt es nach zwei Versuchen sichtbar, stoppt das Setup.

Die drei tatsächlich aufgezeichneten Textstände ergeben mit v1.1 denselben
vollständigen geprüften Text und dieselbe bereits bestätigte Prüfsumme:
`5b91cb6c6b389362df312b3f4fdf72fddb36e407a67f1c73b6d4433c011f3d1b`.
Die Fixture `tests/fixtures/jpmorgan/consent-presentation-20260930.json` enthält
diese öffentlichen Textstände und den SHA-256 des Ursprungsberichts.

Nur `jpmorgan-consent-form-v1.1/run.sh` für `install`, `prepare`, `accept`,
`verify` und `acceptance` verwenden. Die Optionen für `accept` bleiben gleich.
Der Installer setzt den installierten v1-Stand voraus, sichert ersetzte Dateien,
stoppt bei fremden Änderungen und aktualisiert Backend/Renderer mit den neun
bestehenden Compose-Dateien. Monitoring und Telegram bleiben in der aktivierten
Konfiguration. Das Wiederanlaufen wird geprüft; es wird keine zusätzliche
Telegram-Testnachricht verschickt. `install` nimmt keine Bedingungen an.

114 gezielte Tests bestanden, einschließlich der echten drei Textstände,
echter Bedingungsänderungen, geänderter Erklärungen, unbekannter Textzusätze,
nachladendem Cookie-Banner und Zustandsspeicherung nach Wiederverwendungsprüfung.
Ruff für das geänderte Modul und den neuen Test bestanden. Live-Zustimmung mit
v1.1 und anschließende Discovery-Abnahme stehen bis zum Betreiberlauf noch aus.
