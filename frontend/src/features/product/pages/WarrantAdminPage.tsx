import { useCallback, useEffect, useRef, useState } from 'react';
import { marketApiClient } from '../../market/services/client';
import type {
  IssuerResponse,
  TradingVenueResponse,
  UnderlyingSummaryResponse,
} from '../../market/types/api';
import { WarrantCreateForm } from '../components/WarrantCreateForm';
import { WarrantProductDetail } from '../components/WarrantProductDetail';
import {
  DISCARD_PRODUCT_DRAFT,
  ProductNavigationGuard,
  type ProductFormGuard,
} from '../hooks/useProductNavigationGuard';
import { warrantApiClient } from '../services/client';
import type { SelectionRepairContext } from '../services/selectionRepairContext';
import type { WarrantResponse } from '../types/api';

type View =
  | { kind: 'catalogue' }
  | { kind: 'create'; sequence: number }
  | { kind: 'product'; product: WarrantResponse };
const CLEAN: ProductFormGuard = { dirty: false, busy: false };

export function WarrantAdminPage({
  selectionContext,
}: { selectionContext?: SelectionRepairContext } = {}) {
  const [warrants, setWarrants] = useState<WarrantResponse[]>([]);
  const [issuers, setIssuers] = useState<IssuerResponse[]>([]);
  const [underlyings, setUnderlyings] = useState<UnderlyingSummaryResponse[]>(
    selectionContext ? [selectionContext.underlying] : [],
  );
  const [venues, setVenues] = useState<TradingVenueResponse[]>([]);
  const [view, setView] = useState<View>({ kind: 'catalogue' });
  const [guard, setGuard] = useState(CLEAN);
  const [loading, setLoading] = useState(true);
  const [catalogueError, setCatalogueError] = useState('');
  const [referenceError, setReferenceError] = useState('');
  const [notice, setNotice] = useState('');
  const [query, setQuery] = useState('');
  const catalogueController = useRef<AbortController | null>(null);
  const guardRef = useRef(CLEAN);
  const returnView = useRef<View>({ kind: 'catalogue' });
  const sequence = useRef(0);
  const viewKey =
    view.kind === 'product'
      ? view.product.id
      : view.kind === 'create'
        ? `create-${view.sequence}`
        : 'catalogue';
  const currentViewKey = useRef(viewKey);
  currentViewKey.current = viewKey;

  const reportGuard = useCallback(
    (next: ProductFormGuard) => {
      if (currentViewKey.current !== viewKey) return;
      guardRef.current = next;
      setGuard(next);
    },
    [viewKey],
  );

  const refreshCatalogue = useCallback(
    async (initial = false, scopeKey?: string) => {
      catalogueController.current?.abort();
      const controller = new AbortController();
      catalogueController.current = controller;
      setLoading(true);
      try {
        const all = await warrantApiClient.list(controller.signal);
        if (controller.signal.aborted || (scopeKey && currentViewKey.current !== scopeKey)) return;
        const filtered = selectionContext
          ? all.filter(
              (item) =>
                item.underlying_id === selectionContext.underlying.id &&
                (!selectionContext.warrantId || item.id === selectionContext.warrantId),
            )
          : all;
        if (selectionContext?.warrantId && filtered.length !== 1) {
          throw new Error(
            'Das angeforderte Produkt ist im passenden Basiswertkontext nicht verfügbar. Keine automatische Ersatzauswahl.',
          );
        }
        setWarrants(filtered);
        setCatalogueError('');
        if (initial)
          setView((current) =>
            current.kind === 'catalogue' && filtered[0]
              ? { kind: 'product', product: filtered[0] }
              : current,
          );
      } catch (cause) {
        if (!controller.signal.aborted && (!scopeKey || currentViewKey.current === scopeKey)) {
          setCatalogueError(
            cause instanceof Error ? cause.message : 'Optionsscheine konnten nicht geladen werden.',
          );
          throw cause;
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    },
    [selectionContext],
  );

  useEffect(() => {
    const controller = new AbortController();
    const failed = () => {
      if (!controller.signal.aborted)
        setReferenceError(
          'Referenzdaten konnten nicht vollständig geladen werden. Bitte Seite neu laden; vorhandene Eingaben bleiben erhalten.',
        );
    };
    void marketApiClient
      .listIssuers(controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) setIssuers(response.items);
      })
      .catch(failed);
    void marketApiClient
      .searchUnderlyings({ lifecycleStatus: 'ACTIVE', limit: 100 }, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;
        setUnderlyings(
          selectionContext &&
            !response.items.some((item) => item.id === selectionContext.underlying.id)
            ? [...response.items, selectionContext.underlying]
            : response.items,
        );
      })
      .catch(failed);
    void marketApiClient
      .listTradingVenues(controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) setVenues(response.items);
      })
      .catch(failed);
    void refreshCatalogue(true).catch(() => undefined);
    return () => {
      controller.abort();
      catalogueController.current?.abort();
    };
  }, [selectionContext, refreshCatalogue]);

  function switchView(next: View) {
    if (guardRef.current.busy) return false;
    if (guardRef.current.dirty && !window.confirm(DISCARD_PRODUCT_DRAFT)) return false;
    guardRef.current = CLEAN;
    setGuard(CLEAN);
    setNotice('');
    currentViewKey.current =
      next.kind === 'product'
        ? next.product.id
        : next.kind === 'create'
          ? `create-${next.sequence}`
          : 'catalogue';
    setView(next);
    return true;
  }

  function startProduct() {
    const previous = view;
    if (switchView({ kind: 'create', sequence: ++sequence.current })) returnView.current = previous;
  }

  const updateProduct = useCallback((updated: WarrantResponse) => {
    setWarrants((items) =>
      items.some((item) => item.id === updated.id)
        ? items.map((item) => (item.id === updated.id ? updated : item))
        : [...items, updated],
    );
  }, []);

  function productCreated(created: WarrantResponse) {
    if (currentViewKey.current !== viewKey) return;
    updateProduct(created);
    guardRef.current = CLEAN;
    setGuard(CLEAN);
    setNotice(
      'Optionsschein und Notierung gespeichert. Ein Kauf wurde noch nicht erfasst. Bestehende Bewertungsläufe bleiben unverändert.',
    );
    currentViewKey.current = created.id;
    setView({ kind: 'product', product: created });
    // Read-only reconciliation never selects another product or retries the confirmed POST.
    void refreshCatalogue(false, created.id).catch(() => {
      if (currentViewKey.current === created.id)
        setNotice(
          'Optionsschein und Notierung sind bereits gespeichert. Die Anzeige konnte nicht aktualisiert werden. Nicht erneut anlegen; Produkt neu laden.',
        );
    });
  }

  const productDeleted = useCallback((deleted: WarrantResponse) => {
    if (currentViewKey.current !== deleted.id) return;
    currentViewKey.current = 'catalogue';
    setWarrants((items) => items.filter((item) => item.id !== deleted.id));
    setView((current) =>
      current.kind === 'product' && current.product.id === deleted.id
        ? { kind: 'catalogue' }
        : current,
    );
    guardRef.current = CLEAN;
    setGuard(CLEAN);
    setNotice(`Optionsschein „${deleted.display_name}“ wurde gelöscht.`);
  }, []);

  const issuerName = (id: string) => issuers.find((item) => item.id === id)?.display_name ?? id;
  const underlyingName = (id: string) => underlyings.find((item) => item.id === id)?.name ?? id;
  const visible = warrants.filter((item) =>
    `${item.display_name} ${item.isin ?? ''} ${item.wkn ?? ''} ${issuerName(item.issuer_id)} ${underlyingName(item.underlying_id)}`
      .toLocaleLowerCase('de-DE')
      .includes(query.toLocaleLowerCase('de-DE').trim()),
  );

  return (
    <div className="w-full min-w-0 space-y-6">
      <ProductNavigationGuard {...guard} />
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Administration · FT-004</p>
          <h1 className="mt-1 text-2xl font-semibold">Optionsscheine</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">
            Produkt im Katalog auswählen und seine Stammdaten prüfen. Änderungen und historische
            Bedingungen sind beim geöffneten Produkt erreichbar.
          </p>
        </div>
        {!selectionContext?.warrantId && view.kind !== 'create' && (
          <button
            type="button"
            disabled={guard.busy}
            onClick={startProduct}
            className="rounded bg-sky-800 px-4 py-2 text-sm disabled:opacity-50"
          >
            Neues Produkt
          </button>
        )}
      </header>
      {referenceError && (
        <p role="alert" className="rounded border border-amber-800 p-3 text-sm">
          {referenceError}
        </p>
      )}
      {catalogueError && (
        <p role="alert" className="rounded border border-rose-800 p-3 text-sm">
          {catalogueError}
        </p>
      )}
      {notice && (
        <p role="status" className="rounded border border-sky-800 p-3 text-sm">
          {notice}
        </p>
      )}
      <div
        className={
          selectionContext?.warrantId
            ? 'min-w-0'
            : 'grid min-w-0 items-start gap-6 lg:grid-cols-[minmax(15rem,0.75fr)_minmax(0,2fr)]'
        }
      >
        {!selectionContext?.warrantId && (
          <section
            aria-label="Produktkatalog"
            className="min-w-0 rounded-xl border border-slate-800"
          >
            <div className="space-y-3 border-b border-slate-800 p-4">
              <h2 className="font-semibold">Vorhandene Produkte</h2>
              <label className="block text-sm">
                Produkte suchen
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="mt-1 w-full min-w-0 rounded border border-slate-700 bg-slate-950 p-2"
                  placeholder="Name, ISIN oder WKN"
                />
              </label>
              <button
                type="button"
                disabled={loading || guard.busy}
                onClick={() => void refreshCatalogue().catch(() => undefined)}
                className="text-sm text-sky-300 underline disabled:opacity-50"
              >
                Katalog neu laden
              </button>
            </div>
            {loading && (
              <p role="status" className="p-4 text-sm">
                Produktkatalog wird geladen …
              </p>
            )}
            <div className="max-h-80 divide-y divide-slate-800 overflow-y-auto lg:max-h-[70vh]">
              {visible.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  aria-pressed={view.kind === 'product' && view.product.id === item.id}
                  disabled={guard.busy}
                  onClick={() => {
                    if (view.kind !== 'product' || view.product.id !== item.id)
                      switchView({ kind: 'product', product: item });
                  }}
                  className={`block w-full min-w-0 break-words px-4 py-3 text-left disabled:opacity-50 ${view.kind === 'product' && view.product.id === item.id ? 'bg-slate-900 ring-1 ring-inset ring-sky-800' : ''}`}
                >
                  <span className="block font-medium">{item.display_name}</span>
                  <span className="mt-1 block text-xs text-slate-400">
                    {underlyingName(item.underlying_id)} · {issuerName(item.issuer_id)}
                  </span>
                  <span className="mt-1 block text-xs text-slate-400">
                    {item.isin ? `ISIN ${item.isin}` : 'keine ISIN'} ·{' '}
                    {item.wkn ? `WKN ${item.wkn}` : 'keine WKN'} ·{' '}
                    {item.lifecycle_status === 'ACTIVE' ? 'Aktiv' : 'Inaktiv'}
                  </span>
                </button>
              ))}
              {!loading && visible.length === 0 && (
                <p className="p-4 text-sm text-slate-400">
                  {warrants.length
                    ? 'Keine passenden Produkte gefunden.'
                    : 'Keine Optionsscheine vorhanden.'}
                </p>
              )}
            </div>
          </section>
        )}
        {view.kind === 'create' ? (
          <WarrantCreateForm
            key={viewKey}
            issuers={issuers}
            underlyings={underlyings}
            venues={venues}
            selectionContext={selectionContext}
            onCreated={productCreated}
            onCancel={() => {
              switchView(returnView.current);
            }}
            onGuardChange={reportGuard}
          />
        ) : view.kind === 'product' ? (
          <WarrantProductDetail
            key={view.product.id}
            product={view.product}
            selectionContext={selectionContext}
            venues={venues}
            issuerName={issuerName(view.product.issuer_id)}
            underlyingName={underlyingName(view.product.underlying_id)}
            onProductChanged={updateProduct}
            onDeleted={productDeleted}
            onGuardChange={reportGuard}
          />
        ) : (
          !loading &&
          !catalogueError && (
            <p className="rounded-xl border border-slate-800 p-5 text-sm text-slate-400">
              Wählen Sie ein Produkt aus dem Katalog oder beginnen Sie mit „Neues Produkt“.
            </p>
          )
        )}
      </div>
    </div>
  );
}
