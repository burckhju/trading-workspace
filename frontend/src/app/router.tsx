import { createBrowserRouter } from 'react-router-dom';

import { ApplicationLayout } from '../layouts/ApplicationLayout';
import { CandidatePage } from '../features/candidate/pages';
import { TopDownWorkflowActionPage } from '../features/administration/pages';
import { MarketAnalysisDetailPage, MarketAnalysisPage } from '../features/analysis/pages';
import { BulkImportPage } from '../features/learning/pages';
import {
  IssuerAdminPage,
  UnderlyingDetailPage,
  UnderlyingFormPage,
  UnderlyingListPage,
  TradingVenueAdminPage,
} from '../features/market/pages';
import { TradeManagementPage } from '../features/trade/pages';
import { TradePlanPage } from '../features/trade_plan/pages';
import { WarrantAdminPage } from '../features/product/pages';
import { ProductSelectionPage } from '../features/product_selection/pages';
import { PostTradeReviewPage } from '../features/post_trade/pages';
import { NotFoundPage } from '../pages/NotFoundPage';

export function createApplicationRouter() {
  return createBrowserRouter([
    {
      path: '/',
      element: <ApplicationLayout />,
      children: [
        { index: true, element: <UnderlyingListPage /> },
        { path: 'underlyings', element: <UnderlyingListPage /> },
        { path: 'market-analyses', element: <MarketAnalysisPage /> },
        { path: 'candidates', element: <CandidatePage /> },
        { path: 'trade-plans', element: <TradePlanPage /> },
        { path: 'trade-management', element: <TradeManagementPage /> },
        { path: 'post-trade', element: <PostTradeReviewPage /> },
        { path: 'product-selection', element: <ProductSelectionPage /> },
        { path: 'learning-imports', element: <BulkImportPage /> },
        { path: 'top-down-admin', element: <TopDownWorkflowActionPage /> },
        { path: 'trading-venues-admin', element: <TradingVenueAdminPage /> },
        { path: 'issuers-admin', element: <IssuerAdminPage /> },
        { path: 'warrants-admin', element: <WarrantAdminPage /> },
        { path: 'market-analyses/:analysisId', element: <MarketAnalysisDetailPage /> },
        { path: 'underlyings/new', element: <UnderlyingFormPage /> },
        { path: 'underlyings/:underlyingId', element: <UnderlyingDetailPage /> },
        { path: 'underlyings/:underlyingId/edit', element: <UnderlyingFormPage /> },
        { path: '*', element: <NotFoundPage /> },
      ],
    },
  ]);
}
