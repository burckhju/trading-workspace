import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  CancellationPreview,
  CancellationRequest,
  InitialPurchaseRequest,
  InitialPurchaseResponse,
  PositionResponse,
  PriceManagementRequest,
  ProductPositionValuationResponse,
  SaleRequest,
  SaleResponse,
  TextManagementRequest,
  TradeManagementEventResponse,
  TradeManagementStateResponse,
  TradeResponse,
  TradeTimelineEntryResponse,
} from '../types/api';

const tradePositionUrl = `${environment.apiBaseUrl}/api/v1/trade-position`;
const monitoringUrl = `${environment.apiBaseUrl}/api/v1/position-monitoring`;
const baseUrl = `${tradePositionUrl}/trades`;

export const tradeTimelineChangedEvent = 'trade-timeline-changed';

function tradeUrl(tradeId: string, path = ''): string {
  return `${baseUrl}/${tradeId}${path}`;
}

function normalizeDecimal(value: string): string {
  return value.trim().replace(',', '.');
}

function notifyTimelineChanged(tradeId: string): void {
  window.dispatchEvent(
    new CustomEvent(tradeTimelineChangedEvent, {
      detail: { tradeId },
    }),
  );
}

export const tradeManagementApiClient = {
  cancellationPreview: (tradeId: string): Promise<CancellationPreview> =>
    requestJson<CancellationPreview>(tradeUrl(tradeId, '/cancellation')),
  cancel: async (tradeId: string, request: CancellationRequest): Promise<CancellationPreview> => {
    const result = await requestJson<CancellationPreview>(tradeUrl(tradeId, '/cancel'), {
      method: 'POST',
      body: request,
    });
    notifyTimelineChanged(tradeId);
    return result;
  },
  purchaseAdditional: async (tradeId: string, request: SaleRequest): Promise<SaleResponse> => {
    const result = await requestJson<SaleResponse>(tradeUrl(tradeId, '/purchases'), {
      method: 'POST',
      body: { ...request, price_per_unit: normalizeDecimal(request.price_per_unit) },
    });
    notifyTimelineChanged(tradeId);
    return result;
  },
  purchaseFromSelection: (request: InitialPurchaseRequest): Promise<InitialPurchaseResponse> =>
    requestJson<InitialPurchaseResponse>(`${tradePositionUrl}/purchases/from-selection`, {
      method: 'POST',
      body: {
        ...request,
        price_per_unit: normalizeDecimal(request.price_per_unit),
      },
    }),

  trade: (tradeId: string, signal?: AbortSignal): Promise<TradeResponse> =>
    requestJson<TradeResponse>(tradeUrl(tradeId), { signal }),

  position: (tradeId: string, signal?: AbortSignal): Promise<PositionResponse> =>
    requestJson<PositionResponse>(tradeUrl(tradeId, '/position'), { signal }),

  managementState: (tradeId: string, signal?: AbortSignal): Promise<TradeManagementStateResponse> =>
    requestJson<TradeManagementStateResponse>(tradeUrl(tradeId, '/management'), { signal }),

  timeline: (tradeId: string, signal?: AbortSignal): Promise<TradeTimelineEntryResponse[]> =>
    requestJson<TradeTimelineEntryResponse[]>(tradeUrl(tradeId, '/timeline'), { signal }),

  productValuation: (
    tradeId: string,
    signal?: AbortSignal,
  ): Promise<ProductPositionValuationResponse> =>
    requestJson<ProductPositionValuationResponse>(
      `${monitoringUrl}/trades/${encodeURIComponent(tradeId)}/product-valuation`,
      { signal },
    ),

  sell: async (tradeId: string, request: SaleRequest): Promise<SaleResponse> => {
    const response = await requestJson<SaleResponse>(tradeUrl(tradeId, '/sales'), {
      method: 'POST',
      body: request,
    });
    notifyTimelineChanged(tradeId);
    return response;
  },

  changeStop: async (
    tradeId: string,
    request: PriceManagementRequest,
  ): Promise<TradeManagementEventResponse> => {
    const response = await requestJson<TradeManagementEventResponse>(
      tradeUrl(tradeId, '/management/stop'),
      { method: 'POST', body: request },
    );
    notifyTimelineChanged(tradeId);
    return response;
  },

  changeTarget: async (
    tradeId: string,
    request: PriceManagementRequest,
  ): Promise<TradeManagementEventResponse> => {
    const response = await requestJson<TradeManagementEventResponse>(
      tradeUrl(tradeId, '/management/target'),
      { method: 'POST', body: request },
    );
    notifyTimelineChanged(tradeId);
    return response;
  },

  updateThesis: async (
    tradeId: string,
    request: TextManagementRequest,
  ): Promise<TradeManagementEventResponse> => {
    const response = await requestJson<TradeManagementEventResponse>(
      tradeUrl(tradeId, '/management/thesis'),
      { method: 'POST', body: request },
    );
    notifyTimelineChanged(tradeId);
    return response;
  },

  addNote: async (
    tradeId: string,
    request: TextManagementRequest,
  ): Promise<TradeManagementEventResponse> => {
    const response = await requestJson<TradeManagementEventResponse>(
      tradeUrl(tradeId, '/management/notes'),
      { method: 'POST', body: request },
    );
    notifyTimelineChanged(tradeId);
    return response;
  },
};
