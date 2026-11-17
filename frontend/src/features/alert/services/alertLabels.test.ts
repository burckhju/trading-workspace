import { describe, expect, it } from 'vitest';

import { alertTypeLabel } from './alertLabels';

describe('persisted alert labels', () => {
  it('keeps unknown types explicit without inferring a known rule', () => {
    expect(alertTypeLabel('FUTURE_RULE')).toBe('FUTURE_RULE');
    expect(alertTypeLabel('toString')).toBe('toString');
  });
});
