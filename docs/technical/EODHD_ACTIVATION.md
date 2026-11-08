# EODHD in einer verwalteten Linux-Installation aktivieren

Dieser Wartungsweg ergänzt den täglichen Linux-Starter um genau einen
Konfigurationswechsel: EODHD mit einem bereits hinterlegten Schlüssel aktivieren.
Die Programmversion und die installierten Images bleiben gleich. Die bestehende
Installation muss vollständig und gesund sein; ein offener oder abweichender
Deploymentzustand wird zuerst unabhängig geklärt.

## Anlass und Umfang

Der Providerstatus unter `/api/v1/market-data/providers/status` unterscheidet
`enabled` und `configured`. Bei `enabled=false, configured=true` ist ein Schlüssel
hinterlegt, der Provider aber abgeschaltet. Das Speichern eines direkten
Indexmappings scheitert in diesem Stand bereits an der fehlenden Providerlaufzeit
mit HTTP 503. Der Schlüsselwert und seine Providerberechtigung sind daraus nicht
abzuleiten.

Der einzige erlaubte Unterschied der effektiven Compose-Konfiguration ist:

    TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED: false → true

Alle übrigen Einstellungen, Schlüssel, Datenbindungen, Ports, Images und
Schutzparameter werden auf Gleichheit geprüft. Die bisherigen versiegelten
Dateien bleiben erhalten. Der normale Starter und der bisherige Migrationshelfer
werden nicht geändert; deren Schutzprüfungen bleiben wirksam.

Der neue Zustand enthält eine eigene Kopie der Konfiguration, die belegte alte
Containeraufnahme, die geprüfte neue Compose-Konfiguration und das Werkzeug.
Die Änderung wird als eigener Vorgang unter dem bestehenden Zustandsordner
vorbereitet. Erst nach erfolgreicher Anwendung wechselt `current-state` auf
diesen Vorgang.

## Vorhandene Automatik ausdrücklich berücksichtigen

EODHD selbst startet keinen eigenen Scheduler. Eine bereits eingeschaltete
Kursaktualisierung oder Positionsüberwachung kann den Provider jedoch nach dem
Backendstart unmittelbar verwenden. Eine eingeschaltete Telegramzustellung kann
dabei neue oder bereits ausstehende Benachrichtigungen zustellen.

`auto_configure=false` verhindert die automatische Mappinganlage; es verhindert
nicht den Kursabruf für vorhandene aktive und validierte Mappings. Die Änderung
deaktiviert oder aktiviert keine dieser bestehenden Automatiken.

Die Vorbereitung zeigt die vier vorhandenen Einstellungen an. Die Anwendung
verlangt bei eingeschaltetem Kursabruf oder eingeschalteter Positionsüberwachung
zusätzlich `--allow-existing-automation`. Dieses Argument erlaubt das Weiterlaufen
der bereits eingerichteten Automatik einschließlich ihrer vorhandenen Zustellung.
Es erzeugt keine gesonderte Testnachricht.

## Vorbereitung auf dem PC

Die qualifizierte Datei `scripts/enable-eodhd-linux.py` beispielsweise nach
`~/Downloads/enable-eodhd-linux.py` übernehmen. Als bisheriger Installationsbenutzer
ausführen:

    python3 ~/Downloads/enable-eodhd-linux.py prepare

Der Standardordner ist `~/Boerse`; für eine abweichende vorhandene Installation
wird derselbe Basisordner wie beim Linux-Starter verwendet. Die Vorbereitung
liest die laufende Installation und schreibt ausschließlich einen neuen privaten
Vorgang. Sie baut keine Images, ersetzt keine Container und ruft keinen
Marktdatenanbieter auf.

Der angezeigte Plan nennt den installierten Commit, die eine Konfigurationsänderung
und die vorhandenen Automatiken. Die Schlüsselwerte erscheinen weder im Plan
noch in der Terminalausgabe. Private Zustandsdateien enthalten die für den Betrieb
notwendige Konfiguration und bleiben auf dem PC.

## Anwendung des geprüften Plans

Erst den von der Vorbereitung ausgegebenen, an genau diesen Vorgang gebundenen
Anwendungsbefehl ausführen. Bei aktiver Automatik gehört ihre ausdrücklich
bestätigte Weiterführung zum Auftrag. Die Anwendung liest Siegel, laufende
Konfiguration, Containeridentitäten und Images erneut. Abweichungen zum
vorbereiteten Zustand führen vor der Änderung zum Abbruch.

Während des Vorgangs ist die Anwendung vorübergehend nicht erreichbar.
Backend und Renderer werden für Datenbank- und Consent-Sicherungen angehalten.
Anschließend werden Backend, Frontend und Renderer mit ihren vorhandenen Images
und der neuen vollständigen Compose-Dateikette neu angelegt. Alle drei benötigen
die neue Herkunft in ihren Containerlabels, damit der bestehende Starter den
neuen Zustand wiedererkennt. Die Datenbank behält ihren Container und ihr Volume.

Es gibt keinen Imagebuild, keinen Imagepull und keine Datenbankmigration.
Nach dem Start werden die effektive Konfiguration, die Imageidentitäten,
Datenbindungen, Bereitschaft und der lokale EODHD-Status geprüft. Erst dann wird
der neue Zustand als installiert eingetragen. Der nächste normale Releasewechsel
übernimmt die neue Einstellung aus dessen `environment.env`.

Ein Fehler nach Beginn der Anwendung behält seinen Vorgang und den `pending`-
Marker. Es gibt keinen automatischen Rollback und keine blinde Wiederholung.
Die sichtbare Phase und das private `operation.log` sind die Grundlage einer
gezielten Wiederherstellung; bestehende Marker und Sicherungen bleiben erhalten.

## Fachliche Grenze

Ein erfolgreicher Konfigurationswechsel belegt die vorhandene EODHD-Laufzeit.
Er belegt keinen gültigen Tarif, keine konkrete Providerberechtigung und keine
vorhandene Historie. Direkte Indexreferenzen gehören nicht zum automatischen
Refreshkatalog für Basiswerte und Optionsscheine.

Für die vorhandene S&P-500-Referenz folgen deshalb weiterhin die getrennten
Oberflächenaktionen zum Speichern von `GSPC` / `INDX`, zur Mappingprüfung und
zum Import des gewählten Zeitraums. Eine Renditegrundlage wird gesondert anhand
eines Belegs bestätigt. Finanz-, Währungs-, Zeit- und Populationsregeln werden
durch diesen Wartungsweg nicht geändert.
