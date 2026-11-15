import { useEffect, useRef, useState, type ReactNode } from 'react';
import type { HebeltraderSessionsReport, SessionPeriodView } from '../hebeltraderSessions';
import { readHebeltraderSessions } from '../services/hebeltraderSessions';

interface Props {
  tradeId: string;
  positionId: string;
  reloadToken?: string | number;
}

const buttonClass =
  'rounded border border-slate-600 px-3 py-2 text-sm disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300';
const periodLabels: Record<SessionPeriodView['status'], string> = {
  COMPLETE: 'Tagesbelege im gelesenen Zeitraum vollständig',
  INCOMPLETE: 'Tagesbelege unvollständig',
  MISSING: 'Kalenderbelege fehlen',
  UNSUITABLE: 'Kalenderbelege für diesen Zeitraum ungeeignet',
  LIMIT_EXCEEDED: 'Zeitraum überschreitet die Lesegrenze',
  NOT_REQUESTED: 'Keine Tagesbelege angefordert',
};
const dayLabels = {
  SESSION: 'Dokumentierte Sitzung',
  CLOSED: 'Dokumentiert geschlossen',
  UNKNOWN: 'Unbekannt',
};

function Time({ value }: { value: string | null }) {
  return value === null ? <>Nicht belegt</> : <time dateTime={value}>{value}</time>;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-slate-400">{label}</dt>
      <dd className="[overflow-wrap:anywhere]">{children}</dd>
    </div>
  );
}

function Pages({
  page,
  total,
  label,
  onPage,
}: {
  page: number;
  total: number;
  label: string;
  onPage: (page: number) => void;
}) {
  if (total <= 25) return null;
  const pages = Math.ceil(total / 25);
  return (
    <nav aria-label={label} className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        className={buttonClass}
        disabled={page === 0}
        onClick={() => onPage(page - 1)}
      >
        Vorherige Seite
      </button>
      <span>
        Seite {page + 1} von {pages} · {total} Einträge insgesamt
      </span>
      <button
        type="button"
        className={buttonClass}
        disabled={page + 1 >= pages}
        onClick={() => onPage(page + 1)}
      >
        Nächste Seite
      </button>
    </nav>
  );
}

function CalendarDays({ report }: { report: HebeltraderSessionsReport }) {
  const [page, setPage] = useState(0);
  const [missingPage, setMissingPage] = useState(0);
  const { period, count } = report;
  return (
    <section aria-label="Gelesene Kalendertage" className="min-w-0 space-y-3">
      <h4 className="font-semibold">Gelesene Kalendertage · {periodLabels[period.status]}</h4>
      <p>
        Zeitraum: <Time value={period.start_date} /> bis <Time value={period.end_date} />.
      </p>
      <p className="text-sm text-slate-300">
        Fehlende oder unbekannte Tage sind keine belegten Feiertage. Die Zählung und die als
        abgeschlossen gekennzeichneten Tage stammen vom Server.
      </p>
      {period.days.length === 0 ? (
        <p>Keine Tageszeilen in dieser Antwort.</p>
      ) : (
        <>
          <div
            className="max-w-full overflow-x-auto rounded border border-slate-700"
            tabIndex={0}
            role="region"
            aria-label="Tagesbelege, horizontal scrollbar"
          >
            <table
              className="w-full text-left text-sm"
              aria-label="Dokumentierte Basiswert-Kalendertage"
            >
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="p-2" scope="col">
                    Sitzungsdatum
                  </th>
                  <th className="p-2" scope="col">
                    Beleg und Zählung
                  </th>
                  <th className="p-2" scope="col">
                    Dokumentierte Intervalle
                  </th>
                  <th className="p-2" scope="col">
                    Belegreferenz
                  </th>
                </tr>
              </thead>
              <tbody>
                {period.days.slice(page * 25, (page + 1) * 25).map((day) => (
                  <tr key={day.session_date} className="border-b border-slate-800 align-top">
                    <th scope="row" className="p-2 font-normal">
                      <Time value={day.session_date} />
                    </th>
                    <td className="p-2">
                      {dayLabels[day.status]}
                      {count.completed_session_dates.includes(day.session_date) && (
                        <p>Als abgeschlossen gezählt</p>
                      )}
                    </td>
                    <td className="p-2">
                      {day.intervals.length === 0 ? (
                        'Keine Handelsintervalle belegt'
                      ) : (
                        <ul className="space-y-1">
                          {day.intervals.map((interval) => (
                            <li key={`${interval.opens_at}:${interval.closes_at}`}>
                              <Time value={interval.opens_at} /> bis{' '}
                              <Time value={interval.closes_at} />
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                    <td className="max-w-72 p-2 [overflow-wrap:anywhere]">
                      {day.source_reference}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pages
            page={page}
            total={period.days.length}
            label="Seiten der Tagesbelege"
            onPage={setPage}
          />
        </>
      )}
      {period.missing_dates.length > 0 && (
        <section aria-label="Fehlende Kalendertage" className="space-y-2">
          <h5 className="font-semibold">Fehlende Kalendertage · {period.missing_dates.length}</h5>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {period.missing_dates.slice(missingPage * 25, (missingPage + 1) * 25).map((day) => (
              <li key={day}>
                <Time value={day} />
              </li>
            ))}
          </ul>
          <Pages
            page={missingPage}
            total={period.missing_dates.length}
            label="Seiten der fehlenden Kalendertage"
            onPage={setMissingPage}
          />
        </section>
      )}
    </section>
  );
}

function Evidence({ report }: { report: HebeltraderSessionsReport }) {
  const { calendar, entry, count } = report;
  const binding = calendar.binding;
  const source = calendar.source;
  return (
    <details className="min-w-0 space-y-3 rounded border border-slate-700 p-3 text-sm">
      <summary className="cursor-pointer font-semibold">
        Kalenderbindung, Quelle und Zeitstände
      </summary>
      <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
        <Field label="Positionsbeginn / Ausführungsbeleg">
          {entry ? (
            <>
              {entry.execution_id} ·{' '}
              {entry.time_precision === 'DATE_ONLY'
                ? 'Nur Datum belegt'
                : 'Genauer Ausführungszeitpunkt'}{' '}
              ·{' '}
              <Time
                value={entry.time_precision === 'DATE_ONLY' ? entry.executed_on : entry.executed_at}
              />{' '}
              · Ausführungszeitzone: {entry.execution_timezone ?? 'Nicht belegt'}
            </>
          ) : (
            'Kein effektiver Kaufbeleg vorhanden'
          )}
        </Field>
        <Field label="Tag 0 in der Kalenderzeitzone">
          <Time value={count.anchor_date} />
        </Field>
        <Field label="Explizit zugeordneter Kalender">
          {calendar.calendar_id ?? 'Nicht belegt'} · Version{' '}
          {calendar.calendar_version ?? 'Nicht belegt'}
        </Field>
        <Field label="Kalenderbeleg">
          {calendar.status === 'AVAILABLE'
            ? 'Vorhanden'
            : calendar.status === 'MISSING'
              ? 'Fehlt'
              : 'Ungeeignet'}{' '}
          · Revision {calendar.revision_number ?? 'Nicht belegt'} ·{' '}
          {calendar.revision_id ?? 'Keine Revision'}
        </Field>
        <Field label="Ersetzte Revision">{calendar.supersedes_revision_id ?? 'Keine'}</Field>
        <Field label="Status des importierten Belegs">
          {calendar.evidence_status === 'ACTIVE'
            ? 'Als aktiver Beleg geführt (keine Regelaktivierung)'
            : calendar.evidence_status === 'WITHDRAWN'
              ? 'Zurückgezogen'
              : 'Kein Beleg'}
        </Field>
        <Field label="Deklarierte Abdeckung">
          <Time value={calendar.coverage_start} /> bis <Time value={calendar.coverage_end} />
        </Field>
        <Field label="Basiswert / Listing">
          {report.underlying_id} · {binding?.listing_id ?? 'Nicht gebunden'}
        </Field>
        <Field label="Handelsplatz / Segment">
          {binding
            ? `${binding.venue_mic} · ${binding.trading_venue_id} · ${binding.market_segment}`
            : 'Nicht gebunden'}
        </Field>
        <Field label="Kalenderzeitzone">{binding?.timezone ?? 'Nicht belegt'}</Field>
        <Field label="Gültigkeit der expliziten Bindung">
          <Time value={binding?.valid_from ?? null} /> bis{' '}
          <Time value={binding?.valid_through ?? null} />
        </Field>
        <Field label="Aufgezeichnet am">
          <Time value={calendar.recorded_at} />
        </Field>
      </dl>
      {source && (
        <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
          <Field label="Herausgeber">{source.publisher}</Field>
          <Field label="Quellenreferenz">{source.reference}</Field>
          <Field label="Originaldokument">
            {source.document_filename} · {source.document_media_type}
          </Field>
          <Field label="Veröffentlicht">
            {source.published_at ? (
              <Time value={source.published_at} />
            ) : source.published_on ? (
              <>
                <Time value={source.published_on} /> · Nur Datum belegt
              </>
            ) : (
              'Nicht belegt'
            )}
          </Field>
          <Field label="Quelle abgerufen am">
            <Time value={source.retrieved_at} />
          </Field>
          <Field label="Dokumentprüfung">
            <Time value={source.reviewed_at} /> · {source.review_reference}
          </Field>
          <Field label="Erfasst durch">{source.recorded_by}</Field>
          <Field label="SHA-256 des Originaldokuments">{source.document_sha256}</Field>
          <Field label="SHA-256 des Importmanifests">{source.manifest_sha256}</Field>
        </dl>
      )}
      <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
        <Field label="Quellenstand bekannt bis">
          <Time value={calendar.known_at} />
        </Field>
        <Field label="Kalender gelesen am">
          <Time value={calendar.read_at} />
        </Field>
        <Field label="Bericht gelesen">
          <Time value={report.read_started_at} /> bis <Time value={report.read_completed_at} />
        </Field>
        <Field label="Position / Trade">
          {report.position_id} · {report.trade_id}
        </Field>
        <Field label="Workspace / Produkt">
          {calendar.workspace_id} · {report.product_id}
        </Field>
        <Field label="Basis dieses Sitzungsberichts">{report.basis_id}</Field>
        <Field label="Fingerabdruck des gelesenen Zeitraums">
          {report.period.fingerprint ?? 'Kein Zeitraum gelesen'}
        </Field>
        <Field label="Regelbasis und Definition">
          {report.baseline_id} · {report.baseline_version} · {report.definition_version}
        </Field>
      </dl>
      {(calendar.reasons.length > 0 || count.reasons.length > 0) && (
        <p className="[overflow-wrap:anywhere]">
          Owner-Codes: {[...new Set([...calendar.reasons, ...count.reasons])].join(', ')}
        </p>
      )}
    </details>
  );
}

function Sessions({ tradeId, positionId }: Props) {
  const [report, setReport] = useState<HebeltraderSessionsReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const generation = useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    const currentGeneration = ++generation.current;
    const current = () => currentGeneration === generation.current && !controller.signal.aborted;
    readHebeltraderSessions(tradeId, positionId, controller.signal)
      .then((value) => {
        if (current()) setReport(value);
      })
      .catch((reason: unknown) => {
        if (current())
          setError(
            reason instanceof Error
              ? reason.message
              : 'Die Basiswertsitzungen konnten nicht gelesen werden.',
          );
      });
    return () => {
      generation.current += 1;
      controller.abort();
    };
  }, [tradeId, positionId, attempt]);
  return (
    <section
      aria-label="Hebeltrader-Basiswertsitzungen"
      className="min-w-0 space-y-4 break-words rounded-xl border border-slate-700 bg-slate-950/40 p-3 sm:p-4"
    >
      <h3 className="font-semibold text-white">Hebeltrader · Basiswertsitzungen</h3>
      <p className="text-slate-300">
        Dokumentierte Basiswertsitzungen seit dem ursprünglichen Kauf, gezählt bis zum
        serverseitigen Lesezeitpunkt. Der Kauftag zählt als Tag 0.
      </p>
      {!report && !error && <p>Basiswertsitzungen werden gelesen …</p>}
      {error && (
        <div className="space-y-2">
          <p role="alert">{error}</p>
          <button
            type="button"
            className={buttonClass}
            onClick={() => {
              setReport(null);
              setError(null);
              setAttempt((value) => value + 1);
            }}
          >
            Basiswertsitzungen erneut lesen
          </button>
        </div>
      )}
      {report && (
        <>
          <dl className="grid gap-3 sm:grid-cols-3">
            <Field label="Sitzungszählung">
              {report.count.status === 'AVAILABLE'
                ? `${report.count.completed_sessions} abgeschlossene Basiswertsitzungen`
                : report.count.status === 'NOT_APPLICABLE'
                  ? 'Für diese Position nicht anwendbar'
                  : 'Nicht beurteilbar'}
            </Field>
            <Field label="Regelfunktion">
              Kalenderbelege und Sitzungszählung. B04, B05, B06 und B58 sind nicht ausgewertet.
            </Field>
            <Field label="Betriebszustand">
              Dieser Teilschnitt ist nicht als laufende Überwachung aktiviert.
            </Field>
          </dl>
          <p>
            Stand der Zählung: <Time value={report.evaluated_at} /> · serverseitiger Lesezeitpunkt,
            keine Original-BID-Zeit.
          </p>
          {report.count.status === 'AVAILABLE' && (
            <p>
              {report.count.threshold_reached ? (
                <>
                  20. abgeschlossene Sitzung: <Time value={report.count.twentieth_session_date} /> ·
                  belegter Schluss: <Time value={report.count.twentieth_closes_at} />.
                </>
              ) : (
                '20 abgeschlossene Sitzungen sind zu diesem Lesezeitpunkt noch nicht erreicht.'
              )}
            </p>
          )}
          {report.count.status === 'AVAILABLE' && report.period.status === 'NOT_REQUESTED' && (
            <p>Seit Tag 0 existieren noch keine späteren Kalendertage für diese Zählung.</p>
          )}
          {report.position_state !== 'OPEN' && (
            <p>
              Position {report.position_state === 'CLOSED' ? 'geschlossen' : 'storniert'}. Die
              vorhandenen Belege bleiben lesbar.
            </p>
          )}
          <p className="text-sm text-slate-300">
            Die Prüfung zur Originalzeit eines Geldkurses, Produktfristen und die Zählung seit Z1
            sind hier nicht enthalten. Eine erreichte Sitzungszahl ist kein Verlust-, Verkaufs- oder
            Überwachungsbefund.
          </p>
          <p className="text-sm text-slate-300">
            Ein geprüfter Dokumentimport ist keine unabhängige Verifikation durch das System und
            kein Live-Marktstatus.
          </p>
          {report.issues.length > 0 && (
            <ul
              aria-label="Offene Voraussetzungen der Sitzungszählung"
              className="space-y-2 text-amber-200"
            >
              {report.issues.map((issue, index) => (
                <li key={`${issue.code}:${index}`}>
                  <p>{issue.detail}</p>
                  <span className="text-xs [overflow-wrap:anywhere]">Code: {issue.code}</span>
                </li>
              ))}
            </ul>
          )}
          {report.notices.length > 0 && (
            <ul
              aria-label="Hinweise des Kalender-Owners"
              className="space-y-2 text-sm text-slate-300"
            >
              {report.notices.map((notice, index) => (
                <li key={index}>{notice}</li>
              ))}
            </ul>
          )}
          <CalendarDays report={report} />
          <Evidence report={report} />
        </>
      )}
    </section>
  );
}

export function HebeltraderSessions(props: Props) {
  return (
    <Sessions key={`${props.tradeId}:${props.positionId}:${props.reloadToken ?? 0}`} {...props} />
  );
}
