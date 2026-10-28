import { useEffect, useRef, useState } from 'react';
import { marketApiClient } from '../../market/services/client';
import { MarketApiError } from '../../market/services/http';
import type { TradingVenueResponse } from '../../market/types/api';
import { captureRequest, finishCapture } from '../../trade/services/capture';
import { currencyEvidenceApi } from '../services/currencyEvidence';
import { historicalCurrencyDayWindow } from '../services/historicalCurrencyDates';
import type {
  CurrencyEvidence,
  CurrencyEvidenceFacts,
  CurrencyEvidenceRequest,
} from '../types/currencyEvidence';

interface Pending {
  dirty: boolean;
  busy: boolean;
  writeBlocked?: boolean;
}
interface Props {
  productId: string;
  execution?: { tradeId: string; executionId: string };
  venues?: TradingVenueResponse[];
  disabled?: boolean;
  readDisabled?: boolean;
  isWriteBlocked?: () => boolean;
  onPendingChange?: (state: Pending) => void;
  onChanged?: () => Promise<void>;
  onCancel?: () => void;
}
const inputClass = 'mt-1 w-full min-w-0 rounded border border-slate-700 bg-slate-950 p-2';
const buttonClass = 'rounded border border-slate-700 px-3 py-2 text-sm disabled:opacity-50';

function blank(execution: Props['execution']): CurrencyEvidenceFacts {
  return {
    kind: execution ? 'EXECUTION_DOCUMENT' : 'HISTORICAL_LISTINGS',
    source_reference: '',
    supersedes_evidence_id: null,
    revoked: false,
    trade_id: execution?.tradeId ?? null,
    execution_id: execution?.executionId ?? null,
    currency_code: null,
    trading_venue_id: null,
    valid_from: null,
    valid_to: null,
    listings: execution ? [] : [{ trading_venue_id: '', currency_code: null }],
    complete_listing_set: false,
  };
}

function factsFrom(source: CurrencyEvidence, revoked: boolean): CurrencyEvidenceFacts {
  return {
    kind: source.kind,
    source_reference: source.source_reference,
    supersedes_evidence_id: source.id,
    revoked,
    trade_id: source.trade_id,
    execution_id: source.execution_id,
    currency_code: source.currency_code,
    trading_venue_id: source.trading_venue_id,
    valid_from: source.valid_from,
    valid_to: source.valid_to,
    listings: source.listings.map((listing) => ({ ...listing })),
    complete_listing_set: source.complete_listing_set,
  };
}

function validate(facts: CurrencyEvidenceFacts): string | null {
  if (facts.source_reference.trim().length < 3) return 'Bitte Quelle und Fundstelle angeben.';
  if (facts.kind === 'EXECUTION_DOCUMENT') {
    if (!facts.currency_code && !facts.trading_venue_id)
      return 'Der Beleg muss eine Ausführungswährung oder einen eindeutigen Handelsplatz nennen.';
    if (facts.currency_code && !/^[A-Z]{3}$/.test(facts.currency_code))
      return 'Bitte den dreistelligen Währungscode aus dem Beleg verwenden.';
  } else {
    const withZone = /T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/;
    if (
      !facts.valid_from ||
      !facts.valid_to ||
      !withZone.test(facts.valid_from) ||
      !withZone.test(facts.valid_to) ||
      !Number.isFinite(Date.parse(facts.valid_from)) ||
      !Number.isFinite(Date.parse(facts.valid_to)) ||
      Date.parse(facts.valid_to) <= Date.parse(facts.valid_from)
    )
      return 'Bitte ein gültiges Zeitfenster mit ausdrücklicher Zeitzone angeben; das Ende ist ausgeschlossen.';
    if (
      !facts.listings.length ||
      facts.listings.some(
        (item) =>
          !item.trading_venue_id ||
          (item.currency_code !== null && !/^[A-Z]{3}$/.test(item.currency_code)),
      )
    )
      return 'Bitte die belegten Handelsplätze und Währungen prüfen; eine fehlende Währung bleibt unbekannt.';
    if (new Set(facts.listings.map((item) => item.trading_venue_id)).size !== facts.listings.length)
      return 'Jeder Handelsplatz darf pro Quelle nur einmal vorkommen.';
  }
  return null;
}

/** Each source is reviewed once; current product listings are never used as historical defaults. */
export function CurrencyEvidenceEditor(props: Props) {
  return (
    <CurrencyEvidenceContext
      key={`${props.productId}:${props.execution?.tradeId ?? ''}:${props.execution?.executionId ?? ''}`}
      {...props}
    />
  );
}

function CurrencyEvidenceContext({
  productId,
  execution,
  venues,
  disabled = false,
  readDisabled = false,
  isWriteBlocked,
  onPendingChange,
  onChanged,
  onCancel,
}: Props) {
  const [history, setHistory] = useState<CurrencyEvidence[] | null>(null);
  const [choices, setChoices] = useState(venues ?? []);
  const [draft, setDraft] = useState(() => blank(execution));
  const [exactTimes, setExactTimes] = useState(false);
  const [days, setDays] = useState({ from: '', through: '' });
  const [dayError, setDayError] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [pending, setPending] = useState<Pending>({ dirty: false, busy: false });
  const [retry, setRetry] = useState<CurrencyEvidenceRequest | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const state = useRef(pending);
  const active = useRef<AbortController | null>(null);
  const alive = useRef(true);
  const refreshRequired = useRef(false);
  const callbacks = useRef({ onPendingChange, onChanged });
  callbacks.current = { onPendingChange, onChanged };
  const scope = `currency-evidence:${productId}:${execution?.executionId ?? 'listings'}`;
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      active.current?.abort();
    };
  }, []);

  function publish(next: Pending) {
    state.current = next;
    setPending(next);
    callbacks.current.onPendingChange?.(next);
  }
  function change(next: CurrencyEvidenceFacts) {
    if (state.current.busy || state.current.writeBlocked || disabled) return;
    setDraft(next);
    setConfirmed(false);
    setMessage('');
    publish({ ...state.current, dirty: true });
  }
  function changeDays(next: typeof days) {
    if (state.current.busy || state.current.writeBlocked || disabled) return;
    setDays(next);
    setDayError('');
    let interval = { valid_from: null as string | null, valid_to: null as string | null };
    if (next.from && next.through) {
      try {
        interval = historicalCurrencyDayWindow(next.from, next.through);
      } catch (cause) {
        setDayError(
          cause instanceof Error ? cause.message : 'Gültigkeitszeitraum nicht verwendbar.',
        );
      }
    }
    change({ ...draft, ...interval });
  }
  function revise(entry: CurrencyEvidence, revoked: boolean) {
    setExactTimes(true);
    setDayError('');
    change(factsFrom(entry, revoked));
  }
  function resetDraft() {
    setDraft(blank(execution));
    setExactTimes(false);
    setDays({ from: '', through: '' });
    setDayError('');
    setConfirmed(false);
  }
  function inScope(entry: CurrencyEvidence) {
    return (
      entry.product_id === productId &&
      (execution
        ? entry.kind === 'EXECUTION_DOCUMENT' &&
          entry.trade_id === execution.tradeId &&
          entry.execution_id === execution.executionId
        : entry.kind === 'HISTORICAL_LISTINGS')
    );
  }
  async function read() {
    if (state.current.busy || readDisabled) return;
    if (
      !retry &&
      state.current.dirty &&
      !window.confirm(
        'Ungespeicherte Quellenangaben verwerfen und die gespeicherte Herkunft neu laden?',
      )
    )
      return;
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    publish({ ...state.current, busy: true, writeBlocked: true });
    setError('');
    try {
      const [response, availableVenues] = await Promise.all([
        currencyEvidenceApi.history(productId, controller.signal),
        venues
          ? Promise.resolve(venues)
          : marketApiClient.listTradingVenues(controller.signal).then((value) => value.items),
      ]);
      if (!alive.current || controller.signal.aborted) return;
      if (response.history.some((entry) => entry.product_id !== productId))
        throw new Error('Die gelesenen Quellen gehören zu einem anderen Produkt.');
      setHistory(response.history.filter(inScope));
      setChoices(availableVenues);
      if (retry) {
        const receipt = response.history.find((entry) => entry.request_id === retry.request_id);
        if (!receipt) {
          setError(
            'Der Quellenauftrag ist noch nicht abschließend geklärt. Ein fehlender Eintrag beim Lesen beweist nicht, dass die Speicherung ausgeblieben ist. Nur denselben Auftrag erneut senden oder die Quellen später erneut laden.',
          );
          publish({ dirty: true, busy: true, writeBlocked: true });
          return;
        }
        if (!inScope(receipt))
          throw new Error('Der gelesene Quellenauftrag gehört nicht zu dieser Buchung.');
        finishCapture(scope);
      }
      resetDraft();
      setRetry(null);
      publish({ dirty: false, busy: true, writeBlocked: true });
      if (retry || refreshRequired.current) {
        const receipt =
          retry && response.history.find((entry) => entry.request_id === retry.request_id);
        setMessage(
          receipt
            ? 'Die Speicherung ist durch die gelesene Quellenversion bestätigt.'
            : 'Quellenstand neu gelesen. Angaben vor einem neuen Speichern prüfen.',
        );
        await callbacks.current.onChanged?.();
        if (!alive.current || controller.signal.aborted) return;
        refreshRequired.current = false;
      }
      publish({ dirty: false, busy: true, writeBlocked: false });
    } catch (cause) {
      if (alive.current && !controller.signal.aborted)
        setError(
          cause instanceof Error ? cause.message : 'Währungsquellen konnten nicht gelesen werden.',
        );
      if (alive.current && !controller.signal.aborted && !retry && !refreshRequired.current)
        publish({ ...state.current, writeBlocked: false });
    } finally {
      if (alive.current && !controller.signal.aborted) publish({ ...state.current, busy: false });
    }
  }
  async function save() {
    if (
      state.current.busy ||
      disabled ||
      isWriteBlocked?.() ||
      !history ||
      (!retry && (!confirmed || state.current.writeBlocked))
    )
      return;
    const problem = validate(draft);
    if (problem) {
      setError(problem);
      return;
    }
    const request = retry ?? {
      ...draft,
      source_reference: draft.source_reference.trim(),
      confirmation: 'CONFIRM_SOURCE_REVIEW' as const,
      request_id: captureRequest(scope, draft),
    };
    const controller = new AbortController();
    active.current?.abort();
    active.current = controller;
    publish({ ...state.current, busy: true });
    setError('');
    setMessage('');
    let receiptReceived = false;
    try {
      const receipt = await currencyEvidenceApi.record(productId, request, controller.signal);
      if (!alive.current || controller.signal.aborted) return;
      if (!inScope(receipt) || receipt.request_id !== request.request_id)
        throw new Error('Die Speicherantwort gehört nicht zum gesendeten Quellenauftrag.');
      receiptReceived = true;
      finishCapture(scope);
      setHistory((previous) => [
        ...(previous ?? []).filter((entry) => entry.id !== receipt.id),
        receipt,
      ]);
      resetDraft();
      setRetry(null);
      publish({ dirty: false, busy: true, writeBlocked: false });
      setMessage(
        request.revoked
          ? 'Quelle widerrufen. Betroffene Zuordnungen werden beim nächsten Lesen neu bewertet.'
          : 'Quellenversion gespeichert. Passende Buchungen verwenden diese Herkunft automatisch beim nächsten Lesen.',
      );
      refreshRequired.current = true;
      await callbacks.current.onChanged?.();
      if (alive.current && !controller.signal.aborted) refreshRequired.current = false;
    } catch (cause) {
      if (!alive.current || controller.signal.aborted) return;
      if (receiptReceived) {
        setError(
          'Quelle gespeichert; der Buchungsstand konnte noch nicht neu gelesen werden. Währungsquellen neu laden, um Quelle und Buchungsstand erneut zu prüfen.',
        );
        publish({ dirty: false, busy: true, writeBlocked: true });
      } else {
        const conflict = cause instanceof MarketApiError && cause.status === 409;
        const uncertain = !(cause instanceof MarketApiError) || cause.status >= 500;
        if (uncertain) {
          setRetry(request);
          refreshRequired.current = true;
        } else {
          setRetry(null);
          if (conflict) refreshRequired.current = true;
        }
        publish({ ...state.current, writeBlocked: conflict || uncertain });
        setError(
          (cause instanceof Error ? cause.message : 'Quelle nicht gespeichert.') +
            (conflict
              ? ' Quellen wurden inzwischen geändert. Bitte neu laden und die Korrektur erneut prüfen.'
              : uncertain
                ? ' Speichererfolg unklar. Nur denselben Auftrag erneut senden oder die Quellen neu laden.'
                : ''),
        );
      }
    } finally {
      if (alive.current && !controller.signal.aborted) publish({ ...state.current, busy: false });
    }
  }
  const superseded = new Set(history?.map((entry) => entry.supersedes_evidence_id));
  const locked = pending.busy || disabled || Boolean(pending.writeBlocked);
  const venueSelect = (value: string, setValue: (value: string) => void, label: string) => (
    <label className="block text-sm">
      {label}
      <select
        className={inputClass}
        value={value}
        onChange={(event) => setValue(event.target.value)}
      >
        <option value="">Nicht belegt</option>
        {value && !choices.some((choice) => choice.id === value) && (
          <option value={value}>{value}</option>
        )}
        {choices.map((venue) => (
          <option key={venue.id} value={venue.id}>
            {venue.name} ({venue.mic})
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <section
      aria-label={execution ? 'Ausführungsbeleg zuordnen' : 'Historische Währungsquellen'}
      className="space-y-3"
    >
      <p className="text-sm text-slate-400">
        {execution
          ? 'Der Beleg wird genau dieser Buchung zugeordnet. Währung und Handelsplatz nur aus dem geprüften Ausführungsbeleg übernehmen.'
          : 'Eine historische Quelle einmal erfassen und für passende Käufe und Verkäufe wiederverwenden. Heutige Notierungen beweisen keine frühere Ausführungswährung.'}
      </p>
      <button
        type="button"
        disabled={pending.busy || readDisabled}
        onClick={() => void read()}
        className={buttonClass}
      >
        Währungsquellen laden
      </button>
      {pending.busy && <p role="status">Währungsquellen werden verarbeitet…</p>}
      {error && (
        <p role="alert" className="text-sm text-amber-300">
          {error}
        </p>
      )}
      {message && (
        <p role="status" className="text-sm">
          {message}
        </p>
      )}
      {history && (
        <>
          <div className="space-y-2" aria-label="Gespeicherte Währungsquellen">
            {!history.length && (
              <p className="text-sm">Noch keine passende historische Quelle gespeichert.</p>
            )}
            {history.map((entry) => (
              <div key={entry.id} className="space-y-2 rounded border border-slate-700 p-3 text-sm">
                <p className="break-words">
                  {entry.source_reference} ·{' '}
                  {superseded.has(entry.id)
                    ? 'ersetzt'
                    : entry.revoked
                      ? 'widerrufen'
                      : 'aktuelle Quellenversion'}
                </p>
                {entry.kind === 'HISTORICAL_LISTINGS' ? (
                  <>
                    <p>
                      Gültig von {entry.valid_from} bis ausschließlich {entry.valid_to}
                    </p>
                    <p>
                      {entry.listings
                        .map(
                          (listing) =>
                            `${choices.find((venue) => venue.id === listing.trading_venue_id)?.name ?? listing.trading_venue_id}: ${listing.currency_code ?? 'Währung unbekannt'}`,
                        )
                        .join(' · ')}
                    </p>
                    <p>
                      {entry.complete_listing_set
                        ? 'Vollständiger relevanter historischer Umfang geprüft'
                        : 'Vollständiger historischer Umfang nicht belegt'}
                    </p>
                  </>
                ) : (
                  <p>
                    Ausführungswährung {entry.currency_code ?? 'unbekannt'} · Handelsplatz{' '}
                    {choices.find((venue) => venue.id === entry.trading_venue_id)?.name ??
                      entry.trading_venue_id ??
                      'unbekannt'}
                  </p>
                )}
                <details>
                  <summary className="cursor-pointer">Quellenversion und Erfassung</summary>
                  <p className="break-all">
                    {entry.id} · erfasst {entry.recorded_at} · {entry.verification}
                  </p>
                  {entry.supersedes_evidence_id && (
                    <p className="break-all">Ersetzt {entry.supersedes_evidence_id}</p>
                  )}
                </details>
                {!superseded.has(entry.id) && !entry.revoked && (
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className={buttonClass}
                      disabled={locked || pending.dirty}
                      onClick={() => revise(entry, false)}
                    >
                      Quelle korrigieren
                    </button>
                    <button
                      type="button"
                      className={buttonClass}
                      disabled={locked || pending.dirty}
                      onClick={() => revise(entry, true)}
                    >
                      Widerruf vorbereiten
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
          <form
            aria-label="Währungsquelle prüfen und speichern"
            onSubmit={(event) => {
              event.preventDefault();
              void save();
            }}
            className="space-y-3"
          >
            <h4 className="font-medium">
              {draft.revoked
                ? 'Quelle widerrufen'
                : draft.supersedes_evidence_id
                  ? 'Quellenkorrektur'
                  : 'Neue geprüfte Quelle'}
            </h4>
            {draft.supersedes_evidence_id && (
              <p className="break-all text-xs">
                Ersetzt genau Quellenversion {draft.supersedes_evidence_id}; die Historie bleibt
                erhalten.
              </p>
            )}
            <fieldset disabled={locked || draft.revoked} className="space-y-3">
              <label className="block text-sm">
                Quelle und Fundstelle
                <input
                  className={inputClass}
                  maxLength={1000}
                  value={draft.source_reference}
                  onChange={(event) => change({ ...draft, source_reference: event.target.value })}
                />
              </label>
              {execution ? (
                <>
                  <label className="block text-sm">
                    Währung laut Ausführungsbeleg
                    <input
                      className={inputClass}
                      value={draft.currency_code ?? ''}
                      maxLength={3}
                      onChange={(event) =>
                        change({
                          ...draft,
                          currency_code: event.target.value.toUpperCase() || null,
                        })
                      }
                    />
                  </label>
                  {venueSelect(
                    draft.trading_venue_id ?? '',
                    (value) => change({ ...draft, trading_venue_id: value || null }),
                    'Handelsplatz laut Ausführungsbeleg (optional)',
                  )}
                </>
              ) : (
                <>
                  {exactTimes ? (
                    <>
                      <p className="text-xs text-slate-400">
                        Exakte Zeitpunkte mit Zeitzone wie 2026-10-01T00:00:00+02:00. Das Ende ist
                        ausgeschlossen. Bei Sommer-/Winterzeit kann der UTC-Versatz zwischen Anfang
                        und Ende wechseln. Vorhandene Intervalle bleiben bei Korrekturen ungerundet
                        erhalten.
                      </p>
                      <label className="block text-sm">
                        Gültig ab, mit Zeitzone
                        <input
                          className={inputClass}
                          value={draft.valid_from ?? ''}
                          onChange={(event) =>
                            change({ ...draft, valid_from: event.target.value || null })
                          }
                        />
                      </label>
                      <label className="block text-sm">
                        Gültig bis ausschließlich, mit Zeitzone
                        <input
                          className={inputClass}
                          value={draft.valid_to ?? ''}
                          onChange={(event) =>
                            change({ ...draft, valid_to: event.target.value || null })
                          }
                        />
                      </label>
                    </>
                  ) : (
                    <>
                      <p className="text-sm text-slate-400">
                        Ganze Kalendertage in Ihrer Browserzeitzone{' '}
                        {Intl.DateTimeFormat().resolvedOptions().timeZone}. Beide gewählten Tage
                        sind eingeschlossen; Sommer- und Winterzeit werden berücksichtigt. Für eine
                        andere Zeitzone oder untertägige Gültigkeit genaue Zeitpunkte verwenden.
                      </p>
                      <label className="block text-sm">
                        Historisch gültig ab (einschließlich)
                        <input
                          type="date"
                          className={inputClass}
                          value={days.from}
                          onChange={(event) => changeDays({ ...days, from: event.target.value })}
                        />
                      </label>
                      <label className="block text-sm">
                        Historisch gültig bis (einschließlich)
                        <input
                          type="date"
                          className={inputClass}
                          value={days.through}
                          onChange={(event) => changeDays({ ...days, through: event.target.value })}
                        />
                      </label>
                      {dayError && (
                        <p role="alert" className="text-sm text-amber-300">
                          {dayError}
                        </p>
                      )}
                      <button
                        type="button"
                        className={buttonClass}
                        onClick={() => {
                          setExactTimes(true);
                          setDayError('');
                        }}
                      >
                        Genaue Zeitpunkte mit Zeitzone verwenden
                      </button>
                    </>
                  )}
                  {draft.listings.map((listing, index) => (
                    <div
                      key={index}
                      className="grid gap-2 rounded border border-slate-800 p-3 sm:grid-cols-2"
                    >
                      {venueSelect(
                        listing.trading_venue_id,
                        (value) =>
                          change({
                            ...draft,
                            listings: draft.listings.map((item, position) =>
                              position === index ? { ...item, trading_venue_id: value } : item,
                            ),
                          }),
                        `Historischer Handelsplatz ${index + 1}`,
                      )}
                      <label className="block text-sm">
                        {`Historische Währung ${index + 1}`}
                        <input
                          className={inputClass}
                          value={listing.currency_code ?? ''}
                          maxLength={3}
                          onChange={(event) =>
                            change({
                              ...draft,
                              listings: draft.listings.map((item, position) =>
                                position === index
                                  ? {
                                      ...item,
                                      currency_code: event.target.value.toUpperCase() || null,
                                    }
                                  : item,
                              ),
                            })
                          }
                        />
                      </label>
                      <button
                        type="button"
                        className={buttonClass}
                        disabled={draft.listings.length === 1}
                        onClick={() =>
                          change({
                            ...draft,
                            listings: draft.listings.filter((_, position) => position !== index),
                          })
                        }
                      >
                        Handelsplatz {index + 1} entfernen
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    className={buttonClass}
                    onClick={() =>
                      change({
                        ...draft,
                        listings: [
                          ...draft.listings,
                          { trading_venue_id: '', currency_code: null },
                        ],
                      })
                    }
                  >
                    Historischen Handelsplatz ergänzen
                  </button>
                  <label className="flex gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={draft.complete_listing_set}
                      onChange={(event) =>
                        change({ ...draft, complete_listing_set: event.target.checked })
                      }
                    />
                    Die Quelle deckt alle relevanten Handelsplätze im gesamten angegebenen Zeitraum
                    ab.
                  </label>
                </>
              )}
            </fieldset>
            <label className="flex gap-2 text-sm">
              <input
                type="checkbox"
                checked={confirmed}
                disabled={locked}
                onChange={(event) => {
                  setConfirmed(event.target.checked);
                  publish({ ...state.current, dirty: true });
                }}
              />
              {draft.revoked
                ? 'Ich habe die Quelle geprüft und widerrufe diese Zuordnung.'
                : 'Ich habe die Originalquelle geprüft; die Angaben entsprechen ihrem historischen Inhalt.'}
            </label>
            <button
              type="submit"
              disabled={
                pending.busy ||
                disabled ||
                (!retry && (!confirmed || Boolean(pending.writeBlocked)))
              }
              className={buttonClass}
            >
              {retry
                ? 'Denselben Quellenauftrag erneut senden'
                : draft.revoked
                  ? 'Quellenwiderruf speichern'
                  : 'Geprüfte Quellenversion speichern'}
            </button>
          </form>
        </>
      )}
      {onCancel && (
        <button
          type="button"
          disabled={pending.busy || Boolean(pending.writeBlocked)}
          onClick={onCancel}
          className={buttonClass}
        >
          Quellenbearbeitung schließen
        </button>
      )}
    </section>
  );
}
