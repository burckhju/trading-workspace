import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ExecutionCurrencyEvidenceSource, PositionValuationBasis } from '../types/api';
import { PositionValuationBasisDetails } from './PositionValuationBasisDetails';

const basis: PositionValuationBasis = {
  definition_version: 'position-unrealized-gross-v1',
  basis_id: 'exact-basis-id',
  position: {
    id: 'position-1',
    trade_id: 'trade-1',
    product_id: 'product-1',
    open_quantity: 10,
    cost_basis: '20',
    average_entry_price: '2',
    realized_gross_pnl: '0',
    opened_at: '2026-10-27T10:00:00Z',
    last_execution_at: '2026-10-27T10:00:00Z',
    closed_at: null,
  },
  cost_basis_currency: 'USD',
  currency_status: 'KNOWN',
  effective_execution_ids: ['effective-buy', 'effective-sale'],
  buy_currency_evidence: [
    {
      execution_id: 'effective-buy',
      currency_code: 'USD',
      source: 'REPLACED_EXECUTION',
      source_execution_ids: ['original-buy'],
      confirmation_ids: ['exact-confirmation'],
    },
  ],
};

const historicalSource: ExecutionCurrencyEvidenceSource = {
  id: 'historical-source-version',
  kind: 'HISTORICAL_LISTINGS',
  source_reference: 'Synthetisches Börsenarchiv, EUR-Notierungen Oktober 2026',
  recorded_at: '2026-10-28T12:00:00Z',
  valid_from: '2026-10-01T00:00:00Z',
  valid_to: '2026-11-01T00:00:00Z',
  source_fingerprint: 'historical-source-fingerprint',
  verification: 'USER_VERIFIED_SOURCE',
};

it('exposes the exact backend basis, execution and confirmation references without a quote currency substitution', async () => {
  render(<PositionValuationBasisDetails basis={basis} />);
  await userEvent.click(screen.getByText('Kostenbasis und Währungsnachweise'));
  expect(screen.getByText('Kostenbasiswährung: USD')).toBeVisible();
  expect(screen.getByText(/Bewertungsdefinition:/)).toHaveTextContent(
    'position-unrealized-gross-v1 · Lesebasis: exact-basis-id',
  );
  expect(screen.getByText(/Wirksame Ausführungen:/)).toHaveTextContent(
    'effective-buy, effective-sale',
  );
  const buy = screen.getByText(/^Kauf effective-buy:/).closest('li')!;
  expect(buy).toHaveTextContent(
    'Kauf effective-buy: USD · aus der ursprünglichen Buchung übernommen',
  );
  await userEvent.click(within(buy).getByText('Verwendete Währungsherkunft'));
  expect(within(buy).getByText('Buchung original-buy')).toBeVisible();
  expect(within(buy).getByText('Bestätigung exact-confirmation')).toBeVisible();
});

it.each([
  ['UNKNOWN', 'Nicht vollständig belegt'],
  ['MIXED', 'Unterschiedliche Kaufwährungen'],
] as const)('keeps the %s basis visibly unqualified', async (currency_status, label) => {
  render(
    <PositionValuationBasisDetails
      basis={{
        ...basis,
        currency_status,
        cost_basis_currency: null,
        buy_currency_evidence: [
          {
            execution_id: 'effective-buy',
            currency_code: null,
            source: currency_status,
            source_execution_ids: [],
            confirmation_ids: [],
          },
        ],
      }}
    />,
  );
  await userEvent.click(screen.getByText('Kostenbasis und Währungsnachweise'));
  expect(screen.getByText(`Kostenbasiswährung: ${label}`)).toBeVisible();
  expect(screen.getByRole('listitem')).toHaveTextContent(
    currency_status === 'MIXED' ? 'widersprüchliche Kaufwährungen' : 'unbekannt',
  );
  expect(screen.queryByText('Bestätigung exact-confirmation')).not.toBeInTheDocument();
  expect(screen.queryByText(/ausdrücklich bestätigt/)).not.toBeInTheDocument();
});

it('does not invent basis references when the backend could not provide them', () => {
  const { container } = render(<PositionValuationBasisDetails basis={null} />);
  expect(container).toBeEmptyDOMElement();
});

it('shows the historical BUY source, exact validity and resolver rule without requesting another confirmation', async () => {
  render(
    <PositionValuationBasisDetails
      basis={{
        ...basis,
        cost_basis_currency: 'EUR',
        buy_currency_evidence: [
          {
            execution_id: 'effective-buy',
            currency_code: 'EUR',
            source: 'HISTORICAL_LISTINGS',
            source_execution_ids: ['effective-buy'],
            confirmation_ids: [],
            evidence_ids: [historicalSource.id],
            evidence: [historicalSource],
            reason: null,
            resolver_version: 'execution-currency-v3',
          },
        ],
      }}
    />,
  );
  await userEvent.click(screen.getByText('Kostenbasis und Währungsnachweise'));
  expect(screen.getByText('Kostenbasiswährung: EUR')).toBeVisible();
  expect(
    screen.getByText(
      'Kauf effective-buy: EUR · automatisch aus historischen Notierungen abgeleitet',
    ),
  ).toBeVisible();
  expect(screen.getByText(/Eine erneute Eingabe ist nicht nötig/)).toBeVisible();
  await userEvent.click(screen.getByText('Verwendete Währungsherkunft'));
  expect(screen.getByText(`Quelle: ${historicalSource.source_reference}`)).toBeVisible();
  expect(
    screen.getByText('Gültig von 2026-10-01T00:00:00Z bis ausschließlich 2026-11-01T00:00:00Z'),
  ).toBeVisible();
  expect(screen.getByText('Quellenversion historical-source-version')).toBeVisible();
  expect(screen.getByText('Quellennachweis historical-source-fingerprint')).toBeVisible();
  expect(screen.getByText('Originalquelle vom Nutzer geprüft')).toBeVisible();
  expect(screen.getByText('Zuordnungsregel execution-currency-v3')).toBeVisible();
  expect(screen.queryByText(/ausdrücklich bestätigt/)).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /bestätigen|speichern/i })).not.toBeInTheDocument();
});

it('keeps a conflicting BUY unqualified and exposes both original documents with the specific review reason', async () => {
  const documents = ['EUR', 'USD'].map((code) => ({
    ...historicalSource,
    id: `document-${code}`,
    kind: 'EXECUTION_DOCUMENT',
    source_reference: `Synthetische Kaufabrechnung ${code}`,
    valid_from: null,
    valid_to: null,
    source_fingerprint: `document-fingerprint-${code}`,
  }));
  render(
    <PositionValuationBasisDetails
      basis={{
        ...basis,
        currency_status: 'UNKNOWN',
        cost_basis_currency: null,
        buy_currency_evidence: [
          {
            execution_id: 'effective-buy',
            currency_code: null,
            source: 'CONFLICT',
            source_execution_ids: ['effective-buy'],
            confirmation_ids: [],
            evidence_ids: documents.map((document) => document.id),
            evidence: documents,
            reason: 'DOCUMENT_CONFLICT',
            resolver_version: 'execution-currency-v3',
          },
        ],
      }}
    />,
  );
  await userEvent.click(screen.getByText('Kostenbasis und Währungsnachweise'));
  expect(screen.getByText('Kostenbasiswährung: Nicht vollständig belegt')).toBeVisible();
  expect(screen.getByText('Kauf effective-buy: widersprüchliche Währungsbelege')).toBeVisible();
  expect(
    screen.getByText(/Die zugeordneten Ausführungsbelege nennen unterschiedliche Währungen/),
  ).toBeVisible();
  await userEvent.click(screen.getByText('Verwendete Währungsherkunft'));
  for (const document of documents) {
    expect(screen.getByText(`Quelle: ${document.source_reference}`)).toBeVisible();
    expect(screen.getByText(`Quellenversion ${document.id}`)).toBeVisible();
    expect(screen.getByText(`Quellennachweis ${document.source_fingerprint}`)).toBeVisible();
  }
  expect(screen.getByText('Zuordnungsregel execution-currency-v3')).toBeVisible();
  expect(screen.queryByText('Kostenbasiswährung: EUR')).not.toBeInTheDocument();
  expect(screen.queryByText(/automatisch aus/)).not.toBeInTheDocument();
  expect(screen.queryByText(/ausdrücklich bestätigt/)).not.toBeInTheDocument();
});
