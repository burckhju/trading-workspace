import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { ErrorNotice } from '../../market/components/ApiFeedback';
import { MarketApiError } from '../../market/services/http';
import { EvidenceSourceStatus } from './EvidenceSourceStatus';
import { JournalEvidenceOrigin } from './JournalEvidenceOrigin';
import {
  evidenceLabel,
  lessonReviewClient,
  type EvidenceChoice,
  type EvidenceRelation,
  type EvidenceSummary,
  type ReviewCommand,
  type ReviewContext,
  type ReviewOperation,
  type ReviewReceipt,
  type LessonVersionSnapshot,
} from '../services/lessonReviewClient';

const actions: Record<ReviewOperation, string> = {
  OPEN_SOURCE_REVIEW: 'Quellenbezogene Prüfung beginnen',
  OPEN_CONTRADICTION_REVIEW: 'Widerspruchsprüfung beginnen',
  CONFIRM_UNCHANGED: 'Interpretation unverändert bestätigen',
  NEW_VERSION: 'Neue Lesson-Version vorbereiten',
  RETIRE: 'Lesson außer Gebrauch nehmen',
};
const inputClass = 'w-full rounded border border-slate-600 bg-slate-900 p-2';

type Preparation = { operation: ReviewOperation; context: ReviewContext };
export function LessonReviewPanel({
  lessonId,
  onChanged,
}: {
  lessonId: string;
  onChanged: () => void;
}) {
  const [context, setContext] = useState<ReviewContext | null>(null);
  const [readError, setReadError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [selectedVersion, setSelectedVersion] = useState('');
  const [preparation, setPreparation] = useState<Preparation | null>(null);
  const [reason, setReason] = useState('');
  const [category, setCategory] = useState('');
  const [content, setContent] = useState('');
  const [choices, setChoices] = useState<EvidenceChoice[]>([]);
  const [triggers, setTriggers] = useState<string[]>([]);
  const [catalog, setCatalog] = useState<EvidenceSummary[] | null>(null);
  const [catalogError, setCatalogError] = useState<unknown>(null);
  const [catalogRetry, setCatalogRetry] = useState(0);
  const [selectedEvidence, setSelectedEvidence] = useState('');
  const [busy, setBusy] = useState(false);
  const [writeError, setWriteError] = useState<unknown>(null);
  const [receipt, setReceipt] = useState<ReviewReceipt | null>(null);
  const active = useRef(false);
  const locked = useRef(false);
  const readSequence = useRef(0);
  const retryCommand = useRef<{ json: string; key: string } | null>(null);
  const reasonInput = useRef<HTMLTextAreaElement>(null);

  const load = useCallback(async () => {
    const sequence = ++readSequence.current;
    setLoading(true);
    setReadError(null);
    try {
      const value = await lessonReviewClient.context(lessonId);
      if (
        value.lesson.id !== lessonId ||
        !value.history.some((v) => v.version.id === value.lesson.current_version_id)
      )
        throw new Error('Der gelesene Lesson-Kontext ist nicht vollständig.');
      if (active.current && sequence === readSequence.current) setContext(value);
    } catch (error) {
      if (active.current && sequence === readSequence.current) setReadError(error);
    } finally {
      if (active.current && sequence === readSequence.current) setLoading(false);
    }
  }, [lessonId]);
  useEffect(() => {
    active.current = true;
    void load();
    return () => {
      active.current = false;
      ++readSequence.current;
    };
  }, [load]);
  useEffect(() => {
    if (preparation) reasonInput.current?.focus();
  }, [preparation]);
  useEffect(() => {
    if (preparation?.operation !== 'NEW_VERSION') return;
    const controller = new AbortController();
    setCatalog(null);
    setCatalogError(null);
    void lessonReviewClient
      .evidence(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setCatalog(value);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setCatalogError(error);
      });
    return () => controller.abort();
  }, [preparation?.operation, catalogRetry]);

  const current = context?.history.find((v) => v.version.id === context.lesson.current_version_id);
  const viewed = context?.history.find(
    (v) => v.version.id === (selectedVersion || context.lesson.current_version_id),
  );
  const currentView = viewed?.version.id === context?.lesson.current_version_id;
  const openSignalId = (value: ReviewContext) =>
    value.signals.find((s) => s.signal.status === 'OPEN')?.signal.id ?? null;
  const contextChanged = !!(
    preparation &&
    context &&
    (preparation.context.lesson.current_version_id !== context.lesson.current_version_id ||
      preparation.context.lesson.current_state !== context.lesson.current_state ||
      openSignalId(preparation.context) !== openSignalId(context))
  );
  const prepare = (operation: ReviewOperation) => {
    if (!context || !current || loading || readError || locked.current) return;
    setPreparation({ operation, context });
    setReason('');
    setCategory(current.version.main_category);
    setContent(current.version.content);
    setChoices(
      current.evidence_links.map(({ learning_evidence_id, relation }) => ({
        learning_evidence_id,
        relation,
      })),
    );
    setTriggers([]);
    setWriteError(null);
    setReceipt(null);
    retryCommand.current = null;
  };
  const valid =
    !!preparation &&
    !!reason.trim() &&
    reason.length <= 200 &&
    (preparation.operation !== 'NEW_VERSION' ||
      (!!content.trim() &&
        !!category.trim() &&
        choices.some((c) => c.relation === 'SUPPORTS') &&
        new Set(choices.map((c) => c.learning_evidence_id)).size === choices.length)) &&
    (preparation.operation !== 'OPEN_CONTRADICTION_REVIEW' || triggers.length > 0);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!preparation || !valid || locked.current || contextChanged || loading || readError) return;
    const pinned = preparation.context;
    const base = {
      expected_current_version_id: pinned.lesson.current_version_id,
      expected_current_state: pinned.lesson.current_state,
      expected_open_signal_id: openSignalId(pinned),
      reason,
      confirmed: true as const,
    };
    let command: ReviewCommand;
    switch (preparation.operation) {
      case 'OPEN_SOURCE_REVIEW':
        command = {
          ...base,
          operation: preparation.operation,
          reviewed_evidence_ids: current!.evidence_links.map((v) => v.learning_evidence_id),
        };
        break;
      case 'OPEN_CONTRADICTION_REVIEW':
        command = { ...base, operation: preparation.operation, contradiction_link_ids: triggers };
        break;
      case 'NEW_VERSION':
        command = {
          ...base,
          operation: preparation.operation,
          main_category: category,
          content,
          evidence: choices,
        };
        break;
      default:
        command = { ...base, operation: preparation.operation };
    }
    const json = JSON.stringify(command);
    if (retryCommand.current?.json !== json)
      retryCommand.current = { json, key: crypto.randomUUID() };
    const key = retryCommand.current.key;
    locked.current = true;
    setBusy(true);
    setWriteError(null);
    try {
      const result = await lessonReviewClient.execute(lessonId, command, key);
      if (!active.current) return;
      setReceipt(result);
      setPreparation(null);
      setSelectedVersion('');
      await load();
      if (active.current) onChanged();
    } catch (error) {
      if (active.current) setWriteError(error);
    } finally {
      if (active.current) {
        locked.current = false;
        setBusy(false);
      }
    }
  };
  return (
    <section
      aria-label="Lesson-Prüfung und Historie"
      className="space-y-4 rounded-xl border border-slate-700 p-5"
    >
      <h2 className="text-lg font-semibold">Lesson prüfen und versionieren</h2>
      <p className="text-sm">
        CURRENT bezeichnet den Stand Ihrer Interpretation, nicht die Aktualität aller Quellen. Eine
        unveränderte Bestätigung repariert keine veraltete Evidenz.
      </p>
      {receipt && (
        <p role="status" className="break-all">
          {receipt.replayed
            ? 'Früheren Befehlsabschluss wiedergefunden'
            : 'Prüfentscheidung gespeichert'}
          : {receipt.result_id}. Der Lesestand wird gesondert geladen.
        </p>
      )}
      <button type="button" disabled={busy || loading} onClick={() => void load()}>
        Lesson-Prüfstand neu laden
      </button>
      {loading && <p role="status">Prüfkontext wird geladen …</p>}
      {readError !== null && (
        <>
          <ErrorNotice error={readError} />
          <p>
            Keine neue Bestätigung bis zum erfolgreichen Neuladen. Ein bestätigter Befehlsabschluss
            bleibt gültig.
          </p>
        </>
      )}
      {context && viewed && (
        <>
          <p>
            Lesestand: {context.read_at} · Lesson-Status: {context.lesson.current_state}
          </p>
          <label className="block">
            Lesson-Version ansehen
            <select
              className={inputClass}
              value={selectedVersion || context.lesson.current_version_id}
              disabled={busy || !!preparation}
              onChange={(e) => setSelectedVersion(e.target.value)}
            >
              {context.history.map((v) => (
                <option key={v.version.id} value={v.version.id}>
                  Version {v.version.version} · {v.version.created_at}
                  {v.version.id === context.lesson.current_version_id
                    ? ' · aktueller Stand'
                    : ' · historisch'}
                </option>
              ))}
            </select>
          </label>
          <article
            aria-label={`Lesson-Snapshot Version ${viewed.version.version}`}
            className="space-y-2 border-l-2 border-slate-700 pl-3"
          >
            <h3>
              Version {viewed.version.version}
              {!currentView && ' — schreibgeschützte Historie'}
            </h3>
            <p>Kategorie: {viewed.version.main_category}</p>
            <p className="whitespace-pre-wrap">{viewed.version.content}</p>
            <p className="break-all text-xs">
              Version-ID: {viewed.version.id} · Vorgänger:{' '}
              {viewed.version.supersedes_version_id ?? 'keiner'} · Erfasst:{' '}
              {viewed.version.created_at} · Actor: {viewed.version.created_by}
            </p>
            {viewed.evidence_links.map((link) => (
              <EvidenceLinkDetails key={`${link.id}:${context.read_at}`} link={link} />
            ))}
          </article>
          {currentView && !preparation && !receipt && (
            <div className="flex flex-wrap gap-3">
              {(context.lesson.current_state === 'CURRENT'
                ? [
                    'OPEN_SOURCE_REVIEW',
                    ...(current?.evidence_links.some((v) => v.relation === 'CONTRADICTS')
                      ? ['OPEN_CONTRADICTION_REVIEW']
                      : []),
                  ]
                : context.lesson.current_state === 'REVIEW_RECOMMENDED'
                  ? ['CONFIRM_UNCHANGED', 'NEW_VERSION', 'RETIRE']
                  : []
              ).map((op) => (
                <button
                  type="button"
                  key={op}
                  disabled={loading || readError !== null || busy}
                  onClick={() => prepare(op as ReviewOperation)}
                >
                  {actions[op as ReviewOperation]}
                </button>
              ))}
              {context.lesson.current_state === 'RETIRED' && (
                <p>Außer Gebrauch. Reaktivierung ist kein automatischer Teil dieser Prüfung.</p>
              )}
            </div>
          )}
          {receipt && !loading && !readError && (
            <button type="button" disabled={busy} onClick={() => setReceipt(null)}>
              Weitere ausdrückliche Prüfung vorbereiten
            </button>
          )}
        </>
      )}
      {preparation && (
        <form
          onSubmit={(event) => void submit(event)}
          aria-label="Lesson-Prüfentscheidung"
          className="space-y-4 rounded border border-slate-600 p-4"
        >
          <h3 className="font-semibold">{actions[preparation.operation]}</h3>
          <p className="break-all text-sm">
            Bestätigt wird genau Lesson-Version {preparation.context.lesson.current_version_id} ·{' '}
            {preparation.context.lesson.current_state}.
          </p>
          {contextChanged && (
            <p role="alert">
              Der Lesson-Stand hat sich geändert. Ihre Eingaben bleiben sichtbar; brechen Sie diesen
              Entwurf ab und bereiten Sie die Entscheidung erneut vor.
            </p>
          )}
          <fieldset disabled={busy} className="space-y-4">
            <label className="block">
              Begründung der Prüfentscheidung (Pflichtfeld, höchstens 200 Zeichen)
              <textarea
                ref={reasonInput}
                className={inputClass}
                value={reason}
                maxLength={200}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
            {preparation.operation === 'OPEN_CONTRADICTION_REVIEW' && (
              <fieldset>
                <legend>Konkrete widersprechende Links auswählen</legend>
                {current?.evidence_links
                  .filter((v) => v.relation === 'CONTRADICTS')
                  .map((v) => (
                    <label key={v.id} className="block break-all">
                      <input
                        type="checkbox"
                        checked={triggers.includes(v.id)}
                        onChange={(e) =>
                          setTriggers((old) =>
                            e.target.checked ? [...old, v.id] : old.filter((id) => id !== v.id),
                          )
                        }
                      />{' '}
                      CONTRADICTS · {v.learning_evidence_id}
                    </label>
                  ))}
              </fieldset>
            )}
            {preparation.operation === 'NEW_VERSION' && (
              <>
                <label className="block">
                  Kategorie der neuen Lesson-Version
                  <input
                    className={inputClass}
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  />
                </label>
                <label className="block">
                  Ausdrückliche Interpretation der neuen Lesson-Version
                  <textarea
                    className={inputClass}
                    rows={5}
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                  />
                </label>
                <p>
                  Vollständiger Evidence-Snapshot der neuen Version. Mindestens ein unterstützender
                  Bezug ist erforderlich. Alte Links werden nicht geändert; neuere Quellen werden
                  nicht automatisch ersetzt.
                </p>
                {choices.map((choice, i) => (
                  <div
                    key={choice.learning_evidence_id}
                    className="space-y-2 rounded border border-slate-700 p-3"
                  >
                    <p className="break-all">
                      Evidence {i + 1}: {choice.learning_evidence_id}
                    </p>
                    <label>
                      Bezug {i + 1}
                      <select
                        className={inputClass}
                        value={choice.relation}
                        onChange={(e) =>
                          setChoices((old) =>
                            old.map((c, index) =>
                              index === i
                                ? { ...c, relation: e.target.value as EvidenceRelation }
                                : c,
                            ),
                          )
                        }
                      >
                        <option value="SUPPORTS">SUPPORTS — unterstützt</option>
                        <option value="CONTRADICTS">CONTRADICTS — widerspricht</option>
                        <option value="CONTEXTUAL">CONTEXTUAL — Kontext</option>
                      </select>
                    </label>
                    <EvidenceSourceStatus evidenceId={choice.learning_evidence_id} />
                    <button
                      type="button"
                      onClick={() => setChoices((old) => old.filter((_, index) => index !== i))}
                    >
                      Evidence {i + 1} aus neuer Version entfernen
                    </button>
                  </div>
                ))}
                <label className="block">
                  Vorhandene Evidence ergänzen
                  <select
                    className={inputClass}
                    value={selectedEvidence}
                    onChange={(e) => setSelectedEvidence(e.target.value)}
                    disabled={!catalog}
                  >
                    <option value="">Quelle ausdrücklich auswählen</option>
                    {catalog
                      ?.filter(
                        (v) => !choices.some((c) => c.learning_evidence_id === v.evidence_id),
                      )
                      .map((v) => (
                        <option key={v.evidence_id} value={v.evidence_id}>
                          {evidenceLabel(v)}
                        </option>
                      ))}
                  </select>
                </label>
                <button
                  type="button"
                  disabled={
                    !selectedEvidence ||
                    !catalog ||
                    choices.some((c) => c.learning_evidence_id === selectedEvidence)
                  }
                  onClick={() => {
                    setChoices((old) => [
                      ...old,
                      { learning_evidence_id: selectedEvidence, relation: 'CONTEXTUAL' },
                    ]);
                    setSelectedEvidence('');
                  }}
                >
                  Ausgewählte Evidence hinzufügen
                </button>
                {catalogError !== null && (
                  <div role="alert">
                    Evidence-Auswahl nicht geladen.{' '}
                    <button type="button" onClick={() => setCatalogRetry((n) => n + 1)}>
                      Evidence-Auswahl erneut laden
                    </button>
                  </div>
                )}
              </>
            )}
            {preparation.operation === 'CONFIRM_UNCHANGED' && (
              <p>
                Sie bestätigen ausschließlich Ihre Interpretation. Quellversionen, Relation und
                Quellenwarnungen bleiben unverändert.
              </p>
            )}
            {preparation.operation === 'RETIRE' && (
              <p>
                Die Lesson wird außer Gebrauch genommen, nicht gelöscht. Historische Inhalte und
                Evidence-Links bleiben erhalten.
              </p>
            )}
            <p>
              Keine Hypothese, Modelländerung, Freigabe, Aktivierung oder Handelsausführung wird
              erzeugt.
            </p>
          </fieldset>
          {writeError !== null && (
            <>
              <ReviewWriteError error={writeError} />
              <p>
                Eingaben bleiben erhalten. Kein automatischer Retry; derselbe unveränderte Befehl
                verwendet beim erneuten Bestätigen denselben Schlüssel.
              </p>
            </>
          )}
          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={!valid || busy || loading || readError !== null || contextChanged}
            >
              Prüfentscheidung verbindlich bestätigen
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setPreparation(null);
                setWriteError(null);
              }}
            >
              Prüfentwurf abbrechen
            </button>
          </div>
        </form>
      )}
      {context && (
        <details>
          <summary>Prüfverlauf und Audit</summary>
          {context.signals.map(({ signal, trigger_link_ids }) => (
            <p key={signal.id} className="my-2 break-all">
              Widerspruchssignal {signal.id} · LessonVersion {signal.lesson_version_id} ·{' '}
              {signal.status} · {signal.resolution ?? 'noch nicht entschieden'} · Auslöser:{' '}
              {trigger_link_ids.join(', ')} · Ergebnisversion:{' '}
              {signal.resulting_lesson_version_id ?? 'keine'}
            </p>
          ))}
          {context.transitions.map((event) => (
            <p key={event.id} className="my-2 break-all">
              {event.occurred_at} · {event.from_state ?? 'Initial'} → {event.to_state} ·{' '}
              {event.reason} · LessonVersion {event.related_lesson_version_id ?? 'nicht angegeben'}{' '}
              · Actor {event.occurred_by}
            </p>
          ))}
        </details>
      )}
    </section>
  );
}

function EvidenceLinkDetails({ link }: { link: LessonVersionSnapshot['evidence_links'][number] }) {
  const [opened, setOpened] = useState(false);
  return (
    <details
      className="rounded border border-slate-800 p-2"
      onToggle={(event) => setOpened(event.currentTarget.open)}
    >
      <summary className="break-all">
        {link.relation} · Evidence {link.learning_evidence_id}
      </summary>
      {opened && (
        <>
          <p className="break-all text-xs">Unveränderlicher Link: {link.id}</p>
          <EvidenceSourceStatus evidenceId={link.learning_evidence_id} />
          <JournalEvidenceOrigin evidenceId={link.learning_evidence_id} />
        </>
      )}
    </details>
  );
}

function ReviewWriteError({ error }: { error: unknown }) {
  const code = error instanceof MarketApiError ? error.response.code : null;
  const conflict = code === 'LESSON_REVIEW_CONFLICT' || code === 'CONCURRENT_MODIFICATION';
  const message = conflict
    ? 'Lesson-Version, Status oder offenes Review haben sich geändert. Laden Sie den Prüfstand neu; eine neue Entscheidung braucht Ihre Bestätigung.'
    : code === 'IDEMPOTENCY_KEY_REUSED'
      ? 'Dieser Befehlsschlüssel gehört zu anderen Eingaben. Bereiten Sie die Entscheidung mit den beabsichtigten Eingaben erneut vor.'
      : 'Die Prüfentscheidung ist nicht bestätigt. Prüfen Sie Eingaben und Lesestand; ein unveränderter Retry erzeugt keinen zweiten Abschluss.';
  return (
    <div role="alert" className="rounded border border-red-800 p-3 text-sm">
      <p>{message}</p>
      {error instanceof MarketApiError && (
        <p>
          {code}: {error.response.message}
        </p>
      )}
    </div>
  );
}
