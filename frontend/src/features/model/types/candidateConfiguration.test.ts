import { describe, expect, it } from 'vitest';

import {
  candidatePolicyImpact,
  proposedCandidateDefinition,
  readCandidateConfiguration,
} from './candidateConfiguration';

describe('candidateConfiguration', () => {
  it('recognizes supported V1 and V2 definitions', () => {
    expect(
      readCandidateConfiguration({
        schema: 'TOP_DOWN_CANDIDATE/1.0',
        direction: 'LONG',
        market_context_allowed: ['FAVORABLE', 'CAUTIOUS'],
      })?.policy,
    ).toBe('FAVORABLE_AND_CAUTIOUS');
    expect(
      readCandidateConfiguration({
        schema: 'TOP_DOWN_CANDIDATE/2.0',
        direction: 'LONG',
        market_context_allowed: ['FAVORABLE'],
      })?.policy,
    ).toBe('FAVORABLE_ONLY');
  });

  it('fails closed for missing, unsupported, or unknown content', () => {
    expect(
      readCandidateConfiguration({ schema: 'TOP_DOWN_CANDIDATE/2.0', direction: 'LONG' }),
    ).toBeNull();
    expect(
      readCandidateConfiguration({
        schema: 'TOP_DOWN_CANDIDATE/3.0',
        direction: 'LONG',
        market_context_allowed: ['FAVORABLE'],
      }),
    ).toBeNull();
    expect(
      readCandidateConfiguration({
        schema: 'TOP_DOWN_CANDIDATE/2.0',
        direction: 'LONG',
        market_context_allowed: ['FAVORABLE'],
        extra: true,
      }),
    ).toBeNull();
    expect(
      readCandidateConfiguration({
        schema: 'TOP_DOWN_CANDIDATE/2.0',
        direction: 'LONG',
        market_context_allowed: ['CAUTIOUS'],
      }),
    ).toBeNull();
  });

  it('always derives proposed Candidate policy as schema 2.0', () => {
    expect(proposedCandidateDefinition('FAVORABLE_ONLY')).toEqual({
      schema: 'TOP_DOWN_CANDIDATE/2.0',
      direction: 'LONG',
      market_context_allowed: ['FAVORABLE'],
    });
    expect(proposedCandidateDefinition('FAVORABLE_AND_CAUTIOUS')).toEqual({
      schema: 'TOP_DOWN_CANDIDATE/2.0',
      direction: 'LONG',
      market_context_allowed: ['FAVORABLE', 'CAUTIOUS'],
    });
  });

  it('keeps impact preview deterministic and no-op free', () => {
    expect(candidatePolicyImpact('FAVORABLE_AND_CAUTIOUS', 'FAVORABLE_ONLY')).toContain(
      'will no longer satisfy',
    );
    expect(candidatePolicyImpact('FAVORABLE_ONLY', 'FAVORABLE_AND_CAUTIOUS')).toContain(
      'will become eligible',
    );
    expect(candidatePolicyImpact('FAVORABLE_ONLY', 'FAVORABLE_ONLY')).toBeNull();
  });
});
