# Test- und Abnahmekonzept

[Übersicht](README.md) · [Hinweisvertrag](notice-contract.md) ·
[Inventur](inventory.md) · [Komponenten und Aktionen](components-and-actions.md)

**Status:** Die folgenden UX-3-Szenarien sind geplante Abnahmekriterien. Eine
zentrale produktive Hinweisarchitektur oder neue UI-Tests sind damit nicht
implementiert. Vorhandene Regressionen wurden für die Inventur im Main-Code
gelesen; ein gelesener Test ist kein ausgeführter Test. Tatsächliche lokale Läufe
und CI-Ergebnisse dieses Dokumentations-PRs gehören ausschließlich in Abschnitt 8.

## 1. Was in welcher Phase nachgewiesen wird

| Nachweis | Diese Planungsphase | Späterer begrenzter Implementierungs-PR |
| --- | --- | --- |
| Fachliche Herkunft | Inventur mit aktuellen Codepfaden, DTOs, Codes und bekannten Lücken prüfen. | Adapter gegen die unveränderten Ownerantworten prüfen. |
| Technische Verträge | Dokumentierte TypeScript-Props und positive/negative Typbeispiele prüfen, ohne Produktimport. | Echte Adapter und Komponenten mit synthetischen Ownerantworten testen. |
| Finanz- und Risikoregeln | Bestehende Verträge als Grenze dokumentieren; keine neue Rechenlogik. | Bestehende Domainregressionen erhalten; Anzeigequalifikation gegen die Ownerergebnisse prüfen. |
| Darstellung und Navigation | Konkrete Sollfälle und vorhandene Zielverträge festlegen. | DOM-/Integrationsprüfungen am genau ausgewählten Host und E2E für dessen tatsächlichen Nutzerweg. |
| Barrierefreiheit | Prüfschritte und Abnahmekriterien festlegen. | Tastatur, mobile Darstellung, Zoom und Screenreader an der implementierten Oberfläche tatsächlich prüfen. |
| Fachliche Freigabe | Entwurf bleibt reviewbar und offen. | Zuständiger Domain-Owner bestätigt Semantik; UX-1/UX-2 bestätigen ihre Integrationsgrenzen. |

Dokumentationstests prüfen Dateiverweise, Struktur, typkonsistente Beispiele
und einen versehentlichen Produktimport. Sie beweisen weder die fachliche
Richtigkeit jeder Textaussage noch die Zielzeilen oder Erreichbarkeit externer
URLs; diese Quellenaussagen wurden zusätzlich unabhängig am Code geprüft.
Sie ersetzen weder Domain- noch Browserprüfungen. Ein Test, der nur den eigenen
Dokumenttext wiederholt, ist kein Nachweis der späteren UX-Funktion.

## 2. Gemeinsame Erwartungen für alle Szenarien

Testdaten sind ausschließlich synthetisch. Echte Nutzerbestände, Tradingdaten,
Providerkonten oder private Belege werden nicht zur Erzeugung von Meldungen
gelesen. Zeit, Quelle, Version, Workspace und Objektidentität gehören zur Fixture.
Fachliche Frischegrenzen, Retry-Sperren und Zulässigkeiten liefert der jeweilige
Owner; die Tests führen keine zusätzlichen UI-Grenzen ein.

Jede relevante Meldung wird auf Zustand, bekannte Ursache, konkrete Auswirkung,
belegte Automatik und notwendigen Nutzerbedarf geprüft. Technische IDs/Codes
bleiben auffindbar, bilden aber bei vorhandenem Fachlabel nicht den Primärtext.
`null`, unbekannte Herkunft und nicht lesbare Quelle dürfen nicht zu einer
erfundenen Zahl, Quelle oder erfolgreichen Operation werden.

Die Matrix verwendet die fünf Arten des [Hinweisvertrags](notice-contract.md).
Ein **Blocker gilt nur für die ausdrücklich genannte Aktion oder Berechnung**.
Eine Warnung darf keinen zusätzlichen Schreibschutz für andere erlaubte
Funktionen erzeugen. Erfolg braucht eine passende Quittung oder einen positiv
qualifizierten neuen Ownerbefund; ein beendeter Request genügt nicht.

Mit **Anzahl** ist die Zahl unterschiedlicher aktiver Ursachen im jeweiligen
Kontext gemeint. Eine Zusammenfassung verweist auf dieselben Ursachen in den
Details, ohne sie zusätzlich zu zählen. Ein separater Betroffenen-Zähler zählt
eindeutige Ausführungen/Objekte. Polls, identische Codes in Badge und Detail sowie
wiederholte Cacheantworten erhöhen keinen dieser Zähler.

Soweit nicht ausdrücklich eine spätere Owneraktion ausgeführt wird, gilt in
jedem Fall: Rendern, Aufklappen, Lesen und Navigieren erzeugen **null neue
Schreibbefehle**. Vorhandene Host-Reads bleiben zulässig; die Hinweiskomponente
startet keine zusätzliche Providerabfrage oder automatische Reparaturmutation.

## 3. Geplante fachliche Testmatrix

Die Nachweise `R1` bis `R14` in Abschnitt 6 benennen bestehende Regressionen.
Sie belegen vorhandene Schutzmuster, aber noch nicht die neue UX-3-Darstellung.

### Trade, Position und Performance

| ID / Fall | Ausgangslage und Schritt | Erwartetes Ergebnis, Aktion und Anzahl | Bestehende Grundlage |
| --- | --- | --- | --- |
| TC-01 Fehlende Ausführungswährung | Wirksamer Kauf mit `ExecutionCurrencyResolution.source=UNKNOWN` und konkretem `NO_HISTORICAL_EVIDENCE`; aktuelles EUR-Listing vorhanden. | **Warnung** mit betroffener Kaufbuchung und nicht berechenbarem G/V. Das heutige Listing behebt nichts. „Vorhandene Kaufbelege prüfen“ liest den vorhandenen Ownerkontext; keine Eingabepflicht vor Quellenprüfung. Eine Ursache, ein betroffenes Objekt. | R1, R2 |
| TC-02 Automatisch nachgewiesene Währung | Vorhandener Resolver liefert `EXECUTION_DOCUMENT`, `HISTORICAL_LISTING(S)` oder einen nach seinem Vertrag zulässigen Vorgängerbezug. | Ruhige **Information**, null aktive Währungswarnungen und keine erneute Bestätigungsaufforderung. Originalreferenz, Gültigkeit und Resolverversion bleiben sichtbar. Kein `USER_CONFIRMED`-Write. Ein ungültiger/zeitlich unpassender Beleg wird im Negativfall nicht übernommen. | R1, R2 |
| TC-03 Widersprüchliche oder verschiedene Quellen | Varianten `CONFLICT/DOCUMENT_CONFLICT`, `CONFLICT/LISTING_CONFLICT` und `MIXED/MULTIPLE_LISTING_CURRENCIES`. | **Warnung**, bei ausdrücklich verlangter nicht möglicher Berechnung deren konkrete **Blockade**. Widerspruch und unterschiedliche historische Handelsplatzwährungen werden richtig erklärt. Quellenvergleich führt zu genau diesen Belegen; eine gemeinsame Ursache statt UNKNOWN-Banner plus identischem Detailbanner. | R1 |
| TC-04 Korrigierte Ausführung | Historisch belegter Kauf wird ersetzt; Owner liefert `CORRECTION_SOURCE_REVIEW_REQUIRED` für die neue Buchung. | Alte Quelle bleibt **historische Information**; aktuelle Nachweislücke der neuen Ausführung bleibt **Warnung**. Keine stille Übernahme widerrufener oder unpassender Belege. Lesender Zugriff auf beide Identitäten; Count nur für die aktuelle Lücke. | R1, R2 |
| TC-05 Fehlende oder gemischte Kostenbasis | Owner liefert `COST_BASIS_CURRENCY_UNKNOWN`, `...MIXED` oder `...MISMATCH`, gegebenenfalls bei weiterhin verfügbarem Marktwert. | **Warnung** benennt die wirksamen Kaufbelege und den nicht berechenbaren G/V. Marktwert und G/V werden nicht gleichgesetzt. Unbekannter G/V bleibt `null`; keine FX-Ersatzrechnung, keine pauschale „EUR bestätigen“-Aktion. Zusammenfassung verweist auf eindeutige BUY-Ursachen. | R1, R2, R3 |
| TC-06 Unvollständiger Performancebericht | Mindestens ein qualifizierter Beitrag und eine relevante ungeklärte Zeile; Owner liefert `PARTIAL`, `total=null`, bekannten `subtotal`. | **Warnung** erklärt Einzel- und Aggregatwirkung. Bekannter Teilbetrag wird als Teilbetrag gezeigt; kein vollständiger Gesamtwert. Eine Sammelmeldung referenziert die Zeilenursachen, ohne diese nochmals zu zählen. Quellen stammen aus derselben Reportantwort. | R3, R4 |
| TC-07 Echte Null, EMPTY und Unbekannt | Drei Fixtures: vollständig geprüfte leere Auswahl `EMPTY`, vollständig belegtes Ergebnis 0 und `NOT_COMPUTABLE` mit `null`. Zusätzlich echter 0-Teilbetrag in `PARTIAL`. | `EMPTY` und belegte 0 sind reguläre **Information**, null Warnungen aufgrund der Nullzahl. `NOT_COMPUTABLE` bleibt unbekannt und erklärt die fehlende Grundlage. Keine Konvertierung von `null` zu 0 oder von echter 0 zu unbekannt. | R3 |
| TC-08 Unterschiedliche Grundgesamtheiten | Dieselben synthetischen Trades erzeugen einen SELL-Bericht und einen Vollabschlussbericht mit abweichenden Summen. | **Information** benennt jeweilige Definition, Zeitraum, Währung und Zeitzone. Keine Konfliktwarnung allein wegen verschiedener Beträge. Ein Bericht übernimmt weder Zähler noch Meldungen des anderen. | R3, R4 |
| TC-09 Storno, Ersetzung und regulärer Ausschluss | Stornierter Fehleintrag, historische Ersatzbuchung, Zeile außerhalb Zeitraum oder Währungsfilter. | Neutrale **historische Information** bzw. Ausschlussdetail; null aktive Warnungen allein deshalb. Kein Verkauf aus Storno, kein doppelter Beitrag aus Ersatzbuchung. Nur beim Versuch, einen überholten Stand zu bearbeiten, erklärt der Owner die konkrete Blockade. | R2, R3 |

### Markt- und Kursdaten

| ID / Fall | Ausgangslage und Schritt | Erwartetes Ergebnis, Aktion und Anzahl | Bestehende Grundlage |
| --- | --- | --- | --- |
| TC-10 Veralteter aktueller Kurs | Owner klassifiziert aktuellen Quotezustand als `STALE`; Originalkurs vorhanden. | **Warnung** nennt Originalzeit, Quelle und konkrete Einschränkung. Der Wert wird nicht als aktuelle Notierung bezeichnet. Bestehender automatischer Abruf wird nur bei vorliegendem Plan erwähnt; Nutzeraktion normalerweise keine. Eine aktuelle Qualitätsursache. | R5, R6 |
| TC-11 Providerfehler mit Ersatzkurs | Tatsächlich fehlgeschlagener Abruf; gespeicherter Kurs mit `retained_quote=true`, eigenen Originalzeiten und unabhängigem Qualitätsbefund. | **Fehler** des Quellenabrufs und aktuelle Kursverwendbarkeit bleiben getrennt. Kein Providererfolg durch Retention. Eine Quellenursache; eine zusätzlich belegte Qualitätslücke wird als eigene Wirkung/Dimension nachvollziehbar, ohne denselben Ausfall in mehreren Bannern zu zählen. Lesend „Kursdatenstatus anzeigen“. | R5, R6 |
| TC-12 Qualifizierte Recovery | Gleiche Source, Listing- und Quellenidentität; Owner liefert später `qualified_success=true`, passenden neuen Abruf und `recovered_at`, Fehlerfolge beendet. Negativ: alte Cacheantwort, Referenz-only, Zeit unbekannt oder retained. | Nur im positiven Fall **Erfolg** mit belegter Zeit, aktive Quellenwarnung entfällt. Historischer Fehler bleibt in Details. Einmalige ruhige Ankündigung, keine Wiederholung beim identischen Read. Negative Varianten behaupten keine Wiederherstellung. | R5, R6 |
| TC-13 HTTP 429 und lokale Retry-Sperre | Echter `GETTEX_DELAYED_RATE_LIMITED`, danach `GETTEX_DELAYED_REQUEST_THROTTLED` ohne erneuten Providerkontakt. | Erster Vorgang als konkreter Abruffehler; anschließendes Warten **Information** innerhalb desselben Befunds. Fehlerzahl bleibt während lokaler Sperre unverändert. Kein „Jetzt abrufen“, das Sperren umgeht; kein aus Jobtermin erfundener garantierter Providerfreigabezeitpunkt. | R5, R6 |
| TC-14 Verwendbarer Kurs aus anderer Quelle | Quelle A weiterhin fehlerhaft, zulässiger aktueller Kurs von B verwendbar; Job insgesamt `AVAILABLE`. | Aktuelle Kursqualitätswarnung entfällt, sofern Owner sie positiv auflöst. A behält genau einen offenen Quellenbefund, B erzeugt keine angebliche Recovery von A. Jobabschluss ist kein pauschales „alle Quellen in Ordnung“. | R5, R6 |
| TC-15 LAST_AVAILABLE in gültiger Sitzung | Owner liefert `LAST_AVAILABLE` und `quote_usable=true` nach bestehender Sitzungsregel; kein zusätzlicher Abruffehler. | **Information** „Letzter verfügbarer Sitzungskurs“ mit Originalzeit; null Warnungen allein wegen `LAST_AVAILABLE`, kein pauschal „veraltet“. Bei späterem Ownerbefund `STALE` ändert sich nur dann die aktuelle Qualifikation. | R5, R6 |
| TC-16 Historische STALE-/Fehlerstichprobe | Frühe Stichprobe `STALE` oder `REQUEST_FAILED`, später qualifizierter aktueller Kurs; gleiche oder andere Erfassungsintervalle. | Historie beschreibt „bei Erfassung“ und bleibt unverändert. Null aktuelle Warnungen allein aus altem Sample; kein Löschen des historischen Fehlers. Eine aktuelle Erfolgsaussage braucht eigenen Ownerbeleg. Keine Gleichsetzung der Samplingregel mit aktueller Sitzungsfrische. | R5, R7 |
| TC-17 Neustart und nicht erneut geprüfte Quelle | Prozesslokale Diagnostik fehlt nach Neustart oder `observed_in_latest_run=false`; persistierte Kursbelege bestehen. | **Information** über begrenzten Prüfstand; keine erfundene Recovery, keine neu erfundene Fehlerfolge. Historische Belege bleiben lesbar. Neues/verschlechtertes Problem nur bei passender Vergleichsevidenz. | R5, R6 |
| TC-18 Fehlende historische Kursbeobachtungen | Leere Serie, unbekannte Originalzeit, `truncated=true`, reguläre Dubletten und außerhalb des Fensters liegende Belege jeweils getrennt. | Leer ist ein erklärter Datenzustand, kein technischer Fehler. Unvollständige Abdeckung ist **Warnung** nur für die beanspruchte vollständige Historie. Dubletten/Filterausschlüsse sind **Information**. Kein `retrieved_at` als erfundener Chartzeitpunkt, kein Backfill und kein Nullkurs. Vorhandene Quellen lesend öffnen. | R7 |

### TradePlan und Produktauswahl

| ID / Fall | Ausgangslage und Schritt | Erwartetes Ergebnis, Aktion und Anzahl | Bestehende Grundlage |
| --- | --- | --- | --- |
| TC-19 Fehlende historische Planversion | Exakte `trade_plan_version_id` nicht vorhanden oder gehört zu anderem Plan; neuere Version existiert. | **Blocker** nur der angeforderten Ansicht/Aktion. Kein Latest-Fallback und kein gültig aussehender fremder Versionsinhalt. „Planversion prüfen“ erhält den konkreten Bezug; bewusste andere Auswahl bleibt möglich. Eine Kontextursache. | R8 |
| TC-20 Regulär abgelöste Planversion | Historische `SUPERSEDED`-Version und ihr Run werden gelesen; Nutzer erwägt neuen Bewertungslauf. | Historie bleibt **Information** und lesbar. Nur neuer Lauf benötigt nach Ownervertrag eine passende APPROVED-Version. Vorhandene ältere APPROVED-Version wird bei gezieltem Bezug nicht durch einen neueren DRAFT ersetzt. | R8, R9 |
| TC-21 NOT_EVALUABLE mit Begründung | Produktbewertung unvollständig; Nutzer möchte das konkrete Produkt dennoch auswählen. | **Warnung** erklärt fehlende Bewertungsgrundlage. Auswahl ist nicht pauschal gesperrt: bestehender Owner fordert nichtleere Begründung und ausdrückliche Bestätigung. Ohne diese Voraussetzungen bleibt genau der Command gesperrt. Eine Ursache, keine doppelte Warnung im Badge und Dialog. | R9 |
| TC-22 INELIGIBLE und NOT_APPLICABLE | Produkt fachlich ausgeschlossen; Marktdatenprüfung deshalb als `NOT_APPLICABLE` ausgelassen. | **Blocker** der Produktauswahl aus konkretem Ausschluss. Keine zusätzliche Kursausfallwarnung aus dem ausgelassenen Prüfschritt; eine aktive Ursache. Historischer Lauf bleibt lesbar, keine automatische Neuberechnung. | R9 |
| TC-23 Fehlende optionale Risikoangaben | Version hat leere optionale Risk Notes; alternativ Owner lehnt tatsächlich einen Pflichtinhalt ab. | Optional fehlend: neutrale Anzeige, null erfundene Freigabe-/Eingabepflichten. Reale Ownerablehnung: konkrete betroffene Voraussetzung erklären. Keine Behauptung „Risiko vollständig“ aus bloßer Feldfüllung. | R8, R9 |

Zusätzlicher Negativfall zu TC-23 und Inventur B01: Eine vom Candidate-Owner
gelieferte `QUALIFIED`-Evaluation behält ihre Qualifikation auch bei `CAUTIOUS`,
`LIMITED` oder fehlenden optionalen `sources` im Read. UX-3 erzeugt daraus keine
neue Freigabepflicht oder `NOT_EVALUABLE`-Diagnose.

### Journal, Lessons und Governance

| ID / Fall | Ausgangslage und Schritt | Erwartetes Ergebnis, Aktion und Anzahl | Bestehende Grundlage |
| --- | --- | --- | --- |
| TC-24 Offener Journalentwurf | Bestehender `DRAFT` mit optional leeren Texten; alternativ noch kein Journal. | Reguläre **Information**, null Warnungen allein durch Entwurfsstatus. „Journal fortsetzen“ öffnet vorhandenen konkreten Entwurf; bei leerer Historie entsteht durch Anzeige kein neuer DRAFT und keine Evidence. | R10 |
| TC-25 Fehlender Reviewabschluss | `EXIT_REVIEW_NOT_FINALIZED`, fehlende Reviewversion oder noch unvollständige Nachbeobachtung; CREATE_DRAFT/FINALIZE gewünscht. | **Blocker** ausschließlich des nicht zulässigen Schritts. Ursache bestimmt mögliche Aktion: Review bewusst bearbeiten oder auf bestehende Beobachtung warten. Bereits erlaubtes Speichern eines vorhandenen Entwurfs bleibt erlaubt. Kein künstliches Fälligkeitsdatum. | R10 |
| TC-26 Historische Journalquelle STALE/UNKNOWN | Historisch gepinnte Quelle veraltet/ungeklärt; bestehender gültiger Entwurf wird gelesen oder gespeichert. | Historische Bindung bleibt sichtbar; heutige Quellenqualifikation getrennt erläutern. Keine automatische Neubindung, menschliche Bewertung oder Finalisierung. Warnung nur für konkret eingeschränkte Verwendung; Historie nicht als gelöscht behandeln. | R10, R11 |
| TC-27 Quellen-GET scheitert | Gebundene Quelle ist bekannt, ihr Abschnittsread scheitert; andere Sektionen sind verfügbar. | Lokaler **Fehler** „Quelle konnte nicht gelesen werden“; keine unbelegte Aussage „Quelle fehlt“. Optionaler lesender Retry, intakte historische Links und andere Daten bleiben nutzbar. Eine Leseursache, kein globaler Finanzfehler. | R4, R11 |
| TC-28 Materialisierungskonflikt | `MATERIALIZATION_CONFLICT`, `SOURCE_VERSION_MISMATCH` oder `SOURCE_BUSY` bei ausdrücklicher Übergabe. | Konkreter gescheiterter/konfliktbehafteter Vorgang; ungeklärten Abschluss nicht als sicher nicht gespeichert ausgeben. Zuerst vorhandenen Status lesen, Quelle und Idempotenz beim Owner belassen. Anzeige erstellt keine zweite Evidence oder Lesson. | R10, R11 |
| TC-29 Lessonreview und Quellenaktualität | Lesson ist `CURRENT`, Evidence oder Review-Vorquelle jedoch `STALE`; alternativ Reviewkonflikt durch neue Version. | „Aktuelle Interpretation“ bedeutet nicht „alle Quellen aktuell“. Keine automatische menschliche Reviewentscheidung. Konflikt bewahrt Entwurf und verlangt bewusstes Prüfen neuer Ownerbasis. Eine Ursache je betroffener Version, keine still neu gebundenen Quellen. | R11 |
| TC-30 Modellfreigabe versus Aktivierung | Proposal-/Modelversion APPROVED, konkrete aktive Runtimeversion unverändert; alternativ Zielversion schon aktiv. | APPROVED, noch nicht aktiv: **Information**, keine Pflichtaktivierung und kein Erfolg „aktiviert“. Vorhandene Aktivierung wird gelesen, nicht erneut geschrieben. Blocker nur bei vom Owner konkret gesperrter neuer Bewertung ohne nutzbares aktives Modell. | R12 |
| TC-31 Hebeltrader-Vertrag vorhanden | Dokumentationsvertrag aus #309 und Versionstag vorhanden, kein passender Runtime-Aktivierungsbeleg. | Keine produktive „Regeln aktiv“-Meldung, keine neue Frischegrenze aus historischem Sollvertrag. Dokumentiert, genehmigt und tatsächlich aktiviert bleiben getrennte Aussagen. Null automatisch erzeugte Orders, Mengenentscheidungen oder Modellaktivierungen. | R12; [Main-Vertrag](../../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md) |

Zusätzlicher Negativfall zu TC-27 und Inventur E11: Der Evidence-Katalog-GET
scheitert, aber die bestehende Auswahl enthält gültige SUPPORTS-Links und alle
übrigen Ownerbedingungen sind erfüllt. Der Readfehler erzeugt keine neue globale
Speichersperre. Tatsächlich fehlende/ungültige Evidence bleibt dagegen eine
vom Owner begründete Blockade des jeweiligen Schreibschritts.

## 4. Geplante Kontext-, Konkurrenz- und Aktionsprüfungen

Für die Race-Fälle werden gezielt auflösbare Promises benutzt. Ein Fixture muss
einen trotz Abort später aufgelösten Request simulieren können. Nur ein erfolgreich
abgebrochener Fetch würde die nötige Generation-/Besitzprüfung nicht belegen.
Geprüft werden jeweils Titel, Detaildaten, Fehler, Erfolg, Recovery, Zähler und
Aktionsziel gemeinsam, nicht nur der sichtbare Geldbetrag.

| ID / Fall | Abfolge | Erwartetes Ergebnis |
| --- | --- | --- |
| TC-32 Wechsel zwischen Trades A → B | In A Hinweis samt offener Detailansicht und Aktion; vor A-Antwort nach B wechseln. | A-Kontext synchron ungültig; kein A-Hinweis, keine A-Quelle und keine A-Aktion in B. B-Ladezustand ist Information. Späterer A-Erfolg oder A-Fehler verändert B nicht. R2, R7. |
| TC-33 A → B → A | Erster A-Read bleibt offen; B und neuer A-Besuch starten; alter A-Read löst zuletzt auf. | Objekt-ID allein genügt nicht: alte Generation verworfen, auch bei identischer ID. Keine alte Erfolgsmeldung, kein fremder Versionspin, keine falsche erneute Warnung. Gilt auch für StrictMode-Wiederholung. R2, R4, R9, R11. |
| TC-34 Überholter Refresh desselben Objekts | Zwei Reads für gleichen Trade/Version; zweiter Read schließt zuerst mit neuerer bestätigter Basis ab. | Älterer Erfolg, Fehler oder `finally` überschreibt weder neue Daten noch Lade-/Erfolgsstatus. Kein Wiederauftauchen bereits positiv aufgelöster Warnungen aus überholter Antwort. Bestehenden Ownerkontextvalidator verwenden. R2, R4. |
| TC-35 Berichtbasis- oder Filterwechsel | Reportart, Währung, Zeitraum oder Zone ändern; zusätzlich neuer `basis.id` beim gleichen Filter. | Jede Antwort vollständig an Art/Filter/Basis binden. Beträge, Zähler, Quellen und Notices gemeinsam ersetzen. Basisänderung allein ist **Information**, keine Recovery oder Verschlechterung. Abweichende Reports nicht zu einer Ursache zusammenrechnen. R3, R4. |
| TC-36 Quellenmapping wechselt | Derselbe Provider/Listingname erhält neue kanonische `identity_key`; alte Fehlerfolge existiert. | Neue Identität übernimmt weder Erfolg noch Fehlerfolge der alten Route. Alte Evidenz bleibt mit ihrem historischen Scope erkennbar. Erfolg der neuen Route ist keine Recovery der alten. Aktuelles Objektziel muss die neue belegte Identität führen. R5. |
| TC-37 Verspäteter API-Fehler | Für A oder ältere Generation scheitert ein Request nach erfolgreichem aktuellen B-/Neu-Read. | Keine neue Alert-/Live-Ankündigung, kein Fehlerbanner und keine gelöschte aktuelle Ansicht. Echte Fehler der aktiven Generation bleiben lokal sichtbar. Abbruch ist kein Benutzerfehler. R2, R4, R7, R11. |
| TC-38 Mehrdeutige URL-Parameter | Doppelte `trade_id`, `run_id` oder Versionspins, fehlende Pflichtkombination oder fremde historische Referenz. | Vorhandene Queryvalidatoren weisen Kontext zurück. Keine „erster Wert gewinnt“-Navigation und kein Ersatz auf aktuelle Version. **Blocker** der betroffenen Zielansicht; null Writes. Exakte Querynamen bleiben im UX-2-Vertrag. R4, R8, R9, R10. |
| TC-39 Unbekannter Mutationsabschluss | Nutzer hat einmal ausdrücklich gespeichert; Verbindung/5xx oder unzuordenbare Antwort lässt den Abschluss offen. | **Warnung** über ungeklärten Abschluss; nicht fälschlich Erfolg oder sicher gescheitertes Speichern. Weitere Commands folgen dem Ownerguard. Lesenden Stand prüfen; identischer Idempotenz-Retry nur durch ausdrückliche Nutzerhandlung im bestehenden Ownerworkflow, nie automatisch aus Notice. R2, R8, R10. |
| TC-40 Erfolg plus fehlgeschlagener Readback | Mutationsreceipt passt exakt zum Befehl, anschließende History-/Positions-/Listenabfrage scheitert. | Bestätigter Schreibabschluss bleibt **Erfolg**; aktueller Lesezustand ist separat **Fehler/Warnung**, ggf. Aktionsblockade weiterer Writes. „Speichern fehlgeschlagen“ wäre falsch. Nur Readback wiederholen; Erfolg und Lesefehler nicht als doppelte Ursache desselben Vorgangs zählen. R2, R8, R9, R11. |
| TC-41 Identische Wiederholungen | Gleicher Befund mehrfach durch Poll, Badge, Detail und Sammelansicht; zwei verschiedene betroffene Ausführungen als Gegenfall. | Eine Ursache je gültigem Owner-/Objekt-/Versionsschlüssel. Betroffenen-Zähler zählt echte Objekte, nicht Abrufe. Übersetzung oder DOM-Reihenfolge erzeugt keine neue Identität. Kein erneutes Liveannouncement bei unverändertem Befund. Verschiedene Objekte bleiben einzeln erreichbar. R5, R6; neue Präsentationsprüfung. |
| TC-42 Priorität und Verschlechterung | Konkreter Blocker, notwendige Entscheidung, Warnung, Datenqualitätsinformation und Erfolg gleichzeitig; anschließend nur Wiederholungszahl erhöhen. | Reihenfolge gemäß Vertrag; Count allein erhöht keine Schwere. Neue Einschränkung nur nach passendem Ownerbeleg als Verschlechterung ankündigen. Historie ist nicht allein wegen hohen Counts dringend. Keine zweite globale Workspace-Priorisierung implementieren. Neue Präsentationsprüfung. |
| TC-43 Unbekannter Code und unvollständige Diagnose | Fehlgeschlagene Operation mit unbekanntem Code; erfolgreicher Read mit unbekanntem Status; `usable=false` als separat bekannter Fakt. | Fehler bleibt **Fehler** mit bekanntem Vorgang, unbekannte Ursache ehrlich benennen. Erfolgreicher Read wird weder pauschal grün noch erfunden blockiert. Bekannte Unverwendbarkeit bleibt erhalten. Keine Klassifikation aus Freitext/UUID und keine Preis- oder Frischeannahme. Neue Adapterprüfung. |
| TC-44 Sichere Aktionen und erneuter Kontextcheck | Hinweis öffnen, fokussieren, Details aufklappen, Link folgen; unmittelbar vor Klick ändert sich Version oder Kontext. | Null Writes durch Anzeige oder Navigation. Ein veraltetes Ziel wird nicht ausgeführt; Zielfachbereich prüft Besitzer/Pins erneut. Lesende Links und spätere schreibende Owneraktionen sind erkennbar getrennt. Fehlende Deep-Link-Unterstützung erzeugt keinen erfundenen Routerparameter. R2, R4, R8–R12. |

## 5. Mobile Darstellung und barrierefreie Abnahme

Die folgenden Prüfungen sind **geplant und manuell noch offen**. Automatische
DOM- oder Accessibilitychecks allein belegen keine verständliche Ansage und
Fokusführung. Die jeweilige Abnahme dokumentiert Browser, Betriebssystem,
Screenreader-Version, Viewport, Zoom und tatsächlich geprüften Commit.

| ID / Fall | Durchführung | Abnahmekriterium |
| --- | --- | --- |
| TC-45 Mobile Ansicht und Zoom | Kompakter Hinweis, Sammelhinweis und geöffnete Details bei 320 CSS px; außerdem 200 % und 400 % Browserzoom an geeignetem Desktopviewport. Lange Produktnamen, deutsche Texte und technische Referenzen verwenden. | Zustand, Auswirkung und primäre Aktion bleiben ohne horizontales Scrollen der kompakten Meldung lesbar und bedienbar. Text wird nicht abgeschnitten; Aktionen überlappen nicht. Breite Evidenztabellen dürfen in eigener beschrifteter, per Tastatur erreichbarer Scrollregion liegen. Details und Rückweg bleiben erreichbar; keine neue Modalpflicht. |
| TC-46 Tastatur und Fokus | Nur Tab, Shift+Tab, Enter und Leertaste; Details öffnen/schließen, Quellenlink folgen, zurückkehren, lesenden Retry auslösen. Befund ändert sich, während Aktion oder Detail fokussiert ist. | Sinnvolle DOM-/Fokusreihenfolge, sichtbarer Fokus, korrekt benannte Links/Buttons, native `details/summary` oder gleichwertige Semantik. Keine Fokusfalle und kein automatischer Sprung bei Polls. Entfällt das fokussierte Element, bleibt Fokus an einem passenden stabilen Kontrollpunkt; dieser Fall wird im Host konkret festgelegt. Ownerguards für ungespeicherte Eingaben bleiben wirksam. |
| TC-47 Statusänderungen und Live-Regionen | Neuer tatsächlicher Operationsfehler, unveränderte alte Warnung, neues Problem, qualifizierte Recovery und historische Ansicht nacheinander auslösen; Summary und Detail gleichzeitig rendern. | Alte/statische Warnungen erhalten nicht allein wegen ihrer Farbe `role=alert`. Echte unmittelbar relevante Operationsfehler werden angemessen einmal angekündigt; Routineänderungen über ruhige Statusansage. Unveränderte Polls und alte Antworten bleiben stumm. Zusammenfassung und Detail sagen denselben Befund nicht doppelt an. Wiederherstellung wird nur mit Ownerbeleg angekündigt. |
| TC-48 Manuelle Screenreader-Abnahme | Mindestens ein Desktop-Screenreader mit Browser sowie ein mobiles Screenreader-/Browserpaar am später implementierten Host. Hinweise, Priorisierung, Aktionen, Zeitangaben und Quellenhistorie ohne visuelle Information bedienen. | Art, betroffener Gegenstand, Auswirkung und Aktionsname sind verständlich; Farbe/Symbol sind nie alleiniger Träger. Quellenzeit, Abrufzeit und historische Gültigkeit werden nicht verwechselt. Technische IDs überlagern keine vorhandenen Fachlabels. Aufklappzustand, Ladezustand, Fehler und Erfolg werden nachvollziehbar vermittelt. Ergebnis mit konkreten Beobachtungen protokollieren; ohne Prüfung bleibt „manuell offen“. |

Bei TC-45 bis TC-48 sind mindestens TC-01, TC-11, TC-24 und TC-40 als Inhalte zu
verwenden: eine echte Datenlücke, ein Ersatzkurs mit Quellenfehler, ein normaler
Entwurf und ein bestätigter Schreibabschluss mit Lesefehler. So wird nicht nur
die Farbe einer idealisierten Erfolgskarte getestet.

## 6. Vorhandene Regressionen und tatsächliche Aussagegrenzen

Die Dateien wurden am in der [Übersicht](README.md) genannten Main-Commit gelesen.
Die Tabelle dokumentiert **bestehende Testfälle**, keine in diesem Dokument
behaupteten neuen Testergebnisse. Angegebene Frontenddateien enthalten aktuelle
Hostregressionen; eine spätere gemeinsame Komponente braucht zusätzlich die
gezielten Adapter-/Darstellungsprüfungen aus der Matrix.

| Referenz | Vorhandene Dateien | Abgedeckte Schutzmuster |
| --- | --- | --- |
| R1 Währungsquellen | [Historischer Resolver](../../../tests/unit/backend/features/trade_position/test_historical_currency_resolution.py), [historische Berichte](../../../tests/unit/backend/features/performance/test_historical_currency_reports.py) | Belegpriorität, widersprüchliche Quellen, identische Doppelbelege, DATE_ONLY-/DST-Gültigkeit, Scopegrenzen, keine unzulässige historische Übernahme. |
| R2 Buchung und Kontext | [ExecutionCurrencyPanel](../../../frontend/src/features/trade/components/ExecutionCurrencyPanel.test.tsx), [ExecutionDatesPanel](../../../frontend/src/features/trade/components/ExecutionDatesPanel.test.tsx), [TradeManagementContext](../../../frontend/src/features/trade/pages/TradeManagementContext.test.tsx) | Quellen-/Ausführungswechsel, A→B→A, verzögerte Writes, belegter Receipt, unklarer Abschluss, Readback-Sperre, keine still übernommene alte Buchung. |
| R3 Finanzbericht | [SELL-Report](../../../tests/unit/backend/features/performance/test_report.py), [Vollabschlussbericht](../../../tests/unit/backend/features/performance/test_closed_report.py) | PARTIAL/NOT_COMPUTABLE/EMPTY, echter 0-Teilbetrag, vollständige vs unbekannte Summe, Ausschlüsse und unterschiedliche Grundgesamtheiten. |
| R4 Performanceansicht und Quellen | [PerformanceWorkspace](../../../frontend/src/features/performance/pages/PerformanceWorkspace.test.tsx), [ClosedTradesPage](../../../frontend/src/features/performance/pages/ClosedTradesPage.test.tsx), [ClosedTradeSourceJourney](../../../frontend/src/features/performance/pages/ClosedTradeSourceJourney.test.tsx) | Filter-/Basiswechsel, späte Antworten und Fehler, unabhängiger Quellenread, optionaler Journalfehler beeinträchtigt nicht den qualifizierten Finanzbefund. |
| R5 Quellenqualität und Recovery | [Refreshdiagnostik](../../../tests/unit/backend/features/market_data/test_refresh_diagnostics.py), [qualifizierte Diagnose](../../../tests/unit/backend/features/market_data/test_refresh_quality_diagnostics.py), [Identität und Persistenz](../../../tests/unit/backend/features/market_data/test_refresh_identity_evidence.py), [Sitzungsfrische](../../../tests/unit/backend/features/position_monitoring/test_quote_freshness.py) | Dedupe, Originalzeiten, retained/alter Cache ohne Recovery, anderer Provider und Mappingrevision getrennt, LAST_AVAILABLE, Warten ohne Fehlerzuwachs, Prozessneustart ohne erfundene Wiederherstellung. |
| R6 gettex und Diagnoseoberfläche | [gettex-Adapter](../../../tests/unit/backend/providers/gettex_delayed/test_gettex_delayed_adapter.py), [gettex-Retention](../../../tests/unit/backend/features/market_data/test_gettex_retention_regression.py), [Refreshpanel](../../../frontend/src/features/operational_workspace/pages/MarketDataRefreshPanel.diagnostics.test.tsx) | Retry-After/Sperren, typed HTTP-Fehler, Validierungsfehler, ursprüngliche Quote bleibt erhalten, Statusread ohne Reparaturmutation, Source-/Joberfolg und offene Fehlerfolgen getrennt. |
| R7 Kurshistorie | [Quote-Sampling](../../../tests/unit/backend/features/market_data/test_quote_history.py), [Originalkursserien](../../../tests/unit/backend/features/market_data/test_warrant_price_history.py), [PositionPriceHistory](../../../frontend/src/features/operational_workspace/components/PositionPriceHistory.test.tsx), [Responsebesitz](../../../frontend/src/features/operational_workspace/services/positionPriceHistory.test.ts) | Fehlerhistorie bleibt erhalten, Originalzeit statt Empfangszeit, kein erfundener Backfill, Währungen/Provider/Kursarten getrennt, leere Historie vs Lesefehler, verspätete fremde Antwort verworfen. |
| R8 Planversion und Speicherung | [ExistingTradePlanPage](../../../frontend/src/features/trade_plan/pages/ExistingTradePlanPage.test.tsx) | Fehlende konkrete Version, falscher Antwortkontext, historischer Versionserhalt, unbekannter Schreibabschluss und Readfehler. |
| R9 Produktauswahl | [Domain](../../../tests/unit/backend/features/product_selection/test_domain.py), [Universum](../../../tests/unit/backend/features/product_selection/test_universe.py), [Auswahlseite](../../../frontend/src/features/product_selection/pages/ProductSelectionPage.test.tsx), [Kontext](../../../frontend/src/features/product_selection/pages/ProductSelectionPage.context.test.tsx), [Reparaturziele](../../../frontend/src/features/product_selection/pages/ProductSelectionPage.repair.test.tsx), [Deep Links](../../../frontend/src/features/product_selection/pages/ProductSelectionPage.deep-link.test.tsx) | NOT_EVALUABLE mit Begründung, INELIGIBLE gesperrt, exakte historische Bedingungen, keine Latest-Substitution, A→B→A, bestätigte Speicherung trotz Readfehler, konkrete Produkt-/Runziele. |
| R10 Journal | [Journalcommands](../../../tests/unit/backend/features/learning/test_journal_commands.py), [TradeJournalPanel](../../../frontend/src/features/learning/components/TradeJournalPanel.test.tsx) | Leerer DRAFT zulässig, FINALIZED unveränderlich, DRAFT keine Evidence, CAS/Idempotenz, bewusste Neubindung, STALE/UNKNOWN kein qualifizierter neuer Quellenbeleg. |
| R11 Herkunft und Lessonreview | [JournalEvidenceOrigin](../../../frontend/src/features/learning/components/JournalEvidenceOrigin.test.tsx), [EvidenceSourceStatus](../../../frontend/src/features/learning/components/EvidenceSourceStatus.test.tsx), [LessonReviewPanel](../../../frontend/src/features/learning/components/LessonReviewPanel.test.tsx) | Exakte Herkunft, Currentness getrennt, späte Antworten, kein stilles Rebase, Receipt trotz Readfehler, historische Inhalte unverändert, keine implizite Reaktivierung. |
| R12 Governance | [ProposalApprovalPanel](../../../frontend/src/features/model/components/ProposalApprovalPanel.test.tsx), [RuntimeActivationPanel](../../../frontend/src/features/model/components/RuntimeActivationPanel.test.tsx) | Nur zulässige explizite Freigabe; keine Doppelfreigabe; APPROVED noch nicht aktiv; ausdrückliche Aktivierung und bereits aktive Zielversion getrennt. |
| R13 Monitoring | [MonitoringRuntimePanel](../../../frontend/src/features/alert/components/MonitoringRuntimePanel.test.tsx), [TradeAlertsPanel](../../../frontend/src/features/alert/components/TradeAlertsPanel.test.tsx) | Laufender Dienst trotz unvollständiger Abdeckung, älterer abgeschlossener Zyklus keine Recovery, enabled nicht gleich running, Alert und Versandstatus getrennt. |
| R14 Bestehende Browserwege | [Performance-Workspace](../../../tests/e2e/performance-workspace-ui.spec.ts), [Positionstabelle](../../../tests/e2e/positions-table.spec.ts), [Tradebuchungen](../../../tests/e2e/trade-execution-consolidation.spec.ts) | Vorhandene Nutzerwege als Integrationsbasis. Kein Beleg der noch nicht implementierten UX-3-Komponente und keine abgeschlossene manuelle Screenreader-Abnahme. |

## 7. Reihenfolge und Abnahmegates für die Folgeimplementierung

1. **Vertrag und Adapter:** Ein eng begrenzter Domainfall mit vorhandenen DTOs,
   positiver/negativer Semantik und genauer Aktion. Hierzu passende TC-Fälle
   auswählen und einen unbekannten Code, fehlenden Beleg sowie Scopewechsel
   einschließen. Keine neue Feldableitung durch UX-3.
2. **Präsentation ohne Seiteneffekte:** Kompakte Karte, Details und sicherer
   Leseaktionslink. TC-41 bis TC-48 ergänzen; DOM-Tests sollen Verhalten prüfen,
   nicht interne CSS-Klassennamen oder die eigene Implementierung spiegeln.
3. **Genau ein bestehender Host:** Vorhandene Owner-/UX-1-/UX-2-Guards erhalten.
   Relevante Race-Fälle TC-32 bis TC-40 mit gezielt verspäteten Ergebnissen und
   dem tatsächlichen Zielworkflow prüfen.
4. **Unveränderte Projektgates:** Erforderliche Backend-, Frontend- und E2E-CI
   am tatsächlichen PR-Head beziehungsweise zugeordneten Merge-Commit bestehen
   lassen. Keine Tests deaktivieren, Coveragegrenzen senken oder alte grüne
   Läufe auf neuen Code übertragen.
5. **Fachliche und manuelle Abnahme:** Domain-Owner prüft Ursache/Wirkung,
   UX-1 die unveränderte Ableitung/Validierung, UX-2 Objektziele und Kontext,
   UX-3 Semantik/Dedupe/Anzeige. Mobile und Screenreaderprüfung ausdrücklich
   dokumentieren. Erst danach gilt die konkrete Folgearbeit als abgenommen.

Ein fehlender eindeutiger Ownercode oder nicht unterstützter Deep Link ist ein
offener Integrationspunkt. Er darf weder mit Freitextheuristik noch erfundener
Route „grün getestet“ werden. Die Entscheidung muss vor Integration des
betroffenen Falls konkret vorliegen; andere klar belegte Fälle können separat
umgesetzt werden.

## 8. Tatsächliches Prüfprotokoll dieses Dokumentations-PRs

### Verifizierte Ausgangs-CI

Diese Läufe gehören ausschließlich zu Main
`1883f7f330719453958f8be1dd51d48db816662e`, wie in der
[Übersicht](README.md) verifiziert:

| Workflow | Ergebnis | Nachweis |
| --- | --- | --- |
| Backend, Main-Push | `success` | [41171213873](https://github.com/burckhju/trading-workspace/actions/runs/41171213873) |
| Frontend, Main-Push | `success` | [41171213875](https://github.com/burckhju/trading-workspace/actions/runs/41171213875) |
| End-to-End, Main-Push | `success` | [41171214040](https://github.com/burckhju/trading-workspace/actions/runs/41171214040) |

Sie beweisen weder den neuen UX-3-Dokumentations-Head noch eine spätere
Implementierung, Installation oder fachliche Abnahme.

### Lokale Dokumentations- und Vertragsprüfung

Am 31.10.2026 auf dem Dokumentationsbaum dieses PRs geprüft. Die Produktdateien
entsprechen unverändert Main `1883f7f330719453958f8be1dd51d48db816662e`.
Der veröffentlichte Commit und sein genauer Tree sind im Draft-PR gebunden;
dieser Text behauptet keinen sich selbst referenzierenden Commit-Hash.

| Prüfung | Befehl / tatsächlicher Umfang | Ergebnis |
| --- | --- | --- |
| Dokumentstruktur und Dateiverweise | `node --test docs/ui/ux-3/verify-docs.mjs` mit Node 22.16.0; sechs Dokumente, 80 eindeutige Inventurzeilen, relative Links, Tabellen, UTF-8, Codezäune, ausschließlich Typeimports und kein Produktimport | 5 Prüfungen bestanden. Linkprüfung prüft vorhandene Dateien, nicht URL-Erreichbarkeit oder alle Zeilenanker. |
| TypeScript-Vertrag | `node frontend/node_modules/typescript/bin/tsc -p docs/ui/ux-3/tsconfig.json`; TypeScript 5.8.3, strict/noEmit, bestehende Domain-DTOs | Bestanden, positive Beispiele und 19 erwartete negative Typfälle. Finanzielle Status-/Betragskonsistenz zusätzlich gegen den Owner gelesen; der Typcheck allein beweist sie nicht. |
| Format der Vertrags-/Prüfdateien | Prettier 3.5.3 mit `frontend/.prettierrc.json` für die beiden TS-Dateien, `tsconfig.json` und `verify-docs.mjs` | Bestanden nach Formatierung; keine Änderung der Projektkonfiguration. |
| Bestehende Frontend-Regressionen | Vitest 3.2.0 mit der in `frontend/.nvmrc` festgelegten Node-Version 22.16.0; die unten genannten 17 Dateien | **437 Tests bestanden**, 0 fehlgeschlagen. Keine vollständige Coverage-/Build-/E2E-Qualifikation daraus abgeleitet. |
| Scope und Whitespace | Gestagter Diff: ausschließlich zehn neue Dateien unter `docs/ui/ux-3/`; `git diff --cached --check` | Bestanden; keine Produktions-, Workflow-, Versions- oder Lockfileänderung. |

Der erste zusätzliche lokale Frontendversuch mit vorinstalliertem Node 24.22.1
zeigte Fehler bei Navigationstests und wurde ohne vollständigen Abschluss
beendet. Er zählt nicht als bestandener Lauf. Der anschließende Lauf mit
Projekt-Node 22.16.0 bestand dieselben 17 Dateien unverändert. Eine eindeutige
Ursache des abweichenden Laufzeit-/Ausführungsumfelds wurde nicht diagnostiziert;
keine Testerwartung und kein Timeout wurden dafür geändert. Im erfolgreichen
Lauf blieb eine React-`act`-Warnung im vorhandenen Produktauswahl-Kontexttest
sichtbar; der Lauf wird nicht als warnungsfrei bezeichnet.

Reproduktion nach `npm ci` im Frontend und Wahl von Node 22.16.0:

```bash
node --test docs/ui/ux-3/verify-docs.mjs
node frontend/node_modules/typescript/bin/tsc -p docs/ui/ux-3/tsconfig.json
node frontend/node_modules/prettier/bin/prettier.cjs --config frontend/.prettierrc.json --check docs/ui/ux-3/contracts.ts docs/ui/ux-3/contracts.type-test.ts docs/ui/ux-3/tsconfig.json docs/ui/ux-3/verify-docs.mjs
```

Der ausgeführte Vitestlauf nutzte Node 22.16.0 über
`npm exec --yes --package=node@22.16.0 -- node node_modules/vitest/vitest.mjs run`
im Verzeichnis `frontend`, mit genau diesen Pfaden als Argumenten:

```text
src/features/trade/components/ExecutionCurrencySources.test.tsx
src/features/trade/components/ExecutionCurrencyPanel.test.tsx
src/features/trade/components/ProductValuationPanel.currency.test.tsx
src/features/trade/pages/TradeManagementContext.test.tsx
src/features/trade/components/TradeSourcesView.test.tsx
src/features/performance/pages/PerformanceWorkspace.test.tsx
src/features/performance/services/performanceReportContext.test.ts
src/features/performance/services/closedReportContext.test.ts
src/features/operational_workspace/pages/MarketDataRefreshPanel.diagnostics.test.tsx
src/features/operational_workspace/components/PositionPriceHistory.test.tsx
src/features/alert/components/MonitoringRuntimePanel.test.tsx
src/features/product_selection/pages/ProductSelectionPage.context.test.tsx
src/features/product_selection/pages/ProductSelectionPage.test.tsx
src/features/trade_plan/pages/ExistingTradePlanPage.test.tsx
src/features/learning/components/TradeJournalPanel.test.tsx
src/features/learning/components/LessonReviewPanel.test.tsx
src/features/model/components/RuntimeActivationPanel.test.tsx
```

Die Dokumentationsprüfungen sind in diesem Schnitt lokale Prüfwerkzeuge und
noch kein eigener CI-Workflow. Die bestehenden vollständigen PR-Gates bleiben
zusätzlich unverändert. Lokale Backend-/PostgreSQL- oder Browser-E2E-Läufe wurden
für diesen Dokumentationsschnitt nicht ausgeführt; ihre gelesenen Testfälle
werden nicht als lokale Testerfolge gezählt.

### CI des neuen Draft-PRs

Der Draft-PR auf `docs/ux-3-notice-contract` enthält den genauen Head-SHA,
gegebenenfalls von GitHub geprüften Merge-SHA und die anschließend abgefragten
Workflowläufe in seiner Beschreibung und seinen Checks. Zum Erstellen dieses
Dokumentationscommits sind diese **noch nicht als erfolgreich behauptet**.
Ausstehend, abgebrochen und übersprungen sind keine bestandenen Tests. Ein
vorheriger grüner Head ist kein Nachweis für einen später geänderten Head.
Die Beschreibung kann aktuelle Prüfungsergebnisse ergänzen, ohne einen neuen
Produkt- oder Dokumentationscommit allein für die CI-Beobachtung zu erzeugen.

### Nicht als erledigt auszugeben

- Neue produktive UX-3-Adapter oder Komponenten: in dieser Phase nicht implementiert.
- Neue DOM-/E2E-Abnahmen der Szenarien TC-01 bis TC-48: geplant, noch offen.
- Mobile/Zoom-/Screenreaderprüfung einer UX-3-Implementierung: noch offen.
- Fachliche Abnahme, Merge nach Main, Veröffentlichung und PC-Installation von
  UX-3: nicht erfolgt.
