import { useCallback, useEffect, useRef, useState } from 'react';

import { operationalWorkspaceApiClient } from '../services/client';
import type { OperationalWorkspaceResponse } from '../types';

export function useWorkspaceActions() {
  const [response, setResponse] = useState<OperationalWorkspaceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const activeLoad = useRef<AbortController | null>(null);
  const reload = useCallback(async () => {
    activeLoad.current?.abort();
    const controller = new AbortController();
    activeLoad.current = controller;
    setLoading(true);
    setError(null);
    try {
      const next = await operationalWorkspaceApiClient.getActions(controller.signal);
      if (!controller.signal.aborted) setResponse(next);
    } catch (caught) {
      if (!controller.signal.aborted)
        setError(
          caught instanceof Error ? caught.message : 'Hinweise konnten nicht geladen werden.',
        );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);
  useEffect(() => {
    void reload();
    return () => activeLoad.current?.abort();
  }, [reload]);
  return { response, loading, error, reload };
}
