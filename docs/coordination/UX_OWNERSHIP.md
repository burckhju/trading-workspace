# UX-Ownership

Gemeinsame Basis und Auftragsblätter: [UX_MASTER_PLAN](UX_MASTER_PLAN.md). Diese Zuordnung regelt technische Zusammenarbeit; fachliche Aufgabenstände stehen nur im [PRODUCT_BACKLOG](../planning/PRODUCT_BACKLOG.md).

## Ein Owner je gemeinsamer UX-Schnittstelle

| Schnittstelle / Änderungsfläche | Ein verantwortlicher Owner | Consumer | Grenze |
|---|---|---|---|
| Seitenkomposition, Navigation, Kontext und Platzierung in `TradeManagementPage.tsx` | UX-2 | UX-1, UX-3, UX-4 | Ein Integrator der gemeinsamen Datei; keine Änderung fremder Formular-/Hinweis-/Chartsemantik. |
| Eingabevorbelegung, manueller Entwurf und Herkunftsanzeige im Eingabefluss | UX-1 | UX-2, UX-3 | Vorbelegung ist keine Bestätigung; Domainvalidierung wird konsumiert. |
| Hostweiter Readback-/Invalidierungsablauf | UX-2 | UX-1-Vorschau, UX-4-Historie und bestehende Buchungsconsumer | Erfolgreiche Owner-Reads erneuern die betroffenen Sichten; fremde Entwürfe erhalten. `ExecutionDatesPanel` bleibt Owner seines Timeline-Reads. |
| Navigations-/URL-Präsentationsvertrag für den Trade-Arbeitsbereich | UX-2 | Trade, Post-Trade, Journal, Lessons; UX-1 und UX-4 | Exakte Identitäten/Pins und begrenzten Berichts-Rückkontext erhalten; keine Daten- oder Berechnungswahrheit in URLs. |
| Einheitliches Hinweismuster, Präsentationspriorität, Fokus-/Live-Region-Verhalten innerhalb des Hinweises und Folgeaktionsdarstellung | UX-3 | UX-1, UX-2, UX-4 | Hostfokusziele und Navigationsübergänge besitzt UX-2; fachliche Schwere/Blockierung nicht umdeuten. |
| Sprache und Präsentation von Datenqualität | UX-3 | UX-1-Herkunft, UX-2-Zusammenfassung, UX-4-Lücken | Domains behalten ihre unterschiedlichen Qualitätscodes; keine universelle fachliche Enum einführen. |
| Diagramm-/Kennzahlenrenderer, Achsen, Einheiten, Lücken und alternative Tabelle | UX-4 | UX-2 und vorhandene Analyse-/Performanceansichten | Nur vorhandene qualifizierte Daten; keine Finanzformel oder zweite Kurshistorie. |
| Koordinationsdokumente, Integrationsreihenfolge und konfliktübergreifende Entscheidung | MASTER-LEAD | Alle vier UX-Leads | Keine Übernahme der Domainownership; kein fachlicher Abschlussstatus außerhalb des Backlogs. |

UX-2 besitzt die gemeinsame Hostdatei, UX-1 die Eingabekomponente: Das sind zwei verschiedene Schnittstellen, keine geteilte Schreibownership derselben Schnittstelle. Die Leads melden gezielte Slot-/Propänderungen dem Hostowner.

## Bestehende Fachverträge bleiben erhalten

Die verbindliche Objektownership steht im [Modul-/Featurekatalog](../planning/MODULE_AND_FEATURE_CATALOG.md#ownership). Für diese UX-Integration sind insbesondere folgende **jeweils getrennte** Verträge relevant:

| Fachvertrag | Ein bestehender Vertragsowner | UX-Consumer |
|---|---|---|
| TradePlan/TradePlanVersion und explizite Freigabe | FT-007 / `trade_plan` | UX-1, UX-2, UX-3 |
| Bewertungslauf und explizite Produktauswahl | FT-008 / `product_selection` | UX-1, UX-2 |
| Trade/Execution/abgeleitete Position, historische Währungsauflösung und Capture-/Preview-DTOs | FT-009/010 als gemeinsamer `trade_position`-Owner | UX-1, UX-2, UX-3, UX-4 |
| Managementereignisse und effektive Managementhistorie | FT-010 im bestehenden TradePosition-Vertrag | UX-2, UX-3, UX-4 |
| Gespeicherte Kursbelege, Quelle und technische Datenqualität | TC-001 / `market_data` | UX-1, UX-3, UX-4 |
| Positionshistorien-Komposition und qualifizierte Executionmarker | `trade_position` | UX-2, UX-4 |
| Marktchart-Normalisierung und Vergleichsqualifikation | Bestehender `analysis`-Owner | UX-4 |
| Monitoringregeln, fachliche Alerts und Risikobewertung | Bestehender `position_monitoring`-Owner | UX-2, UX-3, UX-4 |
| Notification und DeliveryAttempt | Bestehende Notification Capability | UX-3 |
| Observation/ExitReview und historische Reviewversion | FT-011 / `post_trade` | UX-2, UX-3 |
| Journal, LearningEvidence und Lessonversionen | FT-012 / `learning` | UX-1, UX-2, UX-3 |
| Berichtsgrundlage, Finanzkennzahlen und Statistikdefinition | Bestehender `performance`-Owner innerhalb FT-012-Zuordnung | UX-1 für Filtervorschlag, UX-2 für Rückweg, UX-4 für Darstellung |

Ein Rollenname erfindet keinen GitHub-Assignee. Der konkret ausführende Lead benennt sich in seiner Repositoryübergabe; nicht belegte Personen oder fremde Chataktivität werden nicht zugewiesen.

## Dateiabstimmung

Vor jedem neuen PR vollständige Dateiliste und gemeinsam betroffene Verträge mit offenen PRs vergleichen. Eine Reservierung besteht aus PR, Head-SHA, genauen Pfaden, Owner, erlaubtem Teilschnitt und Integrationsreihenfolge im vorhandenen Übergabebericht. Keine zweite Aufgabenliste oder Datei-Lock-Datenbank anlegen.

Konkreter laufender Fall: #311 und #312 berühren beide `frontend/src/features/trade/pages/TradeManagementPage.tsx`. UX-2 koordiniert diese Einbindung; UX-1 liefert die gezielte Preview-/Reload-Änderung. Weitere parallele Hostumbauten warten auf diese Abstimmung. Eigenständige, nicht überlappende Komponentenarbeit kann im jeweils autorisierten Auftrag fortgesetzt werden.

Änderungen an DTOs, API-Routen, Domainmodellen, historischen Referenzen oder Statusbedeutungen gehen vor Umsetzung zum einzelnen zuständigen Domain-Owner. Der MASTER dokumentiert die Entscheidung und prüft die Consumer. Eine rein technische Präsentationsfreigabe ersetzt diese Prüfung nicht.
