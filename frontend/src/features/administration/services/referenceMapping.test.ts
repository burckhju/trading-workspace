import { describe, expect, it } from 'vitest';
import { chartIdentity } from '../../../test/chartFixtures';
import {
  mappingInputsChanged,
  MappingRevisionConflict,
  referenceBasisForMapping,
  requireCurrentMapping,
  resolveListingMapping,
  resolveReferenceMapping,
  sameMappingRevision,
} from './referenceMapping';
import type { ProviderMapping } from './topDownAdminClient';

const mapping = (overrides: Partial<ProviderMapping> = {}): ProviderMapping => ({
  id: 'mapping-secondary',
  workspace_id: 'workspace',
  listing_id: 'secondary-listing',
  market_data_instrument_id: 'listing-instrument',
  provider: 'EODHD',
  provider_symbol: 'SAP',
  provider_exchange_code: 'XETRA',
  status: 'ACTIVE',
  validated_at: '2026-10-25T12:00:00Z',
  validation_message: 'Technical validation passed',
  created_at: '2026-10-20T12:00:00Z',
  updated_at: '2026-10-25T12:00:00Z',
  version: 3,
  ...overrides,
});
const indexMapping = () =>
  mapping({
    id: 'm',
    listing_id: null,
    market_data_instrument_id: 'reference:sp500',
    provider_symbol: 'GSPC',
    provider_exchange_code: 'INDX',
    version: 1,
  });

describe('listing mapping identities', () => {
  it('uses the exact nonprimary listing and EODHD, irrespective of result order', () => {
    const exact = mapping();
    const values = [
      mapping({ id: 'primary', listing_id: 'primary-listing' }),
      indexMapping(),
      mapping({ id: 'other-provider', provider: 'JPMORGAN' }),
      exact,
    ];
    expect(resolveListingMapping(values, 'secondary-listing')).toBe(exact);
    expect(resolveListingMapping(values, 'secondary-listing', exact.id)).toBe(exact);
  });

  it('allows no mapping for creation but does not accept a missing explicit identity', () => {
    expect(resolveListingMapping([], 'secondary-listing')).toBeNull();
    expect(() => resolveListingMapping([], 'secondary-listing', 'missing')).toThrow(/Mapping-ID/);
    expect(() => resolveListingMapping([], '')).toThrow(/Notierung/);
  });

  it.each([
    mapping({ id: 'foreign', listing_id: 'foreign-listing' }),
    mapping({ id: 'foreign', provider: 'JPMORGAN' }),
    indexMapping(),
  ])('blocks a supplied mapping owned by another identity/provider', (foreign) => {
    expect(() =>
      resolveListingMapping([foreign, mapping()], 'secondary-listing', foreign.id),
    ).toThrow(/Mapping-ID/);
  });

  it('rejects multiple EODHD matches rather than selecting the first', () => {
    expect(() =>
      resolveListingMapping([mapping(), mapping({ id: 'second' })], 'secondary-listing'),
    ).toThrow(/Mehrdeutige/);
    expect(() =>
      resolveListingMapping([mapping(), mapping({ provider: 'JPMORGAN' })], 'secondary-listing'),
    ).toThrow(/Mapping-ID/);
  });

  it.each([{ version: 0 }, { version: 1.5 }, { provider_symbol: '' }, { status: 'UNKNOWN' }])(
    'blocks an incomplete full mapping response %j',
    (invalid) => {
      expect(() => resolveListingMapping([mapping(invalid)], 'secondary-listing')).toThrow(
        /unvollständig/,
      );
    },
  );
});

describe('listing-free reference mapping chain', () => {
  it('matches the structured DTO without interpreting the provider_identity label', () => {
    const identity = { ...chartIdentity(), provider_identity: 'not:parseable.text' };
    const value = indexMapping();
    expect(resolveReferenceMapping([mapping(), value], identity)).toBe(value);
    expect(value.provider_symbol).toBe('GSPC');
    expect(value.listing_id).toBeNull();
  });

  it('allows a genuinely new reference mapping without inventing a listing', () => {
    const identity = {
      ...chartIdentity(),
      instrument_id: null,
      mapping_id: null,
      mapping_version: null,
    };
    expect(resolveReferenceMapping([], identity)).toBeNull();
    expect(
      resolveReferenceMapping([], { ...identity, instrument_id: 'existing-instrument' }),
    ).toBeNull();
  });

  it.each([{ listing_id: 'invented-listing' }, { id: 'another-mapping' }, { version: 2 }])(
    'rejects a conflicting authoritative mapping %j',
    (conflict) => {
      expect(() =>
        resolveReferenceMapping([mapping({ ...indexMapping(), ...conflict })], chartIdentity()),
      ).toThrow(/stimmen nicht überein/);
    },
  );

  it('rejects stale catalogue, missing mapping and wrong instrument chains', () => {
    expect(() => resolveReferenceMapping([], chartIdentity())).toThrow(/fehlt/);
    expect(() =>
      resolveReferenceMapping([indexMapping()], { ...chartIdentity(), instrument_id: 'foreign' }),
    ).toThrow(/fehlt/);
    expect(() =>
      resolveReferenceMapping([indexMapping()], { ...chartIdentity(), mapping_id: null }),
    ).toThrow(/stimmen nicht überein/);
    expect(() => resolveReferenceMapping([indexMapping()], chartIdentity(), 'foreign')).toThrow(
      /Mapping-ID/,
    );
  });

  it('rejects multiple or listing-like reference identities', () => {
    expect(() =>
      resolveReferenceMapping([indexMapping(), indexMapping()], chartIdentity()),
    ).toThrow(/Mehrdeutige/);
    expect(() =>
      resolveReferenceMapping([], { ...chartIdentity(), listing_id: 'listing' }),
    ).toThrow(/listingfreie/);
    expect(() => resolveReferenceMapping([], { ...chartIdentity(), instrument_id: null })).toThrow(
      /Instrumentidentität/,
    );
  });
});

describe('mapping edits and revision-bound evidence', () => {
  it('suppresses an unchanged PUT even after backend normalization', () => {
    expect(mappingInputsChanged(mapping(), ' sap ', ' xetra ')).toBe(false);
    expect(mappingInputsChanged(mapping(), 'SAP', 'US')).toBe(true);
    expect(mappingInputsChanged(null, 'SAP', 'XETRA')).toBe(true);
    expect(mappingInputsChanged(null, ' ', '')).toBe(false);
  });

  it('requires review after creation, deletion, revision or a changed read value', () => {
    expect(sameMappingRevision(mapping(), { ...mapping() })).toBe(true);
    expect(sameMappingRevision(null, null)).toBe(true);
    for (const current of [null, mapping({ version: 4 }), mapping({ provider_symbol: 'NEW' })]) {
      expect(sameMappingRevision(mapping(), current)).toBe(false);
      expect(() => requireCurrentMapping(mapping(), current)).toThrow(MappingRevisionConflict);
    }
    expect(() => requireCurrentMapping(null, mapping())).toThrow(/erneut prüfen/);
    expect(() => requireCurrentMapping(mapping(), mapping())).not.toThrow();
  });

  it('does not carry index basis over a PUT or revalidation revision', () => {
    const identity = chartIdentity();
    expect(referenceBasisForMapping(identity, indexMapping())).toEqual({
      returnBasis: 'PRICE_INDEX',
      source: 'https://example.test/evidence',
    });
    const revised = { ...indexMapping(), version: 2 };
    expect(referenceBasisForMapping(identity, revised)).toEqual({
      returnBasis: 'UNKNOWN',
      source: null,
    });
    expect(
      referenceBasisForMapping(
        { ...identity, mapping_version: 2, return_basis: 'UNKNOWN', basis_source: null },
        revised,
      ),
    ).toEqual({ returnBasis: 'UNKNOWN', source: null });
    expect(
      referenceBasisForMapping(
        { ...identity, instrument_id: null },
        { ...indexMapping(), market_data_instrument_id: null },
      ),
    ).toEqual({ returnBasis: 'UNKNOWN', source: null });
  });

  it.each([
    null,
    mapping(),
    { ...indexMapping(), id: 'foreign' },
    { ...indexMapping(), market_data_instrument_id: 'foreign' },
  ])('keeps evidence unknown without the exact full mapping identity', (value) =>
    expect(referenceBasisForMapping(chartIdentity(), value)).toEqual({
      returnBasis: 'UNKNOWN',
      source: null,
    }),
  );
});
