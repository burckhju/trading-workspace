import { createElement } from 'react';
import { useSearchParams } from 'react-router-dom';

import { ProductValuationPanel } from '../components/ProductValuationPanel';
import { TradeManagementPage as TradeManagementPageBase } from './TradeManagementPage';

export function TradeManagementPage() {
  const [searchParams] = useSearchParams();
  const tradeId = searchParams.get('trade_id');

  return createElement(
    'div',
    { className: 'min-w-0 w-full space-y-6 [overflow-wrap:anywhere]' },
    createElement(TradeManagementPageBase),
    tradeId ? createElement(ProductValuationPanel, { tradeId }) : null,
  );
}
