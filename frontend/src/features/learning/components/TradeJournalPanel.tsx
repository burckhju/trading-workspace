import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import {
  journalClient,
  type JournalCommand,
  type JournalEntry,
  type JournalHistory,
  type JournalTexts,
  type JournalVersion,
} from '../services/journalClient';
import { LessonDraftFromEvidence } from './LessonDraftFromEvidence';

const fields = [
  ['what_went_well', 'Was lief gut?'],
  ['would_do_differently', 'Was würde ich anders machen?'],
  ['additional_notes', 'Weitere Notizen'],
] as const;
const button = 'rounded border border-slate-600 px-3 py-2 text-sm disabled:opacity-50';
function texts(version: JournalTexts): JournalTexts {
  return {
    what_went_well: version.what_went_well ?? '',
    would_do_differently: version.would_do_differently ?? '',
    additional_notes: version.additional_notes ?? '',
  };
}
export function JournalVersionSource({ entry }: { entry: JournalEntry }) {
  const v = entry.version;
  return (
    <div className="space-y-1 break-all text-xs text-slate-400">
      <p>
        JournalVersion: {v.id} · {entry.is_latest ? 'Neuester Stand' : 'Historischer Stand'}
      </p>
      <p>
        ExitReviewVersion: {v.source_exit_review_version_id ?? 'Unbekannt (historischer Altstand)'}
      </p>
      <p>
        Quellenprüfung jetzt: {entry.source_currentness} · {entry.source_checked_at}
      </p>
      <p>
        Erfasst: {v.created_at} · Bearbeitet: {v.updated_at}
      </p>
      {v.finalized_at && (
        <p>
          Finalisiert: {v.finalized_at} · Actor: {v.finalized_by}
        </p>
      )}
      {v.supersedes_version_id && <p>Folgestand von: {v.supersedes_version_id}</p>}
      <p>
        Die Prüfung ist keine Aussage über damalige Datenkenntnis. Reflexion ist keine realisierte
        Performance.
      </p>
    </div>
  );
}

export function TradeJournalPanel({
  tradeId,
  refreshVersion = 0,
}: {
  tradeId: string;
  refreshVersion?: number;
}) {
  const [history, setHistory] = useState<JournalHistory | null>(null);
  const [editor, setEditor] = useState<JournalVersion | null>(null);
  const [form, setForm] = useState<JournalTexts>({
    what_went_well: '',
    would_do_differently: '',
    additional_notes: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<JournalCommand | null>(null);
  const [lessonId, setLessonId] = useState<string | null>(null);
  const active = useRef(true);
  const pending = useRef(false);
  const readNumber = useRef(0);
  const attempt = useRef<{ signature: string; key: string } | null>(null);
  const initialVersionId = useRef(
    new URLSearchParams(window.location.search).get('journal_version_id'),
  );
  const choose = useCallback((version: JournalVersion | null) => {
    setEditor(version);
    setForm(
      texts(version ?? { what_went_well: '', would_do_differently: '', additional_notes: '' }),
    );
    setConfirm(null);
    setLessonId(null);
  }, []);
  const load = useCallback(
    async (reset = false, preferredId?: string) => {
      const number = ++readNumber.current;
      try {
        const next = await journalClient.history(tradeId);
        if (!active.current || number !== readNumber.current) return;
        setHistory(next);
        setError(null);
        if (reset)
          choose(
            next.versions.find((v) => v.version.id === preferredId)?.version ??
              next.versions[0]?.version ??
              null,
          );
        else
          setEditor((previous) => {
            if (previous) return previous;
            const first =
              next.versions.find((v) => v.version.id === initialVersionId.current)?.version ??
              next.versions[0]?.version ??
              null;
            if (first) setForm(texts(first));
            return first;
          });
      } catch {
        if (active.current && number === readNumber.current)
          setError('Journal konnte nicht geladen werden. Ungespeicherter Text bleibt erhalten.');
      }
    },
    [choose, tradeId],
  );
  useEffect(() => {
    active.current = true;
    void load();
    const reads = readNumber;
    return () => {
      active.current = false;
      ++reads.current;
    };
  }, [load, refreshVersion]);
  async function submit(command: JournalCommand) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError(null);
    setConfirm(null);
    const signature = JSON.stringify(command);
    if (attempt.current?.signature !== signature)
      attempt.current = { signature, key: `journal:${crypto.randomUUID()}` };
    try {
      const receipt = await journalClient.command(tradeId, command, attempt.current.key);
      if (active.current) {
        // Read-back, not a receipt, owns mutable draft state.
        attempt.current = null;
        await load(
          true,
          receipt.result_type === 'TRADE_JOURNAL_VERSION'
            ? receipt.result_id
            : 'version_id' in command
              ? command.version_id
              : undefined,
        );
      }
    } catch (e) {
      if (active.current)
        setError(
          `${e instanceof Error ? e.message : 'Journaländerung fehlgeschlagen.'} Text bleibt erhalten. Bei Konflikt gespeicherten Stand bewusst laden; bei unklarer Antwort denselben Befehl wiederholen.`,
        );
    } finally {
      pending.current = false;
      if (active.current) setBusy(false);
    }
  }
  const entry = history?.versions.find((v) => v.version.id === editor?.id);
  const dirty = editor && JSON.stringify(texts(editor)) !== JSON.stringify(form);
  const latest = history?.versions[0]?.version;
  const sourceId = history?.handoff.ready ? history.handoff.exit_review_version_id : null;
  return (
    <section
      aria-label="Trade-Journal"
      className="mt-6 space-y-4 rounded-xl border border-slate-700 p-5"
    >
      <h2 className="text-lg font-semibold">Trade-Journal</h2>
      <p className="text-sm text-slate-400">
        Persönliche Reflexion, nicht Exit Review, Lesson oder Performance. Alle drei Textfelder sind
        optional. Ein Abschluss sichert nur den gespeicherten Stand.
      </p>
      {error && (
        <p role="alert" className="text-sm text-red-300">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <button className={button} disabled={busy} onClick={() => void load()}>
          Quellenstand neu laden
        </button>
        <button className={button} disabled={busy} onClick={() => void load(true, editor?.id)}>
          Gespeicherten Journalstand laden (lokalen Text verwerfen)
        </button>
      </div>
      {!history && !error && <p role="status">Journal wird geladen …</p>}
      {history && !history.handoff.ready && (
        <p className="text-amber-300">
          Neuer Entwurf / Abschluss noch nicht bereit: {history.handoff.reason}. Bestehende Entwürfe
          bleiben bearbeitbar.
        </p>
      )}
      {sourceId && latest?.status !== 'DRAFT' && (
        <button
          className={button}
          disabled={busy}
          onClick={() =>
            setConfirm({
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
      {history && history.versions.length === 0 && <p>Noch kein Journal gespeichert.</p>}
      <nav aria-label="Journalversionen" className="flex flex-wrap gap-2">
        {history?.versions.map(({ version }) => (
          <button
            key={version.id}
            className={button}
            disabled={busy}
            onClick={() => {
              if (!dirty) choose(version);
              else setError('Ungespeicherten Text zuerst speichern oder bewusst verwerfen.');
            }}
          >
            Journal V{version.version} · {version.status === 'DRAFT' ? 'Entwurf' : 'Finalisiert'}
          </button>
        ))}
      </nav>
      {editor && entry && (
        <>
          <h3 className="font-semibold">
            Journal V{editor.version} ·{' '}
            {editor.status === 'DRAFT' ? 'Entwurf' : 'Finalisiert (unveränderlich)'}
          </h3>
          <JournalVersionSource entry={entry} />
          {editor.status === 'DRAFT' ? (
            <>
              {fields.map(([key, label]) => (
                <label key={key} className="block text-sm">
                  {label}
                  <textarea
                    aria-label={label}
                    disabled={busy}
                    value={form[key] ?? ''}
                    onChange={(event) =>
                      setForm((previous) => ({ ...previous, [key]: event.target.value }))
                    }
                    className="mt-1 block min-h-20 w-full rounded border border-slate-600 bg-slate-950 p-2"
                  />
                </label>
              ))}
              <p className="text-xs">
                Änderungsstand {editor.edit_revision} ·{' '}
                {dirty ? 'Ungespeicherte Änderungen' : 'Gespeicherter Stand'}
              </p>
              <div className="flex flex-wrap gap-3">
                <button
                  className={button}
                  disabled={busy}
                  onClick={() =>
                    void submit({
                      operation: 'SAVE_DRAFT',
                      version_id: editor.id,
                      expected_edit_revision: editor.edit_revision,
                      ...form,
                    })
                  }
                >
                  Journalentwurf speichern
                </button>
                <button
                  className={button}
                  disabled={
                    busy ||
                    !!dirty ||
                    !sourceId ||
                    sourceId !== editor.source_exit_review_version_id ||
                    entry.source_currentness !== 'CURRENT'
                  }
                  onClick={() =>
                    sourceId &&
                    setConfirm({
                      operation: 'FINALIZE',
                      version_id: editor.id,
                      expected_edit_revision: editor.edit_revision,
                      expected_exit_review_version_id: sourceId,
                      confirmed: true,
                    })
                  }
                >
                  Journal finalisieren
                </button>
                {sourceId && sourceId !== editor.source_exit_review_version_id && (
                  <button
                    className={button}
                    disabled={busy || !!dirty}
                    onClick={() =>
                      setConfirm({
                        operation: 'REBIND_SOURCE',
                        version_id: editor.id,
                        expected_edit_revision: editor.edit_revision,
                        expected_exit_review_version_id: sourceId,
                        confirmed: true,
                      })
                    }
                  >
                    Neue Review-Quelle übernehmen
                  </button>
                )}
              </div>
            </>
          ) : (
            <>
              {fields.map(([key, label]) => (
                <div key={key}>
                  <h4 className="text-sm text-slate-400">{label}</h4>
                  <p className="whitespace-pre-wrap">
                    {editor[key]?.trim() ? editor[key] : 'Nicht ausgefüllt'}
                  </p>
                </div>
              ))}
              {fields.every(([key]) => !editor[key]?.trim()) && (
                <p className="text-amber-300">
                  Inhaltsleerer Abschluss – keine persönliche Bewertung dokumentiert.
                </p>
              )}
              {!entry.learning_evidence_id && (
                <button
                  className={button}
                  disabled={busy}
                  onClick={() =>
                    setConfirm({ operation: 'MATERIALIZE', version_id: editor.id, confirmed: true })
                  }
                >
                  Journalversion als Evidence übergeben
                </button>
              )}
              {entry.learning_evidence_id && (
                <>
                  <p className="break-all text-xs">
                    LearningEvidence: {entry.learning_evidence_id} · Typ TRADE_JOURNAL_VERSION
                  </p>
                  <p>
                    Explizite Lesson-Ableitung mit Relation SUPPORTS (unterstützende persönliche
                    Reflexion).
                  </p>
                  <LessonDraftFromEvidence
                    key={entry.learning_evidence_id}
                    learningEvidenceId={entry.learning_evidence_id}
                    onCreated={setLessonId}
                  />
                  {lessonId && (
                    <Link className="text-emerald-300 underline" to={`/lessons/${lessonId}`}>
                      Angelegte Lesson öffnen
                    </Link>
                  )}
                </>
              )}
            </>
          )}
        </>
      )}
      {confirm && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Journalaktion bestätigen"
          className="space-y-3 rounded border border-amber-600 p-4"
        >
          <h3 className="font-semibold">
            {confirm.operation === 'FINALIZE'
              ? 'Gespeichertes Journal unveränderlich abschließen?'
              : 'Journalaktion bewusst bestätigen'}
          </h3>
          <p>
            {confirm.operation === 'CREATE_DRAFT' && latest
              ? 'Die letzte finale Version bleibt erhalten. Ihre Texte werden als bearbeitbare Vorlage kopiert.'
              : 'Keine Ausführung, Lesson oder Modelländerung wird automatisch ausgelöst.'}
          </p>
          <p className="break-all text-xs">
            Trade: {tradeId} · {confirm.operation} · Quelle:{' '}
            {'expected_exit_review_version_id' in confirm
              ? confirm.expected_exit_review_version_id
              : confirm.version_id}
          </p>
          {confirm.operation === 'FINALIZE' &&
            editor &&
            fields.map(([key, label]) => (
              <p key={key} className="whitespace-pre-wrap text-sm">
                {label}: {editor[key]?.trim() ? editor[key] : 'Nicht ausgefüllt'}
              </p>
            ))}
          {confirm.operation === 'MATERIALIZE' && (
            <p>
              Diese historische persönliche Reflexion wird referenzierbar. Veraltete Quellen und
              frühere Inhalte werden dadurch nicht aktuell.
            </p>
          )}
          <button className={button} disabled={busy} onClick={() => void submit(confirm)}>
            Journalaktion bestätigen
          </button>
          <button className={button} onClick={() => setConfirm(null)}>
            Abbrechen
          </button>
        </div>
      )}
    </section>
  );
}
