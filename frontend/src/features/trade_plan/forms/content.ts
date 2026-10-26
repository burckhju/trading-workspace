import type { TradePlanContentRequest, TradePlanVersionResponse } from '../types/api';

/** Copy only editable content; identity, status and lineage remain bound by the command. */
export function tradePlanContentFromVersion(
  version: TradePlanVersionResponse,
): TradePlanContentRequest {
  return {
    thesis: version.thesis,
    entry: { ...version.entry },
    invalidation: { ...version.invalidation },
    targets: version.targets.map((target) => ({ ...target })),
    risk_assumptions: { ...version.risk_assumptions },
  };
}

export function createEmptyTradePlanContent(): TradePlanContentRequest {
  return {
    thesis: '',
    entry: { type: 'PRICE', currency: '', price: '' },
    invalidation: {},
    targets: [{ sequence: 1, price: '' }],
    risk_assumptions: { thesis_risk: '' },
  };
}
