import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { expect, it, vi } from 'vitest';
import { chartIdentity } from '../../../test/chartFixtures';
import type { ProviderMapping, VenueReconciliation } from '../services/topDownAdminClient';
import { MappingEditor, MappingStatus } from './MappingEditor';

const mapping: ProviderMapping = {
  id: 'mapping',
  workspace_id: 'workspace',
  listing_id: 'secondary-listing',
  market_data_instrument_id: 'instrument',
  provider: 'EODHD',
  provider_symbol: 'SAP',
  provider_exchange_code: 'XETRA',
  status: 'ACTIVE',
  validated_at: '2026-10-26T12:00:00Z',
  validation_message: 'Technical validation passed',
  created_at: '2026-10-25T12:00:00Z',
  updated_at: '2026-10-26T12:00:00Z',
  version: 3,
};

it('edits structured mapping values and explains the destructive save separately from validation', async () => {
  function Editor() {
    const [symbol, setSymbol] = useState(mapping.provider_symbol);
    const [exchange, setExchange] = useState(mapping.provider_exchange_code);
    return (
      <MappingEditor
        mapping={mapping}
        symbol={symbol}
        exchange={exchange}
        onSymbolChange={setSymbol}
        onExchangeChange={setExchange}
      />
    );
  }
  const user = userEvent.setup();
  render(<Editor />);
  expect(screen.getByLabelText('Geprüftes EODHD-Symbol')).toHaveValue('SAP');
  expect(screen.getByLabelText('Geprüfter EODHD-Exchange-Code')).toHaveValue('XETRA');
  expect(
    screen.getByText(/deaktiviert das Mapping und löscht die bisherige Validierung/),
  ).toBeInTheDocument();
  expect(screen.getByText(/Keine Änderung/)).toBeInTheDocument();
  await user.clear(screen.getByLabelText('Geprüftes EODHD-Symbol'));
  await user.type(screen.getByLabelText('Geprüftes EODHD-Symbol'), ' sap ');
  expect(screen.getByText(/Keine Änderung/)).toBeInTheDocument();
  await user.clear(screen.getByLabelText('Geprüfter EODHD-Exchange-Code'));
  await user.type(screen.getByLabelText('Geprüfter EODHD-Exchange-Code'), 'US');
  expect(screen.queryByText(/Keine Änderung/)).not.toBeInTheDocument();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
});

it('prevents edits while the parent mutation is pending and does not infer new provider values', () => {
  render(
    <MappingEditor
      mapping={null}
      symbol=""
      exchange=""
      onSymbolChange={vi.fn()}
      onExchangeChange={vi.fn()}
      disabled
    />,
  );
  expect(screen.getByLabelText('Geprüftes EODHD-Symbol')).toHaveValue('');
  expect(screen.getByLabelText('Geprüftes EODHD-Symbol')).toBeDisabled();
  expect(screen.getByLabelText('Geprüfter EODHD-Exchange-Code')).toBeDisabled();
  expect(screen.getByText(/neue Mapping wird deaktiviert gespeichert/)).toBeInTheDocument();
});

it.each<VenueReconciliation['status']>(['MATCHED', 'CONFLICT', 'AMBIGUOUS', 'UNRESOLVED'])(
  'retains %s independently of technically ACTIVE mapping state',
  (status) => {
    render(
      <MappingStatus
        mapping={mapping}
        venue={{
          status,
          listing_venue_id: 'venue',
          evidence_venue_ids: [],
          explanation: `Synthetic ${status} evidence`,
        }}
      />,
    );
    expect(
      screen.getByText(/Mappingrevision: 3 · Technischer Mappingstatus: ACTIVE/),
    ).toBeInTheDocument();
    expect(screen.getByText(`Handelsplatzabgleich: ${status}`)).toBeInTheDocument();
    expect(screen.getByText(`Synthetic ${status} evidence`)).toBeInTheDocument();
    if (status === 'MATCHED') {
      expect(screen.getByText('Der Handelsplatz ist eindeutig zugeordnet.')).toBeInTheDocument();
    } else {
      expect(
        screen.getByText(/Reparaturschritt ist nicht als eindeutig geklärt belegt/),
      ).toBeInTheDocument();
    }
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  },
);

it('does not replace a failed or absent venue read with a successful reconciliation', () => {
  render(<MappingStatus mapping={mapping} venue={null} />);
  expect(screen.getByText('Handelsplatzabgleich: Noch nicht gelesen')).toBeInTheDocument();
  expect(screen.getByText(/aktives Mapping belegt allein keinen eindeutig/)).toBeInTheDocument();
});

it('uses UNKNOWN after a mapping revision changes and does not show stale evidence', () => {
  const direct = {
    ...mapping,
    id: 'm',
    listing_id: null,
    market_data_instrument_id: 'reference:sp500',
    version: 2,
  };
  const { rerender } = render(
    <MappingStatus mapping={direct} referenceIdentity={chartIdentity()} />,
  );
  expect(screen.getByText('Renditegrundlage dieser Mappingrevision: UNKNOWN')).toBeInTheDocument();
  expect(screen.queryByText(/Beleg:/)).not.toBeInTheDocument();
  rerender(
    <MappingStatus
      mapping={direct}
      referenceIdentity={{ ...chartIdentity(), mapping_version: 2 }}
    />,
  );
  expect(
    screen.getByText('Renditegrundlage dieser Mappingrevision: PRICE_INDEX'),
  ).toBeInTheDocument();
  expect(screen.getByText('Beleg: https://example.test/evidence')).toBeInTheDocument();
});

it('clearly represents missing mapping and validation without invented values', () => {
  const { rerender } = render(<MappingStatus mapping={null} />);
  expect(screen.getByText(/noch kein EODHD-Mapping belegt/)).toBeInTheDocument();
  rerender(
    <MappingStatus mapping={{ ...mapping, validated_at: null, validation_message: null }} />,
  );
  expect(screen.getByText('Letzte technische Prüfung: Noch nicht geprüft')).toBeInTheDocument();
});
