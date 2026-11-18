import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { MarketApiError } from '../../market/services/http';
import { readDeadlineExitListing, saveDeadlineExitListing } from '../services/deadlineExitListing';
import type { DeadlineExitListingReport } from '../types/deadlineExitListing';

const reasonLabels: Record<string, string> = {
  PRODUCT_EXIT_LISTING_MISSING: 'Ein fester Ausstiegshandelsplatz fehlt.',
  PRODUCT_EXIT_LISTING_WITHDRAWN: 'Die bisherige Festlegung wurde zurückgenommen.',
  PRODUCT_EXIT_TERMS_CHANGED: 'Die Produktbedingungen haben sich seit der Festlegung geändert.',
  PRODUCT_EXIT_TERMS_AFTER_KNOWLEDGE:
    'Die Produktbedingungen waren zum maßgeblichen Kenntnisstand noch nicht belegt.',
  PRODUCT_EXIT_LISTING_CHANGED:
    'Die gewählte Notierung hat sich geändert oder ist nicht mehr verfügbar.',
  PRODUCT_EXIT_VENUE_CHANGED: 'Die Handelsplatzangaben haben sich seit der Festlegung geändert.',
  PRODUCT_EXIT_WARRANT_INACTIVE: 'Dieses Produkt ist nicht aktiv.',
};

function initialChoice(report: DeadlineExitListingReport): string {
  return report.available_listings.some((item) => item.listing_id === report.selected_listing_id)
    ? (report.selected_listing_id ?? '')
    : '';
}

function Choice({ warrantId }: { warrantId: string }) {
  const [report, setReport] = useState<DeadlineExitListingReport | null>(null);
  const [selected, setSelected] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const alive = useRef(false);
  const generation = useRef(0);
  const readController = useRef<AbortController | null>(null);
  const writing = useRef(false);

  const read = useCallback(async () => {
    readController.current?.abort();
    const controller = new AbortController();
    readController.current = controller;
    const currentGeneration = ++generation.current;
    const current = () =>
      alive.current && !controller.signal.aborted && currentGeneration === generation.current;
    setLoading(true);
    setError('');
    try {
      const next = await readDeadlineExitListing(warrantId, controller.signal);
      if (!current()) return;
      setReport(next);
      setSelected(initialChoice(next));
      setBlocked(false);
      setUncertain(false);
      setNotice('');
    } catch (cause) {
      if (current()) {
        setError(cause instanceof Error ? cause.message : 'Ausstiegshandelsplatz nicht lesbar.');
        setBlocked(true);
      }
    } finally {
      if (current()) setLoading(false);
    }
  }, [warrantId]);

  useEffect(() => {
    alive.current = true;
    void read();
    return () => {
      alive.current = false;
      generation.current += 1;
      readController.current?.abort();
    };
  }, [read]);

  async function save(listingId: string | null) {
    if (!report || loading || writing.current || blocked) return;
    writing.current = true;
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const next = await saveDeadlineExitListing(warrantId, report, listingId);
      if (!alive.current) return;
      setReport(next);
      setSelected(initialChoice(next));
      setUncertain(false);
      setNotice(
        listingId === null
          ? 'Festlegung zurückgenommen. Produkttermin-Erinnerungen benötigen wieder eine ausdrückliche Wahl.'
          : 'Ausstiegshandelsplatz gespeichert. Diese Wahl bleibt für weitere Prüfdurchläufe erhalten.',
      );
    } catch (cause) {
      if (!alive.current) return;
      setBlocked(true);
      setUncertain(!(cause instanceof MarketApiError) || cause.status >= 500);
      setError(
        cause instanceof MarketApiError && cause.status === 409
          ? 'Produktbedingungen, Handelsplatz oder Auswahl wurden zwischenzeitlich geändert. Gespeicherten Stand neu lesen und die gewünschte Notierung prüfen.'
          : cause instanceof MarketApiError
            ? `Die Auswahl wurde nicht bestätigt: ${cause.message}. Gespeicherten Stand vor einem weiteren Versuch neu lesen.`
            : 'Speichererfolg unklar. Gespeicherten Stand neu lesen; die Auswahl nicht erneut senden, bevor der Stand geklärt ist.',
      );
    } finally {
      writing.current = false;
      if (alive.current) setSaving(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (selected && report?.available_listings.some((item) => item.listing_id === selected))
      void save(selected);
  }

  const busy = loading || saving;
  const changed = Boolean(report) && selected !== initialChoice(report!);
  return (
    <section
      aria-label="Ausstiegshandelsplatz für Produkttermine"
      className="min-w-0 space-y-3 rounded-xl border border-slate-700 bg-slate-950/40 p-3 sm:p-4"
    >
      <h3 className="font-semibold text-white">Produkttermine · fester Ausstiegshandelsplatz</h3>
      <p className="text-sm text-slate-300">
        Einmalige fachliche Auswahl aus den vorhandenen Notierungen dieses Produkts. Die Festlegung
        gilt für seine Produkttermin-Erinnerungen und muss nicht täglich bestätigt werden.
      </p>
      {loading && <p>Gespeicherte Festlegung wird gelesen …</p>}
      {error && (
        <p role="alert" className="text-amber-200">
          {error}
        </p>
      )}
      {uncertain && (
        <p className="text-amber-200">
          Der Speichererfolg bleibt ungeklärt, bis der gespeicherte Stand erfolgreich gelesen wurde.
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      {report && (
        <>
          <p>
            {report.status === 'AVAILABLE'
              ? `Gespeicherter Ausstiegshandelsplatz: ${report.selected_venue_mic}`
              : report.status === 'UNSUITABLE'
                ? 'Die bisherige Festlegung ist mit den aktuellen Produkt- oder Notierungsbelegen nicht verwendbar.'
                : 'Noch kein Ausstiegshandelsplatz ausdrücklich festgelegt.'}
          </p>
          {report.recorded_at && (
            <p className="text-xs text-slate-400">
              Zuletzt gespeichert: <time dateTime={report.recorded_at}>{report.recorded_at}</time>
            </p>
          )}
          {report.available_listings.length > 0 ? (
            <form
              onSubmit={submit}
              aria-label="Ausstiegshandelsplatz festlegen"
              className="space-y-3"
            >
              <label className="block text-sm">
                Vorhandene Notierung für Produkttermine
                <select
                  value={selected}
                  disabled={busy || blocked}
                  onChange={(event) => {
                    setSelected(event.target.value);
                    setNotice('');
                  }}
                  className="mt-1 w-full min-w-0 rounded border border-slate-700 bg-slate-950 p-2"
                >
                  <option value="">Bitte ausdrücklich auswählen</option>
                  {report.available_listings.map((option) => (
                    <option key={option.listing_id} value={option.listing_id}>
                      {option.venue_name} · {option.venue_mic} · {option.quotation_currency_code}
                      {option.symbol ? ` · ${option.symbol}` : ''}
                    </option>
                  ))}
                </select>
              </label>
              {changed && <p className="text-xs text-amber-200">Auswahl noch nicht gespeichert.</p>}
              <button
                type="submit"
                disabled={
                  busy || blocked || !selected || (!changed && report.status === 'AVAILABLE')
                }
                className="rounded bg-sky-800 px-3 py-2 text-sm disabled:opacity-50"
              >
                {saving ? 'Festlegung wird gespeichert …' : 'Ausstiegshandelsplatz speichern'}
              </button>
            </form>
          ) : (
            <p>
              Keine geeignete vorhandene Notierung verfügbar. Die Produktstammdaten müssen zuerst
              geklärt werden.
            </p>
          )}
          {report.selected_listing_id && (
            <button
              type="button"
              disabled={busy || blocked}
              onClick={() => void save(null)}
              className="rounded border border-slate-600 px-3 py-2 text-sm disabled:opacity-50"
            >
              Festlegung zurücknehmen
            </button>
          )}
          {report.reasons.length > 0 && (
            <details className="text-xs text-slate-400">
              <summary className="cursor-pointer">Offene Voraussetzungen der Festlegung</summary>
              <ul className="mt-2 space-y-1">
                {report.reasons.map((reason, index) => (
                  <li key={`${reason}:${index}`}>
                    {Object.hasOwn(reasonLabels, reason)
                      ? reasonLabels[reason]
                      : `Offene Voraussetzung: ${reason}`}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
      <button
        type="button"
        disabled={busy}
        onClick={() => void read()}
        className="rounded border border-slate-600 px-3 py-2 text-sm disabled:opacity-50"
      >
        {changed ? 'Auswahl verwerfen und Stand neu lesen' : 'Gespeicherten Stand neu lesen'}
      </button>
      <p className="text-xs text-slate-400">
        Die Wahl allein bestätigt keine produktbezogene letzte Handelsuhrzeit und keine vollständige
        B05-Qualifikation. Sie erzeugt keine Order oder Kursaktualisierung.
      </p>
    </section>
  );
}

export function DeadlineExitListingChoice({ warrantId }: { warrantId: string }) {
  return <Choice key={warrantId} warrantId={warrantId} />;
}
