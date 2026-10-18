import { ivLabel } from '../services/iv';
import { riskLabel } from '../services/riskLabels';
import type { RiskView } from '../types/risk';
import { IvModelCalculator } from './IvModelCalculator';
import { WarrantQuoteHistory } from '../../product/components/WarrantQuoteHistory';

export function IvRiskPanel({ view }: { view: RiskView }) {
  const iv = view.iv;
  const quote = view.quote_evidence;
  const label = (code: string) => ivLabel(code) ?? riskLabel(code);
  return (
    <section
      aria-label="Implizite Volatilität"
      className="min-w-0 space-y-3 break-words rounded border border-slate-600 p-3"
    >
      <h4 className="font-semibold">Implizite Volatilität (IV)</h4>
      <p>Datenqualität: nicht auswertbar. Das IV-Risikoniveau ist unbekannt.</p>
      <dl className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {[
          'IV aktuell',
          'IV-Veränderung (Prozentpunkte)',
          'Historisches IV-Perzentil / Rank',
          'Vega / monetäre Positionssensitivität',
          'Nächstes belegtes Ereignis',
          'Verlustszenario der Position',
        ].map((title) => (
          <div key={title} className="min-w-0">
            <dt className="text-slate-400">{title}</dt>
            <dd>Nicht verfügbar</dd>
          </div>
        ))}
      </dl>
      <p>
        IV ist ein aus einem Optionspreis unter Modellannahmen abgeleiteter Parameter, keine
        beobachtete künftige Schwankung oder Richtungsprognose. Hohe IV bedeutet nicht automatisch
        teuer; niedrige IV nicht automatisch günstig.
      </p>
      <details className="space-y-2">
        <summary className="cursor-pointer font-semibold">
          Warum IV-Kennzahlen fehlen · Daten und Grenzen
        </summary>
        {iv ? (
          <ul className="list-disc space-y-1 pl-5">
            {[...iv.reasons, iv.history_status, iv.event_status].map((reason) => (
              <li key={reason}>{label(reason)}</li>
            ))}
          </ul>
        ) : (
          <p>Diese ältere Auswertung enthält noch keine IV-Datenprüfung.</p>
        )}
        <p>
          Bewertet am {view.evaluated_at} · {iv?.policy_version ?? 'keine IV-Version'}. Gespeicherte
          Auswertungen sind Momentaufnahmen, keine gleichmäßig abgetastete IV-Historie.
        </p>
        <p>
          Quelle: {quote?.provider ?? view.quote_quality.provider ?? 'unbekannt'} · Kursroute:{' '}
          {quote?.identity_key ?? 'unbekannt'} · Kursart: {iv?.quote_side ?? 'unbekannt'}.
        </p>
        <p>
          Originalkurszeit Optionsschein: {view.quote_quality.observed_at ?? 'unbekannt'} ·
          Abrufzeit: {view.quote_quality.received_at ?? 'unbekannt'} · Alter:{' '}
          {iv?.quote_age_seconds == null ? 'unbekannt' : `${iv.quote_age_seconds} Sekunden`}.
        </p>
        <p>
          Basiswert: {view.listing?.symbol ?? 'unbekannt'} · Originalzeit eines passenden Kurses:
          unbekannt. Ein Handelstag oder Abrufzeitpunkt ist kein genauer Kurszeitpunkt.
        </p>
        <p>
          Währungen: Schein {quote?.quote?.currency ?? 'unbekannt'}, Basiswert{' '}
          {view.listing?.currency ?? 'unbekannt'}, Basispreis{' '}
          {view.product?.strike_currency ?? 'unbekannt'}. Bezugsverhältnis{' '}
          {view.product?.ratio ?? 'unbekannt'}; Konvention:{' '}
          {view.product?.ratio_convention === 'UNDERLYING_UNITS_PER_WARRANT'
            ? 'Basiswerteinheiten je Schein (manuell belegt)'
            : 'noch nicht bestätigt'}
          .
        </p>
        {view.product?.evidence_revision != null && (
          <p>
            Manuell geprüfter Produktbeleg, Revision {view.product.evidence_revision}:{' '}
            {view.product.evidence_document}. Bewertungszeitpunkt:{' '}
            {view.product.expiry_at ?? 'unbekannt'}. Die Anwendung hat den Beleg nicht selbst
            verifiziert.
          </p>
        )}
        <p>
          Feed-Verzögerung:{' '}
          {quote?.quote?.feed_delay_seconds == null
            ? 'unbekannt'
            : `${quote.quote.feed_delay_seconds} Sekunden`}{' '}
          · bestehende Altersgrenze:{' '}
          {quote?.quote?.max_quote_age_seconds == null
            ? 'unbekannt'
            : `${quote.quote.max_quote_age_seconds} Sekunden`}
          .
        </p>
        <p>
          Breite Spreads und kleines Vega können eine IV-Schätzung stark verzerren. IV und
          Zeitwertverlust sind getrennte Größen. Vor Ereignissen steigt IV häufig und fällt danach
          häufig; das ist keine Garantie. Ohne verifiziertes Ereignisdatum wird kein
          IV-Crush-Hinweis erzeugt.
        </p>
        <p>
          Die Historie eines einzelnen Scheins verändert sich mit Moneyness und Restlaufzeit.
          Skew/Smile, Laufzeitstruktur und Regimewechsel begrenzen Vergleiche; fehlende Werte sind
          keine Nullwerte.
        </p>
        <p>
          Stop-/Zielregeln und ihre Benachrichtigungen bleiben unverändert. Die Schwellen der
          realisierten Volatilität werden nicht auf IV übertragen. Aus fehlenden IV-Daten folgt
          keine Entwarnung.
        </p>
      </details>
      {view.product?.warrant_id && (
        <WarrantQuoteHistory key={view.product.warrant_id} warrantId={view.product.warrant_id} />
      )}
      <IvModelCalculator key={view.trade_id} tradeId={view.trade_id} />
    </section>
  );
}
