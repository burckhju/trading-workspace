# FT-006: versionierte Quellenqualitaet — isolierter Kernnachweis

25.10.2026. Dieser Bericht ist ein technischer Nachweis, kein zweites Backlog.
Aufgabenstatus bleiben im [Product Backlog](../planning/PRODUCT_BACKLOG.md).
Der abhaengige Gesamtweg ist [PR #276](https://github.com/burckhju/trading-workspace/pull/276).

## Ausgangspunkt und Parallelgrenze

Basis ist Main `27098f173caf56bd0fd11f2ff6bc600a7e8e633a`, Tree
`68065a3f8944e8ea9526d3b154f46c961662d1ef`, Softwareversion 1.5.15.
#276 wurde waehrend der Untersuchung unabhaengig mit Main integriert und fuer
v1.5.16 vorbereitet. Seine laufenden Commits werden hier nicht ueberschrieben.
Dieser getrennte Folgeschnitt aendert weder #276 noch Navigation, Runtime-Defaults,
API, Persistenz, Governancefreigaben, Migrationen, Dependencies oder Workflows.

## Reproduzierter Befund

Die bestehenden Owneradapter uebernehmen die Preisqualitaet unveraendert in den
Snapshot. Persistierte Preise verwenden VALID; der Rechner 1.0.0 vergleicht dort
jedoch mit GOOD, dem Wortschatz seiner Analyseausgabe. Vollstaendige synthetische
VALID-Reihen liefern deshalb LIMITED. Ein kuenstlicher GOOD-Quellwert liefert
hingegen GOOD. Quellenwarnungen sind im alten Rechner nicht in den Ergebnisnotes
sichtbar. Dies ist ein reproduzierter Rechenvertrag, kein Schadensnachweis am Depot.

Das historische Modell wird nicht repariert, indem gehashte Quellwerte in GOOD
umgeschrieben oder alte Ausgaben nachtraeglich aufgewertet werden.

## Implementierter, ausdruecklich begrenzter Zusatz

`calculator_v1_0_1.py` verwendet die unveraenderte 1.0.0-Arithmetik und berechnet
in der eigenstaendigen Modellversion 1.0.1 die Quellenqualitaet aus Originalfakten:
Nur ausreichend viele ausgewaehlte Preise, durchgehend VALID und ohne Warnungen
oder fehlende ausgewaehlte Preiswerte ergeben im Rechenkern GOOD. INSUFFICIENT hat
Vorrang; andere oder unbekannte Quellflags bleiben LIMITED. Quellenwarnungen und
abweichende Flags werden mit Datum in Notes erhalten. Auch fehlerhafte leere
Warnungseintraege werden nicht als sauberer Input ausgegeben.

Kennzahlen, Rundung, Kriterien, Schwellen und die Rohsnapshotzeilen bleiben gleich.
Zeitabhaengige Aktualitaet bleibt Aufgabe des vorhandenen Application Service;
dieser reine Rechenkern behauptet keine Kalenderabdeckung oder aktuelle Kurse.

`model_versions.py` dispatcht nur nach ausdruecklich uebergebener Modell-ID und
exakter Version. Es gibt keinen latest-Default und keinen Fallback unbekannter
Identitaeten. 1.0.0 ruft weiterhin unveraendert den alten Rechner auf. Der bisherige
produktiv verwendete Import, seine Versionskonstante und Governanceprovenienz
bleiben unberuehrt. Die Softwareversion wird nicht erhoeht.

## Tatsaechlich ausgefuehrte lokale Tests

Kein vollstaendiger Repositorycheckout: Git-Clone scheiterte an DNS-Aufloesung.
Die benoetigten fuenf Domainquelldateien wurden einzeln gelesen und ihre vollstaendigen
Bytes gegen die von GitHub gelieferten Git-Blob-Identitaeten abgeglichen:

| Datei unter `backend/app/features/analysis/domain/` | Git-Blob |
|---|---|
| calculator.py | `7ece74da68639cd26c5bbc73fcdf8b65dac426b8` |
| indicators.py | `4977db3f88aa666734bab16dc768c3315b16fa92` |
| models.py | `da35d64b8cf12000e63a7b251808a755fe4427ab` |
| enums.py | `8c6a105177466beb3941c28c8f6d1c5dad2ef170` |
| errors.py | `a37be4c3182010fabcca10ca04617fe940893933` |

Laufzeit: Python 3.13.5, pytest 9.0.2. Das ist kein Python-3.12-CI-Nachweis.
13 Quellenvertragsfaelle wurden zuerst mit unveraendertem 1.0.0-Rechner geprueft:
**6 fehlgeschlagen, 7 bestanden**. Gegenueber der finalen Testdatei wurde in der
isolierten Rotkopie ausschliesslich der Import des zu pruefenden Rechners auf den
alten Rechner umgebunden; die ausgefuehrten Assertions sind gleich.
Die sechs Fehler sind zwei VALID-Positivfaelle (CLOSE/ADJUSTED_CLOSE), der falsche
GOOD-Quellflag und drei fehlende Warnungsdiagnosen. Bei den Warnungsfaellen war
LIMITED bereits vorhanden; nur dessen Warnungsnachweis fehlte.

Mit dem Zusatz bestehen **31/31 Domainfaelle**, ohne Skip oder Retry. Darin sind die
13 obigen Faelle enthalten, nicht zusaetzlich zu zaehlen. Weitere Faelle sichern
Einzelfehler, fehlende Adjusted-Closes, INSUFFICIENT samt Warnung, unveraenderte
Kennzahlen/Kriterien/Inputs, historischen 1.0.0-Hash und getrennten 1.0.1-Hash sowie
den exakten Versionsdispatch und Ablehnung unbekannter Modelle/Versionen.
Python-AST-Pruefung und Whitespacepruefung bestanden. Ruff, Black und mypy sowie
die vollstaendigen Backend-/Frontend-/E2E-Gates wurden lokal nicht ausgefuehrt.
Aktuelle PR-CI muss separat an ihren tatsaechlichen Head/Checkout/Tree gebunden werden.

## Noch nicht geliefert — B07 bleibt offen

Dies ist nur der implementierte und lokal getestete versionierte Rechenkern,
**keine vollstaendige produktive FT-006-Korrektur**. Die bisherigen Owner verwenden
weiter 1.0.0. Es gab weder PostgreSQL- noch Browserausfuehrung dieses Zusatzes.

Vor Integration sind Run, Retry und Verify auf den gespeicherten exakten
Modellvertrag zu binden, fuer Listing- und Referenzowner gemeinsam. Der vorhandene
Provenienzlistener ist auf den alten Runtimevertrag zugeschnitten; 1.0.1 darf keine
falsche genehmigte 1.0.0-Referenz erhalten. Neue Snapshots muessen ihre wirkliche
Version hashen; historische Versionen, Hashes, Ergebnisse und Quellen bleiben
unveraendert. Kein impliziter Wechsel einer aktiven Governanceversion.

Erst der danach erneut ausgefuehrte reale Browser/API/PostgreSQL-Gesamtweg mit
GOOD-Referenz, Negativfaellen und allen unveraenderten Ownergates kann die offene
B07-Grenze aus #276 schliessen. Keine technische Gesamtuebergabereife, Fachabnahme,
wirtschaftliche Ueberlegenheit, Veroeffentlichung, Installation oder Aktivierung
wird aus diesen Domaintests abgeleitet.
