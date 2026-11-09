import { describe, expect, it, vi } from 'vitest';
import { queuedChartRead } from './chartReadQueue';

describe('shared chart read bound', () => {
  it('never exceeds four active reads, cancels queued work and releases slots after errors', async () => {
    const finish: (() => void)[] = [];
    const started: number[] = [];
    const controllers = Array.from({ length: 7 }, () => new AbortController());
    const reads = controllers.map((controller, index) =>
      queuedChartRead(() => {
        started.push(index);
        return new Promise<number>((resolve, reject) =>
          finish.push(() => (index === 0 ? reject(new Error('failed')) : resolve(index))),
        );
      }, controller.signal),
    );
    const all = Promise.allSettled(reads);
    await Promise.resolve();
    expect(started).toEqual([0, 1, 2, 3]);
    controllers[4].abort();
    finish.splice(0).forEach((resolve) => resolve());
    await vi.waitFor(() => expect(started).toEqual([0, 1, 2, 3, 5, 6]));
    finish.splice(0).forEach((resolve) => resolve());
    const outcomes = await all;
    expect(outcomes[0].status).toBe('rejected');
    expect(outcomes[4]).toMatchObject({ status: 'rejected', reason: { name: 'AbortError' } });
    expect(outcomes[6]).toMatchObject({ status: 'fulfilled', value: 6 });
    const aborted = new AbortController();
    aborted.abort();
    const operation = vi.fn();
    await expect(queuedChartRead(operation, aborted.signal)).rejects.toMatchObject({
      name: 'AbortError',
    });
    expect(operation).not.toHaveBeenCalled();
  });
});
