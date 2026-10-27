import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';

import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';
import { SetupDiscardDialog } from '../../administration/components/SetupDiscardDialog';
import { MarketApiError, MarketTransportError } from '../../market/services/http';
import { AnalysisStatusBadge } from '../components/AnalysisStatusBadge';
import {
  analysisContextReturnTo,
  analysisDetailUrl,
  canonicalAnalysisSetupUrl,
  parseAnalysisSetupContext,
  type AnalysisSetupContext,
} from '../services/analysisWorkflowContext';
import { analysisApiClient } from '../services/client';
import type {
  AnalysisDetail,
  AnalysisEvent,
  AnalysisRun,
  AnalysisRunDetail,
  AnalysisSummary,
  AnalysisVerification,
  SnapshotPage,
} from '../types/api';

function fmt(value: string): string {
  return new Date(value).toLocaleString('de-DE');
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : 'Der Lesestand konnte nicht geprüft werden.';
}

function positiveVersion(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
}

function requireRead(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function requireReceipt(condition: unknown): asserts condition {
  if (!condition)
    throw new MarketTransportError(
      'Die Antwort bestätigt den angeforderten Schritt nicht eindeutig. Abschluss unbekannt.',
    );
}

const terminalStatuses = ['COMPLETED', 'COMPLETED_WITH_WARNINGS', 'NOT_EVALUABLE', 'FAILED'];
const replacementStatuses = ['COMPLETED', 'COMPLETED_WITH_WARNINGS', 'NOT_EVALUABLE'];

function validRun(run: AnalysisRun | undefined): run is AnalysisRun {
  return Boolean(
    run &&
      positiveVersion(run.version) &&
      typeof run.status === 'string' &&
      typeof run.quality_status === 'string' &&
      typeof run.model_id === 'string' &&
      run.model_id &&
      typeof run.model_version === 'string' &&
      run.model_version &&
      Number.isSafeInteger(run.observation_count) &&
      run.observation_count >= 0 &&
      Number.isFinite(Date.parse(run.analysis_time)) &&
      typeof run.input_hash === 'string',
  );
}

function sameAnalysis(left: AnalysisSummary, right: AnalysisSummary): boolean {
  return (
    left.id === right.id &&
    left.underlying_id === right.underlying_id &&
    left.listing_id === right.listing_id &&
    (left.market_data_instrument_id ?? null) === (right.market_data_instrument_id ?? null)
  );
}

function sameRun(left: AnalysisRun, right: AnalysisRun): boolean {
  return (
    left.version === right.version &&
    left.status === right.status &&
    left.quality_status === right.quality_status &&
    left.model_id === right.model_id &&
    left.model_version === right.model_version &&
    left.observation_count === right.observation_count &&
    left.analysis_time === right.analysis_time &&
    left.input_hash === right.input_hash
  );
}

type DetailContext = { context: AnalysisSetupContext; version: number | null };

function parseDetailContext(analysisId: string, search: string): DetailContext {
  const params = new URLSearchParams(search);
  const versions = params.getAll('version');
  let version: number | null = null;
  if (versions.length) {
    requireRead(
      versions.length === 1 &&
        /^[1-9]\d*$/.test(versions[0]) &&
        positiveVersion(Number(versions[0])),
      'Die angeforderte Analyseversion ist ungültig. Bitte einen eindeutigen Versionslink öffnen.',
    );
    version = Number(versions[0]);
  }
  requireRead(
    !params.has('analysis_id') ||
      (params.getAll('analysis_id').length === 1 && params.get('analysis_id') === analysisId),
    'Die Analyseidentitäten im Link widersprechen sich.',
  );
  requireRead(
    !params.has('source_version') ||
      (version !== null &&
        params.getAll('source_version').length === 1 &&
        params.get('source_version') === String(version)),
    'Die angeforderte Quellversion widerspricht der ausgewählten Analyseversion.',
  );
  params.delete('version');
  params.set('analysis_id', analysisId);
  if (version !== null) params.set('source_version', String(version));
  return { context: parseAnalysisSetupContext(params), version };
}

type DetailSnapshot = {
  detail: AnalysisDetail;
  events: AnalysisEvent[];
  run: AnalysisRunDetail | null;
};

async function readDetail(
  context: AnalysisSetupContext,
  version: number | null,
  signal: AbortSignal,
): Promise<DetailSnapshot> {
  const [detail, events] = await Promise.all([
    analysisApiClient.get(context.analysisId, signal),
    analysisApiClient.events(context.analysisId, signal),
  ]);
  signal.throwIfAborted();
  requireRead(
    detail?.analysis?.id === context.analysisId && Array.isArray(detail.runs),
    'Der gelesene Analysestand gehört nicht zum angeforderten Kontext.',
  );
  const identity = detail.analysis;
  requireRead(
    identity.listing_id === null
      ? identity.underlying_id === null && Boolean(identity.market_data_instrument_id)
      : Boolean(identity.listing_id && identity.underlying_id),
    'Die gespeicherten Analyseidentitäten sind unvollständig oder widersprüchlich.',
  );
  requireRead(
    (!context.underlyingId || context.underlyingId === identity.underlying_id) &&
      (!context.listingId || context.listingId === identity.listing_id) &&
      (!context.instrumentId || context.instrumentId === identity.market_data_instrument_id),
    'Die gewählte Analyse gehört nicht zu den Identitäten im Link.',
  );
  requireRead(
    detail.runs.every(validRun) &&
      new Set(detail.runs.map((run) => run.version)).size === detail.runs.length &&
      Array.isArray(events),
    'Die Versionshistorie konnte nicht eindeutig gelesen werden.',
  );
  if (version === null) return { detail, events, run: null };
  const summary = detail.runs.find((run) => run.version === version);
  requireRead(summary, `Die ausdrücklich gewählte Version ${version} ist nicht vorhanden.`);
  const run = await analysisApiClient.getRun(context.analysisId, version, signal);
  signal.throwIfAborted();
  requireRead(
    run?.analysis &&
      sameAnalysis(identity, run.analysis) &&
      validRun(run.run) &&
      sameRun(summary, run.run) &&
      run.run.version === version &&
      run.metrics &&
      run.parameters &&
      Array.isArray(run.criteria) &&
      Array.isArray(run.notes) &&
      Array.isArray(run.data_sources),
    'Die gelesene Ergebnisversion passt nicht zur ausgewählten Analyse. Bitte den Lesestand erneut laden.',
  );
  return { detail, events, run };
}

function supersedingEvent(snapshot: DetailSnapshot, version: number) {
  return snapshot.events.find(
    (event) => event.event_type === 'SUPERSEDED' && event.source_version === version,
  );
}

function lifecycleBasis(snapshot: DetailSnapshot, version: number, replacement: string): string {
  return JSON.stringify({
    analysis: snapshot.detail.analysis,
    run: snapshot.run?.run,
    superseded: supersedingEvent(snapshot, version) ?? null,
    replacement: snapshot.detail.runs.find((run) => run.version === Number(replacement)) ?? null,
  });
}

function validateRetryReceipt(result: AnalysisRun, snapshot: DetailSnapshot) {
  const source = snapshot.run!.run;
  // RunSummaryResponse has no analysis_id. The request scope and later exact
  // run/event readback bind the response; no unsupported receipt fields are invented.
  requireReceipt(
    validRun(result) &&
      result.version > Math.max(...snapshot.detail.runs.map((run) => run.version)) &&
      terminalStatuses.includes(result.status) &&
      result.model_id === source.model_id &&
      result.model_version === source.model_version &&
      result.input_hash === source.input_hash &&
      result.observation_count === source.observation_count,
  );
}

function validateSupersedeReceipt(
  result: AnalysisEvent,
  source: AnalysisRun,
  replacement: number,
  reason: string,
) {
  requireReceipt(
    result &&
      typeof result.id === 'string' &&
      result.id &&
      result.event_type === 'SUPERSEDED' &&
      result.version === source.version &&
      result.source_version === source.version &&
      result.replacement_version === replacement &&
      result.from_status === source.status &&
      result.to_status === 'SUPERSEDED' &&
      result.reason === (reason || null) &&
      Number.isFinite(Date.parse(result.occurred_at)),
  );
}

function validateVerification(result: AnalysisVerification) {
  requireReceipt(
    result &&
      [
        'verified',
        'model_available',
        'input_hash_matches',
        'metrics_match',
        'criteria_match',
        'quality_status_match',
        'notes_match',
      ].every((key) => typeof result[key as keyof AnalysisVerification] === 'boolean'),
  );
}

function MetricTable({ metrics }: { metrics: Record<string, string | null> }) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {Object.entries(metrics).map(([name, value]) => (
        <div key={name} className="min-w-0 rounded-lg border border-slate-800 p-3">
          <dt className="break-words text-xs uppercase tracking-wide text-slate-500">
            {name.replaceAll('_', ' ')}
          </dt>
          <dd className="mt-1 break-words font-mono text-sm">{value ?? 'nicht verfügbar'}</dd>
        </div>
      ))}
    </dl>
  );
}

type LifecycleMode = 'retry' | 'supersede';
type Receipt =
  | { kind: 'retry'; message: string; run: AnalysisRun }
  | { kind: 'supersede'; message: string; event: AnalysisEvent }
  | { kind: 'verify'; message: string; verification: AnalysisVerification }
  | { kind: 'unknown'; message: string };

function validateReadback(
  receipt: Receipt | null,
  snapshot: DetailSnapshot,
  version: number | null,
) {
  if (version === null) return;
  if (receipt?.kind === 'retry') {
    const created = snapshot.detail.runs.find((run) => run.version === receipt.run.version);
    requireRead(
      created &&
        sameRun(created, receipt.run) &&
        supersedingEvent(snapshot, version)?.replacement_version === receipt.run.version,
      'Der bestätigte Retry ist im aktuellen Lesestand noch nicht vollständig sichtbar.',
    );
  }
  if (receipt?.kind === 'supersede')
    requireRead(
      snapshot.events.some(
        (event) =>
          event.id === receipt.event.id &&
          event.source_version === version &&
          event.replacement_version === receipt.event.replacement_version,
      ),
      'Das bestätigte Lifecycle-Ereignis ist im aktuellen Lesestand noch nicht sichtbar.',
    );
}

function detailReturn(search: string): string {
  try {
    const original = new URLSearchParams(search);
    const safe = new URLSearchParams({ analysis_id: 'return-context' });
    for (const name of ['candidate_id', 'evaluation_id', 'overview_context'])
      for (const value of original.getAll(name)) safe.append(name, value);
    const context = parseAnalysisSetupContext(safe);
    return analysisContextReturnTo({ ...context, analysisId: '' });
  } catch {
    return '/market-analyses';
  }
}

export function MarketAnalysisDetailPage() {
  const { analysisId = '' } = useParams();
  const location = useLocation();
  const receipts = useRef(new Map<string, Receipt>());
  const parsed = useMemo(() => {
    try {
      return { value: parseDetailContext(analysisId, location.search), error: null };
    } catch (error) {
      return { value: null, error: errorText(error) };
    }
  }, [analysisId, location.search]);
  if (!parsed.value)
    return (
      <section className="space-y-4">
        <Link to={detailReturn(location.search)}>
          {detailReturn(location.search).startsWith('/candidates?')
            ? 'Zurück zum Kandidaten'
            : 'Zurück zu Marktanalysen'}
        </Link>
        <h1 className="text-3xl font-semibold">Marktanalyse</h1>
        <p role="alert">{parsed.error}</p>
      </section>
    );
  // A confirmed route/query change owns a new draft and read generation. Reads
  // of the same context never remount the editor or replace its draft defaults.
  return (
    <AnalysisDetailContext
      key={`${analysisId}?${location.search}`}
      {...parsed.value}
      receipts={receipts.current}
    />
  );
}

function AnalysisDetailContext({
  context,
  version,
  receipts,
}: DetailContext & { receipts: Map<string, Receipt> }) {
  const navigate = useNavigate();
  const [snapshot, setSnapshot] = useState<DetailSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [readError, setReadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const receiptKey = `${context.analysisId}:${version ?? 'draft'}`;
  const [receipt, setReceipt] = useState<Receipt | null>(() => receipts.get(receiptKey) ?? null);
  const receiptRef = useRef<Receipt | null>(receipt);
  const [mode, setMode] = useState<LifecycleMode | null>(null);
  const [reason, setReason] = useState('');
  const [replacementVersion, setReplacementVersion] = useState('');
  const [busy, setBusy] = useState(false);
  const [transition, setTransition] = useState<(() => void) | null>(null);
  const [showSnapshot, setShowSnapshot] = useState(false);
  const [snapshotPage, setSnapshotPage] = useState<SnapshotPage | null>(null);
  const [snapshotOffset, setSnapshotOffset] = useState(0);
  const [snapshotError, setSnapshotError] = useState<string | null>(null);
  const snapshotLimit = 50;
  const live = useRef(true);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const busyRef = useRef(false);
  const dirtyRef = useRef(false);
  const editorHeading = useRef<HTMLHeadingElement>(null);
  const returnTo = analysisContextReturnTo({ ...context, analysisId: '' });

  const load = useCallback(async () => {
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    const requestGeneration = ++generation.current;
    setLoading(true);
    setReadError(null);
    try {
      const next = await readDetail(context, version, abort.signal);
      if (!live.current || generation.current !== requestGeneration) return;
      if (version === null && next.detail.runs.length) {
        const latest = Math.max(...next.detail.runs.map((run) => run.version));
        void navigate(analysisDetailUrl(context.analysisId, latest, context), { replace: true });
        return;
      }
      validateReadback(receiptRef.current, next, version);
      setSnapshot(next);
    } catch (error) {
      if (!abort.signal.aborted && live.current && generation.current === requestGeneration)
        setReadError(errorText(error));
    } finally {
      if (live.current && generation.current === requestGeneration) setLoading(false);
    }
  }, [context, navigate, version]);

  useEffect(() => {
    live.current = true;
    void load();
    return () => {
      live.current = false;
      controller.current?.abort();
    };
  }, [load]);

  useEffect(() => {
    if (mode) editorHeading.current?.focus();
  }, [mode]);

  useEffect(() => {
    if (!showSnapshot || version === null) return;
    const abort = new AbortController();
    let current = true;
    setSnapshotError(null);
    void analysisApiClient
      .getSnapshot(context.analysisId, version, snapshotOffset, snapshotLimit, abort.signal)
      .then((page) => {
        if (!current || abort.signal.aborted) return;
        requireRead(
          page &&
            Array.isArray(page.items) &&
            page.offset === snapshotOffset &&
            page.limit === snapshotLimit &&
            Number.isSafeInteger(page.total) &&
            page.total >= 0,
          'Die Snapshot-Seite passt nicht zum angeforderten Ausschnitt.',
        );
        setSnapshotPage(page);
      })
      .catch((error: unknown) => {
        if (current && !abort.signal.aborted) setSnapshotError(errorText(error));
      });
    return () => {
      current = false;
      abort.abort();
    };
  }, [context.analysisId, version, showSnapshot, snapshotOffset]);

  const resetDraft = () => {
    dirtyRef.current = false;
    setReason('');
    setReplacementVersion('');
    setMode(null);
    setTransition(null);
  };
  const localTransition = (next: () => void) => {
    if (busyRef.current) return;
    if (dirtyRef.current) setTransition(() => next);
    else next();
  };
  const chooseMode = (next: LifecycleMode | null) => {
    localTransition(() => {
      resetDraft();
      setMode(next);
      setActionError(null);
    });
  };

  async function perform(action: LifecycleMode | 'verify') {
    if (
      busyRef.current ||
      loading ||
      readError ||
      !snapshot?.run ||
      version === null ||
      receipt?.kind === 'unknown' ||
      (action !== 'verify' && mode !== action) ||
      (action === 'verify' && mode !== null)
    )
      return;
    if (action === 'supersede' && !positiveVersion(Number(replacementVersion))) return;
    busyRef.current = true;
    setBusy(true);
    setActionError(null);
    setReadError(null);
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    const requestGeneration = ++generation.current;
    const isCurrent = () => live.current && requestGeneration === generation.current;
    let writeStarted = false;
    let confirmed: Receipt | null = null;
    try {
      const fresh = await readDetail(context, version, abort.signal);
      if (!isCurrent()) return;
      setSnapshot(fresh);
      if (
        lifecycleBasis(fresh, version, replacementVersion) !==
        lifecycleBasis(snapshot, version, replacementVersion)
      ) {
        setActionError(
          'Der Lesestand hat sich geändert. Bitte Quelle und Aktion erneut prüfen; die Eingaben bleiben erhalten.',
        );
        return;
      }
      const source = fresh.run!.run;
      const superseded = supersedingEvent(fresh, version);
      if (action !== 'verify') {
        requireRead(!superseded, 'Diese Version wurde bereits ersetzt.');
        requireRead(
          terminalStatuses.includes(source.status),
          'Die Quellversion ist noch nicht abgeschlossen.',
        );
      }
      if (action === 'retry') {
        requireRead(
          ['FAILED', 'NOT_EVALUABLE'].includes(source.status),
          'Diese Version darf nicht erneut aus dem Snapshot ausgeführt werden.',
        );
        writeStarted = true;
        const result = await analysisApiClient.retry(context.analysisId, version, reason);
        validateRetryReceipt(result, fresh);
        confirmed = {
          kind: 'retry',
          run: result,
          message: `Retry als Version ${result.version} bestätigt. Die Quellversion ${version} bleibt historisch lesbar.`,
        };
      } else if (action === 'supersede') {
        const replacement = fresh.detail.runs.find(
          (run) => run.version === Number(replacementVersion),
        );
        requireRead(
          replacement &&
            replacement.version > version &&
            replacementStatuses.includes(replacement.status),
          'Die gewählte Ersatzversion ist nicht mehr zulässig.',
        );
        writeStarted = true;
        const result = await analysisApiClient.supersede(
          context.analysisId,
          version,
          replacement.version,
          reason,
        );
        validateSupersedeReceipt(result, source, replacement.version, reason);
        confirmed = {
          kind: 'supersede',
          event: result,
          message: `Version ${version} wurde durch Version ${replacement.version} ersetzt.`,
        };
      } else {
        writeStarted = true;
        const result = await analysisApiClient.verify(context.analysisId, version);
        validateVerification(result);
        confirmed = {
          kind: 'verify',
          verification: result,
          message: `Reproduzierbarkeitsprüfung für Version ${version} abgeschlossen.`,
        };
      }
      if (!isCurrent()) return;
      receiptRef.current = confirmed;
      receipts.set(receiptKey, confirmed);
      setReceipt(confirmed);
      resetDraft();
      // A confirmed write remains confirmed even if any following GET fails.
      const readback = await readDetail(context, version, abort.signal);
      if (!isCurrent()) return;
      validateReadback(confirmed, readback, version);
      setSnapshot(readback);
    } catch (error) {
      if (!isCurrent()) return;
      if (confirmed) {
        setReadError(`Schritt bestätigt; Nachlesen fehlgeschlagen: ${errorText(error)}`);
      } else if (!writeStarted || (error instanceof MarketApiError && error.status < 500)) {
        setActionError(
          error instanceof MarketApiError
            ? `${error.response.code}: ${error.message}`
            : errorText(error),
        );
      } else {
        const unknown: Receipt = {
          kind: 'unknown',
          message: `Abschluss unbekannt: ${errorText(error)} Es wird ausschließlich neu gelesen. Ein passender aktueller Stand beweist nicht den Abschluss dieses Requests; die Aktion wird nicht erneut gesendet.`,
        };
        receiptRef.current = unknown;
        receipts.set(receiptKey, unknown);
        setReceipt(unknown);
        try {
          const current = await readDetail(context, version, abort.signal);
          if (isCurrent()) setSnapshot(current);
        } catch (readFailure) {
          if (isCurrent()) setReadError(errorText(readFailure));
        }
      }
    } finally {
      if (isCurrent()) {
        busyRef.current = false;
        setBusy(false);
      }
    }
  }

  const guard = (
    <PendingNavigationGuard
      shouldBlock={() => busyRef.current || dirtyRef.current}
      busy={busy}
      onDiscard={resetDraft}
    />
  );
  const heading = (
    <header>
      <Link className="text-sm text-slate-400 underline" to={returnTo}>
        {context.candidateId ? 'Zurück zum Kandidaten' : 'Zurück zu Marktanalysen'}
      </Link>
      <h1 className="mt-3 text-3xl font-semibold">Marktanalyse</h1>
    </header>
  );
  if (!snapshot)
    return (
      <section className="space-y-4">
        {guard}
        {heading}
        {readError ? <p role="alert">{readError}</p> : <p role="status">Analyse wird geladen …</p>}
        {readError && (
          <button type="button" className="rounded border px-3 py-2" onClick={() => void load()}>
            Nur Lesestand erneut laden
          </button>
        )}
      </section>
    );

  const detail = snapshot.detail;
  const runDetail = snapshot.run;
  const selectedRun = runDetail?.run ?? null;
  const supersedeEvent = version === null ? undefined : supersedingEvent(snapshot, version);
  const retryable = selectedRun && ['FAILED', 'NOT_EVALUABLE'].includes(selectedRun.status);
  const replacementCandidates = detail.runs.filter(
    (run) => version !== null && run.version > version && replacementStatuses.includes(run.status),
  );
  const frozen = busy || loading || Boolean(readError) || receipt?.kind === 'unknown';
  const parameterEntries = Object.entries(runDetail?.parameters ?? {});
  const verification = receipt?.kind === 'verify' ? receipt.verification : null;
  const page = snapshotPage?.offset === snapshotOffset ? snapshotPage : null;
  const setupContext: Partial<AnalysisSetupContext> = {
    ...context,
    sourceVersion: version,
    underlyingId: detail.analysis.underlying_id ?? '',
    listingId: detail.analysis.listing_id ?? '',
    instrumentId: detail.analysis.market_data_instrument_id ?? '',
  };

  return (
    <section className="min-w-0 space-y-8">
      {guard}
      {transition && (
        <SetupDiscardDialog
          onStay={() => setTransition(null)}
          onDiscard={() => {
            if (busyRef.current) return;
            const next = transition;
            resetDraft();
            next();
          }}
        />
      )}
      {heading}
      <div className="space-y-3">
        <p className="break-all font-mono text-xs text-slate-500">{detail.analysis.id}</p>
        <p className="break-words text-sm text-slate-400">
          {detail.analysis.listing_id === null
            ? `Marktreferenz · Dateninstrument ${detail.analysis.market_data_instrument_id}`
            : `Basiswert ${detail.analysis.underlying_id} · Listing ${detail.analysis.listing_id}`}
        </p>
        <Link
          className="inline-block rounded-lg border border-slate-700 px-3 py-2"
          to={canonicalAnalysisSetupUrl(setupContext)}
        >
          {version === null
            ? 'Erste Analyseversion vorbereiten'
            : `Neue Analyseversion aus Version ${version} vorbereiten`}
        </Link>
      </div>

      {receipt && (
        <div
          role={receipt.kind === 'unknown' ? 'alert' : 'status'}
          className="space-y-2 rounded-lg border border-slate-700 p-3"
        >
          <p>{receipt.message}</p>
          {receipt.kind === 'retry' && (
            <Link
              className="underline"
              to={analysisDetailUrl(context.analysisId, receipt.run.version, context)}
            >
              Ergebnis des Retries · Version {receipt.run.version}
            </Link>
          )}
        </div>
      )}
      {actionError && (
        <p role="alert" className="rounded-lg border border-amber-700 p-3 text-amber-200">
          {actionError}
        </p>
      )}
      {readError && (
        <p role="alert" className="rounded-lg border border-amber-700 p-3 text-amber-200">
          {readError}
        </p>
      )}
      {(readError || receipt?.kind === 'unknown') && (
        <button
          type="button"
          disabled={busy || loading}
          className="rounded-lg border px-3 py-2 disabled:opacity-40"
          onClick={() => void load()}
        >
          Nur Lesestand erneut laden
        </button>
      )}
      {loading && <p role="status">Lesestand wird aktualisiert …</p>}

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">Versionshistorie</h2>
          {detail.runs.length > 0 && (
            <select
              aria-label="Analyseversion"
              value={version ?? ''}
              disabled={busy}
              onChange={(event) => {
                if (!busyRef.current)
                  void navigate(
                    analysisDetailUrl(context.analysisId, Number(event.target.value), context),
                  );
              }}
              className="max-w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
            >
              {detail.runs.map((run) => (
                <option key={run.version} value={run.version}>
                  Version {run.version} · {run.status}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                <th className="p-3">Version</th>
                <th className="p-3">Status</th>
                <th className="p-3">Qualität</th>
                <th className="p-3">Zeitpunkt</th>
                <th className="p-3">Lebenszyklus</th>
              </tr>
            </thead>
            <tbody>
              {detail.runs.map((run) => {
                const event = supersedingEvent(snapshot, run.version);
                return (
                  <tr key={run.version} className="border-t border-slate-800">
                    <td className="p-3">{run.version}</td>
                    <td className="p-3">
                      <AnalysisStatusBadge value={run.status} kind="status" />
                    </td>
                    <td className="p-3">
                      <AnalysisStatusBadge value={run.quality_status} kind="quality" />
                    </td>
                    <td className="p-3">{fmt(run.analysis_time)}</td>
                    <td className="p-3">
                      {event
                        ? `Ersetzt durch Version ${event.replacement_version}`
                        : 'Aktiv/historisch unverändert'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {!detail.runs.length && <p>Für diese Analyse wurde noch keine Version ausgeführt.</p>}
      </section>

      {runDetail && (
        <div className="space-y-8">
          <section className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-xl font-semibold">Ergebnis · Version {runDetail.run.version}</h2>
              <AnalysisStatusBadge value={runDetail.run.status} kind="status" />
              <AnalysisStatusBadge value={runDetail.run.quality_status} kind="quality" />
              {supersedeEvent && (
                <span className="rounded-full border border-slate-600 px-2 py-1 text-xs">
                  Ersetzt durch Version {supersedeEvent.replacement_version}
                </span>
              )}
            </div>
            <MetricTable metrics={runDetail.metrics} />
            {runDetail.notes.length > 0 && (
              <div>
                <h3 className="font-medium">Hinweise</h3>
                <ul className="list-disc pl-5 text-sm text-slate-300">
                  {runDetail.notes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">Bewertungskriterien</h2>
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900 text-slate-400">
                  <tr>
                    <th className="p-3">Kriterium</th>
                    <th className="p-3">Klassifikation</th>
                    <th className="p-3">Wert</th>
                    <th className="p-3">Erklärung</th>
                  </tr>
                </thead>
                <tbody>
                  {runDetail.criteria.map((criterion) => (
                    <tr key={criterion.code} className="border-t border-slate-800">
                      <td className="p-3 font-mono text-xs">{criterion.code}</td>
                      <td className="p-3">{criterion.classification}</td>
                      <td className="p-3 font-mono">{criterion.value ?? '–'}</td>
                      <td className="p-3 text-slate-300">{criterion.explanation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-xl font-semibold">Reproduzierbarkeit</h2>
              <button
                type="button"
                disabled={frozen || mode !== null}
                onClick={() => void perform('verify')}
                className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40"
              >
                Reproduzierbarkeit prüfen
              </button>
            </div>
            <dl className="grid gap-3 md:grid-cols-2">
              <div className="min-w-0 rounded-lg border border-slate-800 p-3">
                <dt className="text-xs text-slate-500">Gespeichertes Analysemodell</dt>
                <dd className="mt-1 break-all font-mono text-xs">
                  {runDetail.run.model_id} / {runDetail.run.model_version}
                </dd>
              </div>
              <div className="min-w-0 rounded-lg border border-slate-800 p-3">
                <dt className="text-xs text-slate-500">Eingabe-Hash</dt>
                <dd className="mt-1 break-all font-mono text-xs">{runDetail.run.input_hash}</dd>
              </div>
              <div className="rounded-lg border border-slate-800 p-3">
                <dt className="text-xs text-slate-500">Analysezeitpunkt</dt>
                <dd className="mt-1">{fmt(runDetail.run.analysis_time)}</dd>
              </div>
              <div className="min-w-0 rounded-lg border border-slate-800 p-3">
                <dt className="text-xs text-slate-500">Datenquellen</dt>
                <dd className="mt-1 break-words">
                  {runDetail.data_sources.join(', ') || 'Keine Quellen ausgewiesen'}
                </dd>
              </div>
            </dl>
            {verification && (
              <div className="rounded-xl border border-slate-800 p-4">
                <strong>
                  {verification.verified ? 'Reproduktion bestätigt' : 'Abweichung festgestellt'}
                </strong>
                <div className="mt-2 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(verification)
                    .filter(([key]) => key !== 'verified')
                    .map(([key, value]) => (
                      <span key={key}>
                        {key.replaceAll('_', ' ')}: {value ? 'OK' : 'abweichend'}
                      </span>
                    ))}
                </div>
              </div>
            )}
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-left text-sm">
                <tbody>
                  {parameterEntries.map(([name, value]) => (
                    <tr key={name} className="border-t border-slate-800 first:border-t-0">
                      <th className="p-3 text-slate-400">{name}</th>
                      <td className="p-3 font-mono text-xs">{JSON.stringify(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="space-y-3 rounded-xl border border-slate-800 p-4">
            {mode ? (
              <form
                aria-label="Lifecycle-Aktion"
                onSubmit={(event) => {
                  event.preventDefault();
                  void perform(mode);
                }}
                className="space-y-4"
              >
                <h2 ref={editorHeading} tabIndex={-1} className="text-xl font-semibold">
                  {mode === 'retry'
                    ? `Retry aus Snapshot · Version ${version}`
                    : `Version ${version} ausdrücklich ersetzen`}
                </h2>
                <p className="text-sm text-slate-400">
                  {mode === 'retry'
                    ? `Der Retry verwendet ausschließlich den gespeicherten Snapshot, die gespeicherten Parameter und ${runDetail.run.model_id} / ${runDetail.run.model_version}. Er erzeugt eine neue Version und ein Lifecycle-Ereignis.`
                    : 'Die ausgewählte Quellversion bleibt unverändert. Ein neues Lifecycle-Ereignis verweist auf die ausdrücklich gewählte neuere Ersatzversion.'}
                </p>
                <label className="block text-sm">
                  Begründung (optional)
                  <input
                    aria-label="Begründung"
                    maxLength={1000}
                    value={reason}
                    disabled={frozen}
                    onChange={(event) => {
                      dirtyRef.current = Boolean(event.target.value || replacementVersion);
                      setReason(event.target.value);
                    }}
                    className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
                  />
                </label>
                {mode === 'supersede' && (
                  <label className="block text-sm">
                    Ersatzversion
                    <select
                      aria-label="Ersatzversion"
                      value={replacementVersion}
                      disabled={frozen}
                      onChange={(event) => {
                        dirtyRef.current = Boolean(reason || event.target.value);
                        setReplacementVersion(event.target.value);
                      }}
                      className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
                    >
                      <option value="">Ersatzversion wählen</option>
                      {replacementCandidates.map((run) => (
                        <option key={run.version} value={run.version}>
                          Version {run.version} · {run.status}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <div className="flex flex-wrap gap-3">
                  <button
                    type="submit"
                    disabled={frozen || (mode === 'supersede' && !replacementVersion)}
                    className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40"
                  >
                    {mode === 'retry' ? 'Retry aus Snapshot bestätigen' : 'Als ersetzt markieren'}
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => chooseMode(null)}
                    className="rounded-lg border px-3 py-2 disabled:opacity-40"
                  >
                    Abbrechen
                  </button>
                  {mode === 'retry' && replacementCandidates.length > 0 && (
                    <button
                      type="button"
                      disabled={frozen}
                      onClick={() => chooseMode('supersede')}
                      className="rounded-lg border px-3 py-2 disabled:opacity-40"
                    >
                      Stattdessen Ersatzversion wählen
                    </button>
                  )}
                  {mode === 'supersede' && retryable && (
                    <button
                      type="button"
                      disabled={frozen}
                      onClick={() => chooseMode('retry')}
                      className="rounded-lg border px-3 py-2 disabled:opacity-40"
                    >
                      Stattdessen Retry vorbereiten
                    </button>
                  )}
                </div>
              </form>
            ) : (
              <>
                <h2 className="text-xl font-semibold">Lifecycle-Aktionen</h2>
                {supersedeEvent ? (
                  <p>Diese historische Version wurde bereits ersetzt.</p>
                ) : (
                  <div className="flex flex-wrap gap-3">
                    {retryable && (
                      <button
                        type="button"
                        disabled={frozen}
                        onClick={() => chooseMode('retry')}
                        className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40"
                      >
                        Retry aus Snapshot
                      </button>
                    )}
                    {terminalStatuses.includes(runDetail.run.status) &&
                      replacementCandidates.length > 0 && (
                        <button
                          type="button"
                          disabled={frozen}
                          onClick={() => chooseMode('supersede')}
                          className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40"
                        >
                          Ersatzversion festlegen
                        </button>
                      )}
                    {!retryable && replacementCandidates.length === 0 && (
                      <p>Für diese Version ist derzeit keine Lifecycle-Änderung verfügbar.</p>
                    )}
                  </div>
                )}
              </>
            )}
          </section>
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">Lifecycle-Events</h2>
            {snapshot.events.length ? (
              <div className="space-y-2">
                {snapshot.events.map((event) => (
                  <article
                    key={event.id}
                    className="rounded-lg border border-slate-800 p-3 text-sm"
                  >
                    <div className="flex flex-wrap justify-between gap-2">
                      <strong>{event.event_type}</strong>
                      <span className="text-slate-500">{fmt(event.occurred_at)}</span>
                    </div>
                    <p className="text-slate-300">
                      Version {event.version ?? '–'}: {event.from_status ?? '–'} → {event.to_status}
                      {event.replacement_version
                        ? ` · Ersatzversion ${event.replacement_version}`
                        : ''}
                    </p>
                    {event.reason && (
                      <p className="mt-1 break-words text-slate-400">Grund: {event.reason}</p>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <p className="text-slate-400">Keine Lifecycle-Events vorhanden.</p>
            )}
          </section>
          <section className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-xl font-semibold">Verwendeter Marktdaten-Snapshot</h2>
              <button
                type="button"
                disabled={busy}
                onClick={() => setShowSnapshot((value) => !value)}
                className="rounded-lg border border-slate-700 px-3 py-2 text-sm"
              >
                {showSnapshot
                  ? 'Snapshot ausblenden'
                  : `Snapshot anzeigen (${runDetail.run.observation_count})`}
              </button>
            </div>
            {showSnapshot && (
              <>
                {snapshotError && <p role="alert">{snapshotError}</p>}
                <div className="max-h-96 overflow-auto rounded-xl border border-slate-800">
                  <table className="w-full text-left text-xs">
                    <thead className="sticky top-0 bg-slate-900 text-slate-400">
                      <tr>
                        <th className="p-3">Datum</th>
                        <th className="p-3">Close</th>
                        <th className="p-3">Adjusted</th>
                        <th className="p-3">Quelle</th>
                        <th className="p-3">Qualität</th>
                      </tr>
                    </thead>
                    <tbody>
                      {page?.items.map((row) => (
                        <tr key={row.trading_date} className="border-t border-slate-800">
                          <td className="p-3">{row.trading_date}</td>
                          <td className="p-3">{row.close}</td>
                          <td className="p-3">{row.adjusted_close ?? '–'}</td>
                          <td className="p-3">
                            {row.provider} · {row.provider_symbol}
                          </td>
                          <td className="p-3">{row.quality_status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
                  <span>
                    {page
                      ? `${page.total === 0 ? 0 : page.offset + 1}–${Math.min(page.offset + page.items.length, page.total)} von ${page.total}`
                      : 'Snapshot wird geladen …'}
                  </span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={busy || snapshotOffset === 0}
                      onClick={() => setSnapshotOffset(Math.max(0, snapshotOffset - snapshotLimit))}
                    >
                      Zurück
                    </button>
                    <button
                      type="button"
                      disabled={
                        busy || page === null || snapshotOffset + snapshotLimit >= page.total
                      }
                      onClick={() => setSnapshotOffset(snapshotOffset + snapshotLimit)}
                    >
                      Weiter
                    </button>
                  </div>
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </section>
  );
}
