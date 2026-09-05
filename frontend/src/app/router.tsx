import { createBrowserRouter } from 'react-router-dom';

import { TopDownWorkflowActionPage } from '../features/administration/pages';
import { MarketAnalysisDetailPage, MarketAnalysisPage } from '../features/analysis/pages';
import { CandidatePage } from '../features/candidate/pages';
import { LessonDetailPage } from '../features/learning/pages/LessonDetailPage';
import { BulkImportPage } from '../features/learning/pages';
import {
  IssuerAdminPage,
  TradingVenueAdminPage,
  UnderlyingDetailPage,
  UnderlyingFormPage,
  UnderlyingListPage,
} from '../features/market/pages';
import { PostTradeLearningPage } from '../features/post_trade/pages/PostTradeLearningPage';
import { ProductSelectionPage } from '../features/product_selection/pages';
import { WarrantAdminPage } from '../features/product/pages';
import { TradeManagementPage } from '../features/trade/pages';
import { TradePlanOverviewPage, TradePlanPage } from '../features/trade_plan/pages';
import { ApplicationLayout } from '../layouts/ApplicationLayout';
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
        { path: 'trade-plans/overview', element: <TradePlanOverviewPage /> },
        { path: 'trade-plans', element: <TradePlanPage /> },
        { path: 'trade-management', element: <TradeManagementPage /> },
        { path: 'post-trade', element: <PostTradeLearningPage /> },
        { path: 'product-selection', element: <ProductSelectionPage /> },
        { path: 'learning-imports', element: <BulkImportPage /> },
        { path: 'lessons/:lessonId', element: <LessonDetailPage /> },
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
