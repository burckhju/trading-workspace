import type { OperationalPosition, PositionAlertProjection } from '../types';

/** Bound fan-out for large depots. The table need not wait for all optional signals. */
export async function loadPositionSignals(
  positions: OperationalPosition[],
  read: (id: string, signal: AbortSignal) => Promise<PositionAlertProjection>,
  update: (id: string, result: PositionAlertProjection | null) => void,
  signal: AbortSignal,
): Promise<void> {
  let next = 0;
  async function worker() {
    while (!signal.aborted && next < positions.length) {
      const position = positions[next++];
      let result: PositionAlertProjection | null = null;
      try {
        const loaded = await read(position.trade_id, signal);
        if (loaded.trade_id === position.trade_id && loaded.position_id === position.position_id)
          result = loaded;
      } catch {
        /* Unavailable is explicit, never a fabricated normal signal. */
      }
      if (!signal.aborted) update(position.position_id, result);
    }
  }
  await Promise.all(Array.from({ length: Math.min(6, positions.length) }, worker));
}
