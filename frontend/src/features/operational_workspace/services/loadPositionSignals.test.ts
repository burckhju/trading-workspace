import { position } from '../../../test/positionFixture';
import { loadPositionSignals } from './loadPositionSignals';
it('bounds concurrency to six for 100 positions, checks identity, and handles per-position failures', async () => {
  let active = 0;
  let maximum = 0;
  const items = Array.from({ length: 100 }, (_, i) =>
    position({ trade_id: `t${i}`, position_id: `p${i}` }),
  );
  const update = vi.fn();
  const read = vi.fn(async (id: string) => {
    active++;
    maximum = Math.max(maximum, active);
    await new Promise((resolve) => setTimeout(resolve, 1));
    active--;
    if (id === 't99') throw new Error('missing');
    return {
      ...position().position_signal!,
      trade_id: id,
      position_id: id === 't98' ? 'wrong' : `p${id.slice(1)}`,
    };
  });
  await loadPositionSignals(items, read, update, new AbortController().signal);
  expect(maximum).toBe(6);
  expect(update).toHaveBeenCalledTimes(100);
  expect(update).toHaveBeenCalledWith('p99', null);
  expect(update).toHaveBeenCalledWith('p98', null);
});
it('does not update an abandoned page or schedule requests after abort', async () => {
  const controller = new AbortController();
  const update = vi.fn();
  const read = vi.fn(async () => {
    controller.abort();
    await Promise.resolve();
    return position().position_signal!;
  });
  await loadPositionSignals(
    Array.from({ length: 100 }, () => position()),
    read,
    update,
    controller.signal,
  );
  expect(read).toHaveBeenCalledTimes(1);
  expect(update).not.toHaveBeenCalled();
});
