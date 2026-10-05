import { riskLabel as label, riskPercent as percent } from '../services/riskLabels';
import type { RiskView } from '../types/risk';

/** Summarizes backend assessments without deriving new thresholds or alert truth. */
export function PositionRiskSummary({ view, proposed }: { view: RiskView; proposed: boolean }) {
  const available =
    view.metrics.status === 'AVAILABLE' && view.assessment.transition !== 'NOT_EVALUABLE';
  const state = view.assessment.state;
  const card = 'min-w-0 rounded-lg border border-slate-700 bg-slate-900/40 p-3';
  const retainedWarning = state.trend_warning || state.volatility_warning;
  return (
    <section aria-label="Risikoübersicht" className="space-y-2">
      <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className={card}>
          <dt className="text-slate-400">Trendrichtung</dt>
          <dd className={available && state.trend_warning ? 'mt-1 text-amber-200' : 'mt-1'}>
            {available ? label(view.assessment.interpretation) : 'Nicht auswertbar'}
          </dd>
          <dd className="mt-1 text-xs text-slate-300">
            {available ? label(state.trend) : 'Keine qualifizierte neue Trendbewertung.'}
          </dd>
          {available && view.assessment.transition === 'CONFIRMING' && (
            <dd className="mt-1 text-xs text-amber-200">
              Wechsel in Prüfung: {state.pending_sessions} von{' '}
              {view.configuration.parameters.confirmation_sessions} Bestätigungstagen.
            </dd>
          )}
          {available && view.assessment.transition === 'INITIALIZED' && (
            <dd className="mt-1 text-xs text-slate-300">Ausgangszustand, noch kein Trendbruch.</dd>
          )}
        </div>
        <div className={card}>
          <dt className="text-slate-400">Realisierte Volatilität</dt>
          <dd className={available && state.volatility_warning ? 'mt-1 text-amber-200' : 'mt-1'}>
            {available ? percent(view.metrics.realized_volatility20) : 'Nicht auswertbar'}
          </dd>
          <dd className="mt-1 text-xs text-slate-300">
            {available
              ? state.volatility_warning
                ? 'Erhöhter Warnzustand in der Auswertung'
                : 'Kein erhöhter Warnzustand in der Auswertung'
              : 'Keine Entwarnung aus fehlenden Daten.'}
          </dd>
          <dd className="mt-1 text-xs text-slate-400">
            20 Tagesrenditen · auf ein Jahr hochgerechnet
          </dd>
        </div>
        <div className={card}>
          <dt className="text-slate-400">Datenstand</dt>
          <dd className="mt-1">
            Basiswert: {label(view.metrics.status)} · {view.metrics.session ?? 'Kurstag unbekannt'}
          </dd>
          <dd className="mt-1 text-xs text-slate-300">{label(view.metrics.reason)}</dd>
          <dd className="mt-1 text-xs text-slate-300">
            Optionsscheinquote: {label(view.quote_quality.status)}
          </dd>
        </div>
        <div className={card}>
          <dt className="text-slate-400">Warnregeln</dt>
          <dd className="mt-1">
            {proposed ? 'Vorschau' : view.configuration.enabled ? 'Aktiv' : 'Deaktiviert'}
          </dd>
          <dd className="mt-1 text-xs text-slate-300">
            {proposed
              ? 'Unverbindliche Vorschau · Aktivierung unverändert'
              : view.configuration.enabled
                ? 'Zustellung separat unter Positions-Alerts prüfen.'
                : 'Diese Auswertung aktiviert keine Warnregeln.'}
          </dd>
        </div>
      </dl>
      {!available && retainedWarning && (
        <p className="text-amber-200">Bisheriger Warnzustand bleibt bei Datenproblemen bestehen.</p>
      )}
    </section>
  );
}
