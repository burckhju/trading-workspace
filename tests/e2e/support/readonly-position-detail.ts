import type { OperationalPosition } from "../../../frontend/src/features/operational_workspace/types";

/** Synthetic GET projections for opening the canonical trade from an existing depot fixture.
 * No writes or financial calculations: monetary values are copied from that fixture.
 */
export function readonlyPositionDetail(
  path: string,
  positions: OperationalPosition[],
): unknown | undefined {
  for (const p of positions) {
    const productId =
      p.product_id ??
      p.position_basis?.position.product_id ??
      p.trade_id.replace("trade-", "product-");
    const tradePath = `/trade-position/trades/${p.trade_id}`;
    if (path.endsWith(tradePath))
      return {
        id: p.trade_id,
        product_id: productId,
        origin: "EXTERNAL",
        trade_plan_id: null,
        trade_plan_version_id: null,
        product_selection_id: null,
        product_evaluation_id: null,
        created_at: p.opened_at,
      };
    if (path.endsWith(`${tradePath}/position`))
      return {
        id: p.position_id,
        trade_id: p.trade_id,
        product_id: productId,
        open_quantity: p.open_quantity,
        cost_basis: p.cost_basis,
        average_entry_price: p.average_entry_price,
        realized_gross_pnl: p.realized_gross_pnl,
        opened_at: p.opened_at,
        opened_on: p.opened_on,
        last_execution_at: p.opened_at,
        closed_at: null,
        is_closed: false,
        is_cancelled: false,
      };
    if (path.endsWith(`${tradePath}/management`))
      return {
        trade_id: p.trade_id,
        stop_price: p.stop_price,
        target_price: p.target_price,
        thesis: null,
        notes: [],
        last_event_at: null,
      };
    if (path.endsWith(`${tradePath}/timeline`)) return [];
    if (path.endsWith(`/warrants/${productId}`))
      return {
        id: productId,
        underlying_id: p.underlying_id ?? "underlying-fixture",
        issuer_id: "issuer-fixture",
        display_name: p.product_name,
        isin: p.product_isin,
        wkn: p.product_wkn,
        product_family: "WARRANT",
        lifecycle_status: "ACTIVE",
        version: 1,
        created_at: p.opened_at,
        updated_at: p.opened_at,
      };
    if (
      path.endsWith(
        `/position-monitoring/trades/${encodeURIComponent(p.trade_id)}/product-valuation`,
      )
    )
      return {
        trade_id: p.trade_id,
        position_id: p.position_id,
        status: p.valuation_status,
        reason:
          p.valuation_status === "LAST_AVAILABLE"
            ? "MARKET_CLOSED_LAST_AVAILABLE_QUOTE"
            : p.valuation_status === "STALE"
              ? "WARRANT_QUOTE_STALE"
              : "SYNTHETIC_STORED_QUOTE",
        warrant_listing_id: null,
        symbol: p.product_symbol,
        bid: null,
        ask: null,
        currency: p.valuation_currency,
        quote_observed_at: p.quote_observed_at,
        quote_age_seconds: null,
        max_quote_age_seconds: null,
        market_value: p.market_value,
        unrealized_gross_pnl: p.unrealized_gross_pnl,
        unrealized_pnl_usable: p.unrealized_pnl_usable,
        unrealized_pnl_reason: p.unrealized_pnl_reason,
        selected_source: p.quote_source,
        valuation_usable: p.valuation_status === "AVAILABLE",
        execution_usable: false,
        analysis_usable: p.market_value !== null,
        analysis_warning: p.analysis_warning,
        analysis_market_value: p.market_value,
        analysis_unrealized_gross_pnl: p.unrealized_gross_pnl,
        analysis_unrealized_pnl_usable: p.unrealized_pnl_usable,
        analysis_unrealized_pnl_reason: p.unrealized_pnl_reason,
        freshness_policy: "SYNTHETIC",
        source_attempts: [],
        position_basis: p.position_basis,
      };
  }
  return undefined;
}
