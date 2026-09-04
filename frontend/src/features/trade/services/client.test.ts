import { beforeEach, describe, expect, it, vi } from 'vitest';

import { requestJson } from '../../market/services/http';
import { tradeManagementApiClient } from './client';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
const requestJsonMock = vi.mocked(requestJson);

describe('tradeManagementApiClient', () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
    requestJsonMock.mockResolvedValue({} as never);
  });

  it('records an initial BUY from a documented product selection and normalizes localized price', async () => {
    await tradeManagementApiClient.purchaseFromSelection({
      product_selection_id: 'selection-1',
      quantity: 10,
      price_per_unit: '2,35',
    });

    expect(requestJsonMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/trade-position/purchases/from-selection',
      {
        method: 'POST',
        body: {
          product_selection_id: 'selection-1',
          quantity: 10,
          price_per_unit: '2.35',
        },
      },
    );
  });

  it('uses the FT-010 read endpoints including persisted trade provenance', async () => {
    const signal = new AbortController().signal;

    await tradeManagementApiClient.trade('trade-1', signal);
    await tradeManagementApiClient.position('trade-1', signal);
    await tradeManagementApiClient.managementState('trade-1', signal);

    expect(requestJsonMock).toHaveBeenNthCalledWith(
      1,
      'http://localhost:8000/api/v1/trade-position/trades/trade-1',
      { signal },
    );
    expect(requestJsonMock).toHaveBeenNthCalledWith(
      2,
      'http://localhost:8000/api/v1/trade-position/trades/trade-1/position',
      { signal },
    );
    expect(requestJsonMock).toHaveBeenNthCalledWith(
      3,
      'http://localhost:8000/api/v1/trade-position/trades/trade-1/management',
      { signal },
    );
  });

  it('maps sale and management commands without duplicating exit events', async () => {
    await tradeManagementApiClient.sell('trade-1', {
      quantity: 5,
      price_per_unit: '2.50',
    });
    await tradeManagementApiClient.changeStop('trade-1', { price: '1.90' });
    await tradeManagementApiClient.changeTarget('trade-1', { price: '3.10' });
    await tradeManagementApiClient.updateThesis('trade-1', { text: 'Trend remains intact' });
    await tradeManagementApiClient.addNote('trade-1', { text: 'Volatility increased' });

    expect(requestJsonMock).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining('/trade-1/sales'),
      expect.objectContaining({ method: 'POST', body: { quantity: 5, price_per_unit: '2.50' } }),
    );
    expect(requestJsonMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining('/trade-1/management/stop'),
      expect.objectContaining({ method: 'POST', body: { price: '1.90' } }),
    );
    expect(requestJsonMock).toHaveBeenNthCalledWith(
      5,
      expect.stringContaining('/trade-1/management/notes'),
      expect.objectContaining({ method: 'POST', body: { text: 'Volatility increased' } }),
    );
  });
});
