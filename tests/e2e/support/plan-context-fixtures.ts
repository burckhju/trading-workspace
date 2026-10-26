import type { UnderlyingDetailResponse } from "../../../frontend/src/features/market/types/api";
import type {
  TradePlanDetailResponse,
  TradePlanVersionResponse,
} from "../../../frontend/src/features/trade_plan/types/api";

// Synthetic browser contracts only; native PostgreSQL cases create their own owner data.
export function planContextFixture(
  planId: string,
  versionId: string,
  underlyingId: string,
  overrides: Partial<TradePlanVersionResponse> = {},
): TradePlanDetailResponse {
  const now = "2026-10-25T10:00:00Z";
  return {
    plan: {
      id: planId,
      underlying_id: underlyingId,
      origin_type: "MANUAL",
      candidate_id: null,
      candidate_evaluation_id: null,
      created_at: now,
      created_by: "synthetic-actor",
    },
    latest_version: {
      id: versionId,
      trade_plan_id: planId,
      version: 1,
      direction: "LONG",
      status: "APPROVED",
      thesis: "Synthetic plan context",
      entry: {
        type: "PRICE",
        currency: "EUR",
        price: "100",
        price_from: null,
        price_to: null,
        trigger: null,
        reference_price: null,
        valid_until: null,
        rationale: null,
      },
      invalidation: {
        stop_price: "95",
        invalidation_rule: "Below support",
        rationale: null,
      },
      targets: [{ sequence: 1, price: "110", rationale: "First target" }],
      risk_assumptions: {
        thesis_risk: "Synthetic risk",
        max_loss_assumption: null,
        notes: null,
      },
      created_at: now,
      created_by: "synthetic-actor",
      previous_version_id: null,
      change_reason: null,
      candidate_evaluation: null,
      approval: {
        approval_id: "synthetic-approval",
        trade_plan_version_id: versionId,
        version: 1,
        actor: "synthetic-actor",
        approved_at: now,
        correlation_id: null,
      },
      events: [],
      ...overrides,
    },
  };
}

export function underlyingContextFixture(
  id: string,
  name = "Synthetischer Basiswert",
): UnderlyingDetailResponse {
  return {
    id,
    name,
    type: "STOCK",
    isin: "US000SYN0001",
    wkn: "BAS001",
    lifecycle_status: "ACTIVE",
    quality_status: "VERIFIED",
    version: 1,
    created_at: "2026-10-25T10:00:00Z",
    updated_at: "2026-10-25T10:00:00Z",
    primary_listing: {
      id: "synthetic-listing",
      ticker: "SYN",
      trading_venue_id: "synthetic-venue",
      trading_venue_mic: "XETR",
      trading_venue_name: "Xetra",
      currency_code: "EUR",
    },
    listings: [],
  };
}
