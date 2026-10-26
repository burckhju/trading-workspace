import type { TradePlanDetailResponse, TradePlanVersionResponse } from '../types/api';

function Value({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="min-w-0">
      <dt className="text-slate-400">{label}</dt>
      <dd className="mt-1 whitespace-pre-wrap break-words">{value || '—'}</dd>
    </div>
  );
}

export function TradePlanVersionContent({ version }: { version: TradePlanVersionResponse }) {
  return (
    <div className="space-y-6">
      <section aria-label="These">
        <h3 className="font-semibold">Trade Thesis</h3>
        <p className="mt-2 whitespace-pre-wrap break-words text-sm">{version.thesis}</p>
      </section>
      <section aria-label="Einstieg">
        <h3 className="font-semibold">Entry · {version.entry.type}</h3>
        <dl className="mt-3 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <Value label="Planwährung" value={version.entry.currency} />
          {version.entry.type === 'PRICE' && (
            <Value label="Entry-Preis" value={version.entry.price} />
          )}
          {version.entry.type === 'PRICE_RANGE' && (
            <>
              <Value label="Preis von" value={version.entry.price_from} />
              <Value label="Preis bis" value={version.entry.price_to} />
            </>
          )}
          {version.entry.type === 'TRIGGER' && (
            <Value label="Trigger" value={version.entry.trigger} />
          )}
          <Value label="Referenzpreis" value={version.entry.reference_price} />
          <Value label="Gültig bis" value={version.entry.valid_until} />
          <Value label="Entry-Begründung" value={version.entry.rationale} />
        </dl>
      </section>
      <section aria-label="Invalidierung">
        <h3 className="font-semibold">Stop und Invalidierung</h3>
        <dl className="mt-3 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <Value label="Technischer Stop" value={version.invalidation.stop_price} />
          <Value label="Invalidierungsregel" value={version.invalidation.invalidation_rule} />
          <Value label="Invalidierungsbegründung" value={version.invalidation.rationale} />
        </dl>
      </section>
      <section aria-label="Geordnete Kursziele">
        <h3 className="font-semibold">Kursziele</h3>
        <ol className="mt-3 space-y-3 text-sm">
          {version.targets.map((target) => (
            <li key={target.sequence} className="rounded-lg border border-slate-800 p-3">
              <p className="font-medium">
                Target {target.sequence} · {target.price}
              </p>
              {target.rationale && (
                <p className="mt-1 whitespace-pre-wrap break-words text-slate-300">
                  {target.rationale}
                </p>
              )}
            </li>
          ))}
        </ol>
      </section>
      <section aria-label="Risikoannahmen">
        <h3 className="font-semibold">Risikoannahmen</h3>
        <dl className="mt-3 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <Value label="Plan-Risiko / Annahme" value={version.risk_assumptions.thesis_risk} />
          <Value label="Max-Loss-Annahme" value={version.risk_assumptions.max_loss_assumption} />
          <Value label="Risk Notes" value={version.risk_assumptions.notes} />
        </dl>
      </section>
      {version.change_reason && (
        <dl>
          <Value label="Änderungsgrund" value={version.change_reason} />
        </dl>
      )}
    </div>
  );
}

export function TradePlanProvenance({
  plan,
  version,
}: {
  plan: TradePlanDetailResponse['plan'];
  version: TradePlanVersionResponse;
}) {
  const candidate = version.candidate_evaluation;
  return (
    <details className="rounded-xl border border-slate-800 p-5">
      <summary className="cursor-pointer font-semibold">Herkunft und Lifecycle anzeigen</summary>
      <div className="mt-4 space-y-4 text-sm">
        <p>
          {plan.origin_type === 'MANUAL'
            ? 'Manueller Ursprung · Basiswert bei Anlage gewählt.'
            : `Kandidatenursprung · gespeicherte Evaluation${candidate ? ` v${candidate.evaluation_version}` : ''}.`}
        </p>
        <p>Erstellt {new Date(version.created_at).toLocaleString('de-DE')}</p>
        {candidate && (
          <>
            <p>
              {candidate.model_id} · {candidate.model_version} · {candidate.direction}
            </p>
            <p>
              {candidate.qualification} · {candidate.quality_status} ·{' '}
              {new Date(candidate.evaluated_at).toLocaleString('de-DE')}
            </p>
            <p className="text-slate-400">
              Diese gespeicherte Evaluation bleibt auch nach späteren Neubewertungen gebunden.
            </p>
          </>
        )}
        {version.approval && (
          <div className="rounded-lg border border-emerald-800 p-3">
            <h3 className="font-medium">Approval-Nachweis</h3>
            <p>
              Version {version.approval.version} ·{' '}
              {new Date(version.approval.approved_at).toLocaleString('de-DE')}
            </p>
          </div>
        )}
        <section>
          <h3 className="font-medium">Lifecycle für Version {version.version}</h3>
          {version.events.length === 0 ? (
            <p className="mt-2 text-slate-400">Noch keine Lifecycle-Ereignisse.</p>
          ) : (
            <ol className="mt-2 space-y-2">
              {version.events.map((event) => (
                <li key={event.id} className="rounded-lg border border-slate-800 p-3">
                  <p>
                    {event.event_type} · {event.from_status ?? '—'} → {event.to_status}
                  </p>
                  <time>{new Date(event.occurred_at).toLocaleString('de-DE')}</time>
                  {event.reason && <p className="mt-1 whitespace-pre-wrap">{event.reason}</p>}
                </li>
              ))}
            </ol>
          )}
        </section>
        <details className="text-xs text-slate-400">
          <summary className="cursor-pointer">Technische Provenance anzeigen</summary>
          <dl className="mt-3 space-y-2 break-all">
            <Value label="TradePlan-ID" value={plan.id} />
            <Value label="Underlying-ID" value={plan.underlying_id} />
            <Value label="TradePlanVersion-ID" value={version.id} />
            <Value label="Vorgängerversion-ID" value={version.previous_version_id} />
            <Value label="Erstellt von" value={version.created_by} />
            <Value label="Candidate-ID" value={plan.candidate_id} />
            <Value label="CandidateEvaluation-ID" value={plan.candidate_evaluation_id} />
            {version.approval && (
              <>
                <Value label="Approval-ID" value={version.approval.approval_id} />
                <Value label="Freigegeben von" value={version.approval.actor} />
                <Value label="Approval-Correlation-ID" value={version.approval.correlation_id} />
              </>
            )}
          </dl>
          {candidate && (
            <ul className="mt-3 space-y-2">
              {candidate.sources.map((source) => (
                <li key={`${source.role}-${source.source_id}-${source.source_version}`}>
                  {source.role} · {source.source_type} · {source.source_id} · v
                  {source.source_version}
                  {' · '}
                  {source.model_id}/{source.model_version}
                </li>
              ))}
            </ul>
          )}
          {version.events.map((event) => (
            <p key={event.id} className="mt-2 break-all">
              {event.event_type} · Actor {event.actor} · Correlation {event.correlation_id ?? '—'}
            </p>
          ))}
        </details>
      </div>
    </details>
  );
}
