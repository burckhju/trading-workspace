import { useEffect, useRef, useState } from 'react';
import type { HebeltraderCoverageItem, HebeltraderEvidenceReport } from '../hebeltraderEvidence';
import { readHebeltraderEvidence } from '../services/hebeltraderEvidence';

interface Props {
  tradeId: string;
  positionId: string;
  reloadToken?: string | number;
}

const statusLabels: Record<HebeltraderCoverageItem['status'], string> = {
  PRESENT: 'Vorhanden',
  MISSING: 'Fehlt',
  CONFLICT: 'Widersprüchlich',
  UNSUITABLE: 'Ungeeignet',
};

function time(value: string) {
  return <time dateTime={value}>{value}</time>;
}

export function HebeltraderEvidenceCoverage(props: Props) {
  return (
    <Coverage key={`${props.tradeId}:${props.positionId}:${props.reloadToken ?? 0}`} {...props} />
  );
}

function Coverage({ tradeId, positionId }: Props) {
  const [report, setReport] = useState<HebeltraderEvidenceReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const requestGeneration = useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    const generation = ++requestGeneration.current;
    const current = () => generation === requestGeneration.current && !controller.signal.aborted;
    readHebeltraderEvidence(tradeId, positionId, controller.signal)
      .then((value) => {
        if (current()) setReport(value);
      })
      .catch((reason: unknown) => {
        if (current()) {
          setError(
            reason instanceof Error
              ? reason.message
              : 'Die Belegabdeckung konnte nicht gelesen werden.',
          );
        }
      });
    return () => {
      requestGeneration.current += 1;
      controller.abort();
    };
  }, [tradeId, positionId, attempt]);

  return (
    <section
      aria-label="Hebeltrader-Belegabdeckung"
      className="min-w-0 space-y-3 break-words rounded-xl border border-slate-700 bg-slate-950/40 p-3 sm:p-4"
    >
      <h3 className="font-semibold text-white">Hebeltrader · Belegabdeckung</h3>
      <p className="text-slate-300">
        Diese Ansicht verbindet gespeicherte Ausführungen und historische Quellen. Sie prüft die
        Belege für spätere Hebeltrader-Regeln.
      </p>
      {!report && !error && <p>Belegabdeckung wird geladen …</p>}
      {error && (
        <div className="space-y-2">
          <p role="alert">{error}</p>
          <button
            type="button"
            className="rounded border border-slate-600 px-3 py-2 focus-visible:outline-2 focus-visible:outline-sky-300"
            onClick={() => {
              setReport(null);
              setError(null);
              setAttempt((value) => value + 1);
            }}
          >
            Belegabdeckung erneut lesen
          </button>
        </div>
      )}
      {report && (
        <>
          <dl className="grid gap-3 sm:grid-cols-3">
            <div>
              <dt className="text-slate-400">Belegabdeckung</dt>
              <dd>
                {report.coverage_status === 'COMPLETE'
                  ? 'Belege dieses Schnitts vollständig'
                  : report.coverage_status === 'CONFLICTED'
                    ? 'Widersprüche in den Belegen'
                    : 'Belege noch unvollständig'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-400">Regelfunktion</dt>
              <dd>F207-4: Evidenzverknüpfung. Keine Baseline-Regelauswertung.</dd>
            </div>
            <div>
              <dt className="text-slate-400">Betriebszustand</dt>
              <dd>Durch diesen Read nicht geprüft.</dd>
            </div>
          </dl>
          <p className="text-sm text-slate-300">
            Vollständige Belege bedeuten keine aktive Hebeltrader-Überwachung. Es werden keine
            Ausführungen gebucht, Regelversionen aktiviert oder Benachrichtigungen ausgelöst.
          </p>
          <dl className="grid gap-3 sm:grid-cols-3">
            <div>
              <dt className="text-slate-400">Ursprüngliche Z1-Bezugsmenge</dt>
              <dd>{report.original_z1_quantity ?? 'Nicht belegt'}</dd>
            </div>
            <div>
              <dt className="text-slate-400">Ausdrücklich zugeordnete Z1-Verkäufe</dt>
              <dd>{report.assigned_z1_sold_quantity ?? 'Nicht belegt'}</dd>
            </div>
            <div>
              <dt className="text-slate-400">Persönlicher Basiswert-Einstieg</dt>
              <dd>
                {report.personal_underlying_entry === null
                  ? 'Nicht vollständig belegt'
                  : `${report.personal_underlying_entry} ${report.underlying_currency ?? 'Währung unbekannt'}`}
              </dd>
            </div>
          </dl>
          <ul aria-label="Benötigte Belege" className="space-y-3">
            {report.items.map((item) => (
              <li key={item.key} className="rounded border border-slate-700 p-3">
                <p className="font-medium">
                  {item.label}: {statusLabels[item.status]}
                </p>
                <p>{item.detail}</p>
                {item.affected_rules.length > 0 && (
                  <p className="text-xs text-slate-300">
                    Benötigt für: {item.affected_rules.join(', ')}. Diese Regeln werden hier nicht
                    ausgewertet.
                  </p>
                )}
                {item.clarification && (
                  <p className="text-amber-200">Klärung: {item.clarification}</p>
                )}
                {item.references.length > 0 && (
                  <details className="text-xs text-slate-400">
                    <summary className="cursor-pointer">Belegreferenzen</summary>
                    <ul>
                      {item.references.map((reference) => (
                        <li key={reference}>{reference}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </li>
            ))}
          </ul>
          <details className="space-y-2 rounded border border-slate-700 p-3 text-xs text-slate-300">
            <summary className="cursor-pointer font-semibold">
              Quellenversion und Zeitstände
            </summary>
            <p>
              Regelbezug: {report.baseline_id} · Version {report.baseline_version}.
            </p>
            <p>
              Lesebeginn: {time(report.read_started_at)} · Leseabschluss:{' '}
              {time(report.read_completed_at)}
            </p>
            <p>Belegbasis: {report.basis_id}</p>
            <p>
              Evidenzrevision: {report.evidence_revision_id ?? 'Noch keine Ergänzung erfasst'}
              {report.evidence_recorded_at && <> · Erfasst: {time(report.evidence_recorded_at)}</>}
            </p>
            {report.source ? (
              <>
                <p>
                  {report.source.source_name} ·{' '}
                  {report.source.external_reference ?? 'Ohne Ausgabenreferenz'} · Quellenversion{' '}
                  {report.source.version} ({report.source.source_version_id})
                </p>
                <p>
                  Ausgabe: {time(report.source.issue_date)} · Nur Datum belegt; keine bekannte
                  Veröffentlichungsuhrzeit.
                </p>
                <p>
                  Erfasst: {time(report.source.recorded_at)} · Importiert:{' '}
                  {time(report.source.imported_at)} · Bestätigt: {time(report.source.accepted_at)}
                </p>
                <p>
                  {report.source.currentness === 'SOURCE_SUPERSEDED'
                    ? 'Historisch gebundene Version; eine neuere Quellenversion ersetzt sie nicht.'
                    : 'Die gebundene Version ist aktuell in ihrer Quelle.'}
                </p>
                {report.source.supersedes_version_id && (
                  <p>Vorgängerversion: {report.source.supersedes_version_id}</p>
                )}
                <p>
                  Datei: {report.source.filename} · SHA-256: {report.source.content_hash}
                </p>
                <p>
                  Importzeile: {report.source.import_row_id} · Importbatch: {report.source.batch_id}
                </p>
              </>
            ) : (
              <p>Keine geeignete historische Hebeltrader-Quellenversion gebunden.</p>
            )}
          </details>
        </>
      )}
    </section>
  );
}
