import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';
import {
  canonicalSetupUrl,
  isWorkflowSetupAction,
  parseReferenceDataContext,
  resolveReferenceDataContext,
} from '../services/referenceDataContext';
import { topDownAdminClient } from '../services/topDownAdminClient';

function dateOffset(days: number) {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function SetupForwarding({ search }: { search: string }) {
  const navigate = useNavigate();
  const [failure, setFailure] = useState<{ search: string; message: string } | null>(null);
  const candidateId = new URLSearchParams(search).get('candidate_id');

  useEffect(() => {
    const abort = new AbortController();
    async function forward() {
      try {
        const context = parseReferenceDataContext(new URLSearchParams(search));
        const resolved = await resolveReferenceDataContext(context, abort.signal);
        if (!abort.signal.aborted) void navigate(canonicalSetupUrl(resolved), { replace: true });
      } catch (reason: unknown) {
        if (!abort.signal.aborted) {
          setFailure({
            search,
            message: reason instanceof Error ? reason.message : 'Der Kontext ist nicht lesbar.',
          });
        }
      }
    }
    void forward();
    return () => abort.abort();
  }, [navigate, search]);

  const error = failure?.search === search ? failure.message : null;
  return (
    <section className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold">Referenzdaten einrichten</h1>
      {error ? (
        <p role="alert" className="rounded-lg border border-rose-800 p-3">
          Kontext gesperrt: {error}
        </p>
      ) : (
        <p role="status">Kontext wird geprüft und in der gemeinsamen Einrichtung geöffnet …</p>
      )}
      <Link
        className="inline-block rounded border border-slate-700 px-4 py-2"
        to={
          candidateId ? `/candidates?candidate=${encodeURIComponent(candidateId)}` : '/candidates'
        }
      >
        Zurück zum Kandidaten
      </Link>
    </section>
  );
}

const remainingActions = new Set([
  'ACTIVATE_OR_REASSIGN_BENCHMARK',
  'ACTIVATE_OR_REASSIGN_SECTOR_REFERENCE',
  'ACTIVATE_OR_REASSIGN_SECTOR',
  'CREATE_OR_SELECT_PRIMARY_LISTING',
  'RUN_MARKET_ANALYSIS',
]);

function RemainingWorkflowAction({ params }: { params: URLSearchParams }) {
  const navigate = useNavigate();
  const action = params.get('action') ?? '';
  const candidateId = params.get('candidate_id') ?? '';
  const resourceId = params.get('resource_id') ?? '';
  const underlyingId = params.get('underlying_id') ?? '';
  const listingId = params.get('listing_id') ?? resourceId;
  const sectorId = params.get('sector_id') ?? resourceId;
  const referenceId = params.get('market_reference_id') ?? resourceId;
  const returnTo = `/candidates?candidate=${encodeURIComponent(candidateId)}`;
  const [startDate, setStartDate] = useState(dateOffset(-400));
  const [endDate, setEndDate] = useState(dateOffset(0));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submitLock = useRef(false);
  const dirty = useRef(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitLock.current) return;
    submitLock.current = true;
    setBusy(true);
    setError(null);
    try {
      switch (action) {
        case 'ACTIVATE_OR_REASSIGN_BENCHMARK':
        case 'ACTIVATE_OR_REASSIGN_SECTOR_REFERENCE':
          if (!referenceId) throw new Error('Die Referenzkennung fehlt.');
          await topDownAdminClient.activateReference(referenceId);
          break;
        case 'ACTIVATE_OR_REASSIGN_SECTOR':
          if (!sectorId) throw new Error('Die Sektorkennung fehlt.');
          await topDownAdminClient.activateSector(sectorId);
          break;
        case 'RUN_MARKET_ANALYSIS': {
          if (!underlyingId || !listingId) throw new Error('Underlying- oder Listing-ID fehlt.');
          const analysis = await topDownAdminClient.createAnalysis(underlyingId, listingId);
          await topDownAdminClient.runAnalysis(analysis.id, startDate, endDate);
          break;
        }
        default:
          throw new Error('Für diese Aktion fehlt ein eindeutiger Eingabeweg.');
      }
      dirty.current = false;
      submitLock.current = false;
      void navigate(returnTo);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Aktion fehlgeschlagen.');
    } finally {
      submitLock.current = false;
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PendingNavigationGuard
        shouldBlock={() => submitLock.current || dirty.current}
        busy={busy}
        onDiscard={() => {
          dirty.current = false;
        }}
      />
      <p className="text-xs uppercase tracking-wide text-slate-500">Top-down Administration</p>
      <h1 className="mt-1 text-2xl font-semibold">Workflow-Schritt ausführen</h1>
      <p className="mt-2 break-words text-sm text-slate-400">{action}</p>
      {error && (
        <p role="alert" className="mt-5 rounded-lg border border-rose-800 p-3 text-sm">
          {error}
        </p>
      )}
      {action === 'CREATE_OR_SELECT_PRIMARY_LISTING' ? (
        <section className="mt-6 space-y-4 rounded-xl border border-slate-800 p-5">
          <p className="text-sm text-slate-300">
            Für den Basiswert muss zuerst ein Primary Listing in der Basiswertverwaltung angelegt
            oder ausgewählt werden.
          </p>
          <div className="flex flex-wrap gap-3">
            {underlyingId && (
              <Link
                to={`/underlyings/${encodeURIComponent(underlyingId)}`}
                className="rounded-lg border border-sky-700 px-4 py-2 text-sm"
              >
                Basiswert öffnen
              </Link>
            )}
            <Link to={returnTo} className="rounded-lg border border-slate-700 px-4 py-2 text-sm">
              Zurück
            </Link>
          </div>
        </section>
      ) : (
        <form
          onSubmit={(event) => void submit(event)}
          className="mt-6 space-y-5 rounded-xl border border-slate-800 p-5"
        >
          {action === 'RUN_MARKET_ANALYSIS' ? (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm">
                Von
                <input
                  type="date"
                  required
                  value={startDate}
                  disabled={busy}
                  onChange={(event) => {
                    dirty.current = true;
                    setStartDate(event.target.value);
                  }}
                  className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
                />
              </label>
              <label className="text-sm">
                Bis
                <input
                  type="date"
                  required
                  value={endDate}
                  disabled={busy}
                  onChange={(event) => {
                    dirty.current = true;
                    setEndDate(event.target.value);
                  }}
                  className="mt-2 w-full rounded border border-slate-700 bg-slate-950 p-2"
                />
              </label>
            </div>
          ) : (
            <p className="text-sm text-slate-300">
              Die aktuell zugeordnete Referenz wird wieder aktiviert. Eine fachliche Neuzuordnung
              bleibt eine separate, historisierte Admin-Aktion.
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <button
              disabled={busy}
              className="rounded-lg border border-sky-700 px-4 py-2 text-sm disabled:opacity-50"
            >
              {busy ? 'Wird ausgeführt …' : 'Aktion ausführen'}
            </button>
            <Link to={returnTo} className="rounded-lg border border-slate-700 px-4 py-2 text-sm">
              Abbrechen
            </Link>
          </div>
        </form>
      )}
    </div>
  );
}

/** The seven shared actions have no editor here: checked context goes to /chart-setup. */
export function TopDownWorkflowActionPage() {
  const [params] = useSearchParams();
  const action = params.get('action') ?? '';
  if (isWorkflowSetupAction(action)) return <SetupForwarding search={params.toString()} />;
  if (remainingActions.has(action))
    return <RemainingWorkflowAction key={params.toString()} params={params} />;
  return (
    <section className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold">Workflow-Kontext gesperrt</h1>
      <p role="alert">
        Unbekannte Aktion: {action || 'keine Aktion angegeben'}. Bitte den Workflow erneut öffnen.
      </p>
      <Link to="/candidates" className="text-sky-300">
        Zurück zu Kandidaten
      </Link>
    </section>
  );
}
