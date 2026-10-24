import { moneyText } from '../services/presentation';
import type { ClosedTradeReport } from '../types/api';

const statusText: Record<ClosedTradeReport['summary']['status'], string> = {
  EMPTY: 'Keine abgeschlossenen Trades in dieser Auswahl',
  COMPLETE: 'Vollständig auswertbare Abschlussauswahl',
  PARTIAL: 'Teilweise auswertbar · Gesamtsumme nicht berechenbar',
  NOT_COMPUTABLE: 'Abschlussauswahl nicht berechenbar',
};

export function ClosedTradeSummary({ report }: { report: ClosedTradeReport }) {
  const { summary, counts, currency, filters } = report;
  const groups = [
    ['Stornierte Fehleinträge', counts.cancelled],
    ['Historie oder Vollabschluss ungeklärt', counts.history_unresolved],
    ['Gültig offen', counts.open],
    ['Vollabschluss sicher außerhalb des Zeitraums', counts.outside_period],
    ['Vollständig belegte andere Währung', counts.other_currency],
    ['Abschlusszeitraum ungeklärt', counts.period_unresolved],
    ['Im Zeitraum, Gesamtergebnis monetär ungeklärt', counts.monetary_unresolved],
    ['Im Zeitraum, vollständig qualifiziert', counts.qualified],
  ] as const;
  return (
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
          <dt className="text-sm text-slate-400">Bruttosumme · vollständige Tradeergebnisse</dt>
          <dd className="mt-1 break-words text-2xl font-semibold" data-testid="closed-trades-total">
            {moneyText(summary.total_display, currency.code)}
          </dd>
        </div>
        {summary.subtotal !== null && (
          <div>
            <dt className="text-sm text-amber-300">
              Teilsumme · nur vollständig qualifizierte Trades
            </dt>
            <dd
              className="mt-1 break-words text-2xl font-semibold"
              data-testid="closed-trades-subtotal"
            >
              {moneyText(summary.subtotal_display, currency.code)}
            </dd>
          </div>
        )}
      </dl>
      {summary.status === 'EMPTY' && (
        <p className="mt-3 text-sm">
          Die Auswahl wurde geprüft. Kein Trade gehört qualifiziert oder ungeklärt zur
          Abschlussauswahl. Die Null beschreibt eine leere Auswahl; Ausschlüsse bleiben einsehbar.
        </p>
      )}
      {summary.status === 'COMPLETE' && (
        <p className="mt-3 text-sm">
          Alle relevanten Trades sind vollständig auswertbar. Jeder Trade zählt einmal mit seinem
          gesamten Bruttoergebnis, einschließlich früherer Teilverkäufe außerhalb des Zeitraums.
          Eine Gesamtsumme von null ist ein gemessenes Ergebnis.
        </p>
      )}
      {summary.status === 'PARTIAL' && (
        <p className="mt-3 text-sm text-amber-300">
          Die Teilsumme umfasst {counts.qualified} vollständig qualifizierte Trades. Wegen{' '}
          {counts.unresolved} ungeklärter Fälle ist die Gesamtsumme unbekannt. Bekannte
          Einzelbeträge aus einem ungeklärten Trade fließen auch nicht in diese Teilsumme ein.
        </p>
      )}
      {summary.status === 'NOT_COMPUTABLE' && (
        <p className="mt-3 text-sm text-amber-300">
          Es gibt relevante ungeklärte Fälle, aber kein vollständig qualifiziertes Tradeergebnis.
          Fehlende Herkunft ergibt weder einen Nullbetrag noch eine neutrale Klassifikation.
        </p>
      )}
      <dl className="mt-5 grid grid-cols-3 gap-3 rounded-lg bg-slate-950/50 p-3 text-sm">
        <div>
          <dt className="text-slate-400">Positive Trades</dt>
          <dd className="mt-1 text-xl font-semibold" data-testid="closed-trades-positive">
            {counts.positive}
          </dd>
        </div>
        <div>
          <dt className="text-slate-400">Negative Trades</dt>
          <dd className="mt-1 text-xl font-semibold" data-testid="closed-trades-negative">
            {counts.negative}
          </dd>
        </div>
        <div>
          <dt className="text-slate-400">Neutrale Trades</dt>
          <dd className="mt-1 text-xl font-semibold" data-testid="closed-trades-neutral">
            {counts.neutral}
          </dd>
        </div>
      </dl>
      <p className="mt-3 text-sm text-slate-400">
        Das Vorzeichen des vollständigen ungerundeten Ergebnisses entscheidet. Neutral bedeutet
        exakt null: +0,004 ist positiv und −0,004 negativ, auch wenn beide bei zwei Nachkommastellen
        als 0,00 erscheinen. Präzise Werte stehen in den Tradequellen. Ungeklärte Trades erhalten
        keine Klassifikation.
      </p>
      <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-slate-400">Eigene Trades geprüft</dt>
          <dd>{counts.examined}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Abschluss sicher im Zeitraum · Währungsauswahl</dt>
          <dd>{counts.in_period}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Vollständig qualifiziert</dt>
          <dd>{counts.qualified}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Relevante ungeklärte Fälle</dt>
          <dd>{counts.unresolved}</dd>
        </div>
      </dl>
      <p className="mt-3 text-xs text-slate-400">
        Summe und Zähler beziehen sich auf die gesamte gelesene Auswahl. Zeilenfilter und lokale
        Seiten ändern sie nicht. Zeitlich oder historisch ungeklärte Fälle sind nicht als sichere
        Abschlüsse dieser Periode gezählt.
      </p>
      <details className="mt-4 text-sm">
        <summary className="cursor-pointer">
          Alle acht Fallgruppen, präzise Summen und Rundung
        </summary>
        <p className="mt-3 text-slate-400">
          Jeder untersuchte Trade steht in genau einer Gruppe. Die erste zutreffende Gruppe hat
          Vorrang. Ungeklärte Historie, Abschlussperiode und Geldherkunft verhindern eine
          vollständige Gesamtsumme.
        </p>
        <table className="mt-3 w-full text-left">
          <caption className="sr-only">Disjunkte Fallgruppen der untersuchten Trades</caption>
          <thead>
            <tr className="border-b border-slate-700">
              <th scope="col" className="py-2 pr-3 font-medium">
                Fallgruppe in Prüfreihenfolge
              </th>
              <th scope="col" className="py-2 text-right font-medium">
                Trades
              </th>
            </tr>
          </thead>
          <tbody>
            {groups.map(([label, count]) => (
              <tr key={label} className="border-b border-slate-800">
                <th scope="row" className="py-2 pr-3 font-normal">
                  {label}
                </th>
                <td className="py-2 text-right">{count}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <dl className="mt-4 space-y-2">
          <div>
            <dt className="text-slate-400">Gesamtsumme · ungerundet</dt>
            <dd className="break-all">
              <code>{summary.total ?? 'Nicht berechenbar'}</code>
              {summary.total !== null && ` ${currency.code}`}
            </dd>
          </div>
          <div>
            <dt className="text-slate-400">Teilsumme qualifizierter Trades · ungerundet</dt>
            <dd className="break-all">
              <code>{summary.subtotal ?? 'Nicht anwendbar'}</code>
              {summary.subtotal !== null && ` ${currency.code}`}
            </dd>
          </div>
          <div>
            <dt className="text-slate-400">
              Rundungsdifferenz zu einzeln gerundeten Tradeergebnissen
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
        <p className="mt-3 text-slate-400">
          Erst ungerundete Tradeergebnisse summieren, dann anzeigen. Rundungsdifferenzen werden
          keinem Trade zugeschlagen. Rundung zur nächsten geraden Ziffer bei exakter Mitte
          (ROUND_HALF_EVEN), {currency.minor_unit} Nachkommastellen; Währungsreferenz{' '}
          {currency.reference_version}.
        </p>
      </details>
    </section>
  );
}
