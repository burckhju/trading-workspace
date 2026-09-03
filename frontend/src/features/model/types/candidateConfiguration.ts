export const CANDIDATE_MODEL_KEY = 'TOP_DOWN_CANDIDATE';
export const CANDIDATE_SCHEMA_V1 = 'TOP_DOWN_CANDIDATE/1.0';
export const CANDIDATE_SCHEMA_V2 = 'TOP_DOWN_CANDIDATE/2.0';

export type CandidateMarketContextPolicy = 'FAVORABLE_AND_CAUTIOUS' | 'FAVORABLE_ONLY';

export interface CandidateConfiguration {
  schema: typeof CANDIDATE_SCHEMA_V1 | typeof CANDIDATE_SCHEMA_V2;
  direction: 'LONG';
  policy: CandidateMarketContextPolicy;
}

const EXPECTED_KEYS = ['direction', 'market_context_allowed', 'schema'];

function hasExactKeys(definition: Record<string, unknown>): boolean {
  return Object.keys(definition).sort().join('|') === EXPECTED_KEYS.join('|');
}

export function readCandidateConfiguration(
  definition: Record<string, unknown>,
): CandidateConfiguration | null {
  if (!hasExactKeys(definition) || definition.direction !== 'LONG') return null;
  const schema = definition.schema;
  if (schema !== CANDIDATE_SCHEMA_V1 && schema !== CANDIDATE_SCHEMA_V2) return null;

  const contexts = definition.market_context_allowed;
  if (!Array.isArray(contexts) || contexts.some((value) => typeof value !== 'string')) return null;
  const unique = [...new Set(contexts)].sort();
  const permissive = unique.length === 2 && unique[0] === 'CAUTIOUS' && unique[1] === 'FAVORABLE';
  const strict = unique.length === 1 && unique[0] === 'FAVORABLE';

  if (schema === CANDIDATE_SCHEMA_V1 && !permissive) return null;
  if (schema === CANDIDATE_SCHEMA_V2 && !permissive && !strict) return null;

  return {
    schema,
    direction: 'LONG',
    policy: strict ? 'FAVORABLE_ONLY' : 'FAVORABLE_AND_CAUTIOUS',
  };
}

export function proposedCandidateDefinition(
  policy: CandidateMarketContextPolicy,
): Record<string, unknown> {
  return {
    schema: CANDIDATE_SCHEMA_V2,
    direction: 'LONG',
    market_context_allowed:
      policy === 'FAVORABLE_ONLY' ? ['FAVORABLE'] : ['FAVORABLE', 'CAUTIOUS'],
  };
}

export function candidatePolicyLabel(policy: CandidateMarketContextPolicy): string {
  return policy === 'FAVORABLE_ONLY' ? 'FAVORABLE only' : 'FAVORABLE + CAUTIOUS';
}

export function candidatePolicyImpact(
  current: CandidateMarketContextPolicy,
  proposed: CandidateMarketContextPolicy,
): string | null {
  if (current === proposed) return null;
  if (proposed === 'FAVORABLE_ONLY') {
    return 'Candidates in a CAUTIOUS market context will no longer satisfy the required market-context criterion.';
  }
  return 'Candidates in a CAUTIOUS market context will become eligible to satisfy the required market-context criterion.';
}
