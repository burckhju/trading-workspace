import { useCallback, useEffect, useLayoutEffect, useRef, useState, type FormEvent } from 'react';
import { MarketTransportError } from '../../market/services/http';
import type { TradingVenueResponse } from '../../market/types/api';
import { DISCARD_PRODUCT_DRAFT, type ProductFormGuard } from '../hooks/useProductNavigationGuard';
import { loadWarrantDetail, type WarrantDetailSnapshot } from '../services/adminContext';
import { warrantApiClient } from '../services/client';
import type { SelectionRepairContext } from '../services/selectionRepairContext';
import type { AddWarrantTermsRequest, WarrantResponse } from '../types/api';
import { WarrantIdentifierCorrection } from './WarrantIdentifierCorrection';
import { WarrantListingFields, type ListingFields } from './WarrantListingFields';
import { WarrantQuoteHistory } from './WarrantQuoteHistory';
import { WarrantTermsEditor, WarrantTermsValues } from './WarrantTermsEditor';
import { WarrantValuationEvidence } from './WarrantValuationEvidence';

type Editor = 'terms' | 'listing' | 'identifiers' | 'evidence' | null;
const EMPTY_LISTING: ListingFields = {
  trading_venue_id: '',
  symbol: '',
  quotation_currency_code: '',
};
const buttonClass = 'rounded border border-slate-700 px-3 py-2 text-sm disabled:opacity-50';

function failureMessage(cause: unknown) {
  return cause instanceof MarketTransportError
    ? 'Speichererfolg unklar. Bitte den gespeicherten Stand prüfen, bevor Sie erneut speichern. Die Eingaben bleiben erhalten.'
    : cause instanceof Error
      ? cause.message
      : 'Die Änderung konnte nicht gespeichert werden.';
}

export function WarrantProductDetail({
  product,
  selectionContext,
  venues,
  issuerName,
  underlyingName,
  onProductChanged,
  onDeleted,
  onGuardChange,
}: {
  product: WarrantResponse;
  selectionContext?: SelectionRepairContext;
  venues: TradingVenueResponse[];
  issuerName: string;
  underlyingName: string;
  onProductChanged: (value: WarrantResponse) => void;
  onDeleted: (value: WarrantResponse) => void;
  onGuardChange: (guard: ProductFormGuard) => void;
}) {
  const id = product.id;
  const [snapshot, setSnapshot] = useState<WarrantDetailSnapshot | null>(null);
  const [reading, setReading] = useState(true);
  const [readError, setReadError] = useState('');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [refreshRequired, setRefreshRequired] = useState(false);
  const [editor, setEditor] = useState<Editor>(null);
  const [editorRevision, setEditorRevision] = useState(0);
  const [listing, setListing] = useState({ ...EMPTY_LISTING });
  const [historicalId, setHistoricalId] = useState('');
  const [dirty, setDirty] = useState(false);
  const [ownBusy, setOwnBusy] = useState(false);
  const [childBusy, setChildBusy] = useState(false);
  const alive = useRef(true);
  const readController = useRef<AbortController | null>(null);
  const writing = useRef(false);
  const childWriting = useRef(false);
  const dirtyRef = useRef(false);
  const editorRegion = useRef<HTMLDivElement>(null);
  const trigger = useRef<Editor>(null);
  const busy = ownBusy || childBusy;
  const selected = snapshot?.warrant ?? product;
  const canAct = Boolean(snapshot) && !reading && !refreshRequired && !readError && !busy;

  const updateDirty = useCallback((value: boolean) => {
    dirtyRef.current = value;
    setDirty(value);
  }, []);
  const updateChildBusy = useCallback(
    (value: boolean) => {
      childWriting.current = value;
      setChildBusy(value);
      onGuardChange({ dirty: dirtyRef.current, busy: writing.current || value });
    },
    [onGuardChange],
  );

  useEffect(() => {
    onGuardChange({ dirty, busy });
  }, [dirty, busy, onGuardChange]);
  useEffect(() => {
    if (busy) return;
    if (editor)
      editorRegion.current
        ?.querySelector('[data-active-editor]')
        ?.querySelector<HTMLElement>(
          'input:not(:disabled), select:not(:disabled), textarea:not(:disabled), button:not(:disabled)',
        )
        ?.focus();
    else if (trigger.current)
      editorRegion.current
        ?.querySelector<HTMLButtonElement>(`[data-editor-trigger="${trigger.current}"]`)
        ?.focus();
  }, [editor, busy]);

  const refresh = useCallback(async () => {
    readController.current?.abort();
    const controller = new AbortController();
    readController.current = controller;
    setReading(true);
    try {
      const next = await loadWarrantDetail(id, selectionContext, controller.signal);
      if (!alive.current || controller.signal.aborted) return;
      setSnapshot(next);
      onProductChanged(next.warrant);
      setReadError('');
      setRefreshRequired(false);
    } catch (cause) {
      if (alive.current && !controller.signal.aborted) {
        setReadError(
          cause instanceof Error ? cause.message : 'Produktdetails konnten nicht geladen werden.',
        );
        throw cause;
      }
    } finally {
      if (alive.current && !controller.signal.aborted) setReading(false);
    }
  }, [id, selectionContext, onProductChanged]);

  useLayoutEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      readController.current?.abort();
    };
  }, []);

  useEffect(() => {
    void refresh().catch(() => undefined);
    return () => readController.current?.abort();
  }, [refresh]);

  function resetEditor() {
    setEditor(null);
    updateDirty(false);
    childWriting.current = false;
    setChildBusy(false);
    setActionError('');
  }

  function cancelEditor() {
    if (writing.current || childWriting.current) return;
    if (dirtyRef.current && !window.confirm(DISCARD_PRODUCT_DRAFT)) return;
    resetEditor();
  }

  function openEditor(next: Exclude<Editor, null>) {
    if (!canAct || editor || writing.current || childWriting.current) return;
    trigger.current = next;
    setListing({ ...EMPTY_LISTING });
    updateDirty(false);
    setActionError('');
    setEditorRevision((value) => value + 1);
    setEditor(next);
  }

  async function reload() {
    if (writing.current || childWriting.current) return;
    if (dirtyRef.current && !window.confirm(DISCARD_PRODUCT_DRAFT)) return;
    // Only a successful explicit read replaces an edit basis; a failed read preserves the draft.
    writing.current = true;
    setOwnBusy(true);
    onGuardChange({ dirty: dirtyRef.current, busy: true });
    try {
      await refresh();
      if (alive.current) resetEditor();
    } catch {
      // refresh renders the read error; no command was sent.
    } finally {
      writing.current = false;
      if (alive.current) setOwnBusy(false);
    }
  }

  async function confirmed(message: string) {
    resetEditor();
    setNotice(message);
    setRefreshRequired(true);
    try {
      await refresh();
    } catch {
      // A failed follow-up read cannot revoke a confirmed command.
      if (alive.current)
        setNotice(
          `${message} Die Anzeige konnte nicht aktualisiert werden. Nicht erneut speichern; Produkt neu laden.`,
        );
    }
  }

  async function command<T>(
    send: () => Promise<T>,
    message: string,
    apply?: (result: T) => void,
    localError = false,
  ) {
    if (writing.current || childWriting.current) return;
    writing.current = true;
    setOwnBusy(true);
    onGuardChange({ dirty: dirtyRef.current, busy: true });
    setActionError('');
    try {
      const result = await send();
      if (!alive.current) return;
      apply?.(result);
      await confirmed(message);
    } catch (cause) {
      if (alive.current && !localError) setActionError(failureMessage(cause));
      throw cause;
    } finally {
      writing.current = false;
      if (alive.current) setOwnBusy(false);
    }
  }

  async function saveTerms(productId: string, request: AddWarrantTermsRequest) {
    if (productId !== id) throw new Error('Der Bedingungsentwurf gehört zu einem anderen Produkt.');
    await command(
      () => warrantApiClient.addTerms(productId, request),
      'Produktbedingungen gespeichert. Eine neue Bedingungsversion wurde angelegt.',
      undefined,
      true,
    );
  }

  async function saveListing(event: FormEvent) {
    event.preventDefault();
    if (
      !venues.some((venue) => venue.id === listing.trading_venue_id) ||
      !/^[A-Z]{3}$/.test(listing.quotation_currency_code)
    ) {
      setActionError('Bitte Handelsplatz und Handelswährung dieses Optionsscheins angeben.');
      return;
    }
    try {
      await command(
        () =>
          warrantApiClient.addListing(id, { ...listing, symbol: listing.symbol.trim() || null }),
        'Notierung gespeichert. Bestehende Bewertungsläufe bleiben unverändert; Bewertung, Auswahl und Kauf bleiben ausdrückliche Schritte.',
      );
    } catch {
      /* The draft and command error remain visible. */
    }
  }

  function applyProduct(updated: WarrantResponse) {
    if (updated.id !== id)
      throw new Error(
        'Die Speicherantwort gehört nicht zum geöffneten Produkt. Bitte den gespeicherten Stand prüfen.',
      );
    setSnapshot((current) => (current ? { ...current, warrant: updated } : current));
    onProductChanged(updated);
  }

  async function toggleStatus() {
    if (!snapshot) return;
    const basis = snapshot.warrant;
    try {
      await command(
        () =>
          basis.lifecycle_status === 'ACTIVE'
            ? warrantApiClient.deactivate(id, basis.version)
            : warrantApiClient.reactivate(id, basis.version),
        basis.lifecycle_status === 'ACTIVE' ? 'Produkt deaktiviert.' : 'Produkt reaktiviert.',
        applyProduct,
      );
    } catch {
      /* Keep the server's protection error visible. */
    }
  }

  async function deleteProduct() {
    if (!snapshot || selectionContext || writing.current || childWriting.current) return;
    const basis = snapshot.warrant;
    if (
      !window.confirm(
        `Optionsschein „${basis.display_name}“ endgültig löschen? ISIN ${basis.isin ?? 'unbekannt'}, WKN ${basis.wkn ?? 'unbekannt'}, Produkt-ID ${basis.id}. Das ist nur möglich, solange keine historische oder operative Verwendung existiert.`,
      )
    )
      return;
    writing.current = true;
    setOwnBusy(true);
    onGuardChange({ dirty: false, busy: true });
    setActionError('');
    try {
      await warrantApiClient.delete(id, basis.version);
      if (alive.current) onDeleted(basis);
    } catch (cause) {
      if (alive.current) setActionError(failureMessage(cause));
    } finally {
      writing.current = false;
      if (alive.current) setOwnBusy(false);
    }
  }

  function identifiersSaved(updated: WarrantResponse) {
    if (!alive.current || updated.id !== id) return;
    writing.current = true;
    setOwnBusy(true);
    onGuardChange({ dirty: false, busy: true });
    applyProduct(updated);
    void confirmed(
      'Kennungen gespeichert. Kurszuordnungen müssen nun erneut geprüft werden.',
    ).finally(() => {
      writing.current = false;
      if (alive.current) setOwnBusy(false);
    });
  }

  const historical =
    snapshot?.terms.filter((item) => item.warrant_id === id && item.effective_to !== null) ?? [];
  const chosenHistory = historical.find((item) => item.id === historicalId);
  const currentTerms = snapshot?.currentTerms;
  return (
    <article
      aria-label={`Produktdetails ${selected.display_name}`}
      className="min-w-0 space-y-6 rounded-xl border border-slate-800 p-5"
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-slate-500">Ausgewähltes Produkt</p>
          <h2 className="mt-1 break-words text-xl font-medium">{selected.display_name}</h2>
          <p className="mt-1 break-words text-sm text-slate-400">
            {underlyingName} · {issuerName}
          </p>
        </div>
        <button type="button" disabled={busy} onClick={() => void reload()} className={buttonClass}>
          Produkt neu laden
        </button>
      </header>
      {reading && <p role="status">Produktdetails werden geladen …</p>}
      {notice && (
        <p role="status" className="rounded border border-sky-800 p-3 text-sm">
          {notice}
        </p>
      )}
      {readError && (
        <p role="alert" className="rounded border border-rose-800 p-3 text-sm">
          Anzeige konnte nicht aktualisiert werden: {readError}
          {snapshot
            ? ' Angezeigt wird der zuletzt geladene Stand. Ein vorhandener Entwurf bleibt an seine ursprüngliche Version gebunden.'
            : ''}
        </p>
      )}
      {actionError && (
        <p role="alert" className="rounded border border-rose-800 p-3 text-sm">
          {actionError}
        </p>
      )}
      {dirty && <p className="text-sm text-amber-300">Ungespeicherte Änderungen</p>}
      <div ref={editorRegion} className="space-y-6">
        <section
          data-active-editor={editor === 'identifiers' ? true : undefined}
          aria-label="Produktidentität und Status"
          className="space-y-3"
        >
          <h3 className="font-semibold">Produktidentität und Status</h3>
          {editor === 'identifiers' ? (
            <WarrantIdentifierCorrection
              key={editorRevision}
              embedded
              disabled={ownBusy || reading}
              warrant={selected}
              onSaved={identifiersSaved}
              onCancel={cancelEditor}
              onDirtyChange={updateDirty}
              onBusyChange={updateChildBusy}
              onReload={() => void reload()}
            />
          ) : (
            <>
              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-slate-400">ISIN</dt>
                  <dd>{selected.isin ?? 'Unbekannt'}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">WKN</dt>
                  <dd>{selected.wkn ?? 'Unbekannt'}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Status</dt>
                  <dd>{selected.lifecycle_status === 'ACTIVE' ? 'Aktiv' : 'Inaktiv'}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Produktversion</dt>
                  <dd>{selected.version}</dd>
                </div>
              </dl>
              <button
                type="button"
                disabled={!canAct || editor !== null}
                data-editor-trigger="identifiers"
                onClick={() => openEditor('identifiers')}
                className={buttonClass}
              >
                Kennungen korrigieren
              </button>
            </>
          )}
          <details className="text-sm text-slate-400">
            <summary className="cursor-pointer">Produktreferenz</summary>
            <p className="mt-2 break-all">Produkt-ID: {selected.id}</p>
          </details>
        </section>
        <section
          data-active-editor={editor === 'terms' ? true : undefined}
          aria-label="Aktuelle Produktbedingungen"
          className="space-y-3 border-t border-slate-800 pt-5"
        >
          <h3 className="font-semibold">Aktuelle Produktbedingungen</h3>
          {snapshot?.termsError && (
            <p role="alert" className="text-sm text-amber-300">
              {snapshot.termsError}
            </p>
          )}
          {editor === 'terms' && snapshot && currentTerms ? (
            <WarrantTermsEditor
              key={editorRevision}
              snapshot={{ ...snapshot, currentTerms }}
              onSave={saveTerms}
              onCancel={cancelEditor}
              onDirtyChange={updateDirty}
              busy={busy}
              onCompare={() => loadWarrantDetail(id, selectionContext)}
              onBasisChanged={(next) => {
                setSnapshot(next);
                onProductChanged(next.warrant);
                setReadError('');
                setRefreshRequired(false);
              }}
            />
          ) : (
            <>
              {currentTerms && <WarrantTermsValues terms={currentTerms} />}
              <button
                type="button"
                disabled={!canAct || !currentTerms || editor !== null}
                data-editor-trigger="terms"
                onClick={() => openEditor('terms')}
                className={buttonClass}
              >
                Produktbedingungen ändern
              </button>
            </>
          )}
        </section>
        <section
          data-active-editor={editor === 'listing' ? true : undefined}
          aria-label="Handelbare Notierungen"
          className="space-y-3 border-t border-slate-800 pt-5"
        >
          <h3 className="font-semibold">Handelbare Notierungen</h3>
          <p className="text-sm text-slate-400">
            Handelsplatz und Handelswährung gehören zu dieser Notierung. Ein aktueller Kurs ist zur
            Stammdatenpflege nicht erforderlich.
          </p>
          {editor === 'listing' ? (
            <form
              aria-label="Notierung hinzufügen"
              onSubmit={(event) => void saveListing(event)}
              className="space-y-3"
            >
              <fieldset disabled={busy} className="min-w-0">
                <WarrantListingFields
                  value={listing}
                  venues={venues}
                  onChange={(next) => {
                    setListing(next);
                    updateDirty(JSON.stringify(next) !== JSON.stringify(EMPTY_LISTING));
                  }}
                />
              </fieldset>
              <div className="flex flex-wrap gap-3">
                <button disabled={busy} className="rounded bg-sky-800 px-3 py-2 text-sm">
                  Notierung speichern
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={cancelEditor}
                  className={buttonClass}
                >
                  Notierung abbrechen
                </button>
              </div>
            </form>
          ) : (
            <>
              {snapshot?.listings.map((item) => (
                <div key={item.id} className="rounded border border-slate-800 p-3 text-sm">
                  <strong>{item.symbol ?? 'Ohne Börsensymbol'}</strong>
                  <p className="mt-1 text-slate-400">
                    {venues.find((venue) => venue.id === item.trading_venue_id)?.name ??
                      item.trading_venue_id}{' '}
                    · {item.quotation_currency_code} ·{' '}
                    {item.lifecycle_status === 'ACTIVE' ? 'Aktiv' : 'Inaktiv'}
                  </p>
                </div>
              ))}
              {snapshot?.listings.length === 0 && (
                <p className="text-sm text-slate-400">
                  Noch keine Notierung hinterlegt. Für die Produktauswahl werden ein belegter
                  Handelsplatz und die Handelswährung benötigt, kein aktueller Kurs.
                </p>
              )}
              <button
                type="button"
                disabled={!canAct || editor !== null}
                data-editor-trigger="listing"
                onClick={() => openEditor('listing')}
                className={buttonClass}
              >
                Notierung hinzufügen
              </button>
            </>
          )}
        </section>
        <section
          data-active-editor={editor === 'evidence' ? true : undefined}
          aria-label="Bewertungsbelege und Kursverlauf"
          className="space-y-3 border-t border-slate-800 pt-5"
        >
          <h3 className="font-semibold">Bewertungsbelege und Kursverlauf</h3>
          {editor === 'evidence' && currentTerms ? (
            <WarrantValuationEvidence
              key={editorRevision}
              embedded
              disabled={ownBusy || reading}
              warrant={selected}
              terms={currentTerms}
              onCancel={cancelEditor}
              onDirtyChange={updateDirty}
              onBusyChange={updateChildBusy}
              onReload={() => void reload()}
            />
          ) : (
            <button
              type="button"
              disabled={!canAct || !currentTerms || editor !== null}
              data-editor-trigger="evidence"
              onClick={() => openEditor('evidence')}
              className={buttonClass}
            >
              Produktmerkmale für IV mit Beleg erfassen
            </button>
          )}
          <WarrantQuoteHistory warrantId={id} />
        </section>
      </div>
      <details className="space-y-3 rounded border border-slate-700 p-3">
        <summary className="cursor-pointer font-semibold">Änderungshistorie</summary>
        <p className="text-sm text-slate-400">
          Frühere Bedingungsversionen bleiben unverändert. Historische Bewertungen behalten ihre
          genaue Produkt-, Bedingungs- und Notierungsreferenz.
        </p>
        {historical.length ? (
          <>
            <label className="block text-sm">
              Historische Bedingungsversion
              <select
                value={historicalId}
                onChange={(event) => setHistoricalId(event.target.value)}
                className="mt-1 w-full min-w-0 rounded border border-slate-700 bg-slate-950 p-2"
              >
                <option value="">Historische Version wählen</option>
                {historical.map((item) => (
                  <option key={item.id} value={item.id}>
                    Version {item.version_no} · gültig bis{' '}
                    {new Date(item.effective_to!).toLocaleString('de-DE')}
                  </option>
                ))}
              </select>
            </label>
            {chosenHistory && (
              <section
                aria-label="Historische Produktbedingungen"
                className="space-y-3 rounded border border-amber-900 p-3"
              >
                <h4 className="font-medium">Historisch · Version {chosenHistory.version_no}</h4>
                <WarrantTermsValues terms={chosenHistory} />
              </section>
            )}
          </>
        ) : (
          <p className="text-sm text-slate-400">Keine früheren Bedingungsversionen vorhanden.</p>
        )}
      </details>
      <details className="space-y-3 rounded border border-slate-700 p-3">
        <summary className="cursor-pointer font-semibold">Weitere Aktionen</summary>
        <p className="text-sm text-slate-400">
          Die Aktionen gelten für das oben geöffnete Produkt. Deaktivieren erhält die Historie.
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={!canAct || editor !== null}
            onClick={() => void toggleStatus()}
            className={buttonClass}
          >
            {selected.lifecycle_status === 'ACTIVE' ? 'Deaktivieren' : 'Reaktivieren'}
          </button>
          {!selectionContext && (
            <button
              type="button"
              disabled={!canAct || editor !== null}
              onClick={() => void deleteProduct()}
              className="rounded border border-rose-800 px-3 py-2 text-sm text-rose-200 disabled:opacity-50"
            >
              Endgültig löschen
            </button>
          )}
        </div>
        {!selectionContext && (
          <p className="text-sm text-slate-400">
            Löschen ist nur für unbenutzte Produkte möglich. Historische und operative Verwendungen
            bleiben geschützt.
          </p>
        )}
      </details>
    </article>
  );
}
