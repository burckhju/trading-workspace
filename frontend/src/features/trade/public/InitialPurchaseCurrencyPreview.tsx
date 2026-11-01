import { ExecutionCurrencyPreview } from '../components/ExecutionCurrencyPreview';
import type { ExecutionCurrencyDraft } from '../services/executionCurrency';

export interface InitialPurchaseCurrencyPreviewProps {
  productId: string;
  date: string;
  time: string;
  value: ExecutionCurrencyDraft;
  onChange: (value: ExecutionCurrencyDraft) => void;
  disabled?: boolean;
}

/** Product selection owns its draft; Trade owns the read-only initial BUY preview. */
export function InitialPurchaseCurrencyPreview({
  productId,
  date,
  time,
  value,
  onChange,
  disabled,
}: InitialPurchaseCurrencyPreviewProps) {
  return (
    <ExecutionCurrencyPreview
      context={{ productId, side: 'BUY' }}
      date={date}
      time={time}
      value={value}
      onChange={onChange}
      disabled={disabled}
    />
  );
}
