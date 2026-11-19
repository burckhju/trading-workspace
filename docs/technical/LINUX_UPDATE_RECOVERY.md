# Wiederaufnahme eines vor Apply fehlgeschlagenen verwalteten Updates

`scripts/retry-linux-update.py` ist ein separat ausgelieferter Supporthelfer für
einen eng begrenzten Fehlerzustand: Der verwaltete Launcher hat den Zielrelease
bereits ausgecheckt, seine Vorbereitung ist jedoch vor `prepared` und vor jedem
Apply-Schritt abgebrochen. Die vier bisherigen Container und der versiegelte
Installationszustand müssen weiterhin unverändert und gesund sein.

Der konkrete Anlass war ein `ReadTimeoutError` von `files.pythonhosted.org` beim
`pip install` im Backend-Imagebuild für v1.5.50. Der parallele Frontend-Build wurde
daraufhin abgebrochen. Die bisherige v1.5.49 lief weiter; sämtliche neuen
Vorbereitungs-/Apply-/Migrationsmarker fehlten. Das belegt noch nicht die
Voraussetzungen jeder späteren Wiederholung: Der Helfer prüft sie unmittelbar
vor einer Änderung erneut auf dem PC.

## Bereitstellung und Aufruf

Den qualifizierten Helfer aus dem in der Übergabe angegebenen unveränderlichen
Commit beziehen, seine dort angegebene SHA256 prüfen und **außerhalb** des
installierten App-Checkouts speichern, beispielsweise unter
`~/Downloads/retry-linux-update.py`. Der App-Checkout und der installierte
Starter werden durch die Bereitstellung des Helfers nicht geändert. Keine
ungeprüfte Datei von einem beweglichen Branch verwenden.

Als bisheriger Installationsbenutzer, ohne `sudo`:

```bash
python3 ~/Downloads/retry-linux-update.py retry v1.5.50 e335a42fd8380d494eb7a0639f57bc6ee2ff476e
```

Der Tag und vollständige Commit benennen den bereits veröffentlichten
Anwendungsrelease. Der Supporthelfer ist ein gesondertes Werkzeug; er benötigt
keinen neuen Anwendungsrelease und verschiebt keinen vorhandenen Tag. Andere
Basisverzeichnisse werden über `--base` angegeben. Bestehende Einstellungen,
Käufe, Verkäufe und Providerfreigaben werden aus der vorhandenen Installation
übernommen. Es gibt keine neue Zugangsdatenabfrage.

## Kontrollierter Ablauf

1. Unter der gemeinsamen `update.lock` die privaten kanonischen Pfade,
   Eigentümer und Dateirechte sowie den tatsächlich offenen Vorgang prüfen.
   `previous-state`, `previous-root`, `previous-revision`, `target-revision`,
   `current-state`, Git-Origin, sauberer Checkout, Release-Tag und `VERSION`
   müssen konsistent sein. Ein ausstehendes `current-state.new` ist eine Sperre.
2. Die bekannten Support-, Launcher- und Deploymentbytes prüfen. Die für diesen
   Übergang verwendeten Compose-/Sandbox-/Deploymentverträge müssen in alter
   und neuer Revision bytegleich sein. Das Werkzeug ist kein allgemeiner
   Wiederanlauf für geänderte Deploymentverträge.
3. Das vollständige alte Siegel einschließlich vorhandener Aktivierungsmetadaten,
   die vier gesunden alten Container, ihre Images, Datenbankidentität,
   Compose-Herkunft und effektiven Daten-/Konfigurationsbindungen prüfen. Die
   Baseline des **fehlgeschlagenen neuen** Prepare-Versuchs muss weiterhin zur
   aktuellen Runtime passen. Die Baseline des alten abgeschlossenen Deployments
   wird nicht als heutige Containeraufnahme verwendet.
4. Nur den sauberen Git-Quellcheckout mit `git checkout --detach` auf die bereits
   installierte alte Revision zurückstellen. Kein Force-Checkout, kein Reset,
   kein Containerwechsel und kein Datenbankrestore. Die alte Installation und
   ihre unveränderten Container danach nochmals vollständig prüfen.
5. Den nachweislich vor Apply gescheiterten Vorgang nachvollziehbar abschließen:
   den äußeren `pending`-Datensatz atomar als `aborted-before-apply` im bisherigen
   Run aufbewahren. Originalverzeichnis, Konfiguration, Quellenarchiv,
   `operation.log` und sonstige Diagnosebelege bleiben erhalten. Der Helfer
   schreibt **keinen** neuen `current-state` und fälscht kein erfolgreiches
   Deployment.
6. Die Sperre freigeben und den unveränderten installierten Launcher mit genau
   dem angegebenen Tag und Commit starten. Dieser nimmt seine Sperre erneut,
   wiederholt sämtliche normalen Prüfungen und führt einen frischen
   Prepare-/Backup-/Apply-/Migrations-/Verifikationsablauf durch. Nur der
   ursprüngliche Launcher finalisiert den erfolgreichen Installationszustand.

Eine andere Operation im kurzen Übergabefenster führt zur normalen Ablehnung
durch den Launcher. Es wird keine Schutzprüfung abgeschaltet oder umgangen.

## Wechsel auf einen neuen veröffentlichten Ersatzrelease

Wenn derselbe Zielbuild wiederholt scheitert und ein gezielt korrigierter Release
qualifiziert und veröffentlicht wurde, ergänzt `replace` den bisherigen
`retry`-Einstieg. Der Helfer wird weiterhin außerhalb des App-Checkouts aus dem
in der Übergabe gebundenen Commit mit überprüfter SHA256 bezogen.

```text
python3 /PFAD/ZUM/retry-linux-update.py replace FAILED_TAG FAILED_SHA NEW_TAG NEW_SHA --base BASISVERZEICHNIS
```

Die konkrete Übergabe füllt alle Werte aus. Beim vorliegenden Fall bleibt der
fehlgeschlagene Zielbezug v1.5.50/e335a42fd8380d494eb7a0639f57bc6ee2ff476e,
während der Ersatzrelease v1.5.51 mit seinem veröffentlichten Commit benannt wird.
Die weiterhin installierte Revision wird aus dem alten versiegelten Zustand
gelesen; sie wird nicht als Nutzereingabe neu behauptet.

Zusätzlich zu allen bisherigen Prüfungen liest `replace` unter derselben Sperre
den neuen Tag frisch aus dem bekannten Origin und holt nur diesen Tag regulär,
ohne Force. Lokaler Tag, vollständiger neuer SHA, `VERSION`, Abstammung vom
fehlgeschlagenen Ziel sowie bytegleiche qualifizierte Deploymentverträge über
installierte, fehlgeschlagene und neue Revision müssen übereinstimmen. Der
aktuelle Checkout bleibt ausschließlich auf installierte oder fehlgeschlagene
Revision begrenzt. Ein lokaler Tag allein genügt nicht als Veröffentlichungsbeleg.

Erst nach diesen Prüfungen folgt die bestehende Quellrückkehr und Archivierung
des nachweislich vor Apply gescheiterten Vorgangs. Dessen `target-revision` und
Deploymentmetadaten bleiben unverändert auf das fehlgeschlagene Ziel gebunden;
der neue Auditbeleg nennt zusätzlich den Ersatzrelease. Der Original-Launcher
wird anschließend mit dem neuen Tag/SHA ausgeführt. Der Helfer schreibt weiterhin
keinen `current-state`; eine neue fehlgeschlagene Vorbereitung erhält ihren
eigenen normalen Vorgang. `retry` behält seinen bisherigen Ablauf für dasselbe Ziel.

Der [Reparaturrelease v1.5.51](../releases/V1.5.51-RELIABLE-BACKEND-BUILD.md)
beschreibt den konkreten Buildbefund, die begrenzte Korrektur und die zugehörigen
Qualifikationsgrenzen.

## Abbruchgrenzen

`prepared`, `apply-started`, `backups-verified`, `migration-started` oder
`deployed` im fehlgeschlagenen neuen Deployment schließen diese Wiederholung
aus. Auch Symlinks an solchen Markerpfaden zählen als vorhandene Marker.
Beschädigte Siegel, abweichende Container, unbekannte Werkzeugbytes, lokale
Quelländerungen und widersprüchliche Zustandszeiger führen zum Stopp.

Ein Abbruch vor dem Archivieren von `pending` bleibt gesperrt und nachvollziehbar.
Auch ein bereits auf die alte Revision zurückgestellter sauberer Checkout wird
nur nach denselben vollständigen Prüfungen akzeptiert. Nach dem kontrollierten
Abschluss des Fehlversuchs ist die alte Installation wieder konsistent; falls
die Übergabe an den normalen Launcher unterbrochen wird, gilt dessen regulärer
`update TAG SHA`-Einstieg.

Ein erneuter Buildfehler behält einen **neuen** offenen Vorgang. Sobald Apply
begonnen hat, gehört die Reparatur ausdrücklich nicht in diesen Helfer.
Phasenmarker, versiegelte Eingaben und Sicherungen werden nicht manuell gelöscht
oder neu geschrieben. Es gibt keine pauschale Wiederholung einer Migration.

Private Prozessausgaben bleiben in privaten Diagnosedateien. Nur bereinigte
Fehlerauszüge weitergeben; keine vollständigen `.env`-, Inspect-, Konfigurations-
oder Sicherungsdateien veröffentlichen.

## Qualifikation und anschließender Betrieb

Gezielte Tests prüfen Herkunft, Siegel, Pfade, Sperren, Containeridentität,
Unterbrechungen und die Wiederholung durch den unveränderten Launcher. Der
vorhandene Docker-/PostgreSQL-Wegwerftest ergänzt einen absichtlich gescheiterten
ersten Build und die anschließende echte Wiederholung. Datenbank-/Consentdaten,
Konfiguration, alte Fehlerbelege und der funktionierende tägliche Starter werden
dabei nachgewiesen; externe Laufzeitverbindungen bleiben abgefangen.

Konkreter Toolcommit, SHA256 und die regulären CI-Ergebnisse werden in der
zugehörigen qualifizierten Übergabe gebunden. Tests belegen keinen bereits
erfolgten Wiederanlauf auf einem Nutzer-PC.

Nach erfolgreichem Update zunächst `trading-workspace status` prüfen und erst
danach die einmalige V2-Aktivierung aus der
[v1.5.50-Release-Notiz](../releases/V1.5.50-INDICATIVE-V2-AND-PRODUCT-DEADLINES.md)
ausführen. Der nächste beobachtete Hintergrundlauf belegt die tatsächliche
Depotabdeckung; eine erfolgreiche Softwareinstallation allein ersetzt ihn nicht.
