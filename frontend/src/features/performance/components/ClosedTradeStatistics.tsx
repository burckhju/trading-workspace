import { moneyText } from '../services/presentation';
import type { ClosedTradeReport } from '../types/api';

export function ClosedTradeStatistics({ report }: { report: ClosedTradeReport }) {
  const { statistics, currency, filters } = report;
  const metrics = [
    {
      id: 'win-rate',
      label: 'Trefferquote',
      metric: statistics.win_rate,
      unit: 'percent',
      definition:
        'Exakt positive vollständige Tradeergebnisse ÷ N × 100. Neutrale Trades zählen zu N.',
    },
    {
      id: 'average-gross-pnl',
      label: 'Ø Bruttoergebnis je Trade',
      metric: statistics.average_gross_pnl,
      unit: 'money',
      definition: 'Vollständige ungerundete Bruttosumme der Abschlusskohorte ÷ N.',
    },
    {
      id: 'median-gross-pnl',
      label: 'Median des Bruttoergebnisses',
      metric: statistics.median_gross_pnl,
      unit: 'money',
      definition:
        'Mittleres ungerundetes Tradeergebnis; bei geradem N Mittelwert der beiden mittleren Ergebnisse.',
    },
    {
      id: 'gross-profit-factor',
      label: 'Profit-Faktor brutto',
      metric: statistics.gross_profit_factor,
      unit: 'ratio',
      definition:
        'Summe positiver ungerundeter Tradeergebnisse ÷ Betrag der Summe negativer Ergebnisse. Ohne Verlusttrades nicht definiert.',
    },
  ] as const;
  const population = statistics.population ?? 'nicht bestimmt';
  const period = `${filters.from_date} bis einschließlich ${filters.to_date} · ${filters.report_timezone}`;
  const displayValue = ({ metric, unit }: Pick<(typeof metrics)[number], 'metric' | 'unit'>) =>
    metric.display === null
      ? (metric.reason ?? 'Nicht verfügbar')
      : unit === 'money'
        ? moneyText(metric.display, currency.code)
        : `${metric.display.replace('.', ',')}${unit === 'percent' ? ' %' : ''}`;
  const unitText = (unit: (typeof metrics)[number]['unit']) =>
    unit === 'money' ? currency.code : unit === 'percent' ? 'Prozent (%)' : 'dimensionslos';

  return (
    <section
      aria-label="Basisstatistiken des Abschlussberichts"
      className="min-w-0 rounded-xl border border-slate-700 bg-slate-900/50 p-4 sm:p-5"
    >
      <h2 className="text-lg font-semibold">Basisstatistiken</h2>
      <p className="mt-2 text-sm" data-testid="closed-trades-statistics-population">
        Population N = {population} · qualifizierte abgeschlossene Trades der gesamten
        Berichtskohorte.
      </p>
      <p className="mt-2 text-sm text-slate-400">
        Die Kennzahlen gelten für den gesamten gewählten und abgerufenen Bericht. Zeilenansichten
        und Seitenwechsel ändern sie nicht. Neutrale Trades zählen im Nenner der Trefferquote mit,
        aber nicht als Gewinne.
      </p>
      <p className="mt-2 text-sm text-slate-400">
        Maßgeblich ist der Vollabschluss im Zeitraum; frühere Teilverkäufe gehören zum vollständigen
        Tradeergebnis. Bei unvollständiger Berichtsgrundlage bleiben alle vier Kennzahlen ohne Wert.
      </p>
      <dl className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ id, label, metric, unit, definition }) => (
          <div key={id} className="min-w-0 rounded-lg bg-slate-950/50 p-3">
            <dt className="text-sm text-slate-400">{label}</dt>
            <dd
              className={`mt-2 break-words ${metric.display === null ? 'text-sm' : 'text-xl font-semibold'}`}
              data-testid={`closed-trades-${id}`}
            >
              {displayValue({ metric, unit })}
            </dd>
            <dd className="mt-3 space-y-2 text-sm text-slate-300 [overflow-wrap:anywhere]">
              <p>{definition}</p>
              <p>
                Grundgesamtheit: vollständige Tradeergebnisse der gesamten Abschlusskohorte · N ={' '}
                {population}.
              </p>
              <p>Zeitraum des Vollabschlusses: {period}.</p>
              <p>
                Einheit: {unitText(unit)} · Kohortenwährung: {currency.code}.
              </p>
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 text-sm text-slate-400">
        Brutto bedeutet vor Kosten und Steuern. Gute Kennzahlen beweisen weder gute
        Einzelentscheidungen noch zukünftige Ergebnisse.
      </p>
      <details className="mt-4 text-sm">
        <summary className="cursor-pointer rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400">
          Präzise Kennzahlen und Herkunft
        </summary>
        <p className="mt-3 [overflow-wrap:anywhere]">
          Die Kennzahlentabelle gilt für vollständige Tradeergebnisse der gesamten Abschlusskohorte
          mit N = {population}. Zeitraum des Vollabschlusses: {period}. Kohortenwährung:{' '}
          {currency.code}.
        </p>
        <div
          role="region"
          aria-label="Kennzahlentabelle, bei Bedarf horizontal scrollbar"
          tabIndex={0}
          className="mt-3 max-w-full overflow-x-auto rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
        >
          <table className="w-full min-w-[36rem] table-fixed text-left">
            <caption className="pb-2 text-left font-medium">
              Kennzahlen des Abschlussberichts · Anzeige und unveränderte Rohwerte
            </caption>
            <thead>
              <tr className="border-b border-slate-700">
                <th scope="col" className="w-1/2 p-2 font-medium">
                  Kennzahl und Definition
                </th>
                <th scope="col" className="w-1/4 p-2 font-medium">
                  Anzeigewert
                </th>
                <th scope="col" className="w-1/4 p-2 font-medium">
                  Ungerundeter Rohwert
                </th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((entry) => (
                <tr key={entry.id} className="border-b border-slate-800 align-top">
                  <th scope="row" className="p-2 font-normal [overflow-wrap:anywhere]">
                    <span className="font-medium">{entry.label}</span>
                    <p className="mt-1 text-slate-400">{entry.definition}</p>
                    <p className="mt-1 text-slate-400">Einheit: {unitText(entry.unit)}</p>
                  </th>
                  <td className="break-all p-2">{displayValue(entry)}</td>
                  <td className="break-all p-2">
                    {entry.metric.raw === null ? (
                      (entry.metric.reason ?? 'Nicht verfügbar')
                    ) : (
                      <>
                        <code>{entry.metric.raw}</code>
                        {entry.unit === 'money'
                          ? ` ${currency.code}`
                          : entry.unit === 'percent'
                            ? ' %'
                            : ''}
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 break-all text-slate-400">
          Statistikdefinition: <code>{statistics.definition_version}</code> · Berichtsgrundlage:{' '}
          <code>{statistics.report_basis_id}</code>.
        </p>
        <p className="mt-2 text-slate-400">
          Berechnung und Anzeigerundung stammen gemeinsam mit den Tradeergebnissen aus derselben
          Antwort. Trefferquote und Profit-Faktor: zwei Nachkommastellen. Geldbeträge:{' '}
          {currency.minor_unit} Nachkommastellen nach Währungsreferenz {currency.reference_version}.
          Rundung zur nächsten geraden Ziffer bei exakter Mitte (ROUND_HALF_EVEN).
        </p>
      </details>
    </section>
  );
}
