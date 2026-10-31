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
  closedListUrl,
  parseClosedContext,
  TradeWorkspaceNavigation,
  tradeLessonLink,
  tradeWorkspaceLink,
} from '../../../shared/trade-workspace-navigation';

const sectionClass = 'space-y-3 rounded-xl border border-slate-800 p-4';
const linkClass = 'text-sky-400 underline focus-visible:outline';
const missing = 'Nicht dokumentiert';
const stamp = (value: string | null | undefined) =>
  value ? new Date(value).toLocaleString('de-DE') : missing;

function SourceDetails({ children }: { children: ReactNode }) {
  return (
    <details>
      <summary className="cursor-pointer">Herkunftsdetails</summary>
      <div className="mt-2 space-y-2 text-sm [overflow-wrap:anywhere]">{children}</div>
    </details>
  );
}

function ReadSection<T>({
  title,
  url,
  id,
  children,
}: {
  title: string;
  url: string;
  id?: string;
  children: (data: T) => ReactNode;
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
    <section id={id} tabIndex={id ? -1 : undefined} className={sectionClass} aria-label={title}>
      <h2 className="text-lg font-semibold">{title}</h2>
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
          <p className="text-xs text-slate-400">
            Eigenes Lesefenster: {stamp(value.read_started_at)} bis {stamp(value.read_completed_at)}
            . Kein gemeinsamer Stand mit anderen Abschnitten.
          </p>
          {children(value.data)}
        </>
      )}
    </section>
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
          : 'Verkauf';
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
        {entry.executed_on
          ? `${entry.executed_on} · Uhrzeit unbekannt · ${entry.execution_timezone}`
          : stamp(entry.occurred_at)}
      </p>
      {entry.kind === 'EXECUTION' && (
        <>
          <p>
            Menge: {entry.quantity}; Preis je Stück: {entry.price_per_unit}
          </p>
          <p>
            Ausführungswährung: {entry.currency_resolution?.currency_code ?? 'Unbekannt'} ·
            Herkunft: {entry.currency_resolution?.source ?? 'UNKNOWN'}
          </p>
        </>
      )}
      {entry.numeric_value !== null && (
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

function Plan({ data }: { data: PlanSource | null }) {
  if (data === null)
    return <p>Eigener EXTERNAL-Trade ohne dokumentierte ursprüngliche Planherkunft.</p>;
  const v = data.version;
  return (
    <>
      <p>
        Ursprünglich referenzierte Planversion {v.version} · Status {v.status}. Keine Auswahl der
        heute neuesten Version.
      </p>
      <Link
        className={linkClass}
        target="_blank"
        rel="noopener noreferrer"
        to={`/trade-plans?${new URLSearchParams({ trade_plan_id: data.plan.id, trade_plan_version_id: v.id })}`}
      >
        Gebundene Planversion öffnen (neuer Tab)
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
              candidate_evaluation: data.candidate_evaluation,
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
      {v.status === 'DRAFT' && (
        <p>Veränderlicher Entwurf. Die Versions-ID allein friert diesen Text nicht ein.</p>
      )}
      {empty && (
        <p>
          {v.status === 'FINALIZED'
            ? 'Finales Journal ohne Reflexionstext.'
            : 'Entwurf ohne Reflexionstext.'}
        </p>
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
      </SourceDetails>
    </>
  );
}

function Evidence({ data, query }: { data: EvidenceSource[]; query: URLSearchParams }) {
  if (data.length === 0)
    return <p>Keine dokumentierte Evidence-/Lesson-Beziehung für diesen Trade.</p>;
  return (
    <>
      {data.map((e) => (
        <article key={e.evidence_id} className="space-y-2 rounded-lg border border-slate-800 p-3">
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
          {e.lesson_links.map((l) => (
            <p key={l.link_id}>
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
            </p>
          ))}
          <SourceDetails>
            <p>Evidence: {e.evidence_id}</p>
            <pre className="whitespace-pre-wrap">{JSON.stringify(e.lesson_links, null, 2)}</pre>
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
}: {
  data: TradeSourceCore;
  tradeId: string;
  query: URLSearchParams;
}) {
  if (data.trade.id.toLowerCase() !== tradeId)
    return <p role="alert">Unpassende Tradeidentität. Weitere Quellen werden nicht gelesen.</p>;
  const replaced = new Set(data.timeline.map((t) => t.supersedes_id).filter(Boolean));
  return (
    <>
      <h1 className="text-2xl font-semibold">
        {data.product_name ?? 'Trade'} · TR-{tradeId.slice(0, 8).toUpperCase()}
      </h1>
      <p>
        Zustand im Ausführungs-Lesefenster: {data.state}; offene Menge:{' '}
        {data.open_quantity ?? 'Nicht verfügbar'}.
      </p>
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
      <ReadSection<PlanSource | null>
        id="trade-plan-sources"
        title="Ursprünglicher Plan"
        url={sourceUrl(tradeId, 'plan')}
      >
        {(v) => <Plan data={v} />}
      </ReadSection>
      <section className={sectionClass} aria-label="Tatsächliche Ausführungen und Management">
        <h2 className="text-lg font-semibold">Tatsächliche Ausführungen und Management</h2>
        <p>
          Ausführungen und Managemententscheidungen bleiben getrennt. Korrekturvorgänger sind
          Historie und zählen nicht zusätzlich. Date-only beweist keine Intraday-Reihenfolge.
        </p>
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
      </section>
      <ReadSection<ReviewSources>
        title="Dokumentierte Exit-Bewertung"
        url={sourceUrl(tradeId, 'reviews', query.get('review_version_id'))}
      >
        {(v) => <Review data={v} query={query} />}
      </ReadSection>
      <ReadSection<JournalSources>
        id="trade-journal-sources"
        title="Journal"
        url={sourceUrl(tradeId, 'journal', query.get('journal_version_id'))}
      >
        {(v) => <Journal data={v} query={query} />}
      </ReadSection>
      <ReadSection<EvidenceSource[]>
        id="trade-evidence-sources"
        title="Evidence und Lesson-Versionen"
        url={sourceUrl(tradeId, 'evidence')}
      >
        {(v) => <Evidence data={v} query={query} />}
      </ReadSection>
    </>
  );
}

export function TradeSourcesView({ query }: { query: URLSearchParams }) {
  const error = sourceQueryError(query);
  const reportContext = parseClosedContext(query).context;
  const tradeId = (query.get('trade_id') ?? '').toLowerCase();
  return (
    <main className="min-w-0 w-full space-y-6 [overflow-wrap:anywhere]">
      <nav aria-label="Quellenansicht verlassen" className="flex flex-wrap gap-x-4 gap-y-2">
        {reportContext && (
          <Link className={linkClass} to={closedListUrl(reportContext)}>
            Zur ursprünglichen Abschlussauswahl
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
        <ReadSection<TradeSourceCore> title="Trade und Quellenstand" url={sourceUrl(tradeId)}>
          {(v) => <Core data={v} tradeId={tradeId} query={query} />}
        </ReadSection>
      )}
    </main>
  );
}
