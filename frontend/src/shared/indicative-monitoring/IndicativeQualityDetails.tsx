interface Props {
  sourceQuoteAt?: string | null;
  sourceTimeBasis?: string | null;
  sourceFreshness?: string | null;
  productScaleQuality?: string | null;
  historyContinuityAssumed?: boolean | null;
}

const timeLabels: Record<string, string> = {
  ORIGINAL_BID_TIME: 'Eigene Original-Geldkurszeit',
  SHARED_QUOTE_TIME: 'Gemeinsame Kurszeit der Quelle; keine eigene BID-Zeit',
  ORIGINAL_TIME_UNKNOWN: 'Original-Kurszeit unbekannt',
};
const freshnessLabels: Record<string, string> = {
  WITHIN_900_SECONDS: 'Bis 900 Sekunden bei Bewertung',
  WITHIN_1800_SECONDS: 'Verzögert · bis 1.800 Sekunden bei Bewertung',
  UNKNOWN: 'Unbekannt; die Empfangszeit belegt kein Kursalter',
};
const scaleLabels: Record<string, string> = {
  DOCUMENTED: 'Dokumentierter Produktmaßstab',
  CURRENT_UNIT_HISTORY_ASSUMED: 'Aktuelle Produkteinheit; historische Kontinuität angenommen',
  UNAVAILABLE: 'Produktmaßstab nicht ausreichend belegt',
};

function label(labels: Record<string, string>, key: string | null | undefined): string {
  return key && Object.hasOwn(labels, key) ? labels[key] : 'Nicht ausgewiesen';
}

/** Present the recorded owner grades; never infer age, continuity or market status. */
export function IndicativeQualityDetails(props: Props) {
  return (
    <div className="space-y-2 text-sm text-slate-300">
      <dl className="grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-slate-400">Zeitbezug der Quelle</dt>
          <dd>{label(timeLabels, props.sourceTimeBasis)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Kurszeit der Quelle</dt>
          <dd>{props.sourceQuoteAt ?? 'Nicht belegt'}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Kursalter im gespeicherten Prüfstand</dt>
          <dd>{label(freshnessLabels, props.sourceFreshness)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Produktmaßstab im gespeicherten Prüfstand</dt>
          <dd>{label(scaleLabels, props.productScaleQuality)}</dd>
        </div>
      </dl>
      {props.historyContinuityAssumed === true && (
        <p className="text-amber-200">
          Die unveränderte Produkteinheit seit dem Kauf ist angenommen, nicht historisch
          verifiziert. Bekannte Maßstabs- oder Währungswidersprüche sperren den Vergleich.
        </p>
      )}
      <p>Aktueller Instrumentmarktstatus nicht bestätigt; keine B58-Qualifikation.</p>
    </div>
  );
}
