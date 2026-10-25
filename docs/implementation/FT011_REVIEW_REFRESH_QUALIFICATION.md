# FT-011: durchgängige Sperre während Review-Rücklesevorgängen

Entscheidung und Auftragsfreigabe: **25.10.2026**.
Basis: Main `8d3416667aefaabb4b0363050c6c65789fcbaed8`,
Tree `03b13e12d46651ebef431e2006e305342d78aa24`.

Dieser begrenzte Folgefix ist vom Nutzer nach der Übergabe des
[Statistik-Draft-PR #282](https://github.com/burckhju/trading-workspace/pull/282)
ausdrücklich autorisiert. Er korrigiert die Freigabe der bestehenden FT-011-Oberfläche
und sichert den vorhandenen nativen Fall ab. Er erweitert weder den fachlichen
Review-Lifecycle noch den Statistikumfang. Merge, Veröffentlichung, neue Version und
PC-Update bleiben separat.

## Konkreter Ausgangsbefund

Im [E2E-Lauf 40204075023](https://github.com/burckhju/trading-workspace/actions/runs/40204075023),
Job `121201163369`, scheiterte der bestehende Fall
`real PostgreSQL: FT011 history survives correction and opens the exact Lesson version`.
Geprüfter PR-Head war `2031e20f10e451b7bb49743b1f0e3c5cd2c41b5e`, tatsächlicher
Testmerge `6c619d5011b6d8b71c8e92249e5c129bd3dbb056`, gemeinsamer Tree
`7ec6e9d1e2f57994ea4939236753c06fdeee26b6`.

Der [archivierte Fehlertrace](https://github.com/burckhju/trading-workspace/actions/runs/40204075023/artifacts/12603540384)
zeigt diese Reihenfolge; Zeiten sind relative Trace-Millisekunden:

1. Der Revalidierungs-POST liefert HTTP 200 für V1 / FINALIZED / STALE.
2. Der eigene abschließende Review-GET endet bei 8385,451 ms.
3. Der Parent-Folgerefresh beginnt bei 8389,340 ms. Der Test sieht den Nachfolge-Button
   bei 8397,435 ms noch als aktiviert.
4. Im Eingabesnapshot bei 8405,589 ms ist derselbe Button wieder deaktiviert; der
   tatsächliche Mausklick bei 8410,586 ms aktiviert ihn nicht.
5. Der zweite Review-GET endet bei 8471,343 ms weiterhin mit V1. Es gibt keinen
   zweiten Review-Erstellungs-POST. Das folgende Ausfüllen der noch schreibgeschützten
   V1-Begründung läuft in den Timeout.

Die beteiligten Produktseiten und der native Fall waren gegenüber Main unverändert.
Der Fehlerlauf bleibt ein fehlgeschlagener Nachweis. Ein erfolgreicher früherer Lauf
oder eine Wiederholung desselben unveränderten Codes würde die Ursache nicht beheben.

## Produktkorrektur und erhaltene Verträge

Ein einziges `loading`-Flag wurde bisher sowohl von expliziten Aktionen als auch
vom extern ausgelösten Leseeffekt gesetzt und gelöscht. Die eigene Aktion gab es
frei, bevor der Effekt für die neue Parent-Refreshversion erneut laden konnte.

Die Korrektur trennt diese beiden Gründe für eine gesperrte Oberfläche:

- Die explizite Aktion beziehungsweise der manuelle Abruf bleibt bis zu seinem
  eigenen Abschluss aktiv.
- Die zuletzt vollständig behandelte externe Refreshversion wird separat quittiert.
  Solange sie von der angeforderten Version abweicht, ist die Oberfläche bereits
  **im Rendern** gesperrt. Die Sperre wartet nicht auf den Beginn des Leseeffekts.
- Der externe Effekt quittiert nur seine eigene, nicht abgebrochene Version. Sein
  Abschluss kann eine noch laufende explizite Aktion nicht freigeben.

Beide bestehenden Review-Rücklesevorgänge bleiben erhalten: zuerst der unmittelbare
Child-Refresh, anschließend der durch den Parent-Callback angeforderte Refresh.
Auch die Status-, Journal- und Evidence-History-Abfragen der umgebenden Seite bleiben
erhalten. Callback-Vertrag, API-Pfade, Requestfolge und fachliche Antworten ändern sich
nicht. Damit bleiben insbesondere der bisherige Rücklesepfad nach Draft-Speicherung
und die Zustandsklärung nach einer fehlgeschlagenen Aktion bestehen.

Die bestehenden Abort-, Sequenz- und Trade-Wechsel-Grenzen bleiben maßgeblich.
Finalisierte Reviews bleiben schreibgeschützt. Eine neue Review-Version entsteht
weiterhin nur durch einen ausdrücklichen Benutzerbefehl. Es gibt keine automatische
Finalisierung, Materialisierung, Wiederholung oder Umdeutung von SOURCE_BUSY.

Unverändert maßgeblich sind
[Review-Lifecycle](../decisions/ADR-S11-006-EXIT-REVIEW-IDENTITY-LIFECYCLE-AND-USER-ASSESSMENT.md),
[Review-Versionierung](../decisions/ADR-S11-008-PERSISTENCE-REVIEW-VERSIONING-AND-INPUT-FINGERPRINT.md)
und [FT-011-Evidence-Ownership](../decisions/ADR-POST-FT012-004-FT011-EVIDENCE-MATERIALIZATION-OWNERSHIP.md).

## Vorab festgelegte Regressionen

Die relevante Grenze ist ein tatsächlich gerenderter Freigabezustand, nicht nur der
später sichtbare Zustand nach allen Effekten. Der Regressionstest verwendet den echten
Review-Child mit einem Parent-Refresh-Harness und kontrolliert zurückgehaltenen
Antworten. Ein Layout-Effekt beobachtet die Button-Sperre genau beim Commit der neuen
Parent-Refreshversion, bevor passive Effekte die Oberfläche nachträglich sperren können.

Erwartet sind:

1. Beim Übergang vom eigenen Rücklesen zum extern angeforderten Rücklesen wird der
   Nachfolge-Button in keinem Commit freigegeben. Die externe Antwort darf dazu bewusst
   offen bleiben.
2. Erst nach dessen Abschluss wird die Nachfolgeaktion bedienbar. Ein einzelner Klick
   erzeugt genau einen Erstellungsbefehl und die tatsächlich neue Draft-Version.
3. Ein externer Leseabschluss während einer noch offenen Aktion gibt deren Controls
   nicht vorzeitig frei.
4. Bestehende Fehleranzeige, Abbruch-/Trade-Wechsel-Schutz und Erhalt ungespeicherter
   Interpretation bleiben durch die vorhandenen Tests abgesichert.

Der gezielte Test wird zunächst gegen den unveränderten Produktcode ausgeführt. Nur
ein reproduzierbarer Fehler an der beschriebenen Grenze und der anschließende Erfolg
mit der Korrektur ergeben einen aussagekräftigen Regressionstest. Es gibt keine Sleeps,
gelockerten Assertions, zusätzlichen Retries oder vergrößerten Timeouts.

## Nativer Nachweis

Der vorhandene FT-011-Fall behält Datei, vollständigen Titel und alle bestehenden
fachlichen Assertions. Die bisherige Finalisierungs-/Owner-Rücklesebarriere bleibt
unverändert: beide Review-GETs und sämtliche erfassten parallelen Ownerantworten
müssen vollständig abgeschlossen sein.

Zusätzlich bindet der Fall die zuvor unvollständig beobachtete Revalidierungs- und
Nachfolgeaktion an ihre tatsächlichen Antworten:

- Response-Erfassung vor dem jeweiligen Klick;
- vollständige erfolgreiche Revalidierungsantwort für dieselbe finalisierte V1 mit
  STALE sowie beide passenden Review-Rücklesevorgänge;
- genau ein Nachfolgeklick und HTTP 201 für V2 / DRAFT mit neuer Versions-ID und
  `supersedes_version_id` der zuvor geprüften V1;
- beide passenden Draft-Rücklesevorgänge und erst danach die editierbare Begründung;
- vollständige parallele Ownerantworten und archivierte Bodies im vorhandenen
  Artefaktweg, bevor der nächste Owner-Schreibschritt beginnt.

Diese zusätzliche Synchronisierung ersetzt die Produktkorrektur nicht. Der
deterministische Frontendtest prüft die tatsächliche Sperrlücke; der native Fall
prüft den vollständigen Browser-/API-/PostgreSQL-Weg und die exakten Versionen.

Der unveränderte isolierte Runner, seine Guards, beiden Testidentitäten,
Nichtmutationsfenster, Artefaktmanifeste und der Cleanup-Vertrag aus
[JOURNAL_EVIDENCE_E2E_QUALIFICATION.md](JOURNAL_EVIDENCE_E2E_QUALIFICATION.md)
gelten weiter. Ebenso bleiben die anderen nativen Performance-, Journal- und
Governancefälle sowie alle regulären PR-Gates erhalten.

## Qualifikation und Integration

Lokal wurden die korrigierten neuen Erwartungen zunächst in einer separaten Kopie
des unveränderten Main-Frontends geprüft: **18 Tests, genau die zwei erwarteten
Race-Fehler, 16 bestanden**. Der Abbruch-/Fehler-Erhaltungsfall bestand bereits dort.
Mit der Produktkorrektur bestanden anschließend **46 Tests in sieben unmittelbar
betroffenen Dateien**, einschließlich aller 18 Review- und elf Learning-Page-Fälle,
Journal, Evidence-History und der zugehörigen Materialisierungs-/Lesson-Rücklesewege.
Diese lokalen Läufe verwenden Node 24.22.1; den regulären Node-22-Nachweis liefert
die unveränderte PR-CI.

Lokale Ergebnisse, der erste fehlgeschlagene Lauf und neue CI-Ergebnisse werden
getrennt ausgewiesen. Finale Commit-/Tree-/Testmerge-Zuordnung, tatsächliche Runs,
Artefakt-Digests und Sichtprüfung stehen in der Übergabe des zugehörigen Draft-PR.
Ein geänderter Test, erfolgreiche Discovery oder ein Artefaktupload allein sind kein
bestandener nativer Fall.

Der Fix erhält einen eigenen Branch und Draft-PR gegen Main. Sein tatsächlicher
Commit wird zusätzlich regulär in den Statistikbranch übernommen, damit der
gemeinsame Stand mit unveränderten Gates qualifiziert wird. Die beiden PRs bleiben
Drafts; eine Übernahme des Fixes auf einen Arbeitsbranch ist keine Main-Integration.
Nach jeder relevanten Main-Fortschreibung sind Basis und kombinierter Nachweis erneut
abzugleichen. Backendowner, Schema, Provider, Gates, Version, Paket-/Lockdateien und
Releasewege gehören nicht zu diesem Folgefix.
