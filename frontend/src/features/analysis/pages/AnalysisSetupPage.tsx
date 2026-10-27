import { useEffect, useMemo, useRef } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';
import { ExistingUnderlyingSelector } from '../../administration/components/ExistingUnderlyingSelector';
import { SetupDiscardDialog } from '../../administration/components/SetupDiscardDialog';
import { AnalysisParametersEditor } from '../components/AnalysisParametersEditor';
import { AnalysisStatusBadge } from '../components/AnalysisStatusBadge';
import { useAnalysisSetup } from '../components/useAnalysisSetup';
import {
  analysisDetailUrl,
  canonicalAnalysisSetupUrl,
  parseAnalysisSetupContext,
  type AnalysisSetupContext,
} from '../services/analysisWorkflowContext';
import { newAnalysisModelVersion } from '../types/api';

const buttonClass = 'rounded border border-slate-600 px-3 py-2 disabled:opacity-50';

export function AnalysisSetupPage() {
  const [params] = useSearchParams();
  const query = params.toString();
  const parsed = useMemo(() => {
    try {
      return { context: parseAnalysisSetupContext(new URLSearchParams(query)), error: '' };
    } catch (error: unknown) {
      return {
        context: null,
        error: error instanceof Error ? error.message : 'Der Analysekontext ist nicht lesbar.',
      };
    }
  }, [query]);
  if (!parsed.context) {
    const candidateId = params.get('candidate_id');
    return (
      <section className="mx-auto max-w-3xl space-y-4">
        <h1 className="text-2xl font-semibold">Analyseauftrag gesperrt</h1>
        <p role="alert">{parsed.error}</p>
        <Link
          className="text-sky-300 underline"
          to={
            candidateId
              ? `/candidates?candidate=${encodeURIComponent(candidateId)}`
              : '/market-analyses'
          }
        >
          Zurück zum Ausgangskontext
        </Link>
      </section>
    );
  }
  return <AnalysisSetupEditor key={parsed.context.key} context={parsed.context} />;
}

function AnalysisSetupEditor({ context }: { context: AnalysisSetupContext }) {
  const navigate = useNavigate();
  const location = useLocation();
  const editor = useAnalysisSetup(context, (created) => {
    void navigate(canonicalAnalysisSetupUrl(created), {
      replace: true,
      state: { createdAnalysisId: created.analysisId },
    });
  });
  const state: unknown = location.state;
  const justCreated = Boolean(
    context.analysisId &&
      state &&
      typeof state === 'object' &&
      'createdAnalysisId' in state &&
      state.createdAnalysisId === context.analysisId,
  );
  const { snapshot, choice, busy, loading, draft, outcome } = editor;
  const running = Boolean(choice.analysisId);
  const lockedUnderlying = Boolean(
    context.underlyingId || context.analysisId || context.workflowAction,
  );
  const lockedListing = Boolean(context.listingId || context.analysisId || context.workflowAction);
  const disabled = busy || loading || !editor.initialReady || outcome !== 'none';
  const returnTo = snapshot?.returnTo ?? context.returnTo;
  const source = snapshot?.source;
  const result = editor.acknowledged;
  const formHeading = useRef<HTMLHeadingElement>(null);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const focusedInitialContext = useRef(false);

  useEffect(() => {
    if (editor.initialReady && !focusedInitialContext.current) {
      focusedInitialContext.current = true;
      formHeading.current?.focus();
    }
  }, [editor.initialReady]);
  useEffect(() => {
    if (result) resultHeading.current?.focus();
  }, [result]);

  return (
    <section className="mx-auto min-w-0 w-full max-w-4xl space-y-5">
      <PendingNavigationGuard
        shouldBlock={editor.shouldBlock}
        busy={busy}
        onDiscard={editor.discardForRoute}
      />
      {editor.pending && !busy && (
        <SetupDiscardDialog onStay={editor.stay} onDiscard={editor.discard} />
      )}
      <header className="space-y-3">
        <Link className="text-sky-300 underline" to={returnTo}>
          {context.candidateId
            ? '← Zurück zum konkreten Kandidaten'
            : '← Zurück zum Ausgangskontext'}
        </Link>
        <h1 className="text-3xl font-semibold">Marktanalyse vorbereiten</h1>
        <p className="text-slate-300">
          {running
            ? 'Neue Analyseversion für den gebundenen Datenkontext.'
            : 'Vorhandenen Basiswert und Notierung übernehmen, dann die Analyse ausdrücklich anlegen.'}{' '}
          Jeder Schreibschritt wird einzeln bestätigt.
        </p>
      </header>

      {justCreated && !result && (
        <p role="status" className="rounded border border-emerald-700 p-3">
          Analyse angelegt: {context.analysisId}. Ihre Identität bleibt erhalten. Der Lauf benötigt
          eine eigene Bestätigung.
        </p>
      )}
      {editor.error && (
        <p role="alert" className="break-words rounded border border-rose-700 p-3">
          {editor.error}
        </p>
      )}
      {editor.readError && (
        <div role="alert" className="space-y-2 rounded border border-amber-700 p-3">
          <p>
            {outcome === 'complete' || justCreated
              ? 'Der Schreibauftrag ist abgeschlossen; das Nachlesen ist gestört. '
              : ''}
            {editor.readError}
          </p>
          <button
            type="button"
            disabled={busy || loading}
            className={buttonClass}
            onClick={editor.reload}
          >
            Nur Lesestand erneut laden
          </button>
        </div>
      )}
      {editor.reviewRequired && (
        <div className="space-y-3 rounded border border-amber-700 p-3">
          <p>
            Der aktuelle Lesestand wurde übernommen. Deine Eingaben bleiben erhalten. Prüfe die
            Identität und vorhandenen Versionen vor einer neuen Bestätigung.
          </p>
          <button
            type="button"
            className={buttonClass}
            disabled={busy || loading}
            onClick={editor.acknowledge}
          >
            Aktuellen Stand prüfen und Entwurf beibehalten
          </button>
        </div>
      )}
      {outcome === 'unknown' && (
        <div className="space-y-3 rounded border border-amber-700 p-3" role="status">
          <p>
            Der Transportabschluss ist unbekannt. Der aktuelle Zustand wird gelesen; ein passender
            Wert beweist nicht den Abschluss dieses Requests. Der Schreibauftrag wird nicht
            wiederholt.
          </p>
          {!editor.readError && (
            <button
              type="button"
              className={buttonClass}
              disabled={busy || loading}
              onClick={editor.reload}
            >
              Nur Lesestand erneut laden
            </button>
          )}
          {editor.possibleAnalyses.length > 0 && (
            <div className="space-y-2">
              <p>Aktuell vorhandene Analysen für genau diesen Basiswert und dieses Listing:</p>
              {editor.possibleAnalyses.map((analysis) => (
                <Link
                  key={analysis.id}
                  className="block break-all text-sky-300 underline"
                  to={analysisDetailUrl(analysis.id, null, context)}
                >
                  Analyse {analysis.id} lesend öffnen
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
      {loading && <p role="status">Analysekontext wird gelesen …</p>}

      {snapshot && (snapshot.underlying || snapshot.detail) && (
        <section
          aria-label="Gebundener Analysekontext"
          className="min-w-0 space-y-2 break-words rounded border border-slate-700 p-4 text-sm"
        >
          <h2 className="font-semibold">Gewählter Kontext</h2>
          {snapshot.underlying && (
            <p>
              <strong>{snapshot.underlying.name}</strong> ·{' '}
              {snapshot.underlying.type === 'ETF' ? 'ETF' : 'Aktie'}
              {snapshot.underlying.isin ? ` · ISIN ${snapshot.underlying.isin}` : ''}
              <span className="block text-xs text-slate-400">
                Basiswert-ID: {snapshot.underlying.id}
              </span>
            </p>
          )}
          {snapshot.listing && (
            <p>
              {snapshot.listing.ticker} ·{' '}
              {snapshot.listing.trading_venue_name ?? snapshot.listing.trading_venue_mic} ·{' '}
              {snapshot.listing.currency_code}
              {!snapshot.listing.is_primary && ' · nichtprimäre Notierung'}
              <span className="block text-xs text-slate-400">
                Listing-ID: {snapshot.listing.id}
              </span>
            </p>
          )}
          {snapshot.detail?.analysis.listing_id === null && (
            <p>
              Direkte Marktreferenzanalyse ohne Basiswert oder Listing
              <span className="block text-xs text-slate-400">
                Dateninstrument: {snapshot.detail.analysis.market_data_instrument_id}
              </span>
            </p>
          )}
          {running && (
            <p className="text-xs text-slate-400">
              Analyse-ID: {choice.analysisId} · Vorhandene Versionen:{' '}
              {snapshot.detail?.runs.length ?? 0}
            </p>
          )}
          {context.workflowAction && (
            <p>
              Aktion und Ausgangsobjekt gehören zum konkreten blockierten Kandidatenschritt{' '}
              {snapshot.workflowStep?.label ?? context.stepCode}. Der tatsächliche Listing-Basiswert
              bleibt gebunden.
            </p>
          )}
        </section>
      )}

      {result && outcome === 'complete' ? (
        <section
          aria-label="Bestätigter Analyselauf"
          className="space-y-3 rounded border border-emerald-700 p-4"
        >
          <h2 ref={resultHeading} tabIndex={-1} className="text-xl font-semibold">
            Schreibauftrag für Version {result.run.version} abgeschlossen
          </h2>
          <div className="flex flex-wrap gap-2">
            <AnalysisStatusBadge value={result.run.status} kind="status" />
            <AnalysisStatusBadge value={result.run.quality_status} kind="quality" />
          </div>
          <p>
            Bestätigter Zeitraum: {result.request.start_date} bis {result.request.end_date}. Der
            gespeicherte Ausführungsstatus bewertet diesen Lauf; daraus folgt keine
            Candidate-Evaluation.
          </p>
          {editor.readRun && (
            <p>
              Version {editor.readRun.run.version} mit Modell {editor.readRun.run.model_id} /{' '}
              {editor.readRun.run.model_version} und ihren Parametern wurde genau nachgelesen.
            </p>
          )}
          {editor.readRun && snapshot?.workflow && (
            <p>
              Aktuelle Kandidaten-Readiness:{' '}
              {snapshot.workflow.ready ? 'bereit' : 'weitere Schritte offen'}.
            </p>
          )}
          <Link
            className="inline-block text-sky-300 underline"
            to={analysisDetailUrl(choice.analysisId, result.run.version, context)}
          >
            Genau diese Analyseversion öffnen
          </Link>
        </section>
      ) : (
        <form
          aria-label="Gemeinsamer Analyseeditor"
          className="min-w-0 space-y-5 rounded-xl border border-slate-700 p-4 sm:p-6"
          onSubmit={(event) => {
            event.preventDefault();
            void editor.submit();
          }}
        >
          <h2 ref={formHeading} tabIndex={-1} className="text-xl font-semibold">
            {running ? 'Neue Analyseversion' : 'Analyse anlegen'}
          </h2>
          {!running && !lockedUnderlying && (
            <ExistingUnderlyingSelector
              value={choice.underlyingId}
              label={snapshot?.underlying?.name}
              disabled={busy || !editor.initialReady || outcome !== 'none'}
              onChange={(id) => editor.changeTarget(id, '')}
            />
          )}
          {!running && !lockedListing && (
            <label className="block text-sm">
              Bestehende Notierung
              <select
                required
                className="mt-1 w-full min-w-0 rounded border border-slate-600 bg-slate-950 p-2"
                disabled={disabled || !snapshot?.underlying}
                value={choice.listingId}
                onChange={(event) => editor.changeTarget(choice.underlyingId, event.target.value)}
              >
                <option value="">Bitte wählen</option>
                {snapshot?.underlying?.listings
                  .filter((listing) => listing.lifecycle_status === 'ACTIVE')
                  .map((listing) => (
                    <option key={listing.id} value={listing.id}>
                      {listing.ticker} · {listing.trading_venue_mic} · {listing.currency_code}
                      {listing.is_primary ? ' · primär' : ''}
                    </option>
                  ))}
              </select>
            </label>
          )}
          {running ? (
            <>
              <p className="text-sm text-slate-300">
                Modell für diesen neuen Lauf: EOD_TREND_MOMENTUM / {newAnalysisModelVersion}.
              </p>
              {source ? (
                <div className="space-y-3 rounded border border-slate-600 p-3 text-sm">
                  <p>
                    Ausdrücklich gewählte Quellversion: {source.run.version} · {source.run.model_id}{' '}
                    / {source.run.model_version}. Die gespeicherten Parameter können als Vorschlag
                    übernommen werden.
                  </p>
                  <p>
                    Der ursprüngliche Anfragezeitraum ist im API-Lesestand nicht enthalten. Bitte
                    Von und Bis für den neuen Lauf selbst wählen. Ein neuer Lauf verwendet aktuelle
                    gespeicherte Marktdaten; Retry aus dem historischen Snapshot bleibt eine eigene
                    Lifecycle-Aktion.
                  </p>
                  <button
                    type="button"
                    className={buttonClass}
                    disabled={disabled}
                    onClick={editor.prepareSource}
                  >
                    Parameter aus Version {source.run.version} vorbereiten
                  </button>
                </div>
              ) : (
                <p className="text-sm text-slate-400">
                  Zeitraumsvorschlag: letzte {context.workflowAction ? 400 : 365} Tage bis heute.
                  Prüfe beide Datumswerte ausdrücklich vor dem Ausführen.
                </p>
              )}
              <AnalysisParametersEditor
                draft={draft}
                onChange={editor.changeDraft}
                disabled={disabled}
              />
            </>
          ) : (
            <p className="text-sm text-slate-300">
              Anlegen speichert nur die Analyseidentität für dieses vorhandene Listing. Zeitraum,
              Parameter und Ausführung werden anschließend separat bestätigt.
            </p>
          )}

          {editor.problem && <p className="text-sm text-amber-200">{editor.problem}</p>}
          <label className="flex items-start gap-3">
            <input
              type="checkbox"
              className="mt-1"
              checked={editor.confirmed}
              disabled={
                disabled ||
                editor.reviewRequired ||
                Boolean(editor.problem) ||
                Boolean(editor.readError)
              }
              onChange={(event) => editor.confirm(event.target.checked)}
            />
            <span>
              {running
                ? 'Ich bestätige diesen Datenkontext, den gewählten Zeitraum und alle Parameter für genau einen neuen Lauf.'
                : 'Ich bestätige die Anlage genau einer Analyse für den angezeigten Basiswert und dieses Listing.'}
            </span>
          </label>
          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              className="rounded border border-sky-600 bg-sky-950 px-4 py-2 disabled:opacity-50"
              disabled={!editor.canSubmit}
            >
              {busy
                ? 'Schritt läuft …'
                : running
                  ? 'Bestätigten Analyselauf ausführen'
                  : 'Bestätigte Analyse anlegen'}
            </button>
            {running && (
              <button
                type="button"
                className={buttonClass}
                disabled={disabled}
                onClick={editor.cancel}
              >
                Eingaben zurücksetzen
              </button>
            )}
            <button
              type="button"
              className={buttonClass}
              disabled={busy || loading}
              onClick={editor.reload}
            >
              Lesestand aktualisieren
            </button>
          </div>
        </form>
      )}
      <p className="text-xs text-slate-400">
        Vor jedem Auftrag wird der Kontext erneut gelesen. Die vorhandenen Analyse-APIs bieten keine
        atomare Versionssperre oder Replaygarantie. Analyseanlage und Lauf bleiben getrennte
        Schreibschritte.
      </p>
    </section>
  );
}
