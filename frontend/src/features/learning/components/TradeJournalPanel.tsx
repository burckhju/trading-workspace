import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { tradeLessonLink } from '../../../shared/trade-workspace-navigation';

import type { JournalEntry } from '../services/journalClient';
import { JournalDialog, JournalTextsView, journalButton as button } from './JournalContent';
import { journalFields } from './journalViewState';
import { LessonDraftFromEvidence } from './LessonDraftFromEvidence';
import {
  useTradeJournal,
  type JournalNavigationState,
  type JournalPanelProps,
} from './useTradeJournal';

export function JournalVersionSource({ entry }: { entry: JournalEntry }) {
  const version = entry.version;
  return (
    <div className="space-y-2 text-xs text-slate-400">
      <p>
        Bearbeitungsrevision {version.edit_revision} · {version.status} ·{' '}
        {entry.is_latest ? 'Neuester Stand' : 'Historischer Stand'}
      </p>
      <p className="break-all">
        Reviewquelle: {version.source_exit_review_version_id ?? 'Unbekannt (historischer Altstand)'}
      </p>
      <p className="break-words">
        Quellenprüfung jetzt: {entry.source_currentness} · {entry.source_checked_at}
      </p>
      <details>
        <summary className="cursor-pointer">Technische Journalherkunft und Audit</summary>
        <div className="mt-2 space-y-1 break-all">
          <p>JournalVersion: {version.id}</p>
          <p>Journal: {version.trade_journal_id}</p>
          <p>ExitReviewVersion: {version.source_exit_review_version_id ?? 'Unbekannt'}</p>
          <p>
            Erfasst: {version.created_at} · Actor: {version.created_by}
          </p>
          <p>
            Bearbeitet: {version.updated_at} · Actor: {version.updated_by}
          </p>
          {version.finalized_at && (
            <p>
              Finalisiert: {version.finalized_at} · Actor: {version.finalized_by}
            </p>
          )}
          {version.supersedes_version_id && <p>Folgestand von: {version.supersedes_version_id}</p>}
        </div>
      </details>
      <p>
        Die heutige Quellenprüfung ändert weder den historischen Inhalt noch seine damalige
        Herkunft.
      </p>
    </div>
  );
}

/** The page owns the single navigation guard; this key only isolates completed context changes. */
export function TradeJournalPanel(props: JournalPanelProps) {
  return <JournalContext key={props.tradeId} {...props} />;
}

function JournalContext(props: JournalPanelProps) {
  const { tradeId, discardVersion = 0, onNavigationStateChange } = props;
  const [query] = useSearchParams();
  const navigation = useRef({
    journal: { dirty: false, pending: false },
    lesson: { dirty: false, pending: false },
  });
  const reporter = useRef(onNavigationStateChange);
  reporter.current = onNavigationStateChange;
  const active = useRef(true);
  useLayoutEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      reporter.current?.({ dirty: false, pending: false });
    };
  }, []);
  const [lessonState, setLessonState] = useState<JournalNavigationState>({
    dirty: false,
    pending: false,
  });
  const journalChanged = useCallback((value: JournalNavigationState) => {
    if (!active.current) return;
    navigation.current.journal = value;
    reporter.current?.({
      dirty: value.dirty || navigation.current.lesson.dirty,
      pending: value.pending || navigation.current.lesson.pending,
    });
  }, []);
  const lessonChanged = useCallback((value: JournalNavigationState) => {
    if (!active.current) return;
    navigation.current.lesson = value;
    setLessonState(value);
    reporter.current?.({
      dirty: value.dirty || navigation.current.journal.dirty,
      pending: value.pending || navigation.current.journal.pending,
    });
  }, []);
  const journal = useTradeJournal({ ...props, onNavigationStateChange: journalChanged });
  const { state, entry, dirty, conflict, canAct } = journal;
  const [localDecision, setLocalDecision] = useState<'discard' | 'load' | null>(null);
  const [boundEvidence, setBoundEvidence] = useState<string | null>(null);
  const [lessonDiscard, setLessonDiscard] = useState(0);
  const evidenceId = entry?.learning_evidence_id ?? null;
  const lessonHeld = lessonState.dirty || lessonState.pending;
  useEffect(() => {
    // A failed read must not unmount a live interpretation. Actual source changes
    // are passed to the form, whose explicit context decision owns the reset.
    if (!lessonHeld) setBoundEvidence(evidenceId);
  }, [evidenceId, lessonHeld]);
  useEffect(() => {
    setLocalDecision(null);
  }, [discardVersion, state.queryKey]);
  const latest = state.history?.versions.find((item) => item.is_latest)?.version;
  const draft = state.history?.versions.find((item) => item.version.status === 'DRAFT')?.version;
  const sourceId = state.history?.handoff.ready
    ? state.history.handoff.exit_review_version_id
    : null;
  const visible = !journal.queryError && state.history !== null;
  const busy = state.pending || lessonState.pending || !!props.isContextPending?.();
  const confirm = state.confirmation;
  const version = entry?.version;
  const sourceMatches =
    !!sourceId &&
    sourceId === version?.source_exit_review_version_id &&
    entry?.source_currentness === 'CURRENT';
  const requestLoad = () => {
    if (busy || props.isContextPending?.()) return;
    if (dirty || state.editor || conflict || state.attempt) setLocalDecision('load');
    else journal.loadSaved();
  };

  return (
    <section
      aria-label="Trade-Journal"
      className="mt-6 min-w-0 space-y-4 rounded-xl border border-slate-700 p-4 sm:p-5"
    >
      <h2 tabIndex={-1} className="text-lg font-semibold">
        Trade-Journal
      </h2>
      <p className="text-sm text-slate-400">
        Persönliche Reflexion, nicht Exit Review, Lesson oder Performance. Alle drei Textfelder sind
        optional. Ein Abschluss sichert nur den gespeicherten Stand.
      </p>
      {(journal.queryError || state.error) && (
        <p role="alert" className="text-sm text-red-300">
          {journal.queryError ?? state.error}
        </p>
      )}
      {state.notice && (
        <p role="status" className="text-sm text-emerald-300">
          {state.notice}
        </p>
      )}
      {state.readState === 'loading' && (
        <p role="status" className="text-sm text-slate-400">
          Journal wird geladen … Vorhandene Eingaben bleiben erhalten.
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className={button}
          disabled={busy || !!journal.queryError}
          onClick={journal.refresh}
        >
          {state.attempt?.outcome === 'confirmed'
            ? 'Nur Lesestand erneut laden'
            : 'Quellenstand neu laden'}
        </button>
        {version && (
          <button
            type="button"
            className={button}
            disabled={busy || !!journal.queryError || state.readState === 'loading'}
            onClick={requestLoad}
          >
            Gespeicherten Journalstand laden (lokalen Text verwerfen)
          </button>
        )}
      </div>
      {state.attempt?.outcome === 'unknown' && (
        <div className="space-y-2 rounded border border-amber-800 p-3 text-sm">
          <p>
            Der ursprüngliche Auftrag bleibt eingefroren: {state.attempt.command.operation}. Ein
            identischer Retry sendet dieselben Eingaben mit demselben Schlüssel und Actor.
          </p>
          <button type="button" className={button} disabled={busy} onClick={journal.retry}>
            Identischen Journalauftrag erneut senden
          </button>
        </div>
      )}
      {visible && state.history && !state.history.handoff.ready && (
        <p className="text-sm text-amber-300">
          Neuer Entwurf / Abschluss noch nicht bereit: {state.history.handoff.reason}. Bestehende
          Entwürfe bleiben bearbeitbar.
        </p>
      )}
      {visible && state.history?.versions.length === 0 && journal.ready && (
        <p>Noch kein Journal gespeichert.</p>
      )}
      {visible && state.history && state.history.versions.length > 0 && (
        <nav aria-label="Journalversionen">
          <label className="block text-sm">
            <span className="text-slate-400">Journalversion ansehen</span>
            <select
              aria-label="Journalversion ansehen"
              className="mt-1 w-full max-w-lg rounded border border-slate-600 bg-slate-950 p-2"
              value={state.selectedId ?? ''}
              disabled={busy}
              onChange={(event) => journal.selectVersion(event.target.value)}
            >
              {state.history.versions.map(({ version: item }) => (
                <option key={item.id} value={item.id}>
                  Journal V{item.version} · {item.status === 'DRAFT' ? 'Entwurf' : 'Finalisiert'}
                </option>
              ))}
            </select>
          </label>
        </nav>
      )}
      {visible && !confirm && !localDecision && (
        <div className="flex flex-wrap gap-3">
          {draft && draft.id !== state.selectedId && (
            <button
              type="button"
              className={button}
              disabled={busy}
              onClick={() => journal.selectVersion(draft.id)}
            >
              Vorhandenen Journalentwurf öffnen
            </button>
          )}
          {!draft && sourceId && journal.ready && (
            <button
              type="button"
              className={button}
              disabled={!canAct || busy || dirty}
              onClick={() =>
                journal.openConfirmation({
                  operation: 'CREATE_DRAFT',
                  expected_latest_version_id: latest?.id ?? null,
                  expected_exit_review_version_id: sourceId,
                  confirmed: true,
                })
              }
            >
              {latest ? 'Folgeversion vorbereiten' : 'Journalentwurf anlegen'}
            </button>
          )}
        </div>
      )}
      {visible && version && entry && (
        <>
          <h3 className="font-semibold">
            Journal V{version.version} ·{' '}
            {version.status === 'DRAFT' ? 'Entwurf' : 'Finalisiert (unveränderlich)'}
          </h3>
          <JournalVersionSource entry={entry} />
        </>
      )}
      {conflict && (
        <p role="alert" className="text-sm text-amber-300">
          Der gespeicherte Stand hat sich geändert. Lokale Eingaben beruhen weiterhin auf
          Bearbeitungsrevision {state.editor?.base.edit_revision ?? 'des bestätigten Auftrags'}.
          Speichern und Abschluss bleiben bis zum bewussten Abgleich gesperrt.
        </p>
      )}
      {localDecision ? (
        <JournalDialog
          returnFocusLabel={
            localDecision === 'load'
              ? 'Gespeicherten Journalstand laden (lokalen Text verwerfen)'
              : 'Bearbeitung abbrechen'
          }
          title={
            localDecision === 'load'
              ? 'Lokale Eingaben verwerfen und gespeicherten Stand laden?'
              : 'Bearbeitung verwerfen und zum gespeicherten Journal zurückkehren?'
          }
          confirmLabel={
            localDecision === 'load'
              ? 'Verwerfen und gespeicherten Stand laden'
              : 'Verwerfen und Lesemodus öffnen'
          }
          busy={busy}
          onCancel={() => {
            if (!props.isContextPending?.()) setLocalDecision(null);
          }}
          onConfirm={() => {
            if (props.isContextPending?.()) return;
            setLocalDecision(null);
            if (localDecision === 'load') journal.loadSaved();
            else journal.cancelEdit();
          }}
        >
          <p>
            Es wird kein Schreibbefehl ausgelöst. Beim Abbrechen bleiben sämtliche lokalen
            Journaltexte erhalten.
          </p>
          {state.attempt && (
            <p>
              Der bisherige Schreibauftrag wird dadurch nicht rückgängig gemacht. Sein Receipt ist
              kein aktueller Entwurfssnapshot.
            </p>
          )}
        </JournalDialog>
      ) : confirm ? (
        <JournalDialog
          returnFocusLabel={
            confirm.command.operation === 'FINALIZE'
              ? 'Journal finalisieren'
              : confirm.command.operation === 'REBIND_SOURCE'
                ? 'Neue Review-Quelle übernehmen'
                : confirm.command.operation === 'MATERIALIZE'
                  ? 'Journalversion als Evidence übergeben'
                  : confirm.copySource
                    ? 'Folgeversion vorbereiten'
                    : 'Journalentwurf anlegen'
          }
          title={
            confirm.command.operation === 'FINALIZE'
              ? 'Gespeichertes Journal unveränderlich abschließen?'
              : 'Journalaktion bewusst bestätigen'
          }
          disabled={!journal.confirmationValid}
          busy={busy}
          onCancel={journal.cancelConfirmation}
          onConfirm={journal.confirm}
        >
          {!journal.confirmationValid && (
            <p role="alert">
              Diese Bestätigung ist nicht mehr aktuell oder der Lesestand ist ungeklärt. Bitte
              abbrechen, neu lesen und die genaue Version erneut bestätigen.
            </p>
          )}
          <p className="break-all text-xs">
            Trade: {tradeId} · {confirm.command.operation} · Quelle:{' '}
            {'expected_exit_review_version_id' in confirm.command
              ? confirm.command.expected_exit_review_version_id
              : confirm.command.version_id}
          </p>
          {confirm.command.operation === 'CREATE_DRAFT' ? (
            <p>
              {confirm.copySource
                ? `Kopierursprung: letzte finale Journal V${confirm.copySource.version}, ID ${confirm.copySource.id}. Ihre gespeicherten Texte werden serverseitig übernommen.`
                : 'Ein erster Journalentwurf mit drei optionalen, leeren Textfeldern wird angelegt.'}{' '}
              Vorhandene finale Versionen, Evidence und Lessons bleiben erhalten.
            </p>
          ) : (
            confirm.saved && (
              <>
                <p className="break-all text-sm">
                  Gespeicherter Stand: Journal V{confirm.saved.version} · Bearbeitungsrevision{' '}
                  {confirm.saved.edit_revision} · {confirm.saved.status} · ID {confirm.saved.id}
                </p>
                <p className="break-all text-xs">
                  Gespeicherte Reviewquelle:{' '}
                  {confirm.saved.source_exit_review_version_id ?? 'Unbekannt'}
                </p>
                <JournalTextsView
                  value={confirm.saved}
                  finalized={
                    confirm.command.operation === 'FINALIZE' || confirm.saved.status === 'FINALIZED'
                  }
                />
              </>
            )
          )}
          {confirm.command.operation === 'MATERIALIZE' && (
            <p>
              Genau diese finale persönliche Reflexion wird als TRADE_JOURNAL_VERSION
              referenzierbar. Historische oder veraltete Quellen werden dadurch nicht aktuell.
            </p>
          )}
          {confirm.command.operation === 'REBIND_SOURCE' && (
            <p>
              Nur die Reviewbindung des gespeicherten Entwurfs wird bewusst geändert. Die
              Journaltexte bleiben erhalten.
            </p>
          )}
          <p className="text-sm text-slate-400">
            Keine Lesson oder Modelländerung wird automatisch ausgelöst.
          </p>
        </JournalDialog>
      ) : visible && version ? (
        <>
          {state.editor ? (
            <div className="space-y-3" aria-label="Journal bearbeiten">
              {journalFields.map(([field, label]) => (
                <label key={field} className="block text-sm">
                  {label}
                  <textarea
                    aria-label={label}
                    disabled={busy || state.readState === 'loading'}
                    value={state.editor?.texts[field] ?? ''}
                    onChange={(event) => journal.changeText(field, event.target.value)}
                    className="mt-1 block min-h-24 w-full rounded border border-slate-600 bg-slate-950 p-2"
                  />
                </label>
              ))}
              <p className="text-xs">
                Lokale Bearbeitungsbasis: Revision {state.editor.base.edit_revision} ·{' '}
                {dirty ? 'Ungespeicherte Änderungen' : 'Gespeicherter Stand'}
              </p>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  className={button}
                  disabled={!canAct || !dirty || busy}
                  onClick={journal.save}
                >
                  Journalentwurf speichern
                </button>
                <button
                  type="button"
                  className={button}
                  disabled={busy}
                  onClick={() => {
                    if (props.isContextPending?.()) return;
                    if (dirty || conflict) setLocalDecision('discard');
                    else journal.cancelEdit();
                  }}
                >
                  Bearbeitung abbrechen
                </button>
              </div>
            </div>
          ) : (
            <JournalTextsView value={version} finalized={version.status === 'FINALIZED'} />
          )}
          <div className="flex flex-wrap gap-3">
            {version.status === 'DRAFT' && (
              <>
                {!state.editor && (
                  <button
                    type="button"
                    className={button}
                    disabled={!canAct || busy}
                    onClick={journal.edit}
                  >
                    Journal bearbeiten
                  </button>
                )}
                <button
                  type="button"
                  className={button}
                  disabled={!canAct || busy || dirty || !sourceMatches}
                  onClick={() =>
                    sourceId &&
                    journal.openConfirmation({
                      operation: 'FINALIZE',
                      version_id: version.id,
                      expected_edit_revision: version.edit_revision,
                      expected_exit_review_version_id: sourceId,
                      confirmed: true,
                    })
                  }
                >
                  Journal finalisieren
                </button>
                {sourceId && sourceId !== version.source_exit_review_version_id && (
                  <button
                    type="button"
                    className={button}
                    disabled={!canAct || busy || dirty}
                    onClick={() =>
                      journal.openConfirmation({
                        operation: 'REBIND_SOURCE',
                        version_id: version.id,
                        expected_edit_revision: version.edit_revision,
                        expected_exit_review_version_id: sourceId,
                        confirmed: true,
                      })
                    }
                  >
                    Neue Review-Quelle übernehmen
                  </button>
                )}
              </>
            )}
            {version.status === 'FINALIZED' && !entry?.learning_evidence_id && (
              <button
                type="button"
                className={button}
                disabled={!canAct || busy || !!state.editor}
                onClick={() =>
                  journal.openConfirmation({
                    operation: 'MATERIALIZE',
                    version_id: version.id,
                    confirmed: true,
                  })
                }
              >
                Journalversion als Evidence übergeben
              </button>
            )}
          </div>
        </>
      ) : null}
      {boundEvidence && (
        <div className="space-y-3 border-t border-slate-800 pt-4">
          <p className="break-all text-xs">
            LearningEvidence: {boundEvidence} · Typ TRADE_JOURNAL_VERSION
          </p>
          <p className="text-sm">
            Explizite Lesson-Ableitung mit Relation SUPPORTS (unterstützende persönliche Reflexion).
          </p>
          <LessonDraftFromEvidence
            lessonHref={(id) => tradeLessonLink(id, null, tradeId, query)}
            learningEvidenceId={evidenceId ?? boundEvidence}
            disabled={!journal.ready || busy || !!state.attempt || !evidenceId}
            discardVersion={discardVersion + lessonDiscard}
            onNavigationStateChange={lessonChanged}
            isContextPending={props.isContextPending}
          />
          {evidenceId !== boundEvidence && !evidenceId && (
            <div role="alert">
              <p>
                Die gelesene Evidencebindung fehlt. Der offene Lessonentwurf bleibt an seiner
                bisherigen Quelle; bitte zuerst den Quellenstand prüfen.
              </p>
              <button
                type="button"
                className={button}
                disabled={busy}
                onClick={() => {
                  if (!props.isContextPending?.()) setLessonDiscard((value) => value + 1);
                }}
              >
                Lessonentwurf verwerfen
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
