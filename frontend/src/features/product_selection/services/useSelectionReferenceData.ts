import { useEffect, useState } from 'react';

import { warrantApiClient } from '../../product/services/client';
import type { WarrantResponse } from '../../product/types/api';
import {
  tradePlanOverviewApiClient,
  type TradePlanOverviewItem,
} from '../../trade_plan/services/overviewClient';

/** Display-only master data. IDs from the persisted evaluation remain authoritative. */
export function useSelectionReferenceData() {
  const [products, setProducts] = useState<Record<string, WarrantResponse>>({});
  const [plans, setPlans] = useState<Record<string, TradePlanOverviewItem>>({});
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setErrors([]);
    setProducts({});
    setPlans({});
    // A single catalogue read serves every evaluation, omission and confirmation.
    // Partial failure must not discard the other catalogue or mutate a selection.
    void Promise.allSettled([
      warrantApiClient.list(controller.signal),
      tradePlanOverviewApiClient.list(controller.signal),
    ]).then(([productResult, planResult]) => {
      if (controller.signal.aborted) return;
      const failures: string[] = [];
      if (productResult.status === 'fulfilled') {
        setProducts(Object.fromEntries(productResult.value.map((item) => [item.id, item])));
      } else {
        failures.push('Produktnamen konnten nicht geladen werden.');
      }
      if (planResult.status === 'fulfilled') {
        setPlans(Object.fromEntries(planResult.value.map((item) => [item.id, item])));
      } else {
        failures.push('TradePlan-Bezeichnungen konnten nicht geladen werden.');
      }
      setErrors(failures);
      setLoading(false);
    });
    return () => controller.abort();
  }, [revision]);

  return { products, plans, loading, errors, reload: () => setRevision((value) => value + 1) };
}
