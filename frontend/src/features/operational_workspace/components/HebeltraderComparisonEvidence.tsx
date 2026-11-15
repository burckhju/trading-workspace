import { useState } from 'react';
import type {
  TargetQualificationIssue,
  TargetQualificationPreview,
} from '../hebeltraderQualification';

export function QualificationIssues({ items }: { items: TargetQualificationIssue[] }) {
  return items.length > 0 ? (
    <ul className="list-disc space-y-1 pl-5">
      {items.map((item) => (
        <li key={`${item.code}:${item.detail}`}>
          {item.detail} <span className="text-xs">({item.code})</span>
        </li>
      ))}
    </ul>
  ) : null;
}

const control =
  'rounded border border-slate-600 px-3 py-2 focus-visible:outline-2 focus-visible:outline-sky-300 disabled:opacity-40';

export function HebeltraderComparisonEvidence({
  preview,
}: {
  preview: TargetQualificationPreview;
}) {
  const [page, setPage] = useState(1);
  const { source, history, entry } = preview;
  const rows = history.rows;
  const pages = Math.max(1, Math.ceil(rows.length / 25));
  const currentPage = Math.min(page, pages);
  const rowReviews = new Map(preview.readiness.rows.map((row) => [row.source_row_id, row]));
  return (
    <div className="min-w-0 space-y-4">
      <section aria-label="Historische Quelle für den Vergleich" className="space-y-2">
        <h4 className="font-semibold">Historische Hebeltrader-Quelle</h4>
        {source ? (
          <>
            <p>
              {source.filename} · Ausgabe {source.issue_date} · Version {source.version} ·{' '}
              {source.currentness === 'SOURCE_SUPERSEDED'
                ? 'Historische, inzwischen ersetzte Version bleibt gebunden'
                : 'Gebundene Quellenversion'}
              .
            </p>
            <p>
              Basiswertmarken in {source.underlying.binding.currency}: Referenz{' '}
              {source.underlying.reference_price}, Z1 {source.underlying.target_1}, Z2{' '}
              {source.underlying.target_2}. Originaleinheiten der Quelle, keine
              Anpassungsnormalisierung.
            </p>
            <p>
              Maßstabsreferenz: {preview.source_scale.source_scale_reference ?? 'Nicht belegt'}. Die
              bisherige Quellen-/Kaufprüfung qualifiziert diese Tageskursreihe nicht automatisch.
            </p>
            <details className="text-xs text-slate-300">
              <summary>Quellenherkunft und getrennte Zeiten</summary>
              <p>
                Quellenversion {source.source_version_id} · Beobachtung {source.observation_id} ·
                Vorgänger {source.supersedes_version_id ?? 'Keiner'}.
              </p>
              <p>
                Externe Referenz: {source.external_reference ?? 'Nicht hinterlegt'} · PDF-Hash:{' '}
                {source.content_hash}.
              </p>
              <p>
                Ausgabedatum {source.issue_date}, nur tagesgenau; keine belegte Publikationsuhrzeit.
                Gespeicherte Zeitmetadaten: {source.observed_at}.
              </p>
              <p>
                Importiert {source.imported_at} · Erfasst {source.recorded_at} · Import angenommen{' '}
                {source.accepted_at} durch {source.accepted_by}.
              </p>
              <p>
                Importzeile {source.import_row_id} · Batch {source.batch_id} · Datei{' '}
                {source.file_id}.
              </p>
            </details>
          </>
        ) : (
          <p>
            Keine geeignete gebundene Quelle verfügbar. Angefragte Version:{' '}
            {preview.attempted_source_version_id ?? 'Nicht vorhanden'}.
          </p>
        )}
        <QualificationIssues items={preview.source_issues} />
      </section>
      <section aria-label="Listing und Vergleichsbereich" className="space-y-2">
        <h4 className="font-semibold">Listing und gesamter Vergleichsbereich</h4>
        <p>
          Basiswert {entry.underlying_id} · Gehaltenes Produkt {entry.product_id} · Richtung{' '}
          {entry.option_direction ?? 'Unbekannt'}.
        </p>
        <p>
          Einstieg: {entry.opened_at ?? entry.opened_on ?? 'Nicht belegt'}
          {entry.opened_at === null && entry.opened_on
            ? ' (nur Datum, keine bekannte Uhrzeit)'
            : ''}{' '}
          · Kaufzeitzone: {entry.opening_timezone ?? 'Nicht belegt'}.
        </p>
        {history.binding ? (
          <>
            <p>
              Listing {history.binding.listing_id} · Handelsplatz {history.binding.venue_mic} ·
              Zeitzone {history.binding.timezone} · Listingwährung {history.binding.currency}.
            </p>
            <p className="text-amber-200">
              Aktuelle Listingreferenz; ihre historische Gültigkeit ist nicht unabhängig
              verifiziert. Eine gespeicherte Kurswährung kann aus dem Listing stammen.
              Providerzuordnung und technische Qualität allein belegen die historische Zuordnung
              nicht.
            </p>
            <details className="text-xs text-slate-300">
              <summary>Listingherkunft und Referenzstände</summary>
              <p>
                Handelsplatz-ID {history.binding.trading_venue_id} · Referenzversion{' '}
                {history.binding.venue_reference_version} · Listingversion{' '}
                {history.binding.listing_version} · Handelsplatzversion{' '}
                {history.binding.venue_version}.
              </p>
              <p>
                Listing angelegt {history.binding.listing_recorded_at}, geändert{' '}
                {history.binding.listing_updated_at}. Handelsplatz angelegt{' '}
                {history.binding.venue_recorded_at}, geändert {history.binding.venue_updated_at}.
              </p>
              <p>Listing-Fingerprint: {history.binding.fingerprint}.</p>
            </details>
          </>
        ) : (
          <p>Passende Listingbindung fehlt.</p>
        )}
        <p>
          Gespeicherter Bereich {history.start_date} bis {history.end_date}: {rows.length}{' '}
          angezeigbare Kursbelege, davon {preview.readiness.usable_row_count} nach zusätzlicher
          Bestätigung geeignet. Die Bestätigung bezieht sich auf den gesamten benannten Bereich,
          nicht nur auf die sichtbare Seite.
        </p>
        <p>
          {history.stored_range_complete
            ? 'Gespeicherter Bereich vollständig gelesen.'
            : 'Gespeicherter Bereich nicht vollständig lesbar.'}{' '}
          {history.intervals_complete
            ? 'Die gelieferten Tagesintervalle sind abgeschlossen.'
            : 'Nicht alle gelieferten Tagesintervalle sind als abgeschlossen belegt.'}{' '}
          Kalenderabdeckung ist nicht geprüft; Kurslücken sind keine belegten Feiertage.
        </p>
        <details className="text-xs text-slate-300">
          <summary>Kursbestand und Lesestand</summary>
          <p>
            Bestandsstatus {history.status} · Beobachtete Zeilen {history.rows_observed} · Grenze{' '}
            {history.row_limit}.
          </p>
          <p>
            Kursbestand-Fingerprint {history.fingerprint} · Kenntnisstand {history.known_at} ·
            Gelesen {history.read_at}.
          </p>
          <p>
            Atomare Prüfbasis {preview.report.current_basis_id} · Letzter Prüfstand{' '}
            {preview.report.latest_assessment?.id ?? 'Keiner'}.
          </p>
          {history.reasons.length > 0 && <p>Ownergründe: {history.reasons.join(', ')}.</p>}
        </details>
      </section>
      <section aria-label="Originalkursbelege" className="space-y-2">
        <h4 className="font-semibold">Gespeicherte Originalkurse des Basiswerts</h4>
        <p>
          Tagesintervalle sind ganze lokale Kalendertage, keine verifizierten Handelssitzungen.
          Abruf und Erfassung sind keine Kurs- oder Trefferuhrzeit.
        </p>
        {rows.length === 0 ? (
          <p>Keine Originalkurszeilen in dieser Antwort verfügbar.</p>
        ) : (
          <>
            <div className="max-w-full overflow-x-auto">
              <table
                aria-label="Gespeicherte Basiswert-Tageskurse"
                className="w-full text-left text-xs"
              >
                <thead>
                  <tr>
                    {['Tag / Tageshoch', 'Quelle / Währung', 'Eignung und Originalbelege'].map(
                      (label) => (
                        <th key={label} scope="col" className="p-2">
                          {label}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {rows.slice((currentPage - 1) * 25, currentPage * 25).map((row) => (
                    <tr key={row.source_row_id} className="border-t border-slate-700 align-top">
                      <td className="p-2">
                        <time dateTime={row.trading_date}>{row.trading_date}</time>
                        <p>
                          {row.high} {row.currency}
                        </p>
                      </td>
                      <td className="p-2">
                        {row.provider} · {row.provider_symbol}
                        <p>
                          {row.currency} · {row.price_type} · {row.quality_status}
                        </p>
                      </td>
                      <td className="space-y-1 p-2">
                        <p>
                          {rowReviews.get(row.source_row_id)?.status ===
                          'SUITABLE_AFTER_CONFIRMATION'
                            ? 'Nach konkreter Vergleichsbestätigung geeignet'
                            : rowReviews.has(row.source_row_id)
                              ? 'Ungeeignet'
                              : 'Wegen übergeordneter Sperre nicht zeilenweise geprüft'}
                        </p>
                        <QualificationIssues
                          items={rowReviews.get(row.source_row_id)?.issues ?? []}
                        />
                        <details>
                          <summary>Originalwerte, Identität und Zeiten</summary>
                          <p>
                            Open {row.open} · High {row.high} · Low {row.low} · Close {row.close}{' '}
                            {row.currency}.
                          </p>
                          <p>
                            Adjusted Close {row.adjusted_close ?? 'Nicht vorhanden'} · Volumen{' '}
                            {row.volume ?? 'Nicht vorhanden'}.
                          </p>
                          <p>
                            {row.scale_status === 'ADJUSTMENT_INDICATION_PRESENT'
                              ? 'Anpassungsindiz vorhanden; daraus wird kein Splitfaktor abgeleitet.'
                              : 'Gemeinsamer Originalmaßstab benötigt eine konkrete Vergleichsbestätigung.'}
                          </p>
                          <p>
                            Warnungen:{' '}
                            {row.warnings.length ? row.warnings.join('; ') : 'Keine gespeichert'} ·
                            Eignungsgründe:{' '}
                            {row.issues.length
                              ? row.issues.join('; ')
                              : 'Keine zusätzlichen gespeichert'}
                            .
                          </p>
                          <p>
                            Kalendertag-Intervall: {row.interval_start ?? 'Unbekannt'} bis{' '}
                            {row.interval_end ?? 'Unbekannt'} (Ende exklusiv). Nur tagesgenau.
                          </p>
                          <p>
                            Quelle aktualisiert {row.source_updated_at ?? 'Unbekannt'} · Abgerufen{' '}
                            {row.retrieved_at} · Erfasst {row.recorded_at} · Speicherstand geändert{' '}
                            {row.last_updated_at}.
                          </p>
                          <p>
                            Zeile {row.source_row_id} · Listing {row.listing_id} · Dateninstrument{' '}
                            {row.market_data_instrument_id ?? 'Nicht zugeordnet'} · Fingerprint{' '}
                            {row.fingerprint}.
                          </p>
                        </details>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <nav
              aria-label="Seiten der Originalkursbelege"
              className="flex flex-wrap items-center gap-2"
            >
              <button
                type="button"
                className={control}
                disabled={currentPage <= 1}
                onClick={() => setPage(currentPage - 1)}
              >
                Vorherige Kursseite
              </button>
              <span>
                Seite {currentPage} von {pages} · {rows.length} Kursbelege insgesamt
              </span>
              <button
                type="button"
                className={control}
                disabled={currentPage >= pages}
                onClick={() => setPage(currentPage + 1)}
              >
                Nächste Kursseite
              </button>
            </nav>
          </>
        )}
      </section>
    </div>
  );
}
