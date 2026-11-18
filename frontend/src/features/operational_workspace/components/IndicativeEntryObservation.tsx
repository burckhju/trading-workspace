import { useEffect, useRef, useState } from 'react';
import {
  IndicativeQualityDetails,
  IndicativeCalendarDetails,
  indicativeReasonLabel,
} from '../../../shared/indicative-monitoring';
import type { IndicativeEntryReport, IndicativeOutcome } from '../indicativeEntry';
import { readIndicativeEntry } from '../services/indicativeEntry';

interface Props {
  tradeId: string;
  positionId: string;
  reloadToken?: string | number;
}

const outcomes: Record<IndicativeOutcome, string> = {
  BELOW_ENTRY: 'Indikativer Geldkurs unter persönlichem Bruttoeinstand',
  AT_OR_ABOVE_ENTRY: 'Indikativer Geldkurs mindestens auf persönlichem Bruttoeinstand',
  NOT_REACHED: '20 Sitzungen für diesen Kursvergleich noch nicht abgeschlossen',
  UNAVAILABLE: 'Einstandsvergleich nicht auswertbar',
  CLOSED: 'Position geschlossen oder storniert',
};
const episodeLabels = {
  ENTRY_LOSS: 'Indikativer Verlusthinweis bleibt offen',
  REVIEW_DUE: '20-Sitzungen-Prüfhinweis bleibt offen',
  DATA_UNAVAILABLE: 'Datenproblem bleibt offen',
};

const readinessLabels: Record<string, string> = {
  AVAILABLE: 'Dokumentbeschaffung abgeschlossen',
  STARTED: 'Dokumentbeschaffung begonnen; Abschluss noch nicht belegt',
  PRODUCT_DOCUMENT_PROVIDER_UNSUPPORTED:
    'Für diesen Emittenten ist kein unterstützter Originaldokumentpfad hinterlegt.',
  PRODUCT_DOCUMENT_ACQUISITION_FAILED: 'Letzter Dokumentabruf fehlgeschlagen',
  REVIEW_READINESS_PARTIAL:
    'Dokumentbeschaffung teilweise abgeschlossen; Voraussetzungen sind noch offen.',
};

const readinessProblemLabels: Record<string, string> = {
  'NYSE:REVIEW_CALENDAR_SOURCE_REVISION_CHANGED':
    'NYSE: Die Originalkalenderquelle hat sich geändert; der neue Stand ist noch nicht qualifiziert.',
  'XSTU:REVIEW_CALENDAR_SOURCE_REVISION_CHANGED':
    'Börse Stuttgart: Die Originalkalenderquelle hat sich geändert; der neue Stand ist noch nicht qualifiziert.',
  'NYSE:REVIEW_CALENDAR_SOURCE_UNAVAILABLE':
    'NYSE: Die Originalkalenderquelle konnte nicht abgerufen werden.',
  'XSTU:REVIEW_CALENDAR_SOURCE_UNAVAILABLE':
    'Börse Stuttgart: Die Originalkalenderquelle konnte nicht abgerufen werden.',
  'PRODUCT:PRODUCT_DOCUMENT_IDENTITY_UNVERIFIED':
    'Das Originaldokument konnte diesem Produkt nicht eindeutig zugeordnet werden.',
  'PRODUCT:PRODUCT_DOCUMENT_SOURCE_BINDING_MISMATCH':
    'Das Originaldokument passt nicht zur gespeicherten Produkt- und Quellenbindung.',
  'PRODUCT:PRODUCT_DOCUMENT_TOO_LARGE':
    'Das Originaldokument überschreitet die unterstützte Dokumentgröße.',
  'PRODUCT:PRODUCT_DOCUMENT_NOT_PDF':
    'Die Produktquelle hat kein verwendbares Original-PDF geliefert.',
};

function Observation({ tradeId, positionId }: Props) {
  const [report, setReport] = useState<IndicativeEntryReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const generation = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    const currentGeneration = ++generation.current;
    const current = () => !controller.signal.aborted && currentGeneration === generation.current;
    readIndicativeEntry(tradeId, positionId, controller.signal)
      .then((value) => {
        if (current()) setReport(value);
      })
      .catch((reason: unknown) => {
        if (current())
          setError(
            reason instanceof Error ? reason.message : 'Indikativer Prüfstand nicht verfügbar.',
          );
      });
    return () => {
      generation.current += 1;
      controller.abort();
    };
  }, [tradeId, positionId]);

  const latest = report?.latest_assessment;
  const openLoss = report?.active_episodes.some((episode) => episode.kind === 'ENTRY_LOSS');
  return (
    <section
      aria-label="Indikative Depotbeobachtung"
      className="min-w-0 space-y-3 rounded-xl border border-slate-700 bg-slate-950/40 p-3 sm:p-4"
    >
      <h3 className="font-semibold text-white">Indikative Depotbeobachtung · diese Position</h3>
      <p className="text-sm text-slate-300">
        Gespeicherte Vergleiche, Kalenderhinweise und Datenprobleme. Die Ansicht liest vorhandene
        Ergebnisse; sie löst keine Kursbeschaffung oder Regelauswertung aus.
      </p>
      {!report && !error && <p>Gespeicherter indikativer Prüfstand wird gelesen …</p>}
      {error && <p role="alert">{error}</p>}
      {report && (
        <>
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-slate-400">Gewählter Regelumfang</dt>
              <dd>
                {report.scope} · {report.definition_version}
              </dd>
            </div>
            <div>
              <dt className="text-slate-400">Aktivierung</dt>
              <dd>
                {report.activation_status === 'SCOPE_ENABLED'
                  ? 'Teilumfang zentral eingeschaltet'
                  : 'Nicht aktiviert'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-400">Hintergrundrunner konfiguriert</dt>
              <dd>
                {report.runner_enabled
                  ? 'Aktiviert; laufender Betrieb separat nachzuweisen'
                  : 'Deaktiviert'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-400">Externe Zustellung dieses Teilumfangs</dt>
              <dd>
                {report.notifications_enabled
                  ? 'Konfiguriert; tatsächlichen Versand am Hinweis prüfen'
                  : 'Ausgeschaltet; Hinweise bleiben im Arbeitsbereich'}
              </dd>
            </div>
          </dl>
          <p className="text-amber-200">
            Indikativer Teilumfang. Keine qualifizierte B04/B57-Überwachung und keine vollständige
            Hebeltrader-Baseline aktiviert.
          </p>
          {report.document_readiness !== undefined && (
            <section
              aria-label="Dokumentbeschaffung"
              className="space-y-2 rounded border border-slate-700 p-3"
            >
              <h4 className="font-semibold">Dokumentbeschaffung</h4>
              {report.document_readiness ? (
                <>
                  <p>
                    {Object.hasOwn(readinessLabels, report.document_readiness.outcome)
                      ? readinessLabels[report.document_readiness.outcome]
                      : 'Gespeicherter Beschaffungsstand nicht eingeordnet.'}
                  </p>
                  <p className="text-xs text-slate-400">
                    Letzter Versuch: {report.document_readiness.attempted_at}
                  </p>
                  <p className="text-xs text-slate-400">
                    Nächster vorgesehener Beschaffungsversuch:{' '}
                    {report.document_readiness.next_attempt_at}
                  </p>
                  {Boolean(report.document_readiness.problems?.length) && (
                    <ul
                      aria-label="Offene Beschaffungsvoraussetzungen"
                      className="space-y-1 text-sm text-amber-200"
                    >
                      {report.document_readiness.problems?.map((problem, index) => (
                        <li key={`${problem}:${index}`}>
                          {Object.hasOwn(readinessProblemLabels, problem)
                            ? readinessProblemLabels[problem]
                            : `Weitere Beschaffungsdiagnose: ${problem}`}
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              ) : (
                <p>Noch kein Dokumentabruf protokolliert.</p>
              )}
              <p className="text-xs text-slate-400">
                Dieser Beschaffungsstand bleibt von gespeicherten Bewertungen getrennt. Ein
                Abruffehler zieht vorhandene Belege nicht zurück. Der nächste Versuch ist keine
                Gültigkeitsfrist der Belege.
              </p>
            </section>
          )}
          <section
            aria-label="Offene indikative Hinweise"
            className="space-y-2 rounded border border-slate-700 p-3"
          >
            <h4 className="font-semibold">Offene gespeicherte Hinweise</h4>
            {report.active_episodes.length > 0 ? (
              <ul className="space-y-2">
                {report.active_episodes.map((episode) => (
                  <li key={episode.id}>
                    <p>
                      {episodeLabels[episode.kind]} · Episode {episode.episode_number}
                    </p>
                    <p className="text-xs text-slate-400">
                      Eröffnet: <time dateTime={episode.opened_at}>{episode.opened_at}</time>
                      {episode.rule_version && ` · ${episode.rule_version}`}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p>
                Keine offenen Hinweise gespeichert. Das bestätigt keine aktuelle oder vollständige
                Datenversorgung.
              </p>
            )}
            {openLoss && latest?.outcome === 'UNAVAILABLE' && (
              <p className="text-amber-200">
                Die Datenlücke oder ungeeignete Entwarnung beendet den bestehenden Verlusthinweis
                nicht.
              </p>
            )}
          </section>
          <section aria-label="Letzter indikativer Prüfstand" className="space-y-3">
            <h4 className="font-semibold">Letzte gespeicherte Bewertung</h4>
            {latest ? (
              <>
                <p>{outcomes[latest.outcome]}</p>
                <p className="text-xs text-slate-400">
                  Bewertet: <time dateTime={latest.evaluated_at}>{latest.evaluated_at}</time> ·
                  Regelversion des Prüfstands:{' '}
                  {latest.rule_version ?? 'nicht gesondert ausgewiesen'}
                </p>
                <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <div>
                    <dt className="text-slate-400">Beobachteter Geldkurs · indikativ</dt>
                    <dd>{latest.bid ?? 'Nicht belegt'}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Persönlicher Bruttoeinstand je Stück</dt>
                    <dd>
                      {latest.gross_entry} {latest.currency ?? 'Währung nicht belegt'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Restmenge im Prüfstand</dt>
                    <dd>{latest.remaining_quantity}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Original-Geldkurszeit</dt>
                    <dd>{latest.original_bid_at ?? 'Nicht belegt'}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Empfangen am</dt>
                    <dd>{latest.received_at ?? 'Nicht belegt'}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Gespeicherte Quelle</dt>
                    <dd>
                      {latest.source.provider ?? 'Nicht belegt'} ·{' '}
                      {latest.source.venue_mic ?? 'Handelsplatz nicht ausgewiesen'}
                    </dd>
                  </div>
                </dl>
                <IndicativeQualityDetails
                  sourceQuoteAt={latest.source_quote_at}
                  sourceTimeBasis={latest.source_time_basis}
                  sourceFreshness={latest.source_freshness}
                  productScaleQuality={latest.product_scale_quality}
                  historyContinuityAssumed={latest.history_continuity_assumed}
                />
                {latest.source.quote_time_text && (
                  <p className="text-xs text-slate-400">
                    Zeitangabe der Quelle: {latest.source.quote_time_text} · kein Ersatz für eine
                    vollständige Original-Geldkurszeit.
                  </p>
                )}
                <p>
                  Sitzungen für den Kursvergleich: {latest.completed_sessions ?? 'Nicht belegt'} ·
                  zugehöriger Zeitbezug: {latest.session_count_at}.
                </p>
                <p>
                  Unabhängiger 20-Sitzungen-Prüfhinweis:{' '}
                  {latest.review_completed_sessions ?? 'Nicht belegt'} abgeschlossene Sitzungen zum
                  Prüfzeitpunkt. Die heutige Sitzungszahl qualifiziert keinen älteren Kurs
                  nachträglich.
                </p>
                <p className="text-xs text-slate-400">
                  Letzter belegter Statuspunkt:{' '}
                  {latest.source.source_status_point ?? 'nicht belegt'} · Originalstatuszeit:{' '}
                  {latest.source.source_status_observed_at ?? 'nicht belegt'} · erfasst:{' '}
                  {latest.source.source_status_captured_at ?? 'nicht belegt'}. Fortgeltung nicht
                  belegt.
                </p>
                <IndicativeCalendarDetails
                  dayPrecision={latest.session_day_precision}
                  quality={latest.calendar_quality}
                  verification={latest.calendar_verification}
                />
                <ul aria-label="Gründe des indikativen Prüfstands" className="space-y-1">
                  {latest.reasons.map((reason, index) => (
                    <li key={`${reason}:${index}`}>{indicativeReasonLabel(reason)}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p>Noch keine indikative Bewertung gespeichert.</p>
            )}
          </section>
          <p className="text-xs text-slate-400">
            {report.assessment_count} Bewertungen · {report.episode_count} Hinweisepisoden · gelesen
            am <time dateTime={report.read_at}>{report.read_at}</time>.
          </p>
          <p className="text-sm text-slate-300">
            Hinweise erfordern eine fachliche Prüfung. Sie erzeugen keine Orders,
            Ausführungsbuchungen oder automatischen Stop- und Zieländerungen.
          </p>
        </>
      )}
    </section>
  );
}

export function IndicativeEntryObservation(props: Props) {
  return (
    <Observation
      key={`${props.tradeId}:${props.positionId}:${props.reloadToken ?? 0}`}
      {...props}
    />
  );
}
