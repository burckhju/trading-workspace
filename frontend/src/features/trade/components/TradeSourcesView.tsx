import { ClosedTradeResult } from '../../performance/components/ClosedTradeResult';
import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { readSource, sourceLink, sourceQueryError, sourceUrl } from '../services/sourceView';
import type {
  EvidenceSource,
  JournalSources,
  PlanSource,
  ReviewSources,
  SourceSnapshot,
  TradeSourceCore,
} from '../services/sourceView';
import type { TradeTimelineEntryResponse } from '../types/api';
import {
  reportReturnLink,
  TradeWorkspaceNavigation,
  tradeLessonLink,
  tradePlanLink,
  tradeWorkspaceLink,
} from '../../../shared/trade-workspace-navigation';

const sectionClass =
  'min-w-0 space-y-3 rounded-xl border border-slate-800 p-3 sm:p-4 [overflow-wrap:anywhere]';
const linkClass =
  'rounded-sm text-sky-400 underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sky-300';
const missing = 'Nicht dokumentiert';
const stamp = (value: string | null | undefined) => {
  if (!value) return missing;
  if (!/(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)) return `${value} (Zeitbasis nicht belegt)`;
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? `${value} (Zeitangabe nicht lesbar)`
    : `${date.toLocaleString('de-DE', { timeZone: 'UTC' })} UTC`;
};

type ReadWindow = Pick<SourceSnapshot<unknown>, 'read_started_at' | 'read_completed_at'>;

function ReadWindowDetails({
  window,
  label = 'Eigenes Lesefenster',
}: {
  window: ReadWindow;
  label?: string;
}) {
  return (
    <p className="text-xs text-slate-400">
      {label}: {stamp(window.read_started_at)} bis {stamp(window.read_completed_at)}. Kein
      gemeinsamer Stand mit anderen Quellenreads.
    </p>
  );
}

function SourceSection({
  title,
  id,
  inList = false,
  headingLevel = 2,
  children,
}: {
  title: string;
  id?: string;
  inList?: boolean;
  headingLevel?: 1 | 2 | 3;
  children: ReactNode;
}) {
  const Heading = headingLevel === 1 ? 'h1' : headingLevel === 3 ? 'h3' : 'h2';
  const section = (
    <section
      id={id}
      tabIndex={id ? -1 : undefined}
      className={`${sectionClass} focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sky-300`}
      aria-label={title}
    >
      <Heading className="text-lg font-semibold">{title}</Heading>
      {children}
    </section>
  );
  return inList ? <li className="min-w-0">{section}</li> : section;
}

function SourceDetails({ children }: { children: ReactNode }) {
  return (
    <details className="min-w-0">
      <summary className="cursor-pointer rounded-sm focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sky-300">
        Herkunftsdetails
      </summary>
      <div className="mt-2 space-y-2 text-sm [overflow-wrap:anywhere]">{children}</div>
    </details>
  );
}

function ReadSection<T>({
  title,
  url,
  id,
  inList,
  headingLevel,
  preceding,
  children,
}: {
  title: string;
  url: string;
  id?: string;
  inList?: boolean;
  headingLevel?: 1 | 2 | 3;
  preceding?: { title: string; children: (data: T) => ReactNode };
  children: (data: T, window: ReadWindow) => ReactNode;
}) {
  const [attempt, setAttempt] = useState(0);
  const [value, setValue] = useState<SourceSnapshot<T> | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setValue(null);
    setError(null);
    readSource<T>(url, controller.signal)
      .then((result) => {
        if (current && !controller.signal.aborted) setValue(result);
      })
      .catch((reason: unknown) => {
        if (current && !controller.signal.aborted)
          setError(reason instanceof Error ? reason.message : 'Quelle nicht verfügbar.');
      });
    return () => {
      current = false;
      controller.abort();
    };
  }, [url, attempt]);
  return (
    <>
      {preceding && (
        <SourceSection title={preceding.title} inList={inList}>
          <p className="text-sm text-slate-400">
            Analyseherkunft und ursprünglicher Plan stammen aus demselben Lesevorgang. Der
            historische Bezug wird nicht durch eine aktuelle Analyse ersetzt.
          </p>
          {error ? (
            <p>
              Analyseherkunft konnte nicht geprüft werden. Fehler und erneutes Lesen der gemeinsamen
              Quelle stehen unter „{title}“.
            </p>
          ) : value === null ? (
            <p>Analyseherkunft wird gemeinsam mit der Planquelle gelesen.</p>
          ) : (
            <>
              <ReadWindowDetails window={value} label={`Dasselbe Lesefenster wie „${title}“`} />
              {preceding.children(value.data)}
            </>
          )}
        </SourceSection>
      )}
      <SourceSection title={title} id={id} inList={inList} headingLevel={headingLevel}>
        {error ? (
          <>
            <p role="alert">
              Quelle konnte nicht gelesen werden. Das bedeutet nicht, dass sie fehlt. {error}
            </p>
            <button type="button" className={linkClass} onClick={() => setAttempt((v) => v + 1)}>
              {title} neu lesen
            </button>
          </>
        ) : value === null ? (
          <p role="status">{title} wird gelesen.</p>
        ) : (
          <>
            <ReadWindowDetails
              window={value}
              label={
                preceding
                  ? 'Eigenes Lesefenster der Planquelle, gemeinsam für Analyse und Plan'
                  : undefined
              }
            />
            {children(value.data, value)}
          </>
        )}
      </SourceSection>
    </>
  );
}

function Execution({ entry, replaced }: { entry: TradeTimelineEntryResponse; replaced: boolean }) {
  const label =
    entry.kind === 'CANCELLATION'
      ? 'Storno – kein Verkauf'
      : entry.kind === 'MANAGEMENT_EVENT'
        ? `Managemententscheidung: ${entry.management_event_type}`
        : entry.execution_side === 'BUY'
          ? 'Kauf'
          : entry.execution_side === 'SELL'
            ? 'Verkauf'
            : 'Ausführungsart nicht dokumentiert';
  return (
    <article
      className="space-y-2 rounded-lg border border-slate-800 p-3"
      aria-label={`Quelle ${entry.id}`}
    >
      <h3 className="font-semibold">{label}</h3>
      <p>
        {replaced ? 'Historisch ersetzt' : 'Wirksamer Quellenstand'}
        {entry.supersedes_id ? ' · Korrektur eines früheren Eintrags' : ''}
      </p>
      <p>
        {entry.kind === 'EXECUTION' ? 'Ausführung: ' : 'Ereigniszeit: '}
        {entry.executed_on
          ? `${entry.executed_on} · Uhrzeit unbekannt · ${entry.execution_timezone ?? 'Zeitzone nicht dokumentiert'}`
          : stamp(entry.occurred_at)}
      </p>
      {entry.kind === 'EXECUTION' && (
        <>
          <p>
            Menge: {entry.quantity == null ? 'Nicht verfügbar' : `${entry.quantity} Stück`}; Preis
            je Stück: {entry.price_per_unit ?? 'Nicht verfügbar'}
          </p>
          <p>
            Ausführungswährung: {entry.currency_resolution?.currency_code ?? 'Unbekannt'} ·
            Herkunft: {entry.currency_resolution?.source ?? 'UNKNOWN'}
          </p>
        </>
      )}
      {entry.numeric_value != null && (
        <p>
          Dokumentierter Wert: {entry.numeric_value}.{' '}
          {entry.price_binding
            ? 'Explizite Preisbindung vorhanden.'
            : 'Preisachse nicht belegt; kein Vergleich.'}
        </p>
      )}
      {entry.text_value && <p className="whitespace-pre-wrap">Benutzertext: {entry.text_value}</p>}
      <SourceDetails>
        <p>
          Quellen-ID: {entry.id}; Vorgänger: {entry.supersedes_id ?? 'Keiner'}
        </p>
        <p>
          Quellentyp: {entry.kind}; Trade: {entry.trade_id ?? missing}
        </p>
        <p>Erfasst: {stamp(entry.recorded_at)}</p>
        <pre className="whitespace-pre-wrap">
          {JSON.stringify(
            {
              price_binding: entry.price_binding,
              currency_resolution: entry.currency_resolution,
              currency_confirmation: entry.currency_confirmation,
            },
            null,
            2,
          )}
        </pre>
      </SourceDetails>
    </article>
  );
}

function Analysis({ data }: { data: PlanSource | null }) {
  if (data === null)
    return (
      <p>
        Keine Analyse-/Kandidatenquelle über einen ursprünglichen Plan dokumentiert. Ein externer
        Trade kann ohne diese Herkunft bestehen.
      </p>
    );
  const evaluation = data.candidate_evaluation;
  if (!evaluation)
    return (
      <p>
        {data.plan.origin_type === 'MANUAL'
          ? 'Manueller Plan ohne gebundene Kandidatenbewertung. Eine Analyseherkunft ist für diesen Ursprung nicht erforderlich.'
          : 'Kandidatenbewertung nicht dokumentiert. Eine heutige Analyse ersetzt diesen fehlenden historischen Beleg nicht.'}
      </p>
    );
  return (
    <>
      <p>
        Historische Kandidatenbewertung der gebundenen Planversion. Qualifikation und
        Quellenqualität sind die gespeicherten Befunde dieser Bewertung.
      </p>
      <dl className="grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-sm text-slate-400">Kandidat-ID</dt>
          <dd>{evaluation.candidate_id}</dd>
        </div>
        <div>
          <dt className="text-sm text-slate-400">Bewertung-ID und Version</dt>
          <dd>
            {evaluation.evaluation_id} · Version {evaluation.evaluation_version}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-slate-400">Modell und Version</dt>
          <dd>
            {evaluation.model_id} · {evaluation.model_version}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-slate-400">Bewertungszeit</dt>
          <dd>{stamp(evaluation.evaluated_at)}</dd>
        </div>
        <div>
          <dt className="text-sm text-slate-400">Qualifikation</dt>
          <dd>{evaluation.qualification}</dd>
        </div>
        <div>
          <dt className="text-sm text-slate-400">Quellenqualität</dt>
          <dd>{evaluation.quality_status}</dd>
        </div>
        <div>
          <dt className="text-sm text-slate-400">Richtung</dt>
          <dd>{evaluation.direction}</dd>
        </div>
      </dl>
      {evaluation.sources.length === 0 ? (
        <p>Keine einzelnen historischen Analysequellen dokumentiert.</p>
      ) : (
        <ul aria-label="Historische Analyse- und Kandidatenquellen" className="space-y-3">
          {evaluation.sources.map((source) => (
            <li
              key={`${source.role}:${source.source_type}:${source.source_id}:${source.source_version}`}
              className="rounded-lg border border-slate-800 p-3"
            >
              <dl className="grid gap-2 sm:grid-cols-2">
                <div>
                  <dt className="text-sm text-slate-400">Quellentyp</dt>
                  <dd>{source.source_type}</dd>
                </div>
                <div>
                  <dt className="text-sm text-slate-400">Rolle</dt>
                  <dd>{source.role}</dd>
                </div>
                <div>
                  <dt className="text-sm text-slate-400">Quellen-ID und Version</dt>
                  <dd>
                    {source.source_id} · Version {source.source_version}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-slate-400">Quellmodell und Version</dt>
                  <dd>
                    {source.model_id} · {source.model_version}
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}
      <p className="text-sm text-slate-400">
        Quellenreferenzen bezeichnen den damaligen Stand. Ein direkter Analyseversionslink ist hier
        nicht belegt; die gebundene Planversion ist im nächsten Abschnitt erreichbar.
      </p>
    </>
  );
}

function Plan({
  data,
  tradeId,
  query,
}: {
  data: PlanSource | null;
  tradeId: string;
  query: URLSearchParams;
}) {
  if (data === null)
    return <p>Eigener EXTERNAL-Trade ohne dokumentierte ursprüngliche Planherkunft.</p>;
  const v = data.version;
  return (
    <>
      <p>
        Ursprünglich referenzierte Planversion {v.version} · Status {v.status}. Keine Auswahl der
        heute neuesten Version.
      </p>
      <p>
        Planherkunft: {data.plan.origin_type ?? missing}. Planfreigabe und Kauf sind unabhängig.
      </p>
      <Link className={linkClass} to={tradePlanLink(data.plan.id, v.id, tradeId, query)}>
        Gebundene Planversion öffnen
      </Link>
      <p>These: {v.thesis}</p>
      <p>
        Einstieg: {v.entry.type};{' '}
        {v.entry.price ?? `${v.entry.price_from ?? '—'} bis ${v.entry.price_to ?? '—'}`}{' '}
        {v.entry.currency}; Auslöser: {v.entry.trigger ?? missing}
      </p>
      <p>
        Ungültigkeit: {v.invalidation.stop_price ?? missing}; Regel:{' '}
        {v.invalidation.invalidation_rule ?? missing}
      </p>
      {v.targets.map((t) => (
        <p key={t.sequence}>
          Ziel {t.sequence}: {t.price}; {t.rationale ?? missing}
        </p>
      ))}
      <p>Risikoannahme: {v.risk_assumptions.thesis_risk}</p>
      <p>
        Gespeicherte Freigabe:{' '}
        {data.approval ? `${data.approval.actor} · ${stamp(data.approval.approved_at)}` : missing}
      </p>
      <p>
        Planmarken und Ausführungspreise sind ohne passende explizite Preisachse nicht vergleichbar.
        Daraus folgt kein automatischer Regelverstoß.
      </p>
      <SourceDetails>
        <p>
          Plan: {data.plan.id}; Version: {v.id}; Erstellt: {stamp(v.created_at)}
        </p>
        <pre className="whitespace-pre-wrap">
          {JSON.stringify(
            {
              approval: data.approval,
              events: data.events,
            },
            null,
            2,
          )}
        </pre>
      </SourceDetails>
    </>
  );
}

function Review({ data, query }: { data: ReviewSources; query: URLSearchParams }) {
  if (!data.selected) return <p>Exit-Bewertung nicht dokumentiert.</p>;
  const v = data.selected.version;
  const fields = [
    ['timing', 'Timing'],
    ['process_adherence', 'Prozesseinhaltung beim Exit'],
    ['risk_decision', 'Risikoentscheidung beim Exit'],
    ['overall_exit_decision', 'Exit-Entscheidung insgesamt'],
  ] as const;
  return (
    <>
      <p>
        {query.has('review_version_id') ? 'Exakt angeforderte Version' : 'Heute ausgewählter Stand'}
        : {v.version} · {v.status}
      </p>
      {v.status === 'DRAFT' && (
        <p>Vorläufiger, veränderlicher Entwurf; CURRENT ist keine finale Abnahme.</p>
      )}
      <p>
        Gespeicherte Currentness: {v.currentness}. Heutige Quellenprüfung: {data.source_currentness}{' '}
        · {stamp(data.checked_at)}.
      </p>
      <p>
        Dokumentierte Exit-Bewertung, kein Gesamturteil über die Tradequalität und keine Ableitung
        aus Gewinn oder Verlust.
      </p>
      <dl>
        {fields.map(([key, label]) => (
          <div key={key}>
            <dt>{label}</dt>
            <dd>
              {v[key] === null
                ? missing
                : v[key] === 'NOT_ASSESSABLE'
                  ? 'NOT_ASSESSABLE – ausdrücklich nicht beurteilbar'
                  : v[key]}
            </dd>
          </div>
        ))}
      </dl>
      <p className="whitespace-pre-wrap">Benutzerbegründung: {v.rationale ?? missing}</p>
      <nav aria-label="Exit-Review-Historie">
        {data.history.map(({ version }) => (
          <p key={version.id}>
            <Link className={linkClass} to={sourceLink(query, 'review_version_id', version.id)}>
              Reviewversion {version.version} · {version.status}
            </Link>
          </p>
        ))}
      </nav>
      <SourceDetails>
        <p>
          Reviewversion: {v.id}; Review: {v.exit_review_id}; Erstellt: {stamp(v.created_at)};
          Finalisiert: {stamp(v.finalized_at)}
        </p>
        <p>Vorgänger: {v.supersedes_version_id ?? 'Keiner'}</p>
        <p>
          Gespeicherter Veraltungsgrund: {v.stale_reason ?? missing}; Zeitpunkt: {stamp(v.stale_at)}
          . Dieser historische Eintrag ersetzt nicht die heutige Quellenprüfung.
        </p>
      </SourceDetails>
    </>
  );
}

function Journal({ data, query }: { data: JournalSources; query: URLSearchParams }) {
  const v = data.selected;
  if (!v) return <p>Journal nicht dokumentiert.</p>;
  const empty = !v.what_went_well && !v.would_do_differently && !v.additional_notes;
  const exactJournalQuery = new URLSearchParams(query);
  exactJournalQuery.set('journal_version_id', v.id);
  return (
    <>
      <p>
        Journalversion {v.version} · {v.status} · Bearbeitungsrevision {v.edit_revision}
      </p>
      <p>
        {query.has('journal_version_id')
          ? 'Exakt angeforderte Journalversion.'
          : 'Heute ausgewählter Journalstand.'}
      </p>
      {v.status === 'DRAFT' && (
        <p>Veränderlicher Entwurf. Die Versions-ID allein friert diesen Text nicht ein.</p>
      )}
      {empty && (
        <>
          <p>
            {v.status === 'FINALIZED'
              ? 'Finales Journal ohne Reflexionstext.'
              : 'Entwurf ohne Reflexionstext.'}
          </p>
          <p>Der gespeicherte Status bewertet nicht die Vollständigkeit der Reflexion.</p>
        </>
      )}
      <p>
        Heutige Prüfung der referenzierten Reviewquelle: {data.source_currentness} ·{' '}
        {stamp(data.checked_at)}. Kein Urteil über den Journaltext.
      </p>
      {v.what_went_well && <p className="whitespace-pre-wrap">{v.what_went_well}</p>}
      {v.would_do_differently && <p className="whitespace-pre-wrap">{v.would_do_differently}</p>}
      {v.additional_notes && <p className="whitespace-pre-wrap">{v.additional_notes}</p>}
      {v.source_exit_review_version_id && (
        <Link
          className={linkClass}
          to={sourceLink(exactJournalQuery, 'review_version_id', v.source_exit_review_version_id)}
        >
          Exakte Journal-Reviewquelle lesen
        </Link>
      )}
      <nav aria-label="Journal-Historie">
        {data.history.map((version) => (
          <p key={version.id}>
            <Link className={linkClass} to={sourceLink(query, 'journal_version_id', version.id)}>
              Journalversion {version.version} · {version.status} · Revision {version.edit_revision}
            </Link>
          </p>
        ))}
      </nav>
      <SourceDetails>
        <p>
          Journalversion: {v.id}; Reviewquelle: {v.source_exit_review_version_id ?? 'Unbekannt'};
          Erstellt: {stamp(v.created_at)}; Geändert: {stamp(v.updated_at)}; Finalisiert:{' '}
          {stamp(v.finalized_at)}
        </p>
        <p>
          Journal: {v.trade_journal_id}; Vorgängerversion: {v.supersedes_version_id ?? 'Keine'}
        </p>
      </SourceDetails>
    </>
  );
}

function Evidence({ data, query }: { data: EvidenceSource[]; query: URLSearchParams }) {
  if (data.length === 0)
    return <p>Keine dokumentierte Evidence-/Lesson-Beziehung für diesen Trade.</p>;
  return (
    <>
      <p>
        Historische Evidence und ihre gespeicherten Lesson-Beziehungen. Die aktuelle
        Materialisierungsbereitschaft und der Lesson-Reviewstatus werden hier nicht geprüft. Eine
        Beziehung bestätigt keine Freigabe und keinen früheren Prozessschritt.
      </p>
      {data.map((e) => (
        <article
          key={e.evidence_id}
          className="min-w-0 space-y-2 rounded-lg border border-slate-800 p-3"
          aria-label={`Evidence ${e.evidence_id}`}
        >
          <h3 className="font-semibold">
            {e.evidence_type} ·{' '}
            {e.source_bound
              ? 'Historisch exakt gebundene Quelle'
              : 'Alte Herkunft nicht vollständig auflösbar'}
          </h3>
          <p>
            Evidence erstellt: {stamp(e.created_at)}. Kein wirtschaftlicher Ausführungszeitpunkt.
          </p>
          {e.review_version_id && (
            <p>
              <Link
                className={linkClass}
                to={sourceLink(query, 'review_version_id', e.review_version_id)}
              >
                Exakte Evidence-Reviewquelle lesen
              </Link>
            </p>
          )}
          {e.journal_version_id && (
            <p>
              <Link
                className={linkClass}
                to={sourceLink(query, 'journal_version_id', e.journal_version_id)}
              >
                Exakte Evidence-Journalquelle lesen
              </Link>
            </p>
          )}
          {e.lesson_links.length === 0 && <p>Keine gespeicherte Lesson-Beziehung.</p>}
          {e.lesson_links.length > 0 && (
            <ul aria-label="Belegte Lesson-Beziehungen" className="space-y-3">
              {e.lesson_links.map((l) => (
                <li key={l.link_id} className="space-y-2">
                  <Link
                    className={linkClass}
                    to={tradeLessonLink(
                      l.lesson_id,
                      l.lesson_version_id,
                      query.get('trade_id') ?? '',
                      query,
                      'sources',
                    )}
                  >
                    {l.lesson_title} · Version {l.lesson_version} · {l.relation} ·{' '}
                    {l.is_current_version ? 'heutige Version' : 'historische Version'}
                  </Link>
                  <dl className="grid gap-2 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="text-slate-400">Lesson-ID</dt>
                      <dd>{l.lesson_id}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">Lessonversion-ID</dt>
                      <dd>{l.lesson_version_id}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">Beziehungs-ID</dt>
                      <dd>{l.link_id}</dd>
                    </div>
                  </dl>
                </li>
              ))}
            </ul>
          )}
          <SourceDetails>
            <p>Evidence: {e.evidence_id}</p>
            <p>
              Reviewversion: {e.review_version_id ?? missing}; Journalversion:{' '}
              {e.journal_version_id ?? missing}; Quellenbindung: {e.source_bound ? 'Ja' : 'Nein'}
            </p>
          </SourceDetails>
        </article>
      ))}
    </>
  );
}

function Core({
  data,
  tradeId,
  query,
  window,
}: {
  data: TradeSourceCore;
  tradeId: string;
  query: URLSearchParams;
  window: ReadWindow;
}) {
  if (data.trade.id.toLowerCase() !== tradeId)
    return <p role="alert">Unpassende Tradeidentität. Weitere Quellen werden nicht gelesen.</p>;
  const replaced = new Set(data.timeline.map((t) => t.supersedes_id).filter(Boolean));
  return (
    <>
      <h2 className="text-2xl font-semibold">
        {data.product_name ?? 'Trade'} · TR-{tradeId.slice(0, 8).toUpperCase()}
      </h2>
      <p>Produktname ist heutige Stammdatenanzeige, keine historische Entscheidungsgrundlage.</p>
      <TradeWorkspaceNavigation
        tradeId={tradeId}
        view="sources"
        cancelled={Boolean(data.trade.cancelled_at)}
        showBackLinks={false}
      />
      <section className={sectionClass} aria-label="Wirtschaftliches Gesamtergebnis">
        <h2 className="text-lg font-semibold">Wirtschaftliches Gesamtergebnis</h2>
        <ClosedTradeResult tradeId={tradeId} productId={data.trade.product_id} query={query} />
      </section>
      <SourceDetails>
        <p>
          Trade: {data.trade.id}; Produkt: {data.trade.product_id}; Ursprung: {data.trade.origin}
        </p>
      </SourceDetails>
      <p>
        Analyse → Plan → Ausführung → Position → Review/Journal → Evidence/Lesson dient als
        Lesereihenfolge. Jeder Abschnitt zeigt seine eigenen Belege; spätere Belege bestätigen
        keinen früheren Schritt. Manuelle Pläne und externe Trades sind mögliche Ursprünge.
      </p>
      <ol aria-label="Belege im Trade-Lebenszyklus" role="list" className="space-y-4">
        <ReadSection<PlanSource | null>
          id="trade-plan-sources"
          title="Ursprünglicher Plan"
          url={sourceUrl(tradeId, 'plan')}
          inList
          preceding={{ title: 'Analyse / Kandidat', children: (v) => <Analysis data={v} /> }}
        >
          {(v) => <Plan data={v} tradeId={tradeId} query={query} />}
        </ReadSection>
        <SourceSection title="Tatsächliche Ausführungen und Management" inList>
          <ReadWindowDetails window={window} label="Gemeinsames Lesefenster mit der Position" />
          <p>
            Ausführungen und Managemententscheidungen bleiben getrennt. Korrekturvorgänger sind
            Historie und zählen nicht zusätzlich. Date-only beweist keine Intraday-Reihenfolge.
          </p>
          {data.timeline.length === 0 && (
            <p>Keine Ausführungs- oder Managementbelege dokumentiert.</p>
          )}
          {data.timeline.map((entry) => (
            <Execution key={entry.id} entry={entry} replaced={replaced.has(entry.id)} />
          ))}
          <SourceDetails>
            <p>
              Historische ausdrückliche Währungserklärungen; abgeleitete Wiederverwendung erzeugt
              keine neue Erklärung.
            </p>
            <pre className="whitespace-pre-wrap">
              {JSON.stringify(data.currency_history, null, 2)}
            </pre>
          </SourceDetails>
        </SourceSection>
        <SourceSection title="Position" inList>
          <ReadWindowDetails window={window} label="Dasselbe Lesefenster wie die Ausführungen" />
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-sm text-slate-400">Gelieferter Positionszustand</dt>
              <dd>{data.state}</dd>
            </div>
            <div>
              <dt className="text-sm text-slate-400">Offene Menge</dt>
              <dd>
                {data.open_quantity == null ? 'Nicht verfügbar' : `${data.open_quantity} Stück`}
              </dd>
            </div>
          </dl>
          {data.state === 'CANCELLED' && (
            <p>Storniert ist kein Verkauf und kein wirtschaftlicher Vollabschluss.</p>
          )}
          {data.state === 'UNKNOWN' && (
            <p>
              Positionszustand unbekannt. Daraus folgt weder „nicht begonnen“ noch „geschlossen“.
            </p>
          )}
          <SourceDetails>
            <p>
              Projektion für Trade: {data.trade.id}; Produkt: {data.trade.product_id}.
            </p>
            <p>Eine eigene Positions-ID wird in dieser Quelle nicht geliefert.</p>
          </SourceDetails>
        </SourceSection>
        <SourceSection title="Review und Journal" inList>
          <p>
            Review und Journal werden unabhängig gelesen. Finalisierung, gespeicherter Quellenstand
            und heutige Quellenprüfung bleiben getrennte Aussagen.
          </p>
          <ReadSection<ReviewSources>
            id="trade-review-sources"
            title="Dokumentierte Exit-Bewertung"
            url={sourceUrl(tradeId, 'reviews', query.get('review_version_id'))}
            headingLevel={3}
          >
            {(v) => <Review data={v} query={query} />}
          </ReadSection>
          <ReadSection<JournalSources>
            id="trade-journal-sources"
            title="Journal"
            url={sourceUrl(tradeId, 'journal', query.get('journal_version_id'))}
            headingLevel={3}
          >
            {(v) => <Journal data={v} query={query} />}
          </ReadSection>
        </SourceSection>
        <ReadSection<EvidenceSource[]>
          id="trade-evidence-sources"
          title="Evidence und Lesson-Versionen"
          url={sourceUrl(tradeId, 'evidence')}
          inList
        >
          {(v) => <Evidence data={v} query={query} />}
        </ReadSection>
      </ol>
    </>
  );
}

export function TradeSourcesView({ query }: { query: URLSearchParams }) {
  const error = sourceQueryError(query);
  const reportReturn = reportReturnLink(query);
  const tradeId = (query.get('trade_id') ?? '').toLowerCase();
  return (
    <main className="min-w-0 w-full space-y-6 [overflow-wrap:anywhere]">
      <nav aria-label="Quellenansicht verlassen" className="flex flex-wrap gap-x-4 gap-y-2">
        {reportReturn && (
          <Link className={linkClass} to={reportReturn.href}>
            {reportReturn.label}
          </Link>
        )}
        <Link
          className={linkClass}
          to={tradeWorkspaceLink('management', tradeId, query, '#trade-overview')}
        >
          Zur Tradeverwaltung
        </Link>
      </nav>
      <p>
        Lesende Quellenansicht. Keine automatische Bewertung, Reparatur, Materialisierung oder
        Revalidierung. Abschnitte werden getrennt gelesen.
      </p>
      {error ? (
        <p role="alert">{error}</p>
      ) : (
        <ReadSection<TradeSourceCore>
          title="Trade und Quellenstand"
          url={sourceUrl(tradeId)}
          headingLevel={1}
        >
          {(v, window) => <Core data={v} tradeId={tradeId} query={query} window={window} />}
        </ReadSection>
      )}
    </main>
  );
}
