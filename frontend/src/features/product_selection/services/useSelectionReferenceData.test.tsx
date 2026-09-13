import { act, renderHook, waitFor } from '@testing-library/react';
import { warrantApiClient } from '../../product/services/client';
import { tradePlanOverviewApiClient } from '../../trade_plan/services/overviewClient';
import { useSelectionReferenceData } from './useSelectionReferenceData';
it('resolves both catalogues once and isolates failures, with explicit retry', async () => {
  const products = vi
    .spyOn(warrantApiClient, 'list')
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValue([]);
  const plans = vi.spyOn(tradePlanOverviewApiClient, 'list').mockResolvedValue([]);
  const { result } = renderHook(useSelectionReferenceData);
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.errors).toEqual(['Produktnamen konnten nicht geladen werden.']);
  act(() => result.current.reload());
  await waitFor(() => expect(products).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(result.current.errors).toEqual([]));
  expect(plans).toHaveBeenCalledTimes(2);
});
it('does not turn a failed plan catalogue into a product selection', async () => {
  vi.spyOn(warrantApiClient, 'list').mockResolvedValue([]);
  vi.spyOn(tradePlanOverviewApiClient, 'list').mockRejectedValue(new Error('offline'));
  const { result } = renderHook(useSelectionReferenceData);
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.errors).toEqual(['TradePlan-Bezeichnungen konnten nicht geladen werden.']);
  expect(result.current.plans).toEqual({});
});
