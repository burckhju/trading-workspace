import { useEffect, useRef, useState } from 'react';
import type { HebeltraderTarget, HebeltraderTargetsReport } from '../hebeltraderTargets';
import { assessHebeltraderTargets, readHebeltraderTargets } from '../services/hebeltraderTargets';

interface Props {
  tradeId: string;
  positionId: string;
  reloadToken?: string | number;
}

const targetLabels: Record<HebeltraderTarget['status'], string> = {
  PROVEN: 'Treffer belegt',
  NOT_PROVEN: 'Kein Treffer in verfügbaren Belegen',
  NOT_ASSESSABLE: 'Nicht beurteilbar',
  REVIEW_REQUIRED: 'Erneute Prüfung erforderlich',
};

const basisLabels = {
  AVAILABLE: 'Prüfgrundlage belegt',
  NOT_ASSESSABLE: 'Nicht beurteilbar',
  NOT_APPLICABLE: 'Derzeit nicht anwendbar',
};

function time(value: string) {
  return <time dateTime={value}>{value}</time>;
}

function Target({ value }: { value: HebeltraderTarget }) {
  return (
    <li className="space-y-1 rounded border border-slate-700 p-3">
      <h4 className="font-semibold">
        {value.target}: {targetLabels[value.status]}
      </h4>
      <p>{value.detail}</p>
      {value.threshold !== null && (
        <p>
          Basiswertmarke: {value.threshold} {value.currency ?? 'Währung unbekannt'}
        </p>
      )}
      {value.status === 'NOT_PROVEN' && <p>Ein fehlender Trefferbeleg ist keine Entwarnung.</p>}
      {value.evidence && (
        <>
          <p>
            Belegtag: {time(value.evidence.trading_date)} · Tageshoch des Basiswerts:{' '}
            {value.evidence.high} {value.currency ?? 'Währung unbekannt'}.
          </p>
          <p>
            Nur tagesgenau belegt; Trefferuhrzeit und Reihenfolge innerhalb des Tages sind
            unbekannt.
          </p>
          <p className="text-xs text-slate-300">
            Ursprüngliche Zielquelle: {value.proof_source_version_id} · Maßstabsreferenz des
            Zielbelegs: {value.proof_scale_reference}
          </p>
          <details className="text-xs text-slate-300">
            <summary className="cursor-pointer">{value.target}-Beleg und Feststellungszeit</summary>
            <p>
              Belegintervall: {value.evidence.interval_start} bis {value.evidence.interval_end}.
              Keine belegten Handelssitzungszeiten.
            </p>
            <p>Festgestellt: {time(value.evidence.detected_at)}</p>
            <p>
              Quelle: {value.evidence.provider} · {value.evidence.provider_symbol} · Listing{' '}
              {value.evidence.listing_id}
            </p>
            <p>
              Ereignis: {value.event_id ?? 'Nicht zugeordnet'} · Kursbeleg:{' '}
              {value.evidence.source_row_id}
            </p>
            <p>Kursbeleg-Fingerprint: {value.evidence.source_fingerprint}</p>
          </details>
        </>
      )}
      {value.reasons.length > 0 && (
        <details className="text-xs text-slate-300">
          <summary className="cursor-pointer">{value.target}-Prüfgründe</summary>
          <ul>
            {value.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </details>
      )}
    </li>
  );
}

export function HebeltraderTargetHistory(props: Props) {
  return (
    <History key={`${props.tradeId}:${props.positionId}:${props.reloadToken ?? 0}`} {...props} />
  );
}

function History({ tradeId, positionId }: Props) {
  const [report, setReport] = useState<HebeltraderTargetsReport | null>(null);
  const [readError, setReadError] = useState<string | null>(null);
  const [commandError, setCommandError] = useState<string | null>(null);
  const [readAttempt, setReadAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [needsReadback, setNeedsReadback] = useState(false);
  const generation = useRef(0);
  const pendingCommand = useRef(false);
  const commandController = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const currentGeneration = ++generation.current;
    const current = () => generation.current === currentGeneration && !controller.signal.aborted;
    readHebeltraderTargets(tradeId, positionId, controller.signal)
      .then((value) => {
        if (!current()) return;
        setReport(value);
        setReadError(null);
        setCommandError(null);
        setNeedsReadback(false);
      })
      .catch((reason: unknown) => {
        if (current())
          setReadError(
            reason instanceof Error
              ? reason.message
              : 'Die Zielhistorie konnte nicht gelesen werden.',
          );
      });
    return () => {
      generation.current += 1;
      controller.abort();
      commandController.current?.abort();
    };
  }, [tradeId, positionId, readAttempt]);

  async function assess() {
    if (!report || pendingCommand.current || needsReadback || report.position_state !== 'OPEN')
      return;
    pendingCommand.current = true;
    setBusy(true);
    setCommandError(null);
    const controller = new AbortController();
    commandController.current = controller;
    const currentGeneration = generation.current;
    const current = () => generation.current === currentGeneration && !controller.signal.aborted;
    try {
      const result = await assessHebeltraderTargets(
        tradeId,
        {
          position_id: positionId,
          request_id: crypto.randomUUID(),
          expected_basis_id: report.current_basis_id,
          expected_assessment_id: report.latest_assessment?.id ?? null,
          confirmation: 'ASSESS_SAVED_HEBELTRADER_EVIDENCE',
        },
        controller.signal,
      );
      if (current()) setReport(result);
    } catch (reason) {
      if (current()) {
        setCommandError(
          reason instanceof Error
            ? reason.message
            : 'Der Ausgang der Prüfung konnte nicht bestätigt werden.',
        );
        setNeedsReadback(true);
      }
    } finally {
      if (current()) {
        pendingCommand.current = false;
        setBusy(false);
      }
    }
  }

  const assessment = report?.latest_assessment;
  return (
    <section
      aria-label="Hebeltrader-Zielhistorie"
      aria-busy={busy}
      className="min-w-0 space-y-3 break-words rounded-xl border border-slate-700 bg-slate-950/40 p-3 sm:p-4"
    >
      <h3 className="font-semibold text-white">Hebeltrader · Dauerhafte Zielbelege</h3>
      <p>
        Gespeicherte Z1-/Z2-Belege auf der Basiswertachse bleiben auch bei späteren Kursrückgängen
        nachvollziehbar. Ein Zieltreffer ist keine Verkaufsausführung.
      </p>
      {!report && !readError && <p>Zielhistorie wird geladen …</p>}
      {readError && <p role="alert">{readError}</p>}
      {commandError && <p role="alert">{commandError}</p>}
      {(readError || needsReadback) && (
        <button
          type="button"
          className="rounded border border-slate-600 px-3 py-2 focus-visible:outline-2 focus-visible:outline-sky-300"
          onClick={() => {
            setReport(null);
            setReadError(null);
            setReadAttempt((value) => value + 1);
          }}
        >
          Gespeicherten Prüfstand erneut lesen
        </button>
      )}
      {report && (
        <>
          <dl className="grid gap-3 sm:grid-cols-3">
            <div>
              <dt className="text-slate-400">Prüfstand</dt>
              <dd>
                {report.currentness === 'NO_ASSESSMENT'
                  ? 'Noch keine gespeicherte Prüfung'
                  : report.currentness === 'CHANGED_INPUTS'
                    ? 'Eingaben seit der Prüfung geändert'
                    : 'Prüfung bezieht sich auf die gespeicherten Eingaben'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-400">Regelfunktion</dt>
              <dd>F207-2: Zielhistorie, Z1-Orientierung und Einstandsschutz-Prüfgrundlage.</dd>
            </div>
            <div>
              <dt className="text-slate-400">Betriebszustand</dt>
              <dd>Dieser Hebeltrader-Teilschnitt ist nicht als laufende Überwachung aktiviert.</dd>
            </div>
          </dl>
          {report.currentness === 'CHANGED_INPUTS' && (
            <p className="text-amber-200">
              Die angezeigte Prüfung ist historisch. Die geänderten Eingaben müssen erneut geprüft
              werden; bisherige Belege bleiben erhalten.
            </p>
          )}
          {needsReadback && (
            <p className="text-amber-200">
              Der angezeigte Stand ist nach dem Schreibversuch noch nicht bestätigt.
            </p>
          )}
          {report.position_state !== 'OPEN' && (
            <p>
              Position {report.position_state === 'CLOSED' ? 'geschlossen' : 'storniert'}:
              gespeicherte Historie bleibt lesbar; keine neue Prüfung.
            </p>
          )}
          {!report.inputs.qualification_reusable && (
            <p className="text-amber-200">
              Die Vergleichsqualifikation für Preisbelege, Listing und Maßstab fehlt oder passt
              nicht zum aktuellen Stand. Daraus folgt keine Freigabe eines Kursvergleichs.
            </p>
          )}
          {report.inputs.issues.length > 0 && (
            <details className="text-xs text-slate-300">
              <summary className="cursor-pointer">Offene Voraussetzungen der Eingaben</summary>
              <ul>
                {report.inputs.issues.map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            </details>
          )}
          {assessment && (
            <>
              <ul aria-label="Gespeicherte Zielbefunde" className="space-y-3">
                {assessment.targets.map((value) => (
                  <Target key={value.target} value={value} />
                ))}
              </ul>
              <section aria-label="Einmalige Z1-Orientierung" className="space-y-1">
                <h4 className="font-semibold">
                  Einmalige Z1-Orientierung · {basisLabels[assessment.orientation.status]}
                </h4>
                <p>{assessment.orientation.detail}</p>
                <p>
                  50 % der ursprünglichen Einstiegsmenge sind eine Orientierung. Konkrete
                  Verkaufsmengen bleiben ausdrückliche eigene Eingaben.
                </p>
                <p>
                  Ursprüngliche Bezugsmenge:{' '}
                  {assessment.orientation.original_quantity ?? 'Nicht belegt'} · Ausdrücklich
                  zugeordnete Z1-Verkäufe:{' '}
                  {assessment.orientation.assigned_sold_quantity ?? 'Nicht belegt'}.
                </p>
              </section>
              <section aria-label="Einstandsschutz-Prüfgrundlage" className="space-y-1">
                <h4 className="font-semibold">
                  Einstandsschutz-Prüfgrundlage · {basisLabels[assessment.protection_basis.status]}
                </h4>
                <p>{assessment.protection_basis.detail}</p>
                {assessment.protection_basis.personal_underlying_entry !== null && (
                  <p>
                    Persönlicher Basiswert-Einstieg:{' '}
                    {assessment.protection_basis.personal_underlying_entry}{' '}
                    {assessment.protection_basis.currency ?? 'Währung unbekannt'}.
                  </p>
                )}
                <p>
                  Dies ist kein bekanntgegebener oder überwachter Schutzvorschlag und kein
                  dokumentierter Brokerstop.
                </p>
              </section>
            </>
          )}
          <details className="space-y-2 rounded border border-slate-700 p-3 text-xs text-slate-300">
            <summary className="cursor-pointer font-semibold">Prüfquelle und Zeitstände</summary>
            <p>
              Gespeicherte Prüfungen: {report.assessment_count} · Position: {report.position_id}
            </p>
            <p>
              Aktuelle Belegbasis: {report.current_basis_id} · Quellenversion der Eingaben:{' '}
              {report.inputs.source_version_id ?? 'Nicht gebunden'}
            </p>
            <p>
              Lesebeginn: {time(report.read_started_at)} · Leseabschluss:{' '}
              {time(report.read_completed_at)}
            </p>
            <p>
              Verfügbare Kursbelege: {report.inputs.available_price_rows} · Kursbestand:{' '}
              {report.inputs.price_history_fingerprint}
            </p>
            <p>
              Listingbindung: {report.inputs.listing_binding_fingerprint ?? 'Nicht belegt'} ·
              Maßstabsreferenz: {report.inputs.source_scale_reference ?? 'Nicht belegt'}
            </p>
            {assessment && (
              <>
                <p>
                  Prüfung {assessment.id} · Gespeichert: {time(assessment.recorded_at)}
                </p>
                <p>
                  Prüfbasis: {assessment.basis_id} · Quellenbasis dieses Prüflaufs:{' '}
                  {assessment.source_version_id ?? 'Nicht gebunden'}
                </p>
                <p>Vorherige Prüfung: {assessment.previous_assessment_id ?? 'Keine'}</p>
              </>
            )}
          </details>
        </>
      )}
      <p className="text-sm text-slate-300">
        Die bewusste Prüfung verwendet bereits gespeicherte Belege. Sie bucht keine Ausführung,
        ändert keinen Stop, aktiviert keine Regelversion und versendet keine Nachricht.
      </p>
      <button
        type="button"
        className="rounded border border-slate-600 px-3 py-2 focus-visible:outline-2 focus-visible:outline-sky-300 disabled:opacity-40"
        disabled={!report || report.position_state !== 'OPEN' || busy || needsReadback}
        onClick={() => void assess()}
      >
        Gespeicherte Belege prüfen
      </button>
      {busy && <p role="status">Gespeicherte Belege werden geprüft …</p>}
    </section>
  );
}
