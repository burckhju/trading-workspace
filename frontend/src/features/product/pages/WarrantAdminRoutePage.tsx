import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { LoadingNotice } from '../../market/components/ApiFeedback';
import { marketApiClient } from '../../market/services/client';
import { productSelectionApiClient } from '../../product_selection/services/client';
import type { SelectionRepairContext } from '../services/selectionRepairContext';
import { WarrantAdminPageWithDelete } from './WarrantAdminPageWithDelete';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Same administration route and forms; only the incoming selection context is resolved here. */
export function WarrantAdminRoutePage() {
  const [params] = useSearchParams();
  const runId = params.get('selection_run_id');
  const warrantId = params.get('warrant_id');
  const key = `${runId ?? ''}:${warrantId ?? ''}`;
  const [state, setState] = useState<{
    key: string;
    context?: SelectionRepairContext;
    error?: string;
  } | null>(null);

  useEffect(() => {
    if (runId === null) return;
    if (!UUID.test(runId) || (warrantId !== null && !UUID.test(warrantId))) {
      setState({
        key,
        error: 'Ungültiger Produktauswahl-Kontext. Bitte den Bewertungslauf erneut öffnen.',
      });
      return;
    }
    const controller = new AbortController();
    setState({ key });
    void (async () => {
      try {
        const detail = await productSelectionApiClient.get(runId, controller.signal);
        if (detail.run.id.toLowerCase() !== runId.toLowerCase()) {
          throw new Error('Der geladene Bewertungslauf passt nicht zum Aufruf.');
        }
        if (
          warrantId &&
          ![...detail.evaluations, ...detail.universe_omissions].some(
            (item) => item.warrant_id.toLowerCase() === warrantId.toLowerCase(),
          )
        ) {
          throw new Error(
            'Produkt gehört nicht zu diesem Bewertungslauf. Es wird kein Ersatzprodukt geöffnet.',
          );
        }
        const underlying = await marketApiClient.getUnderlying(
          detail.run.underlying_id,
          controller.signal,
        );
        if (underlying.id !== detail.run.underlying_id)
          throw new Error('Basiswertkontext ist widersprüchlich.');
        if (!controller.signal.aborted)
          setState({
            key,
            context: {
              runId: detail.run.id,
              underlying,
              warrantId: warrantId?.toLowerCase(),
            },
          });
      } catch (error: unknown) {
        if (!controller.signal.aborted)
          setState({
            key,
            error:
              error instanceof Error
                ? error.message
                : 'Produktauswahl-Kontext konnte nicht geladen werden.',
          });
      }
    })();
    return () => controller.abort();
  }, [key, runId, warrantId]);

  if (runId === null) return <WarrantAdminPageWithDelete />;
  const returnUrl = UUID.test(runId)
    ? `/product-selection?${new URLSearchParams({ run_id: runId })}`
    : '/product-selection';
  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-amber-800 p-4 text-sm">
        <h2 className="font-semibold">Stammdaten für die Produktauswahl vervollständigen</h2>
        <p className="mt-2">
          {state?.key === key && state.context ? `${state.context.underlying.name}: ` : ''}
          Produktidentität, Handelsplatz und Handelswährung müssen belegt sein. Ein aktueller Kurs
          ist hier nicht erforderlich. Nach der Pflege zurückkehren und „Produkte neu bewerten“
          wählen. Das verändert weder den alten Lauf noch erzeugt es einen Kauf.
        </p>
        <Link to={returnUrl} className="mt-3 inline-block text-sky-300 underline">
          Zurück zur Produktauswahl
        </Link>
      </section>
      {state?.key !== key || (!state.context && !state.error) ? (
        <LoadingNotice label="Produktauswahl-Kontext wird geprüft …" />
      ) : state.error ? (
        <p role="alert" className="rounded-xl border border-rose-800 p-4 text-sm">
          {state.error}
        </p>
      ) : (
        <WarrantAdminPageWithDelete key={key} selectionContext={state.context} />
      )}
    </div>
  );
}
