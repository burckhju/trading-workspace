import type { ChartIdentity } from '../../analysis/types/charts';
import { mappingInputsChanged, referenceBasisForMapping } from '../services/referenceMapping';
import type { ProviderMapping, VenueReconciliation } from '../services/topDownAdminClient';

interface MappingEditorProps {
  mapping: ProviderMapping | null;
  symbol: string;
  exchange: string;
  onSymbolChange: (value: string) => void;
  onExchangeChange: (value: string) => void;
  disabled?: boolean;
}

/** The page owns the only form, pending state, confirmation and navigation guard. */
export function MappingEditor({
  mapping,
  symbol,
  exchange,
  onSymbolChange,
  onExchangeChange,
  disabled = false,
}: MappingEditorProps) {
  return (
    <fieldset disabled={disabled} className="min-w-0 space-y-4">
      <legend className="mb-2 font-medium">
        {mapping ? 'Vorhandenes EODHD-Mapping bearbeiten' : 'EODHD-Mapping anlegen'}
      </legend>
      <div className="grid min-w-0 gap-4 sm:grid-cols-2">
        <label className="block min-w-0 text-sm">
          Geprüftes EODHD-Symbol
          <input
            required
            maxLength={64}
            value={symbol}
            onChange={(event) => onSymbolChange(event.target.value)}
            className="mt-1 w-full min-w-0 rounded border border-slate-600 bg-slate-950 p-2"
          />
        </label>
        <label className="block min-w-0 text-sm">
          Geprüfter EODHD-Exchange-Code
          <input
            required
            maxLength={32}
            value={exchange}
            onChange={(event) => onExchangeChange(event.target.value)}
            className="mt-1 w-full min-w-0 rounded border border-slate-600 bg-slate-950 p-2"
          />
        </label>
      </div>
      <p className="text-sm text-amber-200">
        {mapping
          ? `Speichern erhöht die Mappingrevision ${mapping.version}, deaktiviert das Mapping und löscht die bisherige Validierung.`
          : 'Das neue Mapping wird deaktiviert gespeichert.'}{' '}
        Validierung und Historienimport bleiben eigene, ausdrücklich bestätigte Aktionen.
      </p>
      {mapping && !mappingInputsChanged(mapping, symbol, exchange) && (
        <p className="text-sm text-slate-300">
          Keine Änderung: Groß-/Kleinschreibung und äußere Leerzeichen erzeugen keinen neuen
          Speicherauftrag.
        </p>
      )}
      <p className="text-xs text-slate-400">
        Providerkennungen werden aus dem Mapping gelesen. Ticker und MIC sind keine Vorlage für neue
        Providerkennungen.
      </p>
    </fieldset>
  );
}

interface MappingStatusProps {
  mapping: ProviderMapping | null;
  venue?: VenueReconciliation | null;
  referenceIdentity?: ChartIdentity | null;
}

const venueMeaning: Record<VenueReconciliation['status'], string> = {
  MATCHED: 'Der Handelsplatz ist eindeutig zugeordnet.',
  CONFLICT: 'Providerbeleg und Listing-Handelsplatz widersprechen sich.',
  AMBIGUOUS: 'Der Providerbeleg lässt mehrere Handelsplätze zu.',
  UNRESOLVED: 'Der Handelsplatz ist nicht aufgelöst.',
};

export function MappingStatus({ mapping, venue, referenceIdentity }: MappingStatusProps) {
  const basis = referenceBasisForMapping(referenceIdentity ?? null, mapping);
  return (
    <div className="min-w-0 space-y-2 break-words text-sm" aria-label="Mappingstand">
      {mapping ? (
        <>
          <p>
            Mappingrevision: {mapping.version} · Technischer Mappingstatus: {mapping.status}
          </p>
          {mapping.validation_message && <p>{mapping.validation_message}</p>}
          <p className="text-slate-400">
            Letzte technische Prüfung: {mapping.validated_at ?? 'Noch nicht geprüft'}
          </p>
        </>
      ) : (
        <p>Für diesen Kontext ist noch kein EODHD-Mapping belegt.</p>
      )}
      {referenceIdentity ? (
        <div>
          <p>Renditegrundlage dieser Mappingrevision: {basis.returnBasis}</p>
          {basis.source && <p>Beleg: {basis.source}</p>}
          {basis.returnBasis === 'UNKNOWN' && (
            <p className="text-amber-200">
              Die Grundlage bleibt unbekannt, bis sie für die aktuelle Revision gesondert belegt
              bestätigt wurde.
            </p>
          )}
        </div>
      ) : mapping?.listing_id ? (
        <div className="space-y-1">
          <p>Handelsplatzabgleich: {venue?.status ?? 'Noch nicht gelesen'}</p>
          {venue ? (
            <>
              <p>{venueMeaning[venue.status]}</p>
              <p>{venue.explanation}</p>
              {venue.status !== 'MATCHED' && (
                <p className="text-amber-200">
                  Der Reparaturschritt ist nicht als eindeutig geklärt belegt. Kein automatischer
                  Import oder Handelsplatzwechsel.
                </p>
              )}
            </>
          ) : (
            <p className="text-slate-400">
              Ein technisch aktives Mapping belegt allein keinen eindeutig zugeordneten
              Handelsplatz.
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
