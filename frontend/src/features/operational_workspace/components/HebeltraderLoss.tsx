import { useEffect, useRef, useState } from 'react';
import type { HebeltraderLossReport, LossOutcome } from '../hebeltraderLoss';
import { readHebeltraderLoss } from '../services/hebeltraderLoss';

interface Props {
  tradeId: string;
  positionId: string;
  reloadToken?: string | number;
}

const outcomeLabels: Record<LossOutcome, string> = {
  LOSS: 'Qualifizierter Verlust festgestellt',
  RECOVERED: 'Qualifizierter Geldkurs mindestens auf Einstand',
  NOT_ASSESSABLE: 'Eingangsdaten nicht ausreichend qualifiziert',
  NOT_REACHED: '20 Sitzungen zur Original-Geldkurszeit noch nicht abgeschlossen',
  CLOSED: 'Position geschlossen oder storniert',
};
const reasonLabels: Record<string, string> = {
  B04_BID_BELOW_GROSS_ENTRY:
    'Der qualifizierte Original-Geldkurs liegt unter dem persönlichen Bruttoeinstand.',
  B57_QUALIFIED_BID_AT_OR_ABOVE_ENTRY:
    'Ein geeigneter Original-Geldkurs erreicht oder überschreitet den persönlichen Bruttoeinstand.',
  TWENTIETH_SESSION_NOT_COMPLETED_AT_BID:
    'Die 20. Basiswertsitzung war zur Original-Geldkurszeit noch nicht abgeschlossen.',
  POSITION_CLOSED_OR_CANCELLED: 'Die Position ist geschlossen oder storniert.',
  B58_REAL_SOURCE_PATH_NOT_QUALIFIED:
    'Der tatsächliche Anbieter-/Instrument-/Handelsplatzpfad ist für B58 noch nicht qualifiziert.',
  B58_ORIGINAL_SUPPLY_MISSING: 'Originaldaten zur passenden Kurs- und Statusquelle fehlen.',
  B58_OPEN_AT_EVALUATION_NOT_PROVEN:
    'Ein offener Instrumentmarkt ist zum Auswertungszeitpunkt nicht belegt.',
  B58_STATUS_SOURCE_MISMATCH: 'Statusquelle und Kursquelle passen nicht zusammen.',
  B58_SUPPLY_GAP_AT_EVALUATION:
    'Die Datenversorgung weist zum Auswertungszeitpunkt eine Lücke auf.',
  ORIGINAL_BID_TOO_OLD: 'Der Original-Geldkurs ist älter als 900 Sekunden.',
  ORIGINAL_BID_SIDE_TIME_MISSING: 'Eine eigene Originalzeit für die Geldkursseite fehlt.',
  EXECUTION_CURRENCY_UNQUALIFIED: 'Die historische Ausführungswährung ist nicht geeignet belegt.',
  EXECUTION_BID_CURRENCY_MISMATCH: 'Ausführungswährung und Geldkurswährung widersprechen sich.',
  PRODUCT_PRICE_SCALE_UNQUALIFIED:
    'Der Produktmaßstab ist für Kaufbasis und Original-Geldkurs nicht ausreichend belegt.',
};
const remainingLabels: Record<string, string> = {
  B05: 'B05 · Produktfristen',
  B06: 'B06 · Schutzüberwachung',
  F207_2_PROTECTION: 'F207-2 · übrige Schutz- und Korrekturregeln',
  F207_5_LIFECYCLE_ACCEPTANCE: 'F207-5 · Meldungslebenszyklus und Betriebsabnahme',
};

function LossStatus({ tradeId, positionId }: Props) {
  const [report, setReport] = useState<HebeltraderLossReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const generation = useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    const currentGeneration = ++generation.current;
    const current = () => !controller.signal.aborted && currentGeneration === generation.current;
    readHebeltraderLoss(tradeId, positionId, controller.signal)
      .then((value) => {
        if (current()) setReport(value);
      })
      .catch((reason: unknown) => {
        if (current())
          setError(
            reason instanceof Error ? reason.message : 'B04/B57-Regelstand nicht verfügbar.',
          );
      });
    return () => {
      generation.current += 1;
      controller.abort();
    };
  }, [tradeId, positionId]);
  const latest = report?.latest_assessment;
  return (
    <section
      aria-label="Hebeltrader-Verlustüberwachung"
      className="min-w-0 space-y-3 rounded-xl border border-slate-700 bg-slate-950/40 p-3 sm:p-4"
    >
      <h3 className="font-semibold text-white">Hebeltrader · B04/B57-Verlustüberwachung</h3>
      <p className="text-sm text-slate-300">
        Gespeicherte Regelauswertungen und Verlustepisoden. Diese Ansicht liest ausschließlich
        vorhandene Ergebnisse.
      </p>
      {!report && !error && <p>Gespeicherter B04/B57-Regelstand wird gelesen …</p>}
      {error && <p role="alert">{error}</p>}
      {report && (
        <>
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-slate-400">Regelumfang</dt>
              <dd>B04/B57 mit B58-Eingängen · {report.definition_version}</dd>
            </div>
            <div>
              <dt className="text-slate-400">Aktivierung des Teilumfangs</dt>
              <dd>
                {report.activation_status === 'NOT_ACTIVATED'
                  ? 'Nicht aktiviert'
                  : report.activation_status === 'BLOCKED_SOURCE'
                    ? 'Durch fehlende Quellenqualifikation blockiert'
                    : 'Teilumfang zentral freigegeben'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-400">Hintergrundrunner konfiguriert</dt>
              <dd>
                {report.runner_enabled
                  ? 'Aktiviert; laufender Betrieb separat nachzuweisen'
                  : 'Deaktiviert'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-400">Gesamte bestätigte Regelbasis</dt>
              <dd>Nicht vollständig aktiviert</dd>
            </div>
          </dl>
          <p className="text-sm text-slate-300">
            Noch außerhalb dieses Teilumfangs:{' '}
            {report.remaining_scope.map((key) => remainingLabels[key] ?? key).join('; ')}.
          </p>
          <section
            aria-label="Gespeicherte Verlustepisode"
            className="rounded border border-slate-700 p-3"
          >
            <h4 className="font-semibold">Gespeicherte Verlustepisode</h4>
            {report.active_episode ? (
              <>
                <p>
                  Verlustepisode {report.active_episode.episode_number} bleibt offen · eröffnet am{' '}
                  <time dateTime={report.active_episode.opened_at}>
                    {report.active_episode.opened_at}
                  </time>
                  .
                </p>
                {latest?.outcome === 'NOT_ASSESSABLE' && (
                  <p className="text-amber-200">
                    Die Datenlücke beendet diese Verlustepisode nicht.
                  </p>
                )}
              </>
            ) : (
              <p>
                Keine offene Verlustepisode gespeichert. Das allein bestätigt keine geeignete
                aktuelle Datenversorgung.
              </p>
            )}
          </section>
          <section aria-label="Letzte gespeicherte B04-Bewertung" className="space-y-2">
            <h4 className="font-semibold">Letzte gespeicherte Bewertung</h4>
            {latest ? (
              <>
                <p>{outcomeLabels[latest.outcome]}</p>
                <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <div>
                    <dt className="text-slate-400">Bewertet am</dt>
                    <dd>
                      <time dateTime={latest.evaluated_at}>{latest.evaluated_at}</time>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Original-Geldkurszeit des Prüfstands</dt>
                    <dd>{latest.bid_at ?? 'Nicht belegt'}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Original-Geldkurs im Prüfstand</dt>
                    <dd>{latest.bid ?? 'Nicht belegt'}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Bruttoeinstand je Stück im Prüfstand</dt>
                    <dd>{latest.gross_entry}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Einstandswährung im Prüfstand</dt>
                    <dd>{latest.currency ?? 'Nicht belegt'}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Restmenge im Prüfstand</dt>
                    <dd>{latest.remaining_quantity}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Abgeschlossene Sitzungen zur BID-Zeit</dt>
                    <dd>{latest.completed_sessions_at_bid ?? 'Nicht belegt'}</dd>
                  </div>
                </dl>
                <ul aria-label="Gründe der B04-Bewertung" className="space-y-1">
                  {latest.reasons.map((reason, index) => (
                    <li key={`${reason}:${index}`}>
                      {reasonLabels[reason] ?? `Offene Voraussetzung laut Prüfstand: ${reason}`}
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p>Noch keine B04/B57-Bewertung gespeichert.</p>
            )}
          </section>
          <p className="text-xs text-slate-400">
            {report.assessment_count} Bewertungen · {report.episode_count} Verlustepisoden · gelesen
            am <time dateTime={report.read_at}>{report.read_at}</time>.
          </p>
          <p className="text-sm text-slate-300">
            Regelauslöser erzeugen ausschließlich Hinweise. Sie erzeugen keine Orders,
            Ausführungsbuchungen oder automatischen Stop- und Zieländerungen.
          </p>
        </>
      )}
    </section>
  );
}

export function HebeltraderLoss(props: Props) {
  return (
    <LossStatus key={`${props.tradeId}:${props.positionId}:${props.reloadToken ?? 0}`} {...props} />
  );
}
