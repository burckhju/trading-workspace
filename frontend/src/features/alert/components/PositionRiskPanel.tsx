import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { riskApi } from '../services/risk';
import { riskLabel as label, riskPercent as percent } from '../services/riskLabels';
import type { RiskParameters, RiskView } from '../types/risk';
import { PositionRiskSummary } from './PositionRiskSummary';
import { IvRiskPanel } from './IvRiskPanel';
import type { PositionRiskPending } from '../types/pending';

interface Props {
  tradeId: string;
  readOnly?: boolean;
  onPendingChange?: (participant: PositionRiskPending | null) => void;
  isContextPending?: () => boolean;
}

export function PositionRiskPanel({
  tradeId,
  readOnly = false,
  onPendingChange,
  isContextPending,
}: Props) {
  // Remount on identity changes, including outstanding command responses.
  return (
    <RiskPanel
      key={tradeId}
      tradeId={tradeId}
      readOnly={readOnly}
      onPendingChange={onPendingChange}
      isContextPending={isContextPending}
    />
  );
}
function RiskPanel({ tradeId, readOnly, onPendingChange, isContextPending }: Props) {
  const [view, setView] = useState<RiskView | null>(null);
  const [parameters, setParameters] = useState<RiskParameters | null>(null);
  const [history, setHistory] = useState<RiskView[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [proposed, setProposed] = useState(false);
  const basisRef = useRef<RiskView | null>(null);
  const parametersRef = useRef<RiskParameters | null>(null);
  const confirmedRef = useRef(false);
  const busyRef = useRef(false);
  const writingRef = useRef(false);
  const ivPending = useRef<PositionRiskPending | null>(null);
  const updateParameters = (next: RiskParameters | null) => {
    parametersRef.current = next;
    setParameters(next);
  };
  const updateConfirmed = (next: boolean) => {
    confirmedRef.current = next;
    setConfirmed(next);
  };
  const participant = useMemo<PositionRiskPending>(
    () => ({
      isDirty: () =>
        Boolean(
          confirmedRef.current ||
            ivPending.current?.isDirty() ||
            (parametersRef.current &&
              basisRef.current &&
              Object.keys(parametersRef.current).some((key) => {
                const field = key as keyof RiskParameters;
                return (
                  String(parametersRef.current![field]) !==
                  String(basisRef.current!.configuration.parameters[field])
                );
              })),
        ),
      isBusy: () => writingRef.current,
      discard: () => {
        const saved = basisRef.current;
        parametersRef.current = saved?.configuration.parameters ?? null;
        confirmedRef.current = false;
        setParameters(parametersRef.current);
        setConfirmed(false);
        setProposed(false);
        setView(saved);
        ivPending.current?.discard();
      },
    }),
    [],
  );
  const reportIvPending = useCallback(
    (value: PositionRiskPending | null) => {
      ivPending.current = value;
      onPendingChange?.(participant);
    },
    [onPendingChange, participant],
  );
  useLayoutEffect(() => {
    onPendingChange?.(participant);
  }, [onPendingChange, participant, parameters, confirmed, busy]);
  useLayoutEffect(() => () => onPendingChange?.(null), [onPendingChange]);
  useEffect(() => {
    const controller = new AbortController();
    riskApi
      .read(tradeId, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) {
          basisRef.current = value;
          setView(value);
          parametersRef.current = value.configuration.parameters;
          setParameters(value.configuration.parameters);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setError('Risikoauswertung konnte nicht geladen werden.');
      });
    return () => controller.abort();
  }, [tradeId]);
  async function command(action: 'preview' | 'evaluate' | 'configure' | 'history') {
    if (!view || !parameters || busyRef.current || isContextPending?.()) return;
    busyRef.current = true;
    writingRef.current = action === 'configure' || action === 'evaluate';
    setBusy(true);
    setError('');
    try {
      if (action === 'history') setHistory(await riskApi.history(tradeId));
      else if (action === 'configure') {
        await riskApi.configure(tradeId, view, parameters, !view.configuration.enabled);
        const accepted = await riskApi.read(tradeId);
        basisRef.current = accepted;
        setView(accepted);
        updateParameters(accepted.configuration.parameters);
        updateConfirmed(false);
        setProposed(false);
      } else {
        const next = await (action === 'preview'
          ? riskApi.preview(tradeId, parameters)
          : riskApi.evaluate(tradeId));
        if (action !== 'preview') basisRef.current = next;
        setView(next);
        setProposed(action === 'preview');
      }
    } catch {
      setError(
        'Aktion fehlgeschlagen. Bei geändertem Regelstand bitte neu laden; es erfolgt keine automatische Wiederholung.',
      );
    } finally {
      busyRef.current = false;
      writingRef.current = false;
      setBusy(false);
    }
  }
  const button = 'rounded border border-slate-500 px-3 py-2 disabled:opacity-40';
  return (
    <section
      id="risk-signals"
      aria-label="Risiko- und Trendsignale"
      className="space-y-3 rounded border border-slate-600 p-4 text-sm"
    >
      <h3 className="font-semibold">Risiko- und Trendsignale</h3>
      {error && <p role="alert">{error}</p>}
      {!view || !parameters ? (
        <p>Daten werden geladen.</p>
      ) : (
        <>
          <p>
            {view.configuration.policy_version} · Revision {view.configuration.revision} ·{' '}
            {proposed
              ? 'Parametervorschau · gespeicherte Aktivierung unverändert'
              : view.configuration.enabled
                ? 'Warnregeln aktiv'
                : 'Warnregeln deaktiviert'}
          </p>
          <p>
            {view.listing?.symbol ?? 'Basiswert unbekannt'} ·{' '}
            {view.listing?.currency ?? 'Währung unbekannt'} ·{' '}
            {view.product?.direction ?? 'Call/Put unbekannt'} · ISIN{' '}
            {view.product?.isin ?? 'unbekannt'}
          </p>
          <PositionRiskSummary view={view} proposed={proposed} />
          <IvRiskPanel view={view} onPendingChange={reportIvPending} />
          <details className="space-y-3 rounded border border-slate-700 p-3">
            <summary className="cursor-pointer font-semibold">
              Kennzahlen, Kursqualität und Quellen im Detail
            </summary>
            <p>
              Parameter: SMA-Band {percent(view.configuration.parameters.hysteresis_fraction)} ·{' '}
              {view.configuration.parameters.confirmation_sessions} Bestätigungstage · Volatilität
              hoch {percent(view.configuration.parameters.volatility_high)}, Rücksetzung{' '}
              {percent(view.configuration.parameters.volatility_reset)} · Datenalter höchstens{' '}
              {view.configuration.parameters.maximum_age_days} Tage.
            </p>
            <p>
              {label(view.metrics.status)}: {label(view.metrics.reason)}. Zeitraum{' '}
              {view.metrics.window_start ?? '—'} bis {view.metrics.session ?? '—'} (
              {view.metrics.observations} Kurse).
            </p>
            <dl className="grid gap-3 sm:grid-cols-2">
              <div>
                <dt>Realisierte Volatilität (20 Renditen, jährlich)</dt>
                <dd>{percent(view.metrics.realized_volatility20)}</dd>
              </div>
              <div>
                <dt>Vorheriges, nicht überlappendes Fenster</dt>
                <dd>{percent(view.metrics.previous_volatility20)}</dd>
              </div>
              <div>
                <dt>Abstand zum SMA20</dt>
                <dd>{percent(view.metrics.distance_sma20)}</dd>
              </div>
              <div>
                <dt>Änderung des SMA20 zum Vortag</dt>
                <dd>{percent(view.metrics.sma20_slope)}</dd>
              </div>
              <div>
                <dt>ATR14 / unbereinigter Schlusskurs</dt>
                <dd>
                  {percent(view.metrics.atr14_relative)}
                  {view.metrics.atr14_relative === null
                    ? ` · ${label(view.metrics.atr_reason)}`
                    : ''}
                </dd>
              </div>
            </dl>
            <p>
              Trend: {label(view.assessment.state.trend)} · {label(view.assessment.transition)} ·{' '}
              {label(view.assessment.interpretation)}. {label(view.assessment.reason)}.
              Bestätigungen: {view.assessment.state.pending_sessions}.
            </p>
            {(view.assessment.state.trend_warning || view.assessment.state.volatility_warning) && (
              <p className="text-amber-200">
                Gespeicherter Warnzustand:{' '}
                {view.assessment.state.trend_warning ? 'Trendverschlechterung. ' : ''}
                {view.assessment.state.volatility_warning ? 'Erhöhte Volatilität.' : ''} Bei
                Datenlücken keine Entwarnung.
              </p>
            )}
            <p>
              Log-Renditen bereinigter Schlusskurse, Stichproben-Standardabweichung × √252. ATR14
              verwendet einfache Mittelung. Keine implizite Volatilität, Erfolgswahrscheinlichkeit
              oder Verkaufsempfehlung.
            </p>
            <h4 className="font-semibold">Optionsscheinquote und Vergleich</h4>
            <p>
              Geld {view.quote_quality.bid ?? 'fehlt'} · Brief {view.quote_quality.ask ?? 'fehlt'} ·
              Spread / Mid {view.quote_quality.spread_mid_percent ?? '—'} %. Volumen Geld/Brief:{' '}
              {view.quote_quality.bid_volume ?? 'unbekannt'} /{' '}
              {view.quote_quality.ask_volume ?? 'unbekannt'}.
            </p>
            <p>
              Quelle: {view.quote_quality.provider ?? 'unbekannt'} · Originalkurszeit:{' '}
              {view.quote_quality.observed_at ?? 'unbekannt'} · Empfangszeit:{' '}
              {view.quote_quality.received_at ?? 'unbekannt'}.
            </p>
            <ul>
              {view.quote_quality.reasons.map((reason) => (
                <li key={reason}>{label(reason)}</li>
              ))}
            </ul>
            <p>
              Aktie/Optionsschein: {label(view.comparison.status)} ·{' '}
              {view.comparison.reasons.map(label).join('; ')}
            </p>
            {view.comparison.status === 'AVAILABLE' && (
              <>
                <p>
                  {view.comparison.price_type}: Aktie {percent(view.comparison.underlying_return)},
                  Optionsschein {percent(view.comparison.warrant_return)}.{' '}
                  {view.comparison.descriptive_divergence
                    ? 'Beobachtete Richtungsdivergenz; keine nachgewiesene Fehlbewertung.'
                    : 'Keine Richtungsdivergenz in diesem Intervall.'}
                </p>
                <table>
                  <caption>Synchrone Reihen, Startwert 100</caption>
                  <thead>
                    <tr>
                      <th>Zeit</th>
                      <th>Aktie</th>
                      <th>Optionsschein</th>
                    </tr>
                  </thead>
                  <tbody>
                    {view.comparison.times.map((time, index) => (
                      <tr key={time}>
                        <td>{time}</td>
                        <td>{view.comparison.normalized_underlying[index]}</td>
                        <td>{view.comparison.normalized_warrant[index]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
            <p>
              Indikative Auswertung. Empfangszeit bestätigt keine Kursaktualität. Keine
              Ausführungsfreigabe.
            </p>
            <details>
              <summary>Herkunft und Reproduzierbarkeit</summary>
              <p>
                Auswertung {view.evaluated_at} · {view.metrics.policy_version} · Snapshot{' '}
                {view.snapshot_id ?? 'ungespeicherte Vorschau'} · Eingangskennung{' '}
                {view.input_fingerprint}
              </p>
              <ul>
                {view.input_prices.map((p) => (
                  <li key={p.trading_date}>
                    {p.trading_date} · {p.provider}/{p.provider_symbol} · bereinigter Schluss{' '}
                    {p.adjusted_close ?? 'fehlt'} {p.currency} · empfangen {p.retrieved_at}
                  </li>
                ))}
              </ul>
            </details>
          </details>
          {!readOnly && (
            <>
              <fieldset disabled={busy || isContextPending?.()} className="min-w-0 space-y-2">
                <legend>Explizite Regelkonfiguration</legend>
                <p>
                  Die vorgeschlagenen Schwellen sind nicht historisch kalibriert. Dezimalbrüche:
                  0.40 bedeutet 40 %. Aktivierung gilt nur für diese Position; eine neue Revision
                  beginnt mit einem neuen Ausgangszustand.
                </p>
                {(Object.keys(parameters) as (keyof RiskParameters)[]).map((key) => (
                  <label key={key} className="block">
                    {
                      {
                        hysteresis_fraction: 'SMA-Hystereseband (Bruch)',
                        confirmation_sessions: 'Bestätigungstage',
                        volatility_high: 'Volatilität Warnschwelle (Bruch)',
                        volatility_reset: 'Volatilität Rücksetzung (Bruch)',
                        maximum_age_days: 'Maximales Alter in Kalendertagen',
                      }[key]
                    }{' '}
                    <input
                      type="number"
                      step="any"
                      className="max-w-full rounded border bg-slate-900 p-1"
                      value={parameters[key]}
                      onChange={(event) => {
                        updateConfirmed(false);
                        updateParameters({
                          ...parameters,
                          [key]:
                            key === 'confirmation_sessions' || key === 'maximum_age_days'
                              ? Number(event.target.value)
                              : event.target.value,
                        });
                      }}
                    />
                  </label>
                ))}
                <button className={button} onClick={() => void command('preview')}>
                  Parameter unverbindlich prüfen
                </button>{' '}
                <button
                  className={button}
                  disabled={proposed}
                  onClick={() => void command('evaluate')}
                >
                  Aktuelle Konfiguration auswerten und speichern
                </button>
                <label className="block">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(event) => updateConfirmed(event.target.checked)}
                  />{' '}
                  Ich bestätige diese Parameter und die Änderung des Aktivierungszustands. Aktive
                  Warnungen können über das bestehende Monitoring zugestellt werden.
                </label>
                <button
                  className={button}
                  disabled={!confirmed || proposed}
                  onClick={() => void command('configure')}
                >
                  {view.configuration.enabled
                    ? 'Warnregeln deaktivieren'
                    : 'Warnregeln für diese Position aktivieren'}
                </button>
                {proposed && (
                  <button
                    className={button}
                    onClick={() => {
                      void riskApi
                        .read(tradeId)
                        .then((value) => {
                          basisRef.current = value;
                          setView(value);
                          setProposed(false);
                        })
                        .catch(() =>
                          setError('Aktuelle Konfiguration konnte nicht geladen werden.'),
                        );
                    }}
                  >
                    Zur aktuellen Konfiguration
                  </button>
                )}
              </fieldset>
              <button
                disabled={busy || isContextPending?.()}
                className={button}
                onClick={() => void command('history')}
              >
                Letzte 20 Auswertungen anzeigen
              </button>
              <ul>
                {history.map((item) => (
                  <li key={item.snapshot_id}>
                    {item.evaluated_at} · Revision {item.configuration.revision} ·{' '}
                    {label(item.assessment.transition)} · {label(item.metrics.reason)}
                    {' · IV: '}
                    {item.iv ? 'nicht auswertbar' : 'noch nicht geprüft'}
                    {' · Quelle '}
                    {item.quote_evidence?.provider ?? 'unbekannt'}
                    {' · Kursart '}
                    {item.iv?.quote_side ?? 'unbekannt'}
                    {' · Kurszeit '}
                    {item.quote_quality.observed_at ?? 'unbekannt'}
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </section>
  );
}
