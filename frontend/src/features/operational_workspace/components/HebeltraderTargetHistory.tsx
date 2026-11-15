import { useCallback, useEffect, useRef, useState } from 'react';
import type { HebeltraderTarget, HebeltraderTargetsReport } from '../hebeltraderTargets';
import { readHebeltraderTargets } from '../services/hebeltraderTargets';
import {
  emptyQualificationSession,
  qualificationSessionKey,
  useHebeltraderQualificationSessions,
  type QualificationSession,
  type QualificationSessions,
} from '../hooks/useHebeltraderQualificationSessions';
import { useHebeltraderTargetCommand } from '../hooks/useHebeltraderTargetCommand';
import { HebeltraderQualification } from './HebeltraderQualification';

interface Props {
  tradeId: string;
  positionId: string;
  reloadToken?: string | number;
  qualificationSessions?: QualificationSessions;
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
  const localSessions = useHebeltraderQualificationSessions();
  const sessions = props.qualificationSessions ?? localSessions;
  const sessionKey = qualificationSessionKey(props.tradeId, props.positionId);
  return (
    <History
      key={`${props.tradeId}:${props.positionId}:${props.reloadToken ?? 0}`}
      tradeId={props.tradeId}
      positionId={props.positionId}
      sessionKey={sessionKey}
      session={sessions.values[sessionKey] ?? emptyQualificationSession}
      update={sessions.update}
    />
  );
}

function History({
  tradeId,
  positionId,
  sessionKey,
  session,
  update,
}: {
  tradeId: string;
  positionId: string;
  sessionKey: string;
  session: QualificationSession;
  update: QualificationSessions['update'];
}) {
  const [report, setReport] = useState<HebeltraderTargetsReport | null>(null);
  const [readError, setReadError] = useState<string | null>(null);
  const [readAttempt, setReadAttempt] = useState(0);
  const generation = useRef(0);
  const acceptReport = useCallback(
    (value: HebeltraderTargetsReport) => {
      generation.current += 1;
      setReport(value);
      setReadError(null);
      // A fresh read may resolve a concrete rejection; it never resolves an unknown write.
      update(sessionKey, (previous) =>
        previous.command?.phase === 'REJECTED' ? { ...previous, command: null } : previous,
      );
    },
    [sessionKey, update],
  );
  const command = useHebeltraderTargetCommand({
    tradeId,
    positionId,
    sessionKey,
    session,
    update,
    onReport: acceptReport,
  });

  useEffect(() => {
    const controller = new AbortController();
    const currentGeneration = ++generation.current;
    const current = () => generation.current === currentGeneration && !controller.signal.aborted;
    readHebeltraderTargets(tradeId, positionId, controller.signal)
      .then((value) => {
        if (!current()) return;
        acceptReport(value);
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
    };
  }, [tradeId, positionId, readAttempt, acceptReport]);

  async function assess() {
    if (
      !report ||
      command.blocked ||
      session.command?.phase === 'REJECTED' ||
      report.position_state !== 'OPEN'
    )
      return;
    await command.execute({
      position_id: positionId,
      request_id: crypto.randomUUID(),
      expected_basis_id: report.current_basis_id,
      expected_assessment_id: report.latest_assessment?.id ?? null,
      confirmation: 'ASSESS_SAVED_HEBELTRADER_EVIDENCE',
    });
  }

  const assessment = report?.latest_assessment;
  return (
    <section
      aria-label="Hebeltrader-Zielhistorie"
      aria-busy={command.busy}
      className="min-w-0 space-y-3 break-words rounded-xl border border-slate-700 bg-slate-950/40 p-3 sm:p-4"
    >
      <h3 className="font-semibold text-white">Hebeltrader · Dauerhafte Zielbelege</h3>
      <p>
        Gespeicherte Z1-/Z2-Belege auf der Basiswertachse bleiben auch bei späteren Kursrückgängen
        nachvollziehbar. Ein Zieltreffer ist keine Verkaufsausführung.
      </p>
      {!report && !readError && <p>Zielhistorie wird geladen …</p>}
      {readError && <p role="alert">{readError}</p>}
      {session.command?.message && (
        <p role={session.command.phase === 'CONFIRMED' ? 'status' : 'alert'}>
          {session.command.message}
        </p>
      )}
      {session.command?.phase === 'REJECTED' && (
        <p>
          Die Anfrage wurde konkret abgelehnt. Vor einer neuen Prüfung den aktuellen Belegstand
          lesen; der Referenzentwurf bleibt erhalten.
        </p>
      )}
      {session.command?.phase === 'UNKNOWN' && (
        <section
          aria-label="Unbestätigter Prüfauftrag"
          className="space-y-2 rounded border border-amber-500 p-3"
        >
          <p>
            Der angezeigte Stand ist nach dem Schreibversuch noch nicht bestätigt. Ein allgemeiner
            Leseabruf klärt den Ausgang dieser Anfrage nicht.
          </p>
          <p>
            Anfrage: {session.command.payload.request_id} · Eingefrorene Belegbasis:{' '}
            {session.command.payload.expected_basis_id}
          </p>
          {session.command.payload.qualification && (
            <p>
              Eingefrorene Belegreferenz: {session.command.payload.qualification.evidence_reference}
            </p>
          )}
          <p>
            Der vollständige Prüfauftrag und der Entwurf bleiben beim Schließen der Details, bei
            Filter- und Seitenwechseln sowie bei „Aktualisieren“ erhalten. Vor dem Verlassen der
            Workspace-Seite oder Neuladen im Browser den Vorgangsbeleg klären; dort endet dieser
            lokale Speicher. Es wird keine neue Anfragekennung erzeugt und nichts automatisch
            wiederholt.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded border border-slate-600 px-3 py-2 disabled:opacity-40"
              disabled={command.busy}
              onClick={() => void command.readReceipt()}
            >
              Beleg genau dieser Anfrage lesen
            </button>
            <button
              type="button"
              className="rounded border border-slate-600 px-3 py-2 disabled:opacity-40"
              disabled={command.busy || !report || report.position_state !== 'OPEN'}
              onClick={() => void command.retry()}
            >
              Denselben eingefrorenen Prüfauftrag erneut senden
            </button>
          </div>
          <p className="text-xs text-slate-300">
            Eine bewusste Wiederholung sendet denselben Inhalt mit derselben Anfragekennung; der
            Server behandelt sie idempotent.
          </p>
          {command.readingReceipt && <p role="status">Vorgangsbeleg wird gelesen …</p>}
          {command.receiptError && <p role="alert">{command.receiptError}</p>}
        </section>
      )}
      {session.command?.receipt?.status === 'RECORDED' && (
        <details className="space-y-2 rounded border border-slate-700 p-3">
          <summary className="cursor-pointer">Gespeicherter Beleg dieser Anfrage</summary>
          <p>
            Anfrage {session.command.receipt.request_id} · Vorgang gespeichert:{' '}
            {session.command.receipt.recorded_at}
          </p>
          <p>
            Damals enthaltener Prüfstand: {session.command.receipt.assessment?.id} · Belegbasis:{' '}
            {session.command.receipt.assessment?.basis_id} · Prüfstand gespeichert:{' '}
            {session.command.receipt.assessment?.recorded_at}
          </p>
          {session.command.receipt.qualification && (
            <p>
              Damals enthaltene Nutzererklärung:{' '}
              {session.command.receipt.qualification.evidence_reference}
            </p>
          )}
          <p>
            Dieser Beleg bestätigt die konkrete Anfrage. Er ersetzt nicht den aktuellen Prüfstand;
            für spätere Änderungen den Prüfstand erneut lesen.
          </p>
          <ul aria-label="Zielbefunde des Vorgangsbelegs" className="space-y-2">
            {session.command.receipt.assessment?.targets.map((target) => (
              <Target key={target.target} value={target} />
            ))}
          </ul>
        </details>
      )}
      {(readError || session.command) && (
        <button
          type="button"
          className="rounded border border-slate-600 px-3 py-2 focus-visible:outline-2 focus-visible:outline-sky-300"
          disabled={command.busy}
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
          <HebeltraderQualification
            tradeId={tradeId}
            positionId={positionId}
            report={report}
            sessionKey={sessionKey}
            session={session}
            update={update}
            blocked={command.blocked}
            onReport={acceptReport}
            onSubmit={command.execute}
          />
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
        disabled={
          !report ||
          report.position_state !== 'OPEN' ||
          command.blocked ||
          session.command?.phase === 'REJECTED'
        }
        onClick={() => void assess()}
      >
        Gespeicherte Belege prüfen
      </button>
      {session.command?.phase === 'PENDING' && (
        <p role="status">Gespeicherte Belege werden geprüft …</p>
      )}
    </section>
  );
}
