import { useEffect, useRef, useState, type ReactNode } from 'react';
import type {
  DocumentedSessionMatch,
  HebeltraderOriginalBidReport,
  OriginalBidCheck,
  ProductSessionCalendar,
} from '../hebeltraderOriginalBid';
import type { SessionEvidenceCurrent, SessionPeriodView } from '../hebeltraderSessions';
import { readHebeltraderOriginalBid } from '../services/hebeltraderOriginalBid';

interface Props {
  tradeId: string;
  positionId: string;
  reloadToken?: string | number;
}
const buttonClass =
  'rounded border border-slate-600 px-3 py-2 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300';
const checkLabels: Record<OriginalBidCheck['status'], string> = {
  SATISFIED: 'Teilvoraussetzung belegt',
  MISSING: 'Beleg fehlt',
  UNSUITABLE: 'Ungeeignet',
  NOT_REACHED: 'Noch nicht erreicht',
  NOT_APPLICABLE: 'Nicht anwendbar',
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

function Match({ label, match }: { label: string; match: DocumentedSessionMatch }) {
  return (
    <Field label={label}>
      {match.status === 'IN_DOCUMENTED_INTERVAL'
        ? 'Innerhalb dokumentierter Handelszeit'
        : match.status === 'OUTSIDE_DOCUMENTED_INTERVAL'
          ? 'Außerhalb dokumentierter Handelszeit'
          : 'Nicht beurteilbar'}
      <p>
        Bezug: <Time value={match.event_at} />
      </p>
      {match.interval && (
        <p>
          Sitzungsdatum <Time value={match.session_date} /> ·{' '}
          <Time value={match.interval.opens_at} /> bis <Time value={match.interval.closes_at} />
        </p>
      )}
    </Field>
  );
}

function CalendarProof({
  label,
  calendar,
  period,
}: {
  label: string;
  calendar: ProductSessionCalendar | SessionEvidenceCurrent | null;
  period: SessionPeriodView;
}) {
  return (
    <section aria-label={label} className="space-y-2">
      <h5 className="font-semibold">{label}</h5>
      {!calendar ? (
        <p>Keine Kalenderbindung in diesem Read.</p>
      ) : (
        <>
          <p>
            Kalender {calendar.calendar_id ?? 'Nicht belegt'} · Version{' '}
            {calendar.calendar_version ?? 'Nicht belegt'} · Revision{' '}
            {calendar.revision_id ?? 'Nicht belegt'}.
          </p>
          <p>
            Instrument: {calendar.instrument_id} ({calendar.instrument_kind}) · Listing:{' '}
            {calendar.binding?.listing_id ?? 'Nicht gebunden'} · MIC:{' '}
            {calendar.binding?.venue_mic ?? 'Nicht belegt'} · Zeitzone:{' '}
            {calendar.binding?.timezone ?? 'Nicht belegt'}.
          </p>
          <p>
            Bindung gültig von <Time value={calendar.binding?.valid_from ?? null} /> bis{' '}
            <Time value={calendar.binding?.valid_through ?? null} /> · Abdeckung{' '}
            <Time value={calendar.coverage_start} /> bis <Time value={calendar.coverage_end} />.
          </p>
          <p>
            Quellenstand bekannt bis <Time value={calendar.known_at} /> · aufgezeichnet{' '}
            <Time value={calendar.recorded_at} /> · gelesen <Time value={calendar.read_at} />.
          </p>
          {calendar.source && (
            <dl className="grid gap-3 sm:grid-cols-2">
              <Field label="Dokumentquelle">
                {calendar.source.publisher} · {calendar.source.reference} ·{' '}
                {calendar.source.document_filename}
              </Field>
              <Field label="Veröffentlichung">
                <Time value={calendar.source.published_at ?? calendar.source.published_on} />
                {calendar.source.published_at === null &&
                  calendar.source.published_on !== null &&
                  ' · Nur Datum belegt'}
              </Field>
              <Field label="Dokumentprüfung">
                <Time value={calendar.source.reviewed_at} /> · {calendar.source.review_reference}
              </Field>
              <Field label="Abruf des Dokuments">
                <Time value={calendar.source.retrieved_at} />
              </Field>
              <Field label="Dokument SHA-256">{calendar.source.document_sha256}</Field>
              <Field label="Manifest SHA-256">{calendar.source.manifest_sha256}</Field>
            </dl>
          )}
        </>
      )}
      <p>
        Gelesener Zeitraum: <Time value={period.start_date} /> bis <Time value={period.end_date} />{' '}
        · Owner-Status: {period.status}.
      </p>
      <p className="[overflow-wrap:anywhere]">
        Zeitraumbezug: {period.fingerprint ?? 'Kein Zeitraum gelesen'}.
      </p>
      {period.missing_dates.length > 0 && (
        <details>
          <summary>Fehlende Kalendertage ({period.missing_dates.length})</summary>
          <p>{period.missing_dates.join(', ')}</p>
        </details>
      )}
    </section>
  );
}

function Evidence({ report }: { report: HebeltraderOriginalBidReport }) {
  const saved = report.saved_quote;
  const quote = saved.quote;
  const original = quote?.original_evidence;
  const route = saved.route;
  const provenance = saved.provenance;
  const economic = report.economic_basis;
  return (
    <details className="min-w-0 space-y-4 rounded border border-slate-700 p-3 text-xs">
      <summary className="cursor-pointer font-semibold">
        Geldkursquelle, Positionsbasis und Kalenderbelege
      </summary>
      <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
        <Field label="Wirtschaftliche Positionsbasis">
          {economic.definition_version} · {economic.basis_id}
        </Field>
        <Field label="Restbestand und Bruttoeinstand des Ausführungsowners">
          {economic.position.open_quantity} Stück · Ø {economic.position.average_entry_price} ·
          Kostenbeitrag {economic.position.cost_basis} ·{' '}
          {economic.cost_basis_currency ?? 'Währung nicht eindeutig belegt'} (
          {economic.currency_status}). Kein Vergleich mit dem Geldkurs.
        </Field>
        <Field label="Effektive Ausführungsbezüge">
          {economic.effective_execution_ids.join(', ') || 'Keine'}
        </Field>
        <Field label="Ursprünglicher Kaufbeleg">
          {report.entry ? (
            <>
              {report.entry.execution_id} ·{' '}
              <Time
                value={
                  report.entry.time_precision === 'DATE_ONLY'
                    ? report.entry.executed_on
                    : report.entry.executed_at
                }
              />{' '}
              ·{' '}
              {report.entry.time_precision === 'DATE_ONLY'
                ? 'Nur Datum belegt'
                : 'Genauer Ausführungszeitpunkt'}{' '}
              · {report.entry.execution_timezone ?? 'Zeitzone nicht belegt'}
            </>
          ) : (
            'Nicht vorhanden'
          )}
        </Field>
        <Field label="Aktuell gewählte gespeicherte Kursroute">
          {saved.provider ?? 'Nicht belegt'} · {saved.identity_key ?? 'Nicht belegt'}
        </Field>
        <Field label="Explizite Produkt-/Listingbindung">
          {route ? (
            <>
              {route.warrant_id} · {route.warrant_listing_id} · {route.venue_mic} · {route.currency}{' '}
              · Auswahl {route.selection_id} am <Time value={route.selected_at} />
            </>
          ) : (
            'Nicht belegt'
          )}
        </Field>
        <Field label="Originalquellenvertrag">
          {original
            ? `${original.source_contract} · ${original.source_reference}`
            : 'Kein zusätzlicher Originalseitenbeleg'}
        </Field>
        <Field label="Quellenidentität">
          {original?.isin ?? quote?.isin ?? 'ISIN nicht belegt'} ·{' '}
          {quote?.provider_symbol ?? 'Symbol nicht belegt'} ·{' '}
          {quote?.source_mode ?? 'Quellenmodus nicht belegt'}
        </Field>
        <Field label="Originalzeittext der BID-Seite">
          {original?.bid ? (
            <>
              {original.bid.original_time_text} · Feld {original.bid.source_field} · Preis{' '}
              {original.bid.price}
            </>
          ) : (
            'Nicht belegt; keine Ableitung aus der gemeinsamen Snapshotzeit'
          )}
        </Field>
        <Field label="Originalzeittext der ASK-Seite">
          {original?.ask ? (
            <>
              {original.ask.original_time_text} · Feld {original.ask.source_field} · Preis{' '}
              {original.ask.price}
            </>
          ) : (
            'Nicht belegt'
          )}
        </Field>
        <Field label="Quelle erzeugt am">
          <Time value={original?.generated_at ?? null} />
        </Field>
        <Field label="Gemeinsame Snapshotzeit (keine BID-Seitenzeit)">
          <Time value={quote?.observed_at ?? null} /> ·{' '}
          {quote?.quote_time_basis ?? 'Zeitbasis nicht belegt'} ·{' '}
          {quote?.quote_time_text ?? 'Kein Originalzeittext'}
        </Field>
        <Field label="Kurs abgerufen am">
          <Time value={saved.retrieved_at} />
        </Field>
        <Field label="Gespeicherte Herkunft">
          {saved.reason} · {saved.refresh_status}
        </Field>
        <Field label="Quellenmeldung zum Handel">
          {quote?.trading_status ?? 'Nicht belegt'} · Kein verifizierter Live-Marktstatus
        </Field>
        <Field label="Retention">
          {quote?.retained ? 'Als beibehaltener Kurs gekennzeichnet' : 'Kein Retentionsnachweis'};
          kein zusätzlicher Frischenachweis
        </Field>
        {provenance && (
          <>
            <Field label="Speichergrenze">
              Veränderlicher Last-success-Stand, keine historische Rekonstruktion. Zeitpunkt der
              Speicherung nicht aufgezeichnet.
            </Field>
            <Field label="SHA-256 des gespeicherten JSON-Payloads">
              {provenance.raw_payload_fingerprint} · Kein Hash ursprünglicher Providerantwortbytes
            </Field>
            <Field label="Persistierte Qualitätsangaben">
              {provenance.quality_status ?? 'Nicht belegt'} ·{' '}
              {provenance.reason_code ?? 'Kein zusätzlicher Code'}
              {provenance.warnings.length > 0 && <p>{provenance.warnings.join(', ')}</p>}
            </Field>
            <Field label="Gespeicherten Kurs gelesen am">
              <Time value={provenance.read_at} />
            </Field>
          </>
        )}
      </dl>
      <CalendarProof
        label="Produktkalender für BID- und Lesezeit"
        calendar={report.product_sessions.calendar}
        period={report.product_sessions.period}
      />
      <CalendarProof
        label="Basiswertkalender für die Original-BID-Zeit"
        calendar={report.underlying_sessions.calendar}
        period={report.underlying_sessions.period}
      />
      <p>
        Die Kalender beruhen auf dokumentierter menschlicher Prüfung. Sie sind keine unabhängig
        verifizierten Live-Quellen und belegen keine Abwesenheit einer Handelsunterbrechung.
      </p>
      <p>
        Positionsbezug: {report.trade_id} · {report.position_id} · {report.product_id} ·{' '}
        {report.underlying_id}.
      </p>
      <p className="[overflow-wrap:anywhere]">
        Berichtsbasis: {report.basis_id} · Regelbasis: {report.baseline_id}{' '}
        {report.baseline_version} · {report.definition_version}.
      </p>
      <p>
        Lesebeginn <Time value={report.read_started_at} /> · Leseabschluss{' '}
        <Time value={report.read_completed_at} />.
      </p>
    </details>
  );
}

function OriginalBid({ tradeId, positionId }: Props) {
  const [report, setReport] = useState<HebeltraderOriginalBidReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const generation = useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    const request = ++generation.current;
    const current = () => request === generation.current && !controller.signal.aborted;
    readHebeltraderOriginalBid(tradeId, positionId, controller.signal)
      .then((value) => {
        if (current()) setReport(value);
      })
      .catch((reason: unknown) => {
        if (current())
          setError(
            reason instanceof Error
              ? reason.message
              : 'Der Original-Geldkursbeleg konnte nicht gelesen werden.',
          );
      });
    return () => {
      generation.current += 1;
      controller.abort();
    };
  }, [tradeId, positionId, attempt]);
  const count = report?.underlying_sessions.count;
  return (
    <section
      aria-label="Hebeltrader-Original-Geldkurs"
      className="min-w-0 space-y-3 break-words rounded-xl border border-slate-700 bg-slate-950/40 p-3 sm:p-4"
    >
      <h3 className="font-semibold text-white">Hebeltrader · Original-Geldkurs</h3>
      <p>
        Gespeicherte Original-Geldkursbelege des gehaltenen Optionsscheins und ihre zeitlichen
        Voraussetzungen. Es wird kein Kurs neu abgerufen.
      </p>
      {!report && !error && <p>Original-Geldkursbeleg wird gelesen …</p>}
      {error && <p role="alert">{error}</p>}
      {report && (
        <>
          <dl className="grid gap-3 sm:grid-cols-3">
            <Field label="Belegabdeckung">
              {report.coverage_status === 'PARTIAL'
                ? 'Teilbelege vorhanden; Gesamtqualifikation offen'
                : report.coverage_status === 'UNSUITABLE'
                  ? 'Belege für diesen Prüfstand ungeeignet oder fehlend'
                  : 'Für diese Position nicht anwendbar'}
            </Field>
            <Field label="Regelfunktion">
              Passive Eingangsbelege. B04, B05, B06 und B58 sind nicht ausgewertet.
            </Field>
            <Field label="Betriebszustand">
              Dieser Teilschnitt ist nicht als laufende Überwachung aktiviert.
            </Field>
          </dl>
          <p>
            Serverseitiger Prüfstand: <Time value={report.evaluated_at} />. Die Aussage gilt für
            diesen Lesestand.
          </p>
          <dl className="grid gap-3 sm:grid-cols-2">
            <Field label="Gespeicherter Geldkurs (BID)">
              {report.bid.price ?? 'Nicht vorhanden'} {report.bid.currency ?? ''} ·{' '}
              {report.bid.status === 'AVAILABLE'
                ? 'Original-BID und Seitenzeit vorhanden'
                : report.bid.status === 'MISSING'
                  ? 'Originalbeleg unvollständig'
                  : report.bid.status === 'UNSUITABLE'
                    ? 'Für diesen Zeitpunkt ungeeignet'
                    : 'Nicht anwendbar'}
            </Field>
            <Field label="Exakte Original-BID-Zeit">
              <Time value={report.bid.original_bid_at} />
            </Field>
            <Field label="Kursalter laut Server">
              {report.bid.age_seconds === null
                ? 'Nicht beurteilbar'
                : `${report.bid.age_seconds} Sekunden`}{' '}
              · Höchstalter {report.bid.maximum_age_seconds} Sekunden
            </Field>
            <Field label="Basiswertsitzungen allein zur BID-Zeit">
              {!count
                ? 'Keine Zählung zur BID-Zeit verfügbar'
                : count.status === 'AVAILABLE'
                  ? `${count.completed_sessions} abgeschlossene Sitzungen`
                  : count.status === 'NOT_APPLICABLE'
                    ? 'Nicht anwendbar'
                    : 'Nicht beurteilbar'}
              {count && (
                <p>
                  Bezug: <Time value={count.evaluated_at} /> · Tag 0:{' '}
                  <Time value={count.anchor_date} />
                </p>
              )}
              {count?.twentieth_session_date && (
                <p>
                  20. Sitzung <Time value={count.twentieth_session_date} /> · Schluss{' '}
                  <Time value={count.twentieth_closes_at} />
                </p>
              )}
            </Field>
            <Match
              label="Produktsitzung zur Original-BID-Zeit"
              match={report.product_sessions.at_bid}
            />
            <Match
              label="Produktsitzung zum Serverlesezeitpunkt"
              match={report.product_sessions.at_read}
            />
          </dl>
          <p>
            {report.product_sessions.interval_relation === 'SAME_INTERVAL'
              ? 'BID- und Lesezeit liegen im selben dokumentierten Handelsintervall.'
              : report.product_sessions.interval_relation === 'DIFFERENT_INTERVALS'
                ? 'BID- und Lesezeit liegen in verschiedenen dokumentierten Handelsintervallen.'
                : 'Ein gemeinsames dokumentiertes Handelsintervall ist nicht beurteilbar.'}{' '}
            Daraus folgt kein verifiziert offener Live-Markt.
          </p>
          <p>
            Einstandsvergleich und Verlustzustand sind nicht Bestandteil dieses Reads. Eine
            vorhandene Seitenzeit oder Quellenmeldung „OPEN“ ersetzt keinen Maßstabs- oder
            Live-Markt-Nachweis.
          </p>
          {report.position_state !== 'OPEN' && (
            <p>
              Position {report.position_state === 'CLOSED' ? 'geschlossen' : 'storniert'}: Die
              gespeicherten Belege bleiben lesbar.
            </p>
          )}
          <ul aria-label="Voraussetzungen für den Original-Geldkurs" className="space-y-2">
            {report.checks.map((check) => (
              <li
                key={check.key}
                className={
                  check.status === 'SATISFIED' || check.status === 'NOT_APPLICABLE'
                    ? ''
                    : 'text-amber-200'
                }
              >
                <p className="font-semibold">
                  {check.label} · {checkLabels[check.status]}
                </p>
                <p>{check.detail}</p>
                {check.reasons.length > 0 && (
                  <details className="text-xs">
                    <summary>Belegcodes</summary>
                    <p className="[overflow-wrap:anywhere]">
                      {check.reasons.join(', ')} · {check.affected_rules.join(', ')}
                    </p>
                  </details>
                )}
              </li>
            ))}
          </ul>
          {report.notices.length > 0 && (
            <details className="text-sm text-slate-300">
              <summary>Hinweise und Grenzen des Owners</summary>
              <ul>
                {report.notices.map((notice, index) => (
                  <li key={index}>{notice}</li>
                ))}
              </ul>
            </details>
          )}
          <Evidence report={report} />
        </>
      )}
      <button
        type="button"
        className={buttonClass}
        disabled={!report && !error}
        onClick={() => {
          setReport(null);
          setError(null);
          setAttempt((value) => value + 1);
        }}
      >
        Gespeicherten Geldkursbeleg erneut lesen
      </button>
    </section>
  );
}

export function HebeltraderOriginalBid(props: Props) {
  return (
    <OriginalBid
      key={`${props.tradeId}:${props.positionId}:${props.reloadToken ?? 0}`}
      {...props}
    />
  );
}
