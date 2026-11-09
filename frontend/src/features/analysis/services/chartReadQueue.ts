type WaitingRead = { start: () => void; cancel: () => void };

let active = 0;
let waiting: WaitingRead[] = [];

function drain() {
  while (active < 4 && waiting.length) waiting.shift()!.start();
}

/** Shared by overview and detail so navigation never bypasses the four-read bound. */
export function queuedChartRead<T>(operation: () => Promise<T>, signal?: AbortSignal): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Chart read cancelled', 'AbortError'));
      return;
    }
    const job: WaitingRead = {
      cancel: () => {
        waiting = waiting.filter((item) => item !== job);
        reject(new DOMException('Chart read cancelled', 'AbortError'));
      },
      start: () => {
        signal?.removeEventListener('abort', job.cancel);
        active += 1;
        void Promise.resolve()
          .then(operation)
          .then(resolve, reject)
          .finally(() => {
            active -= 1;
            drain();
          });
      },
    };
    waiting.push(job);
    signal?.addEventListener('abort', job.cancel, { once: true });
    drain();
  });
}
