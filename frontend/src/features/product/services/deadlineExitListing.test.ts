import { MarketApiError, requestJson } from '../../market/services/http';
import { deadlineExitReport, savedDeadlineExitReport } from '../test/deadlineExitListingFixture';
import {
  readDeadlineExitListing,
  saveDeadlineExitListing,
  verifyDeadlineExitListing,
} from './deadlineExitListing';

vi.mock('../../market/services/http', async (original) => ({
  ...(await original<typeof import('../../market/services/http')>()),
  requestJson: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(requestJson).mockReset();
});

it('reads the product-scoped existing listing choices without sending a command', async () => {
  const report = deadlineExitReport({ warrant_id: 'synthetic/product' });
  vi.mocked(requestJson).mockResolvedValue(report);
  const signal = new AbortController().signal;
  expect(await readDeadlineExitListing(report.warrant_id, signal)).toBe(report);
  expect(requestJson).toHaveBeenCalledExactlyOnceWith(
    expect.stringMatching(/warrants\/synthetic%2Fproduct\/deadline-exit-listing$/),
    { signal },
  );
});

it('derives every concurrency guard from the read report and chosen actual listing', async () => {
  const report = deadlineExitReport();
  vi.mocked(requestJson).mockResolvedValue(savedDeadlineExitReport());
  await saveDeadlineExitListing(report.warrant_id, report, 'synthetic-listing');
  expect(requestJson).toHaveBeenCalledExactlyOnceWith(
    expect.stringMatching(/deadline-exit-listing$/),
    {
      method: 'PUT',
      body: {
        listing_id: 'synthetic-listing',
        expected_revision_number: 0,
        expected_terms_id: 'synthetic-terms',
        expected_listing_version: 3,
        expected_venue_version: 2,
      },
    },
  );
});

it('uses an explicit withdrawal with no fabricated listing or client request identity', async () => {
  const report = savedDeadlineExitReport();
  vi.mocked(requestJson).mockResolvedValue(
    deadlineExitReport({ revision_number: 2, reasons: ['PRODUCT_EXIT_LISTING_WITHDRAWN'] }),
  );
  await saveDeadlineExitListing(report.warrant_id, report, null);
  expect(requestJson).toHaveBeenCalledExactlyOnceWith(
    expect.stringMatching(/deadline-exit-listing$/),
    {
      method: 'PUT',
      body: {
        listing_id: null,
        expected_revision_number: 1,
        expected_terms_id: 'synthetic-terms',
        expected_listing_version: null,
        expected_venue_version: null,
      },
    },
  );
});

it('rejects invented or foreign listing choices before any write', async () => {
  const report = deadlineExitReport();
  await expect(
    saveDeadlineExitListing(report.warrant_id, report, 'foreign-listing'),
  ).rejects.toThrow(/vorhandenen Notierungen/);
  await expect(
    saveDeadlineExitListing('foreign-warrant', report, 'synthetic-listing'),
  ).rejects.toThrow(/anderen Produkt/);
  expect(requestJson).not.toHaveBeenCalled();
});

it('rejects foreign reports and inconsistent usable selections without selecting a fallback', () => {
  const report = deadlineExitReport();
  const invalid = [
    null,
    { ...report, warrant_id: 'foreign' },
    { ...report, definition_version: 'future' },
    { ...report, status: 'AVAILABLE' },
    { ...report, revision_number: -1 },
    { ...report, available_listings: [...report.available_listings, ...report.available_listings] },
    { ...savedDeadlineExitReport(), selected_venue_mic: 'FOREIGN' },
    { ...report, available_listings: [{ ...report.available_listings[0], venue_version: null }] },
  ];
  for (const value of invalid)
    expect(() => verifyDeadlineExitListing(value, report.warrant_id)).toThrow(
      /Ausstiegshandelsplatz/,
    );
  const withdrawn = deadlineExitReport({
    reasons: ['PRODUCT_EXIT_LISTING_WITHDRAWN'],
    revision_number: 2,
  });
  expect(verifyDeadlineExitListing(withdrawn, report.warrant_id).selected_listing_id).toBeNull();
});

it('explains absent product terms without requesting technical identifiers', async () => {
  vi.mocked(requestJson).mockRejectedValue(
    new MarketApiError(409, {
      code: 'PRODUCT_EXIT_TERMS_MISSING',
      message: 'Missing synthetic terms',
      details: [],
      timestamp: '2026-11-18T15:30:00Z',
    }),
  );
  await expect(readDeadlineExitListing('synthetic-warrant')).rejects.toThrow(
    /Aktuelle Produktbedingungen fehlen/,
  );
});
