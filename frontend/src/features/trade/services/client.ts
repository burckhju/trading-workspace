import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type {
  InitialPurchaseRequest,
  InitialPurchaseResponse,
  PositionResponse,
  PriceManagementRequest,
  SaleRequest,
  SaleResponse,
  TextManagementRequest,
  TradeManagementEventResponse,
  TradeManagementStateResponse,
  TradeResponse,
} from '../types/api';

const tradePositionUrl = `${environment.apiBaseUrl}/api/v1/trade-position`;
const baseUrl = `${tradePositionUrl}/trades`;

function tradeUrl(tradeId: string, path = ''): string {
  return `${baseUrl}/${tradeId}${path}`;
}

function normalizeDecimal(value: string): string {
  return value.trim().replace(',', '.');
}

export const tradeManagementApiClient = {
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

  sell: (tradeId: string, request: SaleRequest): Promise<SaleResponse> =>
    requestJson<SaleResponse>(tradeUrl(tradeId, '/sales'), {
      method: 'POST',
      body: request,
    }),

  changeStop: (
    tradeId: string,
    request: PriceManagementRequest,
  ): Promise<TradeManagementEventResponse> =>
    requestJson<TradeManagementEventResponse>(tradeUrl(tradeId, '/management/stop'), {
      method: 'POST',
      body: request,
    }),

  changeTarget: (
    tradeId: string,
    request: PriceManagementRequest,
  ): Promise<TradeManagementEventResponse> =>
    requestJson<TradeManagementEventResponse>(tradeUrl(tradeId, '/management/target'), {
      method: 'POST',
      body: request,
    }),

  updateThesis: (
    tradeId: string,
    request: TextManagementRequest,
  ): Promise<TradeManagementEventResponse> =>
    requestJson<TradeManagementEventResponse>(tradeUrl(tradeId, '/management/thesis'), {
      method: 'POST',
      body: request,
    }),

  addNote: (
    tradeId: string,
    request: TextManagementRequest,
  ): Promise<TradeManagementEventResponse> =>
    requestJson<TradeManagementEventResponse>(tradeUrl(tradeId, '/management/notes'), {
      method: 'POST',
      body: request,
    }),
};
