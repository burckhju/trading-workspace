import { moneyText } from '../services/presentation';
import type { ClosedTradeReport } from '../types/api';

export function ClosedTradeStatistics({ report }: { report: ClosedTradeReport }) {
  const { statistics, currency } = report;
  const metrics = [
    ['win-rate', 'Trefferquote', statistics.win_rate, 'percent'],
    ['average-gross-pnl', 'Ø Bruttoergebnis je Trade', statistics.average_gross_pnl, 'money'],
    ['median-gross-pnl', 'Median des Bruttoergebnisses', statistics.median_gross_pnl, 'money'],
    ['gross-profit-factor', 'Profit-Faktor brutto', statistics.gross_profit_factor, 'ratio'],
  ] as const;

  return (
    <section
      aria-label="Basisstatistiken des Abschlussberichts"
      className="min-w-0 rounded-xl border border-slate-700 bg-slate-900/50 p-4 sm:p-5"
    >
      <h2 className="text-lg font-semibold">Basisstatistiken</h2>
      <p className="mt-2 text-sm" data-testid="closed-trades-statistics-population">
        Population N = {statistics.population ?? 'nicht bestimmt'} · qualifizierte abgeschlossene
        Trades der gesamten Berichtskohorte.
      </p>
      <p className="mt-2 text-sm text-slate-400">
        Die Kennzahlen gelten für den gesamten gewählten und abgerufenen Bericht. Zeilenansichten
        und Seitenwechsel ändern sie nicht. Neutrale Trades zählen im Nenner der Trefferquote mit,
        aber nicht als Gewinne.
      </p>
      <dl className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(([id, label, metric, unit]) => (
          <div key={id} className="min-w-0 rounded-lg bg-slate-950/50 p-3">
            <dt className="text-sm text-slate-400">{label}</dt>
            <dd
              className={`mt-2 break-words ${metric.display === null ? 'text-sm' : 'text-xl font-semibold'}`}
              data-testid={`closed-trades-${id}`}
            >
              {metric.display === null
                ? metric.reason
                : unit === 'money'
                  ? moneyText(metric.display, currency.code)
                  : `${metric.display.replace('.', ',')}${unit === 'percent' ? ' %' : ''}`}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 text-sm text-slate-400">
        Brutto bedeutet vor Kosten und Steuern. Gute Kennzahlen beweisen weder gute
        Einzelentscheidungen noch zukünftige Ergebnisse.
      </p>
      <details className="mt-4 text-sm">
        <summary className="cursor-pointer">Präzise Kennzahlen und Herkunft</summary>
        <dl className="mt-3 space-y-3">
          {metrics.map(([id, label, metric, unit]) => (
            <div key={id}>
              <dt className="text-slate-400">{label} · ungerundet</dt>
              <dd className="break-all">
                {metric.raw === null ? (
                  metric.reason
                ) : (
                  <>
                    <code>{metric.raw}</code>
                    {unit === 'money' ? ` ${currency.code}` : unit === 'percent' ? ' %' : ''}
                  </>
                )}
              </dd>
            </div>
          ))}
        </dl>
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
