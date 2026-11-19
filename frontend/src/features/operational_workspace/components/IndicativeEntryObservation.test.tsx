import { act, render, screen, within } from '@testing-library/react';
import type { IndicativeEntryReport } from '../indicativeEntry';
import { readIndicativeEntry } from '../services/indicativeEntry';
import {
  indicativeAssessment,
  indicativeEpisode,
  indicativeReport,
} from '../test/indicativeEntryFixture';
import { IndicativeEntryObservation } from './IndicativeEntryObservation';

vi.mock('../services/indicativeEntry', () => ({ readIndicativeEntry: vi.fn() }));

beforeEach(() => {
  vi.mocked(readIndicativeEntry).mockReset().mockResolvedValue(indicativeReport());
});

const show = () =>
  render(<IndicativeEntryObservation tradeId="synthetic-trade" positionId="synthetic-position" />);

it('shows scope, activation and missing assessment without claiming running monitoring', async () => {
  show();
  expect(await screen.findByText('Nicht aktiviert')).toBeInTheDocument();
  expect(screen.getByText(/INDICATIVE_ENTRY_V2 · indicative-entry-review-v2/)).toBeInTheDocument();
  expect(screen.getByText(/Keine qualifizierte B04\/B57-Überwachung/)).toBeInTheDocument();
  expect(screen.getByText('Deaktiviert')).toBeInTheDocument();
  expect(screen.getByText(/Noch keine indikative Bewertung gespeichert/)).toBeInTheDocument();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(readIndicativeEntry).toHaveBeenCalledExactlyOnceWith(
    'synthetic-trade',
    'synthetic-position',
    expect.any(AbortSignal),
  );
});

it('keeps delayed source time, receipt, assumed scale and a weaker recovery separate from an active loss', async () => {
  const active = [
    indicativeEpisode(),
    indicativeEpisode({
      id: 'synthetic-data',
      kind: 'DATA_UNAVAILABLE',
      rule_version: 'indicative-entry-review-v2',
    }),
  ];
  vi.mocked(readIndicativeEntry).mockResolvedValue(
    indicativeReport({
      activation_status: 'SCOPE_ENABLED',
      runner_enabled: true,
      latest_assessment: indicativeAssessment({
        session_day_precision: 'CONSERVATIVE_DATE_BOUND',
        calendar_quality: 'CURRENT_DOCUMENT_REFERENCE_MARKET_ASSUMED',
        calendar_verification:
          'ENGINEERING_REVIEW_OF_ORIGINAL_CALENDAR_NOT_INDEPENDENT_VERIFICATION',
      }),
      assessment_count: 2,
      active_episodes: active,
      recent_episodes: active,
      episode_count: 2,
    }),
  );
  show();
  expect(await screen.findByText('Einstandsvergleich nicht auswertbar')).toBeInTheDocument();
  expect(screen.getByText(/Indikativer Verlusthinweis bleibt offen/)).toBeInTheDocument();
  expect(screen.getByText(/Datenproblem bleibt offen/)).toBeInTheDocument();
  expect(
    screen.getByText('Gemeinsame Kurszeit der Quelle; keine eigene BID-Zeit'),
  ).toBeInTheDocument();
  expect(screen.getByText('Verzögert · bis 1.800 Sekunden bei Bewertung')).toBeInTheDocument();
  expect(
    screen.getByText('Aktuelle Produkteinheit; historische Kontinuität angenommen'),
  ).toBeInTheDocument();
  expect(screen.getByText(/nicht historisch verifiziert/)).toBeInTheDocument();
  expect(screen.getByText(/schwächere Belegqualität/)).toHaveTextContent(
    'beendet den bestehenden Verlusthinweis nicht',
  );
  expect(screen.getByText(/Sitzungen für den Kursvergleich: 19/)).toHaveTextContent(
    '2026-11-18T15:10:00Z',
  );
  expect(screen.getByText(/Unabhängiger 20-Sitzungen-Prüfhinweis: 20/)).toBeInTheDocument();
  expect(
    screen.getByText('Sitzungszahl konservativ; Kaufdatum ohne genaue Uhrzeit.'),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/Referenzmarkt aus aktuellem Produktdokument angenommen/),
  ).toHaveTextContent('historische Basiswertlisting ist nicht unabhängig belegt');
  expect(
    screen.getByText('Originalkalender technisch geprüft; keine unabhängige Systemverifikation.'),
  ).toBeInTheDocument();
  const latest = within(screen.getByRole('region', { name: 'Letzter indikativer Prüfstand' }));
  expect(latest.getByText('Original-Geldkurszeit').nextElementSibling).toHaveTextContent(
    'Nicht belegt',
  );
  expect(latest.getByText('Empfangen am').nextElementSibling).toHaveTextContent(
    '2026-11-18T15:29:00Z',
  );
  expect(screen.getByText(/Letzter belegter Statuspunkt: OPEN/)).toHaveTextContent(
    'Fortgeltung nicht belegt',
  );
  expect(screen.getByText(/Aktueller Instrumentmarktstatus nicht bestätigt/)).toBeInTheDocument();
});

it('keeps unknown original age unknown despite a recent receipt', async () => {
  vi.mocked(readIndicativeEntry).mockResolvedValue(
    indicativeReport({
      latest_assessment: indicativeAssessment({
        source_quote_at: null,
        source_time_basis: 'ORIGINAL_TIME_UNKNOWN',
        source_freshness: 'UNKNOWN',
        evaluation_mode: 'INDICATIVE_ISSUER',
        product_scale_quality: 'DOCUMENTED',
        history_continuity_assumed: false,
        reasons: ['INDICATIVE_BID_BELOW_GROSS_ENTRY'],
        outcome: 'BELOW_ENTRY',
      }),
      assessment_count: 1,
    }),
  );
  show();
  expect(await screen.findByText('Original-Kurszeit unbekannt')).toBeInTheDocument();
  expect(screen.getByText('Unbekannt; die Empfangszeit belegt kein Kursalter')).toBeInTheDocument();
  expect(screen.getByText('Dokumentierter Produktmaßstab')).toBeInTheDocument();
  expect(screen.queryByText(/Bis 900 Sekunden/)).not.toBeInTheDocument();
  expect(screen.queryByText(/nicht historisch verifiziert/)).not.toBeInTheDocument();
});

it('explains a known currency contradiction as a blocked comparison without inventing a zero', async () => {
  vi.mocked(readIndicativeEntry).mockResolvedValue(
    indicativeReport({
      latest_assessment: indicativeAssessment({
        bid: null,
        reasons: ['EXECUTION_BID_CURRENCY_MISMATCH'],
        product_scale_quality: 'UNAVAILABLE',
        history_continuity_assumed: false,
      }),
      assessment_count: 1,
    }),
  );
  show();
  expect(
    await screen.findByText(/Ausführungswährung und Geldkurswährung widersprechen sich/),
  ).toHaveTextContent('Vergleich ist gesperrt');
  expect(
    screen.getByText('Beobachteter Geldkurs · indikativ').nextElementSibling,
  ).toHaveTextContent('Nicht belegt');
  expect(screen.queryByText('0')).not.toBeInTheDocument();
  expect(screen.queryByText('NaN')).not.toBeInTheDocument();
});

it('reports an unreadable status without inventing no open episodes', async () => {
  vi.mocked(readIndicativeEntry).mockRejectedValue(new Error('Synthetischer Lesefehler.'));
  show();
  expect(await screen.findByRole('alert')).toHaveTextContent('Synthetischer Lesefehler.');
  expect(screen.queryByText(/Keine offenen Hinweise/)).not.toBeInTheDocument();
});

it('shows a failed document fetch without withdrawing stored facts or treating retry time as expiry', async () => {
  const episode = indicativeEpisode();
  vi.mocked(readIndicativeEntry).mockResolvedValue(
    indicativeReport({
      document_readiness: {
        outcome: 'PRODUCT_DOCUMENT_ACQUISITION_FAILED',
        attempted_at: '2026-11-18T15:31:00Z',
        next_attempt_at: '2026-11-18T15:46:00Z',
        problems: [
          'NYSE:REVIEW_CALENDAR_SOURCE_REVISION_CHANGED',
          'XSTU:REVIEW_CALENDAR_SOURCE_UNAVAILABLE',
          'PRODUCT:PRODUCT_DOCUMENT_IDENTITY_UNVERIFIED',
        ],
      },
      latest_assessment: indicativeAssessment({
        outcome: 'BELOW_ENTRY',
        reasons: ['INDICATIVE_BID_BELOW_GROSS_ENTRY'],
      }),
      assessment_count: 1,
      active_episodes: [episode],
      recent_episodes: [episode],
      episode_count: 1,
    }),
  );
  show();
  expect(await screen.findByText('Letzter Dokumentabruf fehlgeschlagen')).toBeInTheDocument();
  expect(screen.getByText(/Indikativer Verlusthinweis bleibt offen/)).toBeInTheDocument();
  expect(
    screen.getByText('Indikativer Geldkurs unter persönlichem Bruttoeinstand'),
  ).toBeInTheDocument();
  const diagnostic = within(screen.getByRole('region', { name: 'Dokumentbeschaffung' }));
  expect(diagnostic.getByText(/Nächster vorgesehener Beschaffungsversuch:/)).toHaveTextContent(
    '2026-11-18T15:46:00Z',
  );
  expect(
    diagnostic.getByText(/Ein Abruffehler zieht vorhandene Belege nicht zurück/),
  ).toHaveTextContent('keine Gültigkeitsfrist');
  expect(diagnostic.queryByRole('button')).not.toBeInTheDocument();
  expect(
    diagnostic.getByText(/NYSE: Die Originalkalenderquelle hat sich geändert/),
  ).toBeInTheDocument();
  expect(
    diagnostic.getByText(/Börse Stuttgart: Die Originalkalenderquelle konnte nicht abgerufen/),
  ).toBeInTheDocument();
  expect(
    diagnostic.getByText(
      'Das Originaldokument konnte diesem Produkt nicht eindeutig zugeordnet werden.',
    ),
  ).toBeInTheDocument();
  expect(readIndicativeEntry).toHaveBeenCalledOnce();
});

function deferred() {
  let resolve!: (value: IndicativeEntryReport) => void;
  const promise = new Promise<IndicativeEntryReport>((yes) => {
    resolve = yes;
  });
  return { promise, resolve };
}

it('guards A to B to A navigation and does not poll or reuse obsolete responses', async () => {
  const first = deferred(),
    second = deferred(),
    third = deferred();
  vi.mocked(readIndicativeEntry)
    .mockReturnValueOnce(first.promise)
    .mockReturnValueOnce(second.promise)
    .mockReturnValueOnce(third.promise);
  const view = render(
    <IndicativeEntryObservation tradeId="synthetic-A" positionId="synthetic-A" />,
  );
  const firstSignal = vi.mocked(readIndicativeEntry).mock.calls[0][2];
  view.rerender(<IndicativeEntryObservation tradeId="synthetic-B" positionId="synthetic-B" />);
  expect(firstSignal?.aborted).toBe(true);
  view.rerender(<IndicativeEntryObservation tradeId="synthetic-A" positionId="synthetic-A" />);
  await act(async () => {
    third.resolve(indicativeReport());
    await third.promise;
  });
  await act(async () => {
    first.resolve(
      indicativeReport({ latest_assessment: indicativeAssessment(), assessment_count: 1 }),
    );
    second.resolve(indicativeReport({ activation_status: 'SCOPE_ENABLED' }));
    await Promise.all([first.promise, second.promise]);
  });
  expect(screen.getByText('Nicht aktiviert')).toBeInTheDocument();
  expect(screen.queryByText('Einstandsvergleich nicht auswertbar')).not.toBeInTheDocument();
  expect(readIndicativeEntry).toHaveBeenCalledTimes(3);
  const lastSignal = vi.mocked(readIndicativeEntry).mock.calls[2][2];
  view.unmount();
  expect(lastSignal?.aborted).toBe(true);
});
