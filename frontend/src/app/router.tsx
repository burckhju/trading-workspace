import { createBrowserRouter } from 'react-router-dom';

import { ApplicationLayout } from '../layouts/ApplicationLayout';
import { MarketAnalysisDetailPage, MarketAnalysisPage } from '../features/analysis/pages';
import {
  UnderlyingDetailPage,
  UnderlyingFormPage,
  UnderlyingListPage,
} from '../features/market/pages';
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
        { path: 'market-analyses/:analysisId', element: <MarketAnalysisDetailPage /> },
        { path: 'underlyings/new', element: <UnderlyingFormPage /> },
        { path: 'underlyings/:underlyingId', element: <UnderlyingDetailPage /> },
        { path: 'underlyings/:underlyingId/edit', element: <UnderlyingFormPage /> },
        { path: '*', element: <NotFoundPage /> },
      ],
    },
  ]);
}
