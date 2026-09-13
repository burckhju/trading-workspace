import { Link } from 'react-router-dom';

import type { TradePlanOverviewItem } from '../services/overviewClient';

export function PlanSelectedProduct({ item }: { item: TradePlanOverviewItem }) {
  // The API resolves the latest explicit selection of this exact plan version.
  // Neither an underlying nor a historical purchase can fill in a missing selection.
  const product = item.selected_product;
  const name = product?.display_name?.trim();
  const wkn = product?.wkn?.trim();
  const isin = product?.isin?.trim();

  return (
    <section
      aria-label="Optionsschein-Auswahl"
      className="mt-4 min-w-0 space-y-2 rounded-lg border border-slate-700 p-3"
    >
      <p className="text-xs text-slate-400">
        Ausgewählter Optionsschein · Version {item.latest_version}
      </p>
      {product ? (
        <>
          <h3 className="break-words text-lg font-semibold">
            {name || 'Produktname nicht verfügbar'}
          </h3>
          <p className="break-words text-sm text-slate-300">
            WKN {wkn || 'nicht hinterlegt'} · ISIN {isin || 'nicht hinterlegt'}
          </p>
          {(!name || !wkn || !isin) && (
            <p className="text-sm text-amber-200">
              Produktdaten unvollständig. Kennungen vor einer Erfassung prüfen.
            </p>
          )}
          <p className="text-xs text-slate-400">
            Zuletzt ausdrücklich ausgewählt; Bezeichnung aus aktuellen Stammdaten. Eine
            Produktauswahl ist kein Kaufnachweis. Tatsächliche Käufe stehen separat im Kaufstatus.
          </p>
          <Link
            to={`/product-selection?run_id=${encodeURIComponent(product.run_id)}`}
            className="inline-flex rounded text-sm text-sky-200 underline underline-offset-4 focus-visible:outline-2"
          >
            Ausgewählten Optionsschein prüfen
          </Link>
        </>
      ) : product === null ? (
        <p className="text-sm text-slate-300">
          Für diese Planversion wurde noch kein Optionsschein ausgewählt.
        </p>
      ) : (
        <p className="text-sm text-amber-200">
          Optionsschein-Auswahl nicht verfügbar. Backendstand prüfen und Übersicht neu laden.
        </p>
      )}
    </section>
  );
}
