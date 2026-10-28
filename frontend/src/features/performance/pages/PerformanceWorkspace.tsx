import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { ClosedTradesReportView } from '../components/ClosedTradesReportView';
import { PerformanceFilters } from '../components/PerformanceFilters';
import { RealizedGrossReportView } from '../components/RealizedGrossReportView';
import { performanceApiClient } from '../services/client';
import {
  closedContextQuery,
  closedFiltersError,
  parseClosedContext,
  verifyClosedReport,
  verifyClosedStatistics,
  type ClosedReportContext,
} from '../services/closedReportContext';
import {
  initialPerformanceFilters,
  parseRealizedContext,
  realizedContextQuery,
  reportFiltersErrors,
  verifyRealizedReport,
  type PerformanceReportKind,
  type RealizedReportContext,
  type ReportFilterErrors,
} from '../services/performanceReportContext';
import { filterKey } from '../services/presentation';
import type { ClosedTradeReport, RealizedGrossFilters, RealizedGrossReport } from '../types/api';

type ReportContext = ClosedReportContext | RealizedReportContext;
type ReportResponse =
  | { kind: 'closed-trades'; report: ClosedTradeReport }
  | { kind: 'realized-gross'; report: RealizedGrossReport };
const titles: Record<PerformanceReportKind, string> = {
  'realized-gross': 'Verkäufe im Zeitraum',
  'closed-trades': 'Trades mit Vollabschluss im Zeitraum',
};

function contextQuery(kind: PerformanceReportKind, context: ReportContext) {
  return kind === 'closed-trades'
    ? closedContextQuery(context as ClosedReportContext)
    : realizedContextQuery(context as RealizedReportContext);
}

function selectionKey(kind: PerformanceReportKind, filters: RealizedGrossFilters) {
  return `${kind}|${filterKey(filters)}`;
}

function draftFromUrl(search: string, context: ReportContext | null, invalid: boolean) {
  if (context) return { ...context.filters, report_currency: 'EUR' };
  if (!invalid) return initialPerformanceFilters();
  const query = new URLSearchParams(search);
  const single = (name: string) => (query.getAll(name).length === 1 ? query.get(name)! : '');
  return {
    from_date: single('from_date'),
    to_date: single('to_date'),
    report_timezone: single('report_timezone'),
    report_currency: 'EUR',
  };
}

/** One draft, one applied router context and one response lifetime for both report kinds. */
export function PerformanceWorkspace({ kind }: { kind: PerformanceReportKind }) {
  const location = useLocation();
  const navigate = useNavigate();
  const parsed = useMemo(() => {
    const query = new URLSearchParams(location.search);
    return kind === 'closed-trades' ? parseClosedContext(query) : parseRealizedContext(query);
  }, [kind, location.search]);
  const currencyError =
    parsed.context && parsed.context.filters.report_currency !== 'EUR'
      ? `Der verlinkte ${kind === 'closed-trades' ? 'Abschlussbericht' : 'Verkaufsbericht'} verwendet ${parsed.context.filters.report_currency}. Diese Ansicht ist auf EUR festgelegt. Für einen neuen EUR-Bericht Zeitraum und Berichtszone prüfen und „Bericht lesen“ wählen.`
      : null;
  // Keep the published closed-context parser compatible while applying the
  // shared form's IANA-only contract to both workspace entry routes.
  const contextFilterError = parsed.context
    ? (Object.values(reportFiltersErrors(parsed.context.filters))[0] ?? null)
    : null;
  const contextError = parsed.error ?? currencyError ?? contextFilterError;
  const context = contextError ? null : parsed.context;
  const [draft, setDraft] = useState(() =>
    draftFromUrl(location.search, parsed.context, Boolean(parsed.error)),
  );
  const [fieldErrors, setFieldErrors] = useState<ReportFilterErrors>({});
  const [response, setResponse] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(contextError);
  const [changedBasis, setChangedBasis] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const lastBasis = useRef(new Map<string, string>());
  const loaded = useRef<ReportResponse | null>(null);
  const localNavigation = useRef<string | null>(null);
  const previousContext = useRef<{ kind: PerformanceReportKind; context: ReportContext } | null>(
    null,
  );

  const invalidate = useCallback(() => {
    generation.current += 1;
    controller.current?.abort();
  }, []);

  const clearResult = useCallback(() => {
    loaded.current = null;
    setResponse(null);
    setLoading(false);
    setChangedBasis(false);
  }, []);

  const read = useCallback(
    async (requestedKind: PerformanceReportKind, requestedContext: ReportContext) => {
      invalidate();
      clearResult();
      setError(null);
      const current = generation.current;
      const requestController = new AbortController();
      controller.current = requestController;
      const requested = requestedContext.filters;
      setLoading(true);
      try {
        let next: ReportResponse;
        if (requestedKind === 'closed-trades') {
          const report = await performanceApiClient.closedTrades(
            requested,
            requestController.signal,
          );
          if (requestController.signal.aborted || current !== generation.current) return;
          verifyClosedReport(report, requested);
          verifyClosedStatistics(report);
          next = { kind: requestedKind, report };
        } else {
          const report = await performanceApiClient.realizedGross(
            requested,
            requestController.signal,
          );
          if (requestController.signal.aborted || current !== generation.current) return;
          verifyRealizedReport(report, requested);
          next = { kind: requestedKind, report };
        }
        const key = selectionKey(requestedKind, requested);
        const previous = requestedContext.basis ?? lastBasis.current.get(key);
        setChangedBasis(previous !== undefined && previous !== next.report.basis.id);
        lastBasis.current.set(key, next.report.basis.id);
        loaded.current = next;
        setResponse(next);
      } catch (cause) {
        if (requestController.signal.aborted || current !== generation.current) return;
        setError(cause instanceof Error ? cause.message : 'Bericht konnte nicht gelesen werden.');
      } finally {
        if (!requestController.signal.aborted && current === generation.current) setLoading(false);
      }
    },
    [clearResult, invalidate],
  );

  useEffect(() => {
    const url = `${location.pathname}${location.search}`;
    const previous = previousContext.current;
    previousContext.current = context ? { kind, context } : null;
    if (localNavigation.current === url) {
      localNavigation.current = null;
      return;
    }
    localNavigation.current = null;
    invalidate();
    setDraft(draftFromUrl(location.search, parsed.context, Boolean(parsed.error)));
    setFieldErrors({});
    setError(contextError);
    // A POP of just a row/page selection may retain the same complete response.
    // A dirty draft has already discarded it and must read the applied URL again.
    if (
      context &&
      previous &&
      loaded.current &&
      previous.kind === kind &&
      selectionKey(kind, previous.context.filters) === selectionKey(kind, context.filters) &&
      previous.context.basis === context.basis &&
      selectionKey(loaded.current.kind, loaded.current.report.filters) ===
        selectionKey(kind, context.filters)
    ) {
      setLoading(false);
      return;
    }
    clearResult();
    if (context) void read(kind, context);
  }, [
    kind,
    location.key,
    location.pathname,
    location.search,
    parsed,
    context,
    contextError,
    clearResult,
    invalidate,
    read,
  ]);

  useEffect(() => invalidate, [invalidate]);

  function change(field: Exclude<keyof RealizedGrossFilters, 'report_currency'>, value: string) {
    invalidate();
    clearResult();
    setDraft((current) => ({ ...current, [field]: value }));
    setFieldErrors({});
    setError(contextError);
  }

  function apply(target: PerformanceReportKind, switching = false) {
    if (switching && target === kind) return;
    invalidate();
    clearResult();
    const requested = {
      ...draft,
      report_currency: 'EUR',
      report_timezone: draft.report_timezone.trim(),
    };
    const errors = reportFiltersErrors(requested);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      setError(closedFiltersError(requested) ?? Object.values(errors)[0]);
      const first = Object.keys(errors)[0];
      const field = formRef.current?.elements.namedItem(first);
      if (field instanceof HTMLElement) field.focus();
      return;
    }
    // Invalid explicit links remain invalid until an explicit read adopts a new selection.
    if (switching && contextError) {
      setError(
        `${contextError} Bitte die neue Auswahl ausdrücklich mit „Bericht lesen“ übernehmen.`,
      );
      return;
    }
    const keepView = !switching && context && filterKey(context.filters) === filterKey(requested);
    const next: ReportContext = keepView
      ? { ...context, filters: requested }
      : { filters: requested, view: 'candidates', page: 0, basis: null };
    setDraft(requested);
    setError(null);
    const pathname = `/performance/${target}`;
    const search = `?${contextQuery(target, next)}`;
    // New URLs are read exclusively by the router effect. Re-reading an identical
    // applied URL is explicit, so it cannot produce a submit-plus-effect double GET.
    if (location.pathname === pathname && location.search === search) void read(target, next);
    else void navigate({ pathname, search });
  }

  function localContext(next: ReportContext) {
    const pathname = `/performance/${kind}`;
    const search = `?${contextQuery(kind, next)}`;
    if (location.pathname === pathname && location.search === search) return;
    localNavigation.current = `${pathname}${search}`;
    void navigate({ pathname, search }, { replace: true });
  }

  const visibleResponse =
    response &&
    context &&
    response.kind === kind &&
    filterKey(response.report.filters) === filterKey(context.filters) &&
    filterKey(response.report.filters) === filterKey(draft)
      ? response
      : null;

  return (
    <div className="min-w-0 w-full space-y-6 [overflow-wrap:anywhere]">
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-500">Performance</p>
        <h1 className="mt-1 text-2xl font-semibold">{titles[kind]}</h1>
        <p className="mt-2 max-w-4xl text-sm text-slate-400">
          {kind === 'realized-gross'
            ? 'Welche Verkäufe gehören in den Zeitraum und welchen Bruttobeitrag liefern sie? Auch Teilverkäufe weiterhin offener Trades zählen. Die Kostenbasis jedes Verkaufs bleibt nachvollziehbar.'
            : 'Welche Trades wurden tatsächlich vollständig abgeschlossen und welches gesamte Bruttoergebnis haben sie erzielt? Jeder Trade zählt einmal nach seinem wirksamen Vollabschluss; frühere Teilverkäufe gehören zu seinem vollständigen Ergebnis.'}
        </p>
        <p className="mt-2 max-w-4xl text-sm text-slate-400">
          Aktueller korrigierter Faktenstand, brutto vor Gebühren, Kommissionen und Steuern. Dies
          ist keine vollständige Depotperformance. Journal, Nachbeobachtung und Lessons sind keine
          Voraussetzung.
        </p>
      </header>
      <div role="group" aria-label="Berichtsart" className="flex flex-wrap gap-2">
        {(Object.keys(titles) as PerformanceReportKind[]).map((target) => (
          <button
            key={target}
            type="button"
            aria-pressed={kind === target}
            className={`rounded-lg border px-3 py-2 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 ${kind === target ? 'border-sky-600 bg-sky-950 text-sky-100' : 'border-slate-700 text-slate-300'}`}
            onClick={() => apply(target, true)}
          >
            {titles[target]}
          </button>
        ))}
      </div>
      <PerformanceFilters
        filters={draft}
        errors={fieldErrors}
        loading={loading}
        formRef={formRef}
        onChange={change}
        onRead={() => apply(kind)}
      />
      {loading && (
        <p role="status">
          Ein konsistenter Quellenstand wird gelesen. Für diese Auswahl liegt noch kein neues
          Ergebnis vor.
        </p>
      )}
      {error && (
        <p role="alert" className="rounded-lg border border-amber-800 p-4 text-sm text-amber-300">
          {error}
        </p>
      )}
      {changedBasis && visibleResponse && (
        <p role="status" className="rounded-lg border border-sky-800 p-4 text-sm">
          Der Quellenstand hat sich gegenüber dem mitgegebenen oder zuletzt gelesenen Stand dieser
          Auswahl geändert. Ergebnis, Zähler, Zeilen, Herkunft und gegebenenfalls
          Abschlusskennzahlen wurden gemeinsam durch den neu gelesenen Stand ersetzt.
        </p>
      )}
      {!visibleResponse && !loading && !error && (
        <p className="text-sm text-slate-400">
          Zeitraum und Berichtszone prüfen und „Bericht lesen“ wählen. Die Berichtswährung ist EUR.
          Ein Wechsel der Berichtsart übernimmt die gültige Auswahl und liest den gewählten Bericht.
        </p>
      )}
      {visibleResponse?.kind === 'closed-trades' && (
        <ClosedTradesReportView
          key={`${selectionKey(kind, visibleResponse.report.filters)}:${visibleResponse.report.basis.id}:${generation.current}`}
          report={visibleResponse.report}
          context={context as ClosedReportContext}
          onContext={localContext}
        />
      )}
      {visibleResponse?.kind === 'realized-gross' && (
        <RealizedGrossReportView
          key={`${selectionKey(kind, visibleResponse.report.filters)}:${visibleResponse.report.basis.id}:${generation.current}`}
          report={visibleResponse.report}
          context={context as RealizedReportContext}
          onContext={localContext}
        />
      )}
    </div>
  );
}
