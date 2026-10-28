import { useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';
import { ExistingUnderlyingSelector } from '../../administration/components/ExistingUnderlyingSelector';
import { MappingEditor, MappingStatus } from '../../administration/components/MappingEditor';
import { SetupDiscardDialog } from '../../administration/components/SetupDiscardDialog';
import { SetupProposals } from '../../administration/components/SetupProposals';
import { useReferenceSetup } from '../../administration/components/useReferenceSetup';
import {
  parseReferenceDataContext,
  type ReferenceDataContext,
  type SetupAction,
} from '../../administration/services/referenceDataContext';
import {
  editsMapping,
  importsHistory,
  isAssignment,
  needsListing,
  needsReference,
  needsSector,
  needsUnderlying,
  selectionForAction,
  setupActions,
} from '../../administration/services/referenceSetup';

const inputClass = 'mt-1 w-full min-w-0 rounded border border-slate-600 bg-slate-950 p-2';
const buttonClass = 'rounded border border-slate-600 px-3 py-2 disabled:opacity-50';

export function ChartSetupPage() {
  const [params] = useSearchParams();
  const candidateId = params.get('candidate_id');
  const query = params.toString();
  const parsed = useMemo(() => {
    try {
      return { context: parseReferenceDataContext(new URLSearchParams(query)), error: '' };
    } catch (reason: unknown) {
      return {
        context: null,
        error:
          reason instanceof Error ? reason.message : 'Der Einrichtungskontext ist nicht lesbar.',
      };
    }
  }, [query]);
  return parsed.context ? (
    <SetupEditor key={parsed.context.key} context={parsed.context} />
  ) : (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold">Einrichtung gesperrt</h1>
      <p role="alert">{parsed.error}</p>
      <Link
        className="text-sky-300 underline"
        to={
          candidateId
            ? `/candidates?candidate=${encodeURIComponent(candidateId)}`
            : '/market-charts'
        }
      >
        {candidateId ? 'Zurück zum Kandidaten' : 'Zurück zu den Diagrammen'}
      </Link>
    </div>
  );
}

function SetupEditor({ context }: { context: ReferenceDataContext }) {
  const editor = useReferenceSetup(context);
  const { selection, draft, snapshot, busy, loading } = editor;
  const action = selection.action;
  const pinned = Boolean(context.workflowAction);
  const candidate = Boolean(context.candidateId);
  const actionLabel = setupActions.find((item) => item.value === action)?.label;
  const lockUnderlying = pinned && action !== 'proxy';
  const lockReference = pinned && (action === 'proxy' || Boolean(context.referenceId));
  const lockSector = pinned && (action === 'sectorReference' || Boolean(context.sectorId));
  const lockListing = pinned && action !== 'proxy';
  const disabled = busy || loading || !editor.resolved;

  return (
    <div className="mx-auto min-w-0 w-full max-w-5xl space-y-5">
      <PendingNavigationGuard
        shouldBlock={editor.shouldBlock}
        busy={busy}
        onDiscard={editor.discardForRoute}
      />
      {editor.pending && !busy && (
        <SetupDiscardDialog onStay={editor.stay} onDiscard={editor.discard} />
      )}
      <header className="min-w-0">
        <Link className="text-sky-300 underline" to={editor.resolved?.returnTo ?? context.returnTo}>
          {candidate ? '← Zurück zum Kandidaten' : '← Zurück zu den Diagrammen'}
        </Link>
        <h1 className="mt-3 text-3xl font-semibold">Diagramm-Datenbasis einrichten</h1>
        <p className="mt-2 text-slate-300">
          Referenzdaten und Mappings an einem Eingabeort. Wähle ein vorhandenes Objekt und bestätige
          jeweils einen Schritt.
        </p>
      </header>
      {editor.error && (
        <p role="alert" className="break-words rounded border border-rose-700 p-3">
          {editor.error}
        </p>
      )}
      {editor.message && (
        <p role="status" className="rounded border border-emerald-700 p-3">
          {editor.message}
        </p>
      )}
      {editor.readError && (
        <div role="alert" className="space-y-2 rounded border border-amber-700 p-3">
          <p>
            {editor.outcome === 'complete'
              ? 'Der Schreibauftrag ist abgeschlossen; das Nachlesen ist gestört. '
              : ''}
            {editor.readError}
          </p>
          <button
            type="button"
            className={buttonClass}
            disabled={busy || loading}
            onClick={editor.reload}
          >
            Nur Lesestand erneut laden
          </button>
        </div>
      )}
      {editor.reviewRequired && (
        <div className="space-y-2 rounded border border-amber-700 p-3">
          <p>
            Der zuletzt gelesene Stand wird getrennt von deinen offenen Eingaben angezeigt. Dein
            Entwurf ist noch nicht gespeichert. Die erneute Prüfung ersetzt keine atomare Sperre
            gegen Änderungen in anderen Tabs.
          </p>
          <button
            type="button"
            className={buttonClass}
            disabled={disabled}
            onClick={editor.acknowledge}
          >
            Aktuellen Stand prüfen und Entwurf beibehalten
          </button>
        </div>
      )}
      {editor.outcome === 'unknown' && !editor.readError && (
        <button
          type="button"
          className={buttonClass}
          disabled={busy || loading}
          onClick={editor.reload}
        >
          Nur Lesestand erneut laden
        </button>
      )}
      {loading && <p role="status">Der gespeicherte Kontext wird gelesen …</p>}

      <form
        aria-label="Gemeinsamer Referenzdaten-Editor"
        className="min-w-0 space-y-5 rounded-xl border border-slate-700 p-4 sm:p-6"
        onSubmit={(event) => {
          event.preventDefault();
          void editor.submit();
        }}
      >
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">{pinned ? actionLabel : 'Objekt und Aktion'}</h2>
          {pinned ? (
            <p className="text-sm text-slate-400">
              Aktion und Ausgangsobjekt sind an diesen Workflow-Schritt gebunden.
            </p>
          ) : (
            <label className="block">
              Aktion
              <select
                className={inputClass}
                value={action}
                disabled={busy || !editor.resolved}
                onChange={(event) =>
                  editor.changeContext(
                    selectionForAction(selection, event.target.value as SetupAction),
                  )
                }
              >
                {['Basiswert / Listing', 'Sektor', 'Referenz', 'Stammdaten ergänzen'].map(
                  (group) => (
                    <optgroup key={group} label={group}>
                      {setupActions
                        .filter((item) => item.group === group)
                        .map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.label}
                          </option>
                        ))}
                    </optgroup>
                  ),
                )}
              </select>
            </label>
          )}
        </div>

        {needsUnderlying(action) && !lockUnderlying && (
          <ExistingUnderlyingSelector
            value={selection.underlyingId}
            label={snapshot?.underlying?.name}
            disabled={busy || !editor.resolved}
            onChange={(underlyingId) => {
              const next = { ...selection, underlyingId, listingId: '', mappingId: '' };
              if (action === 'proxy') editor.changeTarget(next);
              else editor.changeContext(next);
            }}
          />
        )}
        {needsReference(action) && !lockReference && (
          <label className="block">
            {action === 'sectorReference'
              ? 'Geeignete Sektorreferenz'
              : 'Markt- / Sektor-Benchmark'}
            <select
              required
              className={inputClass}
              disabled={disabled}
              value={selection.referenceId}
              onChange={(event) => {
                const referenceId = event.target.value;
                if (action === 'stockMarket' || action === 'sectorReference')
                  editor.changeTarget({ referenceId });
                else editor.changeContext({ ...selection, referenceId, mappingId: '' });
              }}
            >
              <option value="">Bitte wählen</option>
              {snapshot?.references
                .filter(
                  (item) =>
                    item.active &&
                    (action !== 'sectorReference' || item.reference_type === 'SECTOR_INDEX'),
                )
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} · {item.code}
                  </option>
                ))}
            </select>
          </label>
        )}
        {needsSector(action) && !lockSector && (
          <label className="block">
            Administrierter Sektor
            <select
              required
              className={inputClass}
              disabled={disabled}
              value={selection.sectorId}
              onChange={(event) => {
                const sectorId = event.target.value;
                if (action === 'stockSector') editor.changeTarget({ sectorId });
                else editor.changeContext({ ...selection, sectorId });
              }}
            >
              <option value="">Bitte wählen</option>
              {snapshot?.sectors
                .filter((item) => item.active)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} · {item.code}
                  </option>
                ))}
            </select>
          </label>
        )}
        {needsListing(action) && !lockListing && (
          <label className="block">
            Eindeutige Notierung
            <select
              required
              className={inputClass}
              disabled={disabled || !snapshot?.underlying}
              value={selection.listingId || snapshot?.listing?.id || ''}
              onChange={(event) => {
                const listingId = event.target.value;
                if (action === 'proxy') editor.changeTarget({ listingId });
                else editor.changeContext({ ...selection, listingId, mappingId: '' });
              }}
            >
              <option value="">Bitte wählen</option>
              {snapshot?.underlying?.listings.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.ticker} · {item.trading_venue_mic} · {item.currency_code}
                  {item.is_primary ? ' · primär' : ''}
                </option>
              ))}
            </select>
          </label>
        )}

        {snapshot && (snapshot.underlying || snapshot.reference || snapshot.sector) && (
          <section
            aria-label="Gewählter Kontext"
            className="min-w-0 space-y-2 break-words rounded border border-slate-700 bg-slate-900/50 p-3 text-sm"
          >
            <h3 className="font-semibold">Gewählter Kontext</h3>
            {snapshot.underlying && (
              <p>
                <strong>{snapshot.underlying.name}</strong> ·{' '}
                {snapshot.underlying.type === 'ETF' ? 'Echtes ETF-Wertpapier' : 'Aktie'}
                {snapshot.underlying.isin ? ` · ISIN ${snapshot.underlying.isin}` : ''}
                <span className="block text-xs text-slate-400">
                  Basiswert-ID: {snapshot.underlying.id}
                </span>
              </p>
            )}
            {snapshot.listing && (
              <p>
                {snapshot.listing.ticker} ·{' '}
                {snapshot.listing.trading_venue_name ?? snapshot.listing.trading_venue_mic} · MIC{' '}
                {snapshot.listing.trading_venue_mic} · {snapshot.listing.currency_code}
                {!snapshot.listing.is_primary && ' · nichtprimäre Notierung'}
                <span className="block text-xs text-slate-400">
                  Listing-ID: {snapshot.listing.id}
                </span>
              </p>
            )}
            {snapshot.reference && (
              <p>
                <strong>{snapshot.reference.name}</strong> · {snapshot.reference.code} ·{' '}
                {snapshot.reference.reference_type}
                <span className="block text-xs text-slate-400">
                  Referenz-ID: {snapshot.reference.id}
                  {editor.isMappingContext && !needsListing(action)
                    ? ' · direkter Index ohne Listing'
                    : ''}
                </span>
              </p>
            )}
            {snapshot.sector && (
              <p>
                <strong>{snapshot.sector.name}</strong> · {snapshot.sector.code}
                <span className="block text-xs text-slate-400">
                  Sektor-ID: {snapshot.sector.id}
                </span>
              </p>
            )}
            {snapshot.mapping && (
              <p className="text-xs text-slate-400">
                Mapping-ID: {snapshot.mapping.id} · Instrument-ID:{' '}
                {snapshot.mapping.market_data_instrument_id ?? 'im API-Datensatz nicht vorhanden'}
              </p>
            )}
            {action === 'proxy' && snapshot.underlying?.type === 'ETF' && (
              <p className="text-amber-200">
                Die ausgewählte Referenz wird ausdrücklich diesem echten ETF-Listing zugeordnet.
                ETF-Kurse sind ein gekennzeichneter Proxy; die direkte Indexidentität bleibt
                eigenständig.
              </p>
            )}
          </section>
        )}

        {editor.isMappingContext && snapshot && (
          <MappingStatus
            mapping={snapshot.mapping}
            venue={snapshot.venue}
            referenceIdentity={needsListing(action) ? null : snapshot.identity}
            showProviderIdentity={
              !editsMapping(action) || editor.reviewRequired || editor.outcome === 'unknown'
            }
          />
        )}
        <fieldset disabled={disabled || editor.outcome === 'unknown'} className="min-w-0 space-y-4">
          <legend className="sr-only">Eingaben für diesen Schritt</legend>
          {action === 'bootstrap' && (
            <p>
              Die vorhandene Bootstrap-Aktion ergänzt die freigegebenen semantischen
              Marktreferenzen. Sie erzeugt keine Provider-Mappings oder Notierungen.
            </p>
          )}
          {(action === 'sector' || action === 'reference') && (
            <div className="grid min-w-0 gap-4 sm:grid-cols-2">
              <label>
                Code
                <input
                  required
                  maxLength={50}
                  className={inputClass}
                  value={draft.code}
                  onChange={(event) => editor.changeDraft({ code: event.target.value })}
                />
              </label>
              <label>
                Name
                <input
                  required
                  maxLength={200}
                  className={inputClass}
                  value={draft.name}
                  onChange={(event) => editor.changeDraft({ name: event.target.value })}
                />
              </label>
              <label>
                Version
                <input
                  required
                  maxLength={50}
                  className={inputClass}
                  value={draft.version}
                  onChange={(event) => editor.changeDraft({ version: event.target.value })}
                />
              </label>
              {action === 'sector' ? (
                <label>
                  Klassifikationssystem
                  <input
                    required
                    maxLength={100}
                    className={inputClass}
                    value={draft.system}
                    onChange={(event) => editor.changeDraft({ system: event.target.value })}
                  />
                </label>
              ) : (
                <label>
                  Region
                  <input
                    required
                    maxLength={50}
                    className={inputClass}
                    value={draft.region}
                    onChange={(event) => editor.changeDraft({ region: event.target.value })}
                  />
                </label>
              )}
              <p className="text-sm text-slate-400 sm:col-span-2">
                Dieser Vorgang legt einen neuen Datensatz an. Name, Code und Klassifikation
                bestehender Objekte werden hier nicht geändert.
              </p>
            </div>
          )}
          {editsMapping(action) && snapshot && (
            <MappingEditor
              mapping={snapshot.mapping}
              symbol={draft.symbol}
              exchange={draft.exchange}
              onSymbolChange={(symbol) => editor.changeDraft({ symbol })}
              onExchangeChange={(exchange) => editor.changeDraft({ exchange })}
              disabled={disabled}
            />
          )}
          {action.endsWith('Validate') && (
            <p className="text-sm text-amber-200">
              Diese ausdrückliche Prüfung kann Providerdaten abrufen und erhöht die Mappingrevision
              auch bei erneuter Validierung. Eine bisherige Index-Renditegrundlage gilt nicht für
              die neue Revision. Ein Import wird dadurch nicht gestartet.
            </p>
          )}
          {action === 'basis' && (
            <label className="block">
              Belegte Indexserie
              <select
                className={inputClass}
                value={draft.basis}
                onChange={(event) => editor.changeDraft({ basis: event.target.value })}
              >
                <option value="PRICE_INDEX">Kursindex</option>
                <option value="TOTAL_RETURN_INDEX">Total-Return-Index</option>
              </select>
            </label>
          )}
          {isAssignment(action) && (
            <div className="space-y-2 rounded border border-amber-900 p-3 text-sm">
              <h3 className="font-semibold">Neue zeitlich gültige Zuordnung</h3>
              <p>
                Bestehende Zuordnungen werden nicht umgebunden. Zeitüberschneidungen weist der
                Server zurück; Änderung oder Beendigung vorhandener Zuordnungen benötigen einen
                eigenen Backend-Vertrag.
              </p>
              <p>
                Herkunft: <strong>{candidate ? 'MANUAL_ADMIN' : 'CHART_SETUP'}</strong> · Gültig ab:{' '}
                {draft.start} · Gültig bis: offen · Qualität: GOOD
              </p>
              {action === 'sectorReference' ? (
                <p>
                  Für Sektor→Referenz speichert der bestehende Vertrag keinen zusätzlichen
                  Quellenbeleg.
                </p>
              ) : (
                candidate && <p>Quellenbeleg: Candidate live workflow</p>
              )}
              <p className="text-slate-400">
                Ein Chart-Lesestand zu einem Stichtag ist keine vollständige administrative
                Zuordnungshistorie.
              </p>
            </div>
          )}
          {((isAssignment(action) && action !== 'sectorReference' && !candidate) ||
            action === 'basis') && (
            <label className="block">
              Quellenbeleg (HTTPS)
              <input
                required
                type="url"
                pattern="https://.*"
                maxLength={action === 'basis' ? 500 : 200}
                className={inputClass}
                value={draft.source}
                onChange={(event) => editor.changeDraft({ source: event.target.value })}
              />
            </label>
          )}
          {isAssignment(action) && !candidate && (
            <label className="block">
              Zuordnung gültig ab
              <input
                required
                type="date"
                className={inputClass}
                value={draft.start}
                onChange={(event) => editor.changeDraft({ start: event.target.value })}
              />
            </label>
          )}
          {importsHistory(action) && (
            <div className="grid min-w-0 gap-4 sm:grid-cols-2">
              <label>
                Import von
                <input
                  required
                  type="date"
                  className={inputClass}
                  max={draft.end}
                  value={draft.start}
                  onChange={(event) => editor.changeDraft({ start: event.target.value })}
                />
              </label>
              <label>
                Import bis
                <input
                  required
                  type="date"
                  className={inputClass}
                  min={draft.start}
                  value={draft.end}
                  onChange={(event) => editor.changeDraft({ end: event.target.value })}
                />
              </label>
              <p className="text-sm text-slate-400 sm:col-span-2">
                Genau dieser Zeitraum wird für das angezeigte Listing/Mapping beziehungsweise die
                direkte Indexreferenz importiert. Providerfehler führen zu keinem Proxywechsel.
              </p>
            </div>
          )}
          {editor.problem && <p className="text-sm text-amber-200">{editor.problem}</p>}
          <label className="flex items-start gap-3">
            <input
              type="checkbox"
              className="mt-1"
              checked={editor.confirmed}
              disabled={
                busy ||
                loading ||
                editor.reviewRequired ||
                editor.outcome !== 'none' ||
                Boolean(editor.problem) ||
                editor.unchanged
              }
              onChange={(event) => editor.confirm(event.target.checked)}
            />
            <span>Ich bestätige den angezeigten Kontext und diesen einzelnen Schritt.</span>
          </label>
          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={!editor.canSubmit}
              className="rounded border border-sky-600 bg-sky-950 px-4 py-2 disabled:opacity-50"
            >
              {busy ? 'Schritt läuft …' : 'Geprüften Schritt ausführen'}
            </button>
            <button
              type="button"
              disabled={busy || loading}
              className={buttonClass}
              onClick={editor.cancel}
            >
              Abbrechen / Eingaben zurücksetzen
            </button>
            <button
              type="button"
              disabled={busy || loading}
              className={buttonClass}
              onClick={editor.reload}
            >
              Lesestand aktualisieren
            </button>
          </div>
        </fieldset>
        {editor.isMappingContext && (
          <p className="text-xs text-slate-400">
            Vor dem Schreiben wird die sichtbare Revision erneut gelesen. Die API bietet keine
            atomare Versionssperre und keine Replaygarantie; eine Änderung unmittelbar nach diesem
            Read kann damit nicht ausgeschlossen werden.
          </p>
        )}
      </form>
      {editor.workflow && editor.outcome !== 'none' && (
        <p className="text-sm text-slate-300">
          Kandidaten-Readiness erneut gelesen:{' '}
          {editor.workflow.ready ? 'bereit laut aktuellem Workflow' : 'weitere Schritte offen'}. Der
          technische Mappingstatus und der Handelsplatzabgleich bleiben eigenständige Angaben. Eine
          Evaluation oder Folgeaktion wurde nicht gestartet.
        </p>
      )}
      {!pinned && (
        <SetupProposals
          busy={busy || !editor.resolved}
          onPrepare={(action, values) =>
            editor.changeContext(selectionForAction(selection, action), values)
          }
        />
      )}
    </div>
  );
}
