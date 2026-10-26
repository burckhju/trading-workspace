import { describe, expect, it } from 'vitest';
import { chartCatalog, chartIdentity } from '../../../test/chartFixtures';
import { MarketTransportError } from '../../market/services/http';
import type { SetupDraft, SetupSelection, SetupSnapshot } from './referenceSetup';
import { validateSetupReceipt } from './referenceSetupReceipt';
import type { ProviderMapping } from './topDownAdminClient';

const mapping: ProviderMapping = {
  id: 'mapping',
  workspace_id: 'workspace',
  listing_id: 'secondary',
  market_data_instrument_id: 'listing-instrument',
  provider: 'EODHD',
  provider_symbol: 'TEST',
  provider_exchange_code: 'XETRA',
  status: 'ACTIVE',
  validated_at: '2026-10-25T12:00:00Z',
  validation_message: 'Technically validated',
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-25T12:00:00Z',
  version: 3,
};
const selection = (action: SetupSelection['action'] = 'listingMapping'): SetupSelection => ({
  action,
  underlyingId: 'actual-owner',
  listingId: 'secondary',
  referenceId: 'sp500',
  sectorId: '',
  mappingId: '',
});
const draft: SetupDraft = {
  code: ' energy ',
  name: ' Energy ',
  system: ' GICS ',
  version: ' 2026 ',
  region: ' de ',
  symbol: ' changed ',
  exchange: ' xetra ',
  source: 'https://example.test/evidence',
  basis: 'PRICE_INDEX',
  start: '2026-10-26',
  end: '2026-10-26',
};
const snapshot = (overrides: Partial<SetupSnapshot> = {}): SetupSnapshot => ({
  catalog: chartCatalog(),
  references: [],
  sectors: [],
  reference: null,
  sector: null,
  identity: chartIdentity(),
  underlying: null,
  listing: {
    id: 'secondary',
    underlying_id: 'actual-owner',
    trading_venue_id: 'venue',
    trading_venue_mic: 'XETR',
    trading_venue_name: 'Test',
    ticker: 'TEST',
    currency_code: 'EUR',
    lifecycle_status: 'ACTIVE',
    is_primary: false,
    version: 1,
    created_at: '2026-10-01T12:00:00Z',
    updated_at: '2026-10-01T12:00:00Z',
  },
  mapping,
  venue: null,
  venueError: '',
  chartContext: null,
  ...overrides,
});
const saved = () => ({
  ...mapping,
  provider_symbol: 'CHANGED',
  status: 'DISABLED',
  validated_at: null,
  version: 4,
});

describe('mapping write receipts', () => {
  it('accepts an exact normalized disabled PUT receipt with increased revision', () => {
    expect(() =>
      validateSetupReceipt(selection(), snapshot(), draft, false, saved()),
    ).not.toThrow();
    expect(() =>
      validateSetupReceipt(selection(), snapshot(), draft, false, { ...saved(), version: 5 }),
    ).not.toThrow();
  });

  it.each([
    {},
    null,
    { ...saved(), id: 'foreign' },
    { ...saved(), workspace_id: 'foreign' },
    { ...saved(), listing_id: 'primary' },
    { ...saved(), market_data_instrument_id: 'foreign' },
    { ...saved(), provider: 'JPMORGAN' },
    { ...saved(), version: 3 },
    { ...saved(), provider_symbol: 'TEST' },
    { ...saved(), provider_exchange_code: 'US' },
    { ...saved(), status: 'ACTIVE' },
    { ...saved(), validated_at: '2026-10-25T12:00:00Z' },
  ])(
    'treats a malformed, stale or foreign result as unknown instead of a completed own PUT',
    (result) => {
      expect(() => validateSetupReceipt(selection(), snapshot(), draft, false, result)).toThrow(
        MarketTransportError,
      );
    },
  );

  it('accepts both explicit technical outcomes of validation but requires a new validation stamp', () => {
    for (const status of ['ACTIVE', 'INVALID']) {
      expect(() =>
        validateSetupReceipt(selection('listingValidate'), snapshot(), draft, true, {
          ...mapping,
          version: 4,
          status,
          validated_at: '2026-10-26T12:00:00Z',
        }),
      ).not.toThrow();
    }
    expect(() =>
      validateSetupReceipt(selection('listingValidate'), snapshot(), draft, true, {
        ...mapping,
        version: 4,
        validated_at: null,
      }),
    ).toThrow(MarketTransportError);
    expect(() =>
      validateSetupReceipt(selection('listingValidate'), snapshot(), draft, true, {
        ...mapping,
        version: 4,
        provider_symbol: 'OTHER',
      }),
    ).toThrow(MarketTransportError);
  });

  it('uses the actual listing-free reference receipt without demanding invented timestamps or reference_id', () => {
    const direct = {
      ...mapping,
      id: 'm',
      listing_id: null,
      market_data_instrument_id: 'reference:sp500',
    };
    const result: Record<string, unknown> = {
      ...direct,
      provider_symbol: 'CHANGED',
      status: 'DISABLED',
      validated_at: null,
      version: 4,
    };
    delete result.created_at;
    delete result.updated_at;
    expect(() =>
      validateSetupReceipt(
        selection('referenceMapping'),
        snapshot({ mapping: direct }),
        draft,
        false,
        result,
      ),
    ).not.toThrow();
    expect(() =>
      validateSetupReceipt(
        selection('referenceMapping'),
        snapshot({ mapping: direct }),
        draft,
        false,
        { ...result, listing_id: 'invented' },
      ),
    ).toThrow(MarketTransportError);
    expect(() =>
      validateSetupReceipt(
        selection('referenceMapping'),
        snapshot({ mapping: direct }),
        draft,
        false,
        { ...result, market_data_instrument_id: 'foreign' },
      ),
    ).toThrow(MarketTransportError);
  });

  it('allows a new reference instrument from the write receipt pending subsequent catalogue readback', () => {
    const empty = snapshot({
      mapping: null,
      identity: {
        ...chartIdentity(),
        instrument_id: null,
        mapping_id: null,
        mapping_version: null,
      },
    });
    expect(() =>
      validateSetupReceipt(selection('referenceMapping'), empty, draft, false, {
        ...saved(),
        listing_id: null,
        market_data_instrument_id: 'new-instrument',
        version: 1,
      }),
    ).not.toThrow();
    expect(() =>
      validateSetupReceipt(selection('referenceMapping'), empty, draft, false, {
        ...saved(),
        listing_id: null,
        market_data_instrument_id: null,
        version: 1,
      }),
    ).toThrow(MarketTransportError);
  });

  it('checks a supplied mapping identity even when no old mapping object was retained', () => {
    expect(() =>
      validateSetupReceipt(
        { ...selection(), mappingId: 'different' },
        snapshot(),
        draft,
        false,
        saved(),
      ),
    ).toThrow(MarketTransportError);
  });
});

describe('other supported command receipts', () => {
  it.each([false, true])(
    'verifies assignment validity/origin without inventing response owner fields (candidate=%s)',
    (candidate) => {
      const result = {
        id: 'assignment',
        valid_from: '2026-10-26',
        valid_to: null,
        source: candidate ? 'MANUAL_ADMIN' : 'CHART_SETUP',
        quality_status: 'GOOD',
        created_at: '2026-10-26T12:00:00Z',
      };
      expect(() =>
        validateSetupReceipt(selection('stockSector'), snapshot(), draft, candidate, result),
      ).not.toThrow();
      expect(() =>
        validateSetupReceipt(selection('sectorReference'), snapshot(), draft, candidate, result),
      ).not.toThrow();
      expect(() =>
        validateSetupReceipt(selection('stockSector'), snapshot(), draft, candidate, {
          ...result,
          valid_from: '2026-10-25',
        }),
      ).toThrow(MarketTransportError);
      expect(() =>
        validateSetupReceipt(selection('stockSector'), snapshot(), draft, candidate, {
          ...result,
          source: 'OTHER',
        }),
      ).toThrow(MarketTransportError);
    },
  );

  it('checks exact listing import identity, requested period and persistence counts', () => {
    const result = {
      listing_id: 'secondary',
      mapping_id: 'mapping',
      workspace_id: 'workspace',
      provider: 'EODHD',
      start_date: draft.start,
      end_date: draft.end,
      inserted: 1,
      updated: 2,
      unchanged: 3,
      processed: 6,
    };
    expect(() =>
      validateSetupReceipt(selection('listingImport'), snapshot(), draft, false, result),
    ).not.toThrow();
    for (const change of [
      { listing_id: 'primary' },
      { mapping_id: 'foreign' },
      { end_date: '2026-10-25' },
      { inserted: -1 },
      { processed: 7 },
    ]) {
      expect(() =>
        validateSetupReceipt(selection('listingImport'), snapshot(), draft, false, {
          ...result,
          ...change,
        }),
      ).toThrow(MarketTransportError);
    }
  });

  it('checks direct import reference/instrument/map identity without requiring a listing DTO', () => {
    const result = {
      market_reference_id: 'sp500',
      market_data_instrument_id: 'reference:sp500',
      mapping_id: 'm',
      currency: 'USD',
      start_date: draft.start,
      end_date: draft.end,
      inserted: 0,
      updated: 0,
      unchanged: 0,
    };
    const direct = snapshot({
      mapping: {
        ...mapping,
        id: 'm',
        listing_id: null,
        market_data_instrument_id: 'reference:sp500',
      },
    });
    expect(() =>
      validateSetupReceipt(selection('referenceImport'), direct, draft, false, result),
    ).not.toThrow();
    expect(() =>
      validateSetupReceipt(selection('referenceImport'), direct, draft, false, {
        ...result,
        market_reference_id: 'other',
      }),
    ).toThrow(MarketTransportError);
    expect(() =>
      validateSetupReceipt(selection('referenceImport'), direct, draft, false, {
        ...result,
        currency: '',
      }),
    ).toThrow(MarketTransportError);
  });

  it('checks creation values according to existing backend normalization', () => {
    const common = {
      id: 'new',
      code: 'ENERGY',
      name: 'Energy',
      active: true,
      created_at: '2026-10-26T12:00:00Z',
    };
    expect(() =>
      validateSetupReceipt(selection('sector'), snapshot(), draft, false, {
        ...common,
        classification_system: 'GICS',
        classification_version: '2026',
      }),
    ).not.toThrow();
    const reference = {
      ...common,
      region: 'DE',
      reference_version: '2026',
      reference_type: 'SECTOR_INDEX',
      role: 'SECTOR_REFERENCE',
    };
    expect(() =>
      validateSetupReceipt(selection('reference'), snapshot(), draft, false, reference),
    ).not.toThrow();
    expect(() =>
      validateSetupReceipt(selection('reference'), snapshot(), draft, false, {
        ...reference,
        role: 'BROAD_MARKET',
      }),
    ).toThrow(MarketTransportError);
  });

  it('recognizes the limited basis response and the complete bootstrap response', () => {
    expect(() =>
      validateSetupReceipt(selection('basis'), snapshot(), draft, false, {
        id: 'evidence',
        return_basis: 'PRICE_INDEX',
      }),
    ).not.toThrow();
    expect(() =>
      validateSetupReceipt(selection('basis'), snapshot(), draft, false, {
        id: 'evidence',
        return_basis: 'TOTAL_RETURN_INDEX',
      }),
    ).toThrow(MarketTransportError);
    const result = ['DAX', 'SP500', 'NASDAQ100'].map((code) => ({ code, id: code, name: code }));
    expect(() =>
      validateSetupReceipt(selection('bootstrap'), snapshot(), draft, false, result),
    ).not.toThrow();
    expect(() =>
      validateSetupReceipt(selection('bootstrap'), snapshot(), draft, false, result.slice(1)),
    ).toThrow(MarketTransportError);
  });
});
