import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { todayInZone } from '../../trade/services/executionDateCorrection';
import { RealizedGrossSources } from '../components/RealizedGrossSources';
import { performanceApiClient } from '../services/client';
import { executionTimeText, filterKey, moneyText, reasonText } from '../services/presentation';
import type { RealizedGrossFilters, RealizedGrossItem, RealizedGrossReport } from '../types/api';

const inputClass =
  'mt-1 block w-full min-w-0 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2';
const buttonClass =
  'rounded-lg border border-slate-600 px-3 py-2 text-sm disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400';
const PAGE_SIZE = 20;
const REPORT_CURRENCY = 'EUR';

function initialFilters(): RealizedGrossFilters {
  const today = todayInZone('Europe/Berlin');
  return {
    from_date: `${today.slice(0, 8)}01`,
    to_date: today,
    report_currency: REPORT_CURRENCY,
    report_timezone: 'Europe/Berlin',
  };
}

const statusText: Record<RealizedGrossReport['summary']['status'], string> = {
  EMPTY: 'Keine wirksamen Verkäufe in dieser Auswahl',
  COMPLETE: 'Vollständig auswertbare Auswahl',
  PARTIAL: 'Teilweise auswertbar · Gesamtsumme nicht berechenbar',
  NOT_COMPUTABLE: 'Auswahl nicht berechenbar',
};
const itemText: Record<RealizedGrossItem['status'], string> = {
  USABLE: 'Verwendbarer Beitrag',
  NOT_COMPUTABLE: 'Datenlücke / nicht berechenbar',
  EXCLUDED: 'Ausgeschlossen',
};

function ReportContent({ report }: { report: RealizedGrossReport }) {
  const [view, setView] = useState('candidates');
  const [page, setPage] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);
  const items = report.items.filter((item) => {
    if (view === 'usable') return item.status === 'USABLE';
    if (view === 'unresolved') return item.status === 'NOT_COMPUTABLE';
    if (view === 'excluded') return item.status === 'EXCLUDED';
    if (view === 'candidates') return item.status !== 'EXCLUDED';
    return true;
  });
  const pages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const visible = items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const { summary, counts, currency, filters } = report;
  return (
    <div className="space-y-6" aria-label="Realisationsbericht">
      <section
        aria-label="Ergebnis und Datenabdeckung"
        className="rounded-xl border border-slate-700 bg-slate-900/50 p-4 sm:p-5"
      >
        <p className="text-sm text-slate-400">
          {filters.from_date} bis einschließlich {filters.to_date} · {filters.report_timezone} ·{' '}
          {currency.code}
        </p>
        <h2 className="mt-2 text-lg font-semibold">{statusText[summary.status]}</h2>
        <dl className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm text-slate-400">Realisierte Bruttosumme · gesamte Auswahl</dt>
            <dd
              className="mt-1 break-words text-2xl font-semibold"
              data-testid="realized-gross-total"
            >
              {moneyText(summary.total_display, currency.code)}
            </dd>
          </div>
          {summary.subtotal !== null && (
            <div>
              <dt className="text-sm text-amber-300">
                Bekannter Teilbetrag · nur verwendbare Beiträge
              </dt>
              <dd
                className="mt-1 break-words text-2xl font-semibold"
                data-testid="realized-gross-subtotal"
              >
                {moneyText(summary.subtotal_display, currency.code)}
              </dd>
            </div>
          )}
        </dl>
        {summary.status === 'EMPTY' && (
          <p className="mt-3 text-sm">
            Die Auswahl wurde geprüft. Es gibt darin keinen wirksamen Verkauf. Ausschlüsse bleiben
            unten einsehbar.
          </p>
        )}
        {summary.status === 'COMPLETE' && (
          <p className="mt-3 text-sm">
            Alle für diese Auswahl relevanten Verkäufe sind auswertbar. Auch Teilverkäufe eines
            weiterhin offenen Trades zählen.
          </p>
        )}
        {summary.status === 'PARTIAL' && (
          <p className="mt-3 text-sm text-amber-300">
            Der Teilbetrag umfasst {counts.usable} verwendbare Beiträge. Wegen {counts.unresolved}{' '}
            ungeklärter Fälle ist die vollständige Summe unbekannt; der Teilbetrag ersetzt sie
            nicht.
          </p>
        )}
        {summary.status === 'NOT_COMPUTABLE' && (
          <p className="mt-3 text-sm text-amber-300">
            Es gibt relevante oder zeitlich ungeklärte Verkäufe, aber keinen verwendbaren Beitrag.
            Fehlende Herkunft ergibt keinen Nullbetrag.
          </p>
        )}
        <p className="mt-3 text-xs text-slate-400">
          Die Gesamtsumme umfasst die vollständige Auswahl, unabhängig von Zeilenfilter und Seite.
          Die Summe wird aus ungerundeten Beiträgen berechnet und für {currency.code} gerundet; ein
          angezeigter Nullbetrag kann einen kleineren ungerundeten Beitrag enthalten.
        </p>
        <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-3 lg:grid-cols-6">
          <div>
            <dt className="text-slate-400">Wirksame SELLs geprüft</dt>
            <dd>{counts.examined}</dd>
          </div>
          <div>
            <dt className="text-slate-400">In der Periode</dt>
            <dd>{counts.in_period}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Verwendbar</dt>
            <dd>{counts.usable}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Ungeklärt</dt>
            <dd>{counts.unresolved}</dd>
          </div>
          <div>
            <dt className="text-slate-400">SELLs ausgeschlossen</dt>
            <dd>{counts.excluded}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Stornierte Trades</dt>
            <dd>{counts.cancelled}</dd>
          </div>
        </dl>
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer">Präzise Summen, Rundung und weitere Zähler</summary>
          <dl className="mt-3 space-y-2">
            <div>
              <dt className="text-slate-400">Gesamtsumme · ungerundet</dt>
              <dd className="break-all">
                <code>{summary.total ?? 'Nicht berechenbar'}</code>
                {summary.total !== null && ` ${currency.code}`}
              </dd>
            </div>
            <div>
              <dt className="text-slate-400">Bekannter Teilbetrag · ungerundet</dt>
              <dd className="break-all">
                <code>{summary.subtotal ?? 'Nicht anwendbar'}</code>
                {summary.subtotal !== null && ` ${currency.code}`}
              </dd>
            </div>
            <div>
              <dt className="text-slate-400">
                Rundungsdifferenz zur Summe der einzeln gerundeten Beiträge
              </dt>
              <dd>
                {summary.rounding_difference_display === null
                  ? 'Nicht anwendbar'
                  : moneyText(summary.rounding_difference_display, currency.code)}
                {summary.rounding_difference !== null && (
                  <>
                    {' '}
                    · präzise <code>{summary.rounding_difference}</code>
                  </>
                )}
              </dd>
            </div>
          </dl>
          <p className="mt-2 text-slate-400">
            Die vom Backend ausgewiesene Rundungsdifferenz gehört zur Summendarstellung und wird
            keinem Verkauf zugeschlagen. Rundung: zur nächsten geraden Ziffer bei exakter Mitte
            (ROUND_HALF_EVEN), {currency.minor_unit} Nachkommastellen; Währungsreferenz{' '}
            {currency.reference_version}.
          </p>
          <p className="mt-2">
            Außerhalb der Periode: {counts.outside_period} · Periodenzugehörigkeit mehrdeutig:{' '}
            {counts.period_ambiguous} · Periodenzugehörigkeit unbekannt: {counts.period_unknown} ·
            relevante oder ungeklärte Kandidaten: {counts.candidates}.
          </p>
        </details>
      </section>

      <section aria-labelledby="realized-gross-items-title" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 id="realized-gross-items-title" className="text-lg font-semibold">
              Verkäufe und Einzelbeiträge
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Quellen öffnen die vollständige Kostenbasis-Herkunft dieses Verkaufs.
            </p>
          </div>
          <label className="text-sm">
            Zeilen anzeigen
            <select
              className={inputClass}
              value={view}
              onChange={(event) => {
                setView(event.target.value);
                setPage(0);
                setExpanded(null);
              }}
            >
              <option value="candidates">Relevante / ungeklärte Fälle ({counts.candidates})</option>
              <option value="usable">Verwendbare Beiträge ({counts.usable})</option>
              <option value="unresolved">Datenlücken ({counts.unresolved})</option>
              <option value="excluded">Ausschlüsse ({counts.excluded})</option>
              <option value="all">Alle geprüften SELLs ({counts.examined})</option>
            </select>
          </label>
        </div>
        {items.length === 0 && (
          <p className="rounded-lg border border-slate-800 p-4 text-sm">
            Keine Verkäufe in diesem Zeilenfilter. Die Berichtssumme und Datenabdeckung oben bleiben
            unverändert.
          </p>
        )}
        <div className="space-y-3">
          {visible.map((item) => (
            <article
              key={item.execution_id}
              aria-label={`Verkauf ${item.execution_id}`}
              className="min-w-0 rounded-xl border border-slate-800 p-4"
            >
              <div className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1.5fr)_minmax(0,1fr)_auto]">
                <div>
                  <h3 className="break-words font-medium">
                    {item.product_name ?? 'Produktname nicht verfügbar'}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500">
                    Heutige Produktanzeige · {item.quantity} Stück verkauft
                  </p>
                  <p className="mt-1 text-sm">{executionTimeText(item, filters.report_timezone)}</p>
                </div>
                <div>
                  <p
                    className={
                      item.status === 'USABLE' ? 'text-sm text-sky-300' : 'text-sm text-amber-300'
                    }
                  >
                    {itemText[item.status]}
                  </p>
                  {item.reasons.map((reason) => (
                    <p key={reason} className="mt-1 text-sm text-slate-400">
                      {reasonText(reason)}
                    </p>
                  ))}
                </div>
                <div>
                  <p className="text-xs text-slate-400">Realisierter Bruttobeitrag</p>
                  <p className="mt-1 break-words font-semibold">
                    {item.status === 'EXCLUDED'
                      ? 'Nicht in der Summe'
                      : moneyText(item.realized_gross_pnl_delta_display, item.currency_code)}
                  </p>
                </div>
                <button
                  type="button"
                  className={`${buttonClass} self-start`}
                  aria-expanded={expanded === item.execution_id}
                  onClick={() =>
                    setExpanded(expanded === item.execution_id ? null : item.execution_id)
                  }
                >
                  {expanded === item.execution_id ? 'Quellen schließen' : 'Quellen und Berechnung'}
                </button>
              </div>
              {expanded === item.execution_id && (
                <RealizedGrossSources item={item} report={report} />
              )}
            </article>
          ))}
        </div>
        {items.length > 0 && (
          <nav
            aria-label="Berichtsseiten"
            className="flex flex-wrap items-center justify-between gap-3 text-sm"
          >
            <p>
              Seite {page + 1} von {pages} · {items.length} Zeilen in diesem Filter · alle Summen
              beziehen sich auf die gesamte Auswahl.
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                className={buttonClass}
                disabled={page === 0}
                onClick={() => {
                  setPage((value) => value - 1);
                  setExpanded(null);
                }}
              >
                Vorherige Seite
              </button>
              <button
                type="button"
                className={buttonClass}
                disabled={page + 1 >= pages}
                onClick={() => {
                  setPage((value) => value + 1);
                  setExpanded(null);
                }}
              >
                Nächste Seite
              </button>
            </div>
          </nav>
        )}
      </section>

      {report.excluded_trades.length > 0 && (
        <section aria-label="Stornierte Trades" className="rounded-xl border border-slate-800 p-4">
          <h2 className="font-semibold">Stornierte Fehleinträge ({counts.cancelled})</h2>
          <p className="mt-1 text-sm text-slate-400">
            Storno ist kein wirtschaftlicher Ausstieg. Diese Trades tragen weder Gewinn noch Verlust
            bei.
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            {report.excluded_trades.map((trade) => (
              <li key={trade.trade_id}>
                <Link
                  className="text-sky-300 underline"
                  to={`/trade-management?trade_id=${encodeURIComponent(trade.trade_id)}#execution-dates`}
                >
                  {trade.product_name ?? 'Produktname nicht verfügbar'} · Trade prüfen
                </Link>
                <span className="ml-2 text-slate-400">{reasonText(trade.reason)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <details className="rounded-xl border border-slate-800 p-4 text-sm">
        <summary className="cursor-pointer font-medium">
          Auswertungsdefinition und Quellenstand
        </summary>
        <div className="mt-3 space-y-2 text-slate-400">
          <p>
            Definition: {report.definition_version}. Wirtschaftliche SELL-Ausführung im gewählten
            Zeitraum; Menge × (tatsächlicher Stückverkaufspreis − Average Cost unmittelbar davor).
            Brutto vor Gebühren, Kommissionen und Steuern. Keine automatische Währungsumrechnung.
          </p>
          <p>
            Aktuell bekannte, wirksame korrigierte Fakten: Eine spätere Korrektur oder
            Währungsbestätigung kann das Ergebnis für einen alten Zeitraum verändern. Ein damaliger
            Wissensstand wird nicht rekonstruiert.
          </p>
          <p>
            Berichtszone: {filters.report_timezone}. Inklusive Kalendertage werden vom Backend als
            Intervall von {report.interval_start_at} bis ausschließlich {report.interval_end_at}{' '}
            zugeordnet. Datum ohne Uhrzeit bleibt Datum; bei mehrdeutiger Zugehörigkeit bleibt der
            Fall ungeklärt.
          </p>
          <p>
            Quellen gelesen von {report.basis.read_started_at} bis {report.basis.read_completed_at};
            berechnet am {report.basis.calculated_at}. Diese Zeiten sind keine Ausführungszeiten.
          </p>
          <p className="break-all">
            Quellenstand: <code>{report.basis.id}</code>
          </p>
          <p>
            Summary, Zähler, Zeilen und geöffnete Quellen gehören zu dieser einen Antwort. Lokale
            Seiten wechseln den Quellenstand nicht. Ein erneutes Lesen oder der Sprung in die
            Trade-Historie kann einen neueren Stand zeigen.
          </p>
        </div>
      </details>
    </div>
  );
}

export function RealizedGrossPage() {
  const [filters, setFilters] = useState(initialFilters);
  const [report, setReport] = useState<RealizedGrossReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [changedBasis, setChangedBasis] = useState(false);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const lastBasis = useRef(new Map<string, string>());

  useEffect(
    () => () => {
      generation.current += 1;
      controller.current?.abort();
    },
    [],
  );

  function change(field: Exclude<keyof RealizedGrossFilters, 'report_currency'>, value: string) {
    generation.current += 1;
    controller.current?.abort();
    setFilters((current) => ({ ...current, [field]: value }));
    setReport(null);
    setLoading(false);
    setError(null);
    setChangedBasis(false);
  }

  async function read() {
    const requested = {
      ...filters,
      report_currency: REPORT_CURRENCY,
      report_timezone: filters.report_timezone.trim(),
    };
    setError(null);
    setReport(null);
    setChangedBasis(false);
    if (!requested.from_date || !requested.to_date || requested.from_date > requested.to_date) {
      setError('Bitte einen gültigen Zeitraum angeben: Von darf nicht nach Bis liegen.');
      return;
    }
    if (!requested.report_timezone) {
      setError('Bitte eine Berichtszeitzone (IANA) angeben.');
      return;
    }
    const current = ++generation.current;
    controller.current?.abort();
    const requestController = new AbortController();
    controller.current = requestController;
    setLoading(true);
    try {
      const result = await performanceApiClient.realizedGross(requested, requestController.signal);
      if (requestController.signal.aborted || current !== generation.current) return;
      const key = filterKey(requested);
      if (filterKey(result.filters) !== key || result.currency.code !== requested.report_currency) {
        throw new Error(
          'Die Antwort gehört nicht zur gewählten Periode, Währung oder Zeitzone. Bitte erneut lesen.',
        );
      }
      const previous = lastBasis.current.get(key);
      setChangedBasis(previous !== undefined && previous !== result.basis.id);
      lastBasis.current.set(key, result.basis.id);
      setReport(result);
    } catch (cause) {
      if (requestController.signal.aborted || current !== generation.current) return;
      setError(cause instanceof Error ? cause.message : 'Bericht konnte nicht gelesen werden.');
    } finally {
      if (!requestController.signal.aborted && current === generation.current) setLoading(false);
    }
  }

  return (
    <div className="min-w-0 w-full space-y-6 [overflow-wrap:anywhere]">
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-500">
          Auswertung tatsächlicher Verkäufe
        </p>
        <h1 className="mt-1 text-2xl font-semibold">Realisierte Bruttoergebnisse</h1>
        <p className="mt-2 max-w-4xl text-sm text-slate-400">
          Welche Verkäufe gehören in den Zeitraum, welchen Ergebnisbeitrag liefern sie, und woher
          stammt ihre Kostenbasis? Der Bericht zeigt den aktuellen korrigierten Faktenstand, brutto
          vor Gebühren, Kommissionen und Steuern.
        </p>
        <p className="mt-2 max-w-4xl text-sm text-slate-400">
          Dies ist eine Realisationsauswertung. Sie beschreibt keine vollständige Depotperformance.
          Journal, Nachbeobachtung und Lessons sind keine Voraussetzung.
        </p>
      </header>
      <form
        aria-label="Realisationszeitraum auswählen"
        className="rounded-xl border border-slate-800 p-4 sm:p-5"
        onSubmit={(event) => {
          event.preventDefault();
          void read();
        }}
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-sm">
            Von (einschließlich)
            <input
              type="date"
              required
              value={filters.from_date}
              onChange={(event) => change('from_date', event.target.value)}
              className={inputClass}
            />
          </label>
          <label className="text-sm">
            Bis (einschließlich)
            <input
              type="date"
              required
              value={filters.to_date}
              onChange={(event) => change('to_date', event.target.value)}
              className={inputClass}
            />
          </label>
          <label className="text-sm">
            Berichtswährung
            <input readOnly value={REPORT_CURRENCY} className={inputClass} />
          </label>
          <label className="text-sm">
            Berichtszeitzone (IANA)
            <input
              required
              value={filters.report_timezone}
              autoComplete="off"
              spellCheck={false}
              list="report-timezones"
              onChange={(event) => change('report_timezone', event.target.value)}
              className={inputClass}
            />
          </label>
        </div>
        <datalist id="report-timezones">
          <option value="Europe/Berlin" />
          <option value="Etc/UTC" />
          <option value="America/New_York" />
          <option value="Asia/Tokyo" />
        </datalist>
        <p className="mt-3 text-xs text-slate-400">
          Vorgeschlagene Berichtszone: Europe/Berlin. Die gewählte Zone bestimmt die
          Periodengrenzen. Die Berichtswährung ist fest Euro (EUR). Sie filtert bereits belegte
          Währungen; sie bestätigt keine Buchung und rechnet nichts um.
        </p>
        <button type="submit" disabled={loading} className={`${buttonClass} mt-4 border-sky-700`}>
          {loading ? 'Bericht wird gelesen…' : 'Bericht lesen'}
        </button>
      </form>
      {loading && (
        <p role="status">
          Ein konsistenter Quellenstand wird gelesen. Für diese Auswahl liegt noch kein neues
          Ergebnis vor.
        </p>
      )}
      {error && (
        <p role="alert" className="rounded-lg border border-amber-800 p-4 text-sm text-amber-300">
          {error}
        </p>
      )}
      {changedBasis && report && (
        <p role="status" className="rounded-lg border border-sky-800 p-4 text-sm">
          Der Quellenstand hat sich seit dem letzten Lesen dieser Auswahl geändert. Summe, Zeilen
          und Herkunft wurden gemeinsam durch den neu gelesenen Stand ersetzt.
        </p>
      )}
      {!report && !loading && !error && (
        <p className="text-sm text-slate-400">
          Zeitraum und Berichtszone prüfen und „Bericht lesen“ wählen. Die Berichtswährung ist EUR.
        </p>
      )}
      {report && (
        <ReportContent key={`${filterKey(report.filters)}:${report.basis.id}`} report={report} />
      )}
    </div>
  );
}
