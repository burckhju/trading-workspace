import { createBrowserRouter, Navigate } from 'react-router-dom';

import { CurrencyAdminPage } from '../features/market/pages/CurrencyAdminPage';

import { TopDownWorkflowActionPage } from '../features/administration/pages';
import { MarketAnalysisDetailPage, MarketAnalysisPage } from '../features/analysis/pages';
import { AnalysisSetupPage } from '../features/analysis/pages/AnalysisSetupPage';
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
import { OperationalWorkspacePage } from '../features/operational_workspace/pages/OperationalWorkspacePage';
import { PostTradeLearningPage } from '../features/post_trade/pages/PostTradeLearningPage';
import { PerformanceWorkspace } from '../features/performance/pages/PerformanceWorkspace';
import { ProductSelectionWorkflowPage } from '../features/product_selection/pages';
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
        { path: 'workspace', element: <OperationalWorkspacePage /> },
        { path: 'underlyings', element: <UnderlyingListPage /> },
        { path: 'market-analyses', element: <MarketAnalysisPage /> },
        { path: 'market-analyses/setup', element: <AnalysisSetupPage /> },
        {
          path: 'market-charts',
          lazy: async () => ({
            Component: (await import('../features/analysis/pages/MarketChartsPage'))
              .MarketChartsPage,
          }),
        },
        {
          path: 'chart-setup',
          lazy: async () => ({
            Component: (await import('../features/analysis/pages/ChartSetupPage')).ChartSetupPage,
          }),
        },
        { path: 'candidates', element: <CandidatePage /> },
        { path: 'trade-plans/overview', element: <TradePlanOverviewPage /> },
        { path: 'trade-plans', element: <TradePlanPage /> },
        { path: 'trade-management', element: <TradeManagementPage /> },
        { path: 'post-trade', element: <PostTradeLearningPage /> },
        { path: 'performance', element: <Navigate to="/performance/realized-gross" replace /> },
        {
          path: 'performance/realized-gross',
          element: <PerformanceWorkspace kind="realized-gross" />,
        },
        {
          path: 'performance/closed-trades',
          element: <PerformanceWorkspace kind="closed-trades" />,
        },
        { path: 'product-selection', element: <ProductSelectionWorkflowPage /> },
        { path: 'learning-imports', element: <BulkImportPage /> },
        { path: 'lessons/:lessonId', element: <LessonDetailPage /> },
        { path: 'top-down-admin', element: <TopDownWorkflowActionPage /> },
        { path: 'trading-venues-admin', element: <TradingVenueAdminPage /> },
        { path: 'issuers-admin', element: <IssuerAdminPage /> },
        { path: 'currencies-admin', element: <CurrencyAdminPage /> },
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
