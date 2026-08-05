# FT-001 Requirements

| ID | Anforderung | Priorität | Akzeptanzkern |
|---|---|---|---|
| U-R-001 | Der Benutzer kann eine Aktie als Basiswert anlegen. | Must | Name, Status und primäre Notierung sind vollständig. |
| U-R-002 | Das System vergibt eine unveränderliche UUID. | Must | UUID bleibt bei Änderungen und Reaktivierung gleich. |
| U-R-003 | Basiswert und Notierung werden getrennt verwaltet. | Must | Ein Basiswert kann mehrere Listings besitzen. |
| U-R-004 | Genau eine aktive Notierung ist primär. | Must | Keine zwei primären aktiven Listings. |
| U-R-005 | Ticker und Markt sind gemeinsam eindeutig. | Must | Dublette wird vor Speicherung verständlich abgelehnt. |
| U-R-006 | ISIN und WKN sind optional und bei Angabe eindeutig. | Must | Normalisierte Dublette wird abgelehnt. |
| U-R-007 | Suche umfasst Name, Ticker, ISIN und WKN. | Must | Ein gemeinsames Suchfeld findet alle vier Arten. |
| U-R-008 | Basiswerte können deaktiviert und reaktiviert werden. | Must | Bestehende Referenzen bleiben erhalten. |
| U-R-009 | Referenzierte Basiswerte können nicht gelöscht werden. | Must | Verwendungen werden als Ablehnungsgrund angezeigt. |
| U-R-010 | Unbenutzte Fehleinträge können endgültig gelöscht werden. | Should | Nach Löschung ist keine fachliche Referenz vorhanden. |
| U-R-011 | Deaktivierte Basiswerte sind in neuen Auswahllisten standardmäßig verborgen. | Must | Filter kann sie in der Verwaltung sichtbar machen. |
| U-R-012 | Änderungen sind mit Zeitstempel und Quelle nachvollziehbar. | Must | Erzeugung und letzte Änderung sind dokumentiert. |
| U-R-013 | Andere Features besitzen nur Lesezugriff auf Stammdaten. | Must | Keine parallele Bearbeitungsmaske außerhalb FT-001. |
| U-R-014 | Optionsscheine sind als Basiswert unzulässig. | Must | Kein `WARRANT` in UnderlyingType oder Anlageformular. |
| U-R-015 | Markt und Währung stammen aus kontrollierten Referenzlisten. | Must | Freitextwerte werden abgelehnt. |
| U-R-016 | ISIN und WKN werden kanonisch normalisiert und formal validiert. | Must | Ungültige Werte können nicht gespeichert werden. |
| U-R-017 | Identifikatoren sind innerhalb des Workspace eindeutig. | Must | Normalisierte Dublette wird verhindert. |
| U-R-018 | Parallele Änderungen überschreiben sich nicht stillschweigend. | Must | Veraltete Version erzeugt Konflikt. |
| U-R-019 | Jede fachliche Änderung erzeugt einen unveränderlichen Audit-Event. | Must | Feldänderungen, Actor, Quelle und Version sind nachvollziehbar. |
| U-R-020 | Lebenszyklus und Datenqualität werden getrennt geführt. | Must | `ACTIVE/INACTIVE` und `DRAFT/COMPLETE/VERIFIED` sind unabhängig. |
| U-R-021 | Nur aktive und mindestens vollständige Basiswerte sind neu operativ auswählbar. | Must | Historische Referenzen bleiben sichtbar. |
