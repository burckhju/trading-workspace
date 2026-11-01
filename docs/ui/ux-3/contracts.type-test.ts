/** Documentation type tests. Synthetic identities only; never execute commands. */
import type { ExecutionCurrencyResolution } from '../../../frontend/src/features/trade/types/api';
import type {
  ClosedTradeItem,
  RealizedGrossItem,
  RealizedGrossReport,
} from '../../../frontend/src/features/performance/types/api';
import type {
  ActivationReadContext,
  ApiFailureNotice,
  ApprovalReadContext,
  AuthorityRef,
  AutomaticResolution,
  ClosedReportSnapshot,
  ClosedTradeStatisticsNotice,
  CurrencyNotice,
  DeepReadonly,
  ExistingDestination,
  GovernanceEvidence,
  KnownSubjectRef,
  NoticeAction,
  NoticeCause,
  NoticeContext,
  NoticeLifecycle,
  NoticePresentation,
  OperationSubjectRef,
  OwnerEvidence,
  OwnerFailureSource,
  PerformanceItemNotice,
  PerformanceReportNotice,
  ReadFailureEvidence,
  RealizedItemEvidence,
  RealizedReportSnapshot,
  ReceiptReadbackFailureEvidence,
  UserNeed,
  WriteRejectionEvidence,
  WriteUnknownEvidence,
} from './contracts';

export const context = {
  workspaceKey: 'synthetic-workspace',
  subject: {
    identity: 'known-object',
    kind: 'execution',
    id: '00000000-0000-4000-8000-000000000001',
    label: 'Synthetische Kaufbuchung',
    versionId: null,
  },
  purpose: 'execution-currency-evidence',
  relatedSubjects: [
    {
      identity: 'known-object',
      kind: 'trade',
      id: '00000000-0000-4000-8000-000000000002',
      label: 'Synthetischer Trade',
      versionId: null,
    },
  ],
  versionPins: {},
  report: null,
  sourceIdentity: null,
  requestGeneration: 1,
  snapshotToken: 'synthetic-read-1',
} as const satisfies NoticeContext;

export const authority = {
  owner: 'trade_position',
  contract: 'execution-currency-v3',
  snapshotToken: context.snapshotToken,
  references: ['currency_resolution.source', 'currency_resolution.reason'],
} as const satisfies AuthorityRef;

export const currencyFacts = {
  currency_code: null,
  source: 'UNKNOWN',
  source_execution_ids: [],
  confirmation_ids: [],
  evidence_ids: [],
  evidence: [],
  reason: 'NO_HISTORICAL_EVIDENCE',
  resolver_version: 'execution-currency-v3',
} satisfies ExecutionCurrencyResolution;

export const destination = {
  availability: 'verified-existing',
  href: '/trade-management?trade_id=00000000-0000-4000-8000-000000000002#execution-dates',
  builder: 'existing trade booking section',
  subject: {
    identity: 'known-object',
    kind: 'trade',
    id: '00000000-0000-4000-8000-000000000002',
    label: 'Synthetischer Trade',
    versionId: null,
  },
  granularity: 'section',
  context,
  relationshipProof: {
    owner: 'trade_position',
    contract: 'ExecutionResponse',
    snapshotToken: context.snapshotToken,
    references: [
      'execution.id=00000000-0000-4000-8000-000000000001',
      'execution.trade_id=00000000-0000-4000-8000-000000000002',
    ],
  },
} as const satisfies ExistingDestination;

export const readAction = {
  kind: 'read',
  label: 'Vorhandene Kaufbelege prüfen',
  destination,
} as const satisfies NoticeAction;

export const decisionAction = {
  kind: 'open-decision',
  label: 'Währungsbestätigung vorbereiten',
  destination,
  decision: 'confirm',
  confirmation: 'explicit-in-owner',
} as const satisfies NoticeAction;

export const currencyNotice = {
  id: 'trade_position:currency-unresolved:synthetic-execution',
  catalogRule: 'execution-currency.unresolved',
  context,
  evidence: {
    authority,
    snapshot: currencyFacts,
    conditionFields: ['source', 'reason'],
  },
  presentation: { kind: 'warning', priority: 'relevant-problem' },
  title: 'Ausführungswährung noch nicht belegt',
  cause: {
    known: true,
    explanation: 'Für diese Buchung liegt kein ausreichender historischer Nachweis vor.',
    proof: authority,
  },
  impact: 'Eine währungsabhängige Qualifikation benötigt einen gültigen Nachweis.',
  automatic: {
    kind: 'none-evidenced',
    explanation: 'Der vorhandene Resolver hat keinen ausreichenden Nachweis gefunden.',
  },
  userNeed: {
    kind: 'optional-inspection',
    explanation: 'Vorhandene Quellen können geprüft werden.',
  },
  lifecycle: {
    kind: 'active',
    change: 'uncompared',
    comparisonSnapshotToken: null,
  },
  time: {
    observedAt: null,
    checkedAt: null,
    validFrom: null,
    validTo: null,
    explanation: 'Fehlende Zeiten bleiben unbekannt.',
  },
  details: [],
  actions: [readAction],
  missingDestination: null,
} as const satisfies CurrencyNotice;

export const receiptAuthority = {
  owner: 'trade_position',
  contract: 'ExecutionCurrencyConfirmation',
  snapshotToken: 'synthetic-confirmation-receipt-2',
  references: ['confirmation.id=synthetic-confirmation-2', 'request_id=synthetic-request-2'],
} as const satisfies AuthorityRef;

export const resolvedCurrencyFacts = {
  currency_code: 'EUR',
  source: 'EXECUTION_DOCUMENT',
  source_execution_ids: [context.subject.id],
  confirmation_ids: [],
  evidence_ids: ['synthetic-document-3'],
  resolver_version: 'execution-currency-v3',
} satisfies ExecutionCurrencyResolution;

export const recoveryAuthority = {
  owner: 'trade_position',
  contract: 'execution-currency-v3',
  snapshotToken: 'synthetic-qualified-read-3',
  references: [
    'currency_resolution.source=EXECUTION_DOCUMENT',
    'evidence_ids=synthetic-document-3',
  ],
} as const satisfies AuthorityRef;

export const successWithReceipt = {
  kind: 'success',
  priority: 'normal',
  completedOperation: 'Explizite Bestätigung gespeichert',
  proof: receiptAuthority,
} as const satisfies NoticePresentation;

export const resolvedWithEvidence = {
  kind: 'resolved',
  proof: {
    authority: recoveryAuthority,
    sameConditionId: currencyNotice.id,
    checkedAt: '2026-10-30T12:00:00Z',
    resolvedImpact: 'Owner bestätigt die nun ausreichende historische Evidenz.',
  },
} as const satisfies NoticeLifecycle;

export const partialSummary = {
  status: 'PARTIAL',
  total: null,
  total_display: null,
  subtotal: '12.50',
  subtotal_display: '12.50',
  rounding_difference: '0.00',
  rounding_difference_display: '0.00',
} satisfies RealizedGrossReport['summary'];

export const emptySummary = {
  status: 'EMPTY',
  total: '0',
  total_display: '0.00',
  subtotal: null,
  subtotal_display: null,
  rounding_difference: null,
  rounding_difference_display: null,
} satisfies RealizedGrossReport['summary'];

// Negative contracts: removing an expected error must fail the typecheck.
// @ts-expect-error A severity word is not an execution currency source.
export const domainSeverityMixup: ExecutionCurrencyResolution['source'] = 'WARNING';

// @ts-expect-error Success needs the completed operation and its evidence.
export const unprovedSuccess: NoticePresentation = {
  kind: 'success',
  priority: 'normal',
};

// @ts-expect-error A blocker must identify the operation and owner proof.
export const unprovedBlocker: NoticePresentation = {
  kind: 'blocker',
  priority: 'blocked-operation',
};

// @ts-expect-error A recovery cannot be inferred from an empty list or timestamp alone.
export const unprovedRecovery: NoticeLifecycle = { kind: 'resolved' };

// @ts-expect-error Information cannot demand a user decision.
export const urgentInformation: NoticePresentation = {
  kind: 'information',
  priority: 'decision-required',
};

export const unprovedDeterioration: NoticeLifecycle = {
  kind: 'active',
  change: 'worsened',
  // @ts-expect-error A first unqualified comparison cannot claim deterioration.
  comparisonSnapshotToken: null,
};

// @ts-expect-error Required user decisions need an operation and owner proof.
export const unprovedNeed: UserNeed = {
  kind: 'required-for-operation',
  explanation: 'Please act',
};

// @ts-expect-error A retry must be backed by a real schedule and owner proof.
export const inventedRetry: AutomaticResolution = {
  kind: 'owner-retry-scheduled',
  explanation: 'Soon',
};

// @ts-expect-error A known cause cannot omit its supporting owner evidence.
export const guessedCause: NoticeCause = {
  known: true,
  explanation: 'Probably an old listing',
};

// @ts-expect-error Decision navigation must state explicit confirmation in the owner.
export const silentDecision: NoticeAction = {
  kind: 'open-decision',
  label: 'Confirm',
  destination,
  decision: 'confirm',
};

export const hiddenPost: NoticeAction = {
  kind: 'read',
  label: 'Open',
  destination,
  // @ts-expect-error Notice actions do not accept write methods or request payloads.
  method: 'POST',
};

export const mutationCallback: NoticeAction = {
  kind: 'read',
  label: 'Open',
  destination,
  // @ts-expect-error Notice actions cannot execute mutations.
  onExecute: () => undefined,
};

export const unavailableTarget = {
  availability: 'integration-required',
  explanation: 'Exact source-check route missing',
  owner: 'UX-2',
} as const;
export const speculativeAction: NoticeAction = {
  kind: 'read',
  label: 'Open source',
  // @ts-expect-error An integration request is not a usable navigation destination.
  destination: unavailableTarget,
};

// @ts-expect-error A response must be tied to a generation and snapshot, not only an ID.
export const incompleteContext: NoticeContext = {
  workspaceKey: 'synthetic',
  subject: context.subject,
};

export const invalidCurrencyFields: OwnerEvidence<ExecutionCurrencyResolution> = {
  authority,
  snapshot: currencyFacts,
  // @ts-expect-error No copied/imagined domain field may replace real DTO keys.
  conditionFields: ['risk_approval_status'],
};

export function approvalIsNotActivation(
  approval: NonNullable<GovernanceEvidence['approval']>,
): void {
  // @ts-expect-error Approval is not a RuntimeActivation result.
  const activation: GovernanceEvidence['activation'] = approval;
  void activation;
}

export function immutableEvidence(value: CurrencyNotice): void {
  // @ts-expect-error Presentation may not turn a read into user confirmation.
  value.evidence.snapshot.source = 'USER_CONFIRMED';
}

export function immutableSources(value: CurrencyNotice): void {
  // @ts-expect-error Presentation must not add source evidence to its input.
  value.evidence.snapshot.evidence_ids?.push('invented-evidence');
}

// @ts-expect-error Money remains a domain decimal string or null, not a JS number fallback.
export const unknownTotalAsNumber: RealizedGrossReport['summary']['total'] = 0;

// Phase-1 precision 1: the attempted object does not exist merely because a form does.
export const knownParent = context.relatedSubjects[0] satisfies KnownSubjectRef;
export const beforeCreate = {
  identity: 'operation-context',
  operation: 'journal.CREATE_DRAFT',
  label: 'Journalentwurf für den gewählten Trade anlegen',
  parent: knownParent,
} as const satisfies OperationSubjectRef;

export const createContext = {
  ...context,
  subject: beforeCreate,
  purpose: 'journal-create-draft',
  snapshotToken: 'synthetic-journal-attempt-1',
} as const satisfies NoticeContext;

// A known parent remains a possible verified destination before the child is known.
export const parentFromCreate = {
  ...destination,
  context: createContext,
  subject: knownParent,
} as const satisfies ExistingDestination;

export const noParentYet = {
  identity: 'operation-context',
  operation: 'trade.capture',
  label: 'Erstkauf erfassen',
  parent: null,
} as const satisfies OperationSubjectRef;

export const fabricatedCreateIdentity: OperationSubjectRef = {
  ...beforeCreate,
  // @ts-expect-error A pending/uncertain create does not have a new object ID.
  id: 'invented-journal-id',
};

export const unknownCreateDestination: ExistingDestination = {
  ...parentFromCreate,
  // @ts-expect-error Only the known parent, not the attempted child, is navigable.
  subject: beforeCreate,
};

// Phase-1 precision 2: HTTP shape is diagnostic evidence, not a write classifier.
export const structured503 = {
  kind: 'api',
  status: 503,
  response: {
    code: 'HTTP_503',
    message: 'Synthetischer strukturierter Serverfehler',
    details: [],
    timestamp: '2026-11-01T10:00:00Z',
  },
} as const satisfies OwnerFailureSource;

export const journalUnknown = {
  classification: 'write-unknown',
  operation: {
    operation: 'journal.CREATE_DRAFT',
    effect: 'write',
    context: createContext,
    classifier: 'useTradeJournal.perform',
    classificationProof: {
      owner: 'learning/journal',
      contract: 'useTradeJournal.perform',
      snapshotToken: createContext.snapshotToken,
      references: ['MarketApiError.status=503', 'attempt.outcome=unknown'],
    },
  },
  error: structured503,
} as const satisfies WriteUnknownEvidence;

export const journalUnknownNotice = {
  ...currencyNotice,
  id: 'learning:journal-create:synthetic-attempt',
  catalogRule: 'journal.command.outcome-unconfirmed',
  context: createContext,
  evidence: {
    authority: journalUnknown.operation.classificationProof,
    snapshot: journalUnknown,
    conditionFields: ['classification', 'operation', 'error'],
  },
  title: 'Ausgang des Journalauftrags noch unklar',
  cause: { known: false, explanation: 'Der Owner hat keinen bestätigten Abschluss.' },
  impact: 'Weitere Journalaufträge bleiben nach dem vorhandenen Ownerguard gesperrt.',
  automatic: { kind: 'none-evidenced', explanation: 'Keine automatische Wiederholung.' },
  userNeed: { kind: 'optional-inspection', explanation: 'Den bestehenden Ownerkontext prüfen.' },
  actions: [],
} as const satisfies ApiFailureNotice;

// @ts-expect-error A structured 503 does not turn the owner's unknown into rejection.
export const journal503AsRejection: WriteRejectionEvidence = journalUnknown;

export const bareApiFailure: ApiFailureNotice = {
  ...journalUnknownNotice,
  evidence: {
    authority,
    // @ts-expect-error Original error without owner operation/classification is insufficient.
    snapshot: structured503.response,
    conditionFields: [],
  },
};

export const explicitRejection = {
  classification: 'write-rejected',
  operation: {
    ...journalUnknown.operation,
    classificationProof: {
      ...journalUnknown.operation.classificationProof,
      references: ['MarketApiError.status=409', 'rejected=true', 'attempt=null'],
    },
  },
  error: {
    ...structured503,
    status: 409,
    response: { ...structured503.response, code: 'JOURNAL_CONFLICT' },
  },
} as const satisfies WriteRejectionEvidence;

export const lessonCreateUnknown = {
  ...journalUnknown,
  operation: {
    ...journalUnknown.operation,
    operation: 'lesson.create-from-evidence',
    context: {
      ...createContext,
      subject: {
        identity: 'operation-context',
        operation: 'lesson.create-from-evidence',
        label: 'Lesson aus gelesener Evidence anlegen',
        parent: {
          identity: 'known-object',
          kind: 'learning-evidence',
          id: 'synthetic-evidence-1',
          label: 'Synthetische Evidence',
          versionId: 'synthetic-evidence-version-1',
        },
      },
    },
    classifier: 'LessonDraftFromEvidence.submit',
    classificationProof: {
      ...journalUnknown.operation.classificationProof,
      contract: 'LessonDraftFromEvidence.submit',
      references: ['uncertain=true', 'unknownOutcome.current=true'],
    },
  },
} as const satisfies WriteUnknownEvidence;

export const inventedLessonRetry: WriteUnknownEvidence = {
  ...lessonCreateUnknown,
  // @ts-expect-error Journal's owner-specific retry is not a generic command capability.
  retry: { method: 'POST', reuseKey: true },
};

export const journalReceipt = {
  result_id: 'synthetic-journal-version-1',
  result_type: 'TRADE_JOURNAL_VERSION',
  replayed: false,
} as const;

export const journalReadback = {
  classification: 'read-failed',
  operation: {
    operation: 'journal.history after CREATE_DRAFT receipt',
    effect: 'read',
    context: {
      ...createContext,
      subject: {
        identity: 'known-object',
        kind: 'journal-version',
        id: journalReceipt.result_id,
        label: 'Bestätigter Journalentwurf',
        versionId: journalReceipt.result_id,
      },
      requestGeneration: 2,
      snapshotToken: 'synthetic-journal-readback-2',
    },
    classifier: 'useTradeJournal.load',
    classificationProof: {
      ...journalUnknown.operation.classificationProof,
      snapshotToken: 'synthetic-journal-readback-2',
      references: ['readState=error', 'receiptAttempt.receipt exists'],
    },
  },
  error: { kind: 'transport', message: 'Lesestand konnte nicht bestätigt werden.' },
} as const satisfies ReadFailureEvidence;

export const receiptWithReadFailure = {
  classification: 'receipt-confirmed-readback-failed',
  operation: {
    ...journalUnknown.operation,
    classificationProof: {
      ...journalUnknown.operation.classificationProof,
      references: ['attempt.outcome=confirmed', 'receipt.result_id=synthetic-journal-version-1'],
    },
  },
  receipt: {
    authority: {
      ...journalUnknown.operation.classificationProof,
      contract: 'JournalReceipt',
      snapshotToken: 'synthetic-journal-receipt-1',
      references: ['result_id=synthetic-journal-version-1'],
    },
    snapshot: journalReceipt,
    conditionFields: ['result_id', 'result_type', 'replayed'],
  },
  readback: journalReadback,
  relationshipProof: {
    ...journalReadback.operation.classificationProof,
    references: ['same frozen trade/command', 'receipt result bound to exact readback'],
  },
} as const satisfies ReceiptReadbackFailureEvidence<typeof journalReceipt>;

export const receiptReadbackNotice = {
  ...journalUnknownNotice,
  id: 'learning:journal-readback:synthetic-attempt',
  catalogRule: 'journal.confirmed-command.readback-failed',
  context: journalReadback.operation.context,
  evidence: {
    authority: receiptWithReadFailure.relationshipProof,
    snapshot: receiptWithReadFailure,
    conditionFields: ['receipt', 'readback'],
  },
  title: 'Journalauftrag bestätigt; aktueller Lesestand nicht bestätigt',
  cause: { known: false, explanation: 'Der anschließende Readback ist fehlgeschlagen.' },
  impact: 'Den exakten Lesestand erneut prüfen; keine weitere Speicherung auslösen.',
} as const satisfies ApiFailureNotice<typeof journalReceipt>;

// @ts-expect-error A readback problem cannot reclassify the confirmed write as unknown.
export const confirmedAsUnknown: WriteUnknownEvidence = receiptWithReadFailure;

// @ts-expect-error A readback failure without the original confirmed receipt is incomplete.
export const missingReceipt: ReceiptReadbackFailureEvidence<typeof journalReceipt> = {
  classification: 'receipt-confirmed-readback-failed',
  operation: receiptWithReadFailure.operation,
  readback: journalReadback,
  relationshipProof: receiptWithReadFailure.relationshipProof,
};

export const successForUnconfirmedWrite: ApiFailureNotice = {
  ...journalUnknownNotice,
  // @ts-expect-error Transport/unknown facts do not become a confirmed-success notice.
  presentation: successWithReceipt,
};

// Phase-1 precision 3: independent reads distinguish absence from non-observation.
export const approvalRequest = {
  workspaceKey: context.workspaceKey,
  reader: 'proposalApprovalClient.getForProposal',
  modelId: 'synthetic-model-A',
  proposalId: 'synthetic-proposal-A',
  versionPins: { approved_version: 'synthetic-version-A2' },
  requestGeneration: 7,
} as const satisfies ApprovalReadContext<'synthetic-model-A'>;

export const activationRequest = {
  workspaceKey: context.workspaceKey,
  reader: 'runtimeActivationClient.getCurrent',
  modelId: 'synthetic-model-A',
  approvedVersionId: 'synthetic-version-A2',
  versionPins: { approved_version: 'synthetic-version-A2' },
  requestGeneration: 3,
} as const satisfies ActivationReadContext<'synthetic-model-A'>;

export const separateGovernance = {
  modelId: 'synthetic-model-A',
  approval: {
    state: 'not-read',
    context: approvalRequest,
    readStartedAt: null,
    readCompletedAt: null,
    snapshotToken: null,
  },
  activation: {
    state: 'loading',
    context: activationRequest,
    readStartedAt: '2026-11-01T10:02:00Z',
    readCompletedAt: null,
    snapshotToken: null,
  },
} as const satisfies GovernanceEvidence<'synthetic-model-A'>;

export const approvalRead = {
  state: 'ready',
  context: approvalRequest,
  readStartedAt: '2026-11-01T10:01:00Z',
  readCompletedAt: '2026-11-01T10:01:01Z',
  snapshotToken: 'synthetic-approval-read-7',
  authority: {
    owner: 'model-governance',
    contract: 'ProposalApprovalPanel',
    snapshotToken: 'synthetic-approval-read-7',
    references: ['proposal_id=synthetic-proposal-A', 'model_id=synthetic-model-A'],
  },
  value: {
    model_version: {
      id: 'synthetic-version-A2',
      model_id: 'synthetic-model-A',
      version: 2,
      status: 'APPROVED',
      definition: {},
      change_summary: 'Synthetische Freigabe',
      created_at: '2026-11-01T09:00:00Z',
      created_by: 'synthetic-actor',
      previous_version_id: 'synthetic-version-A1',
    },
    approval: {
      id: 'synthetic-approval-A2',
      proposal_id: 'synthetic-proposal-A',
      model_version_id: 'synthetic-version-A2',
      approved_at: '2026-11-01T09:00:00Z',
      approved_by: 'synthetic-actor',
      correlation_id: null,
    },
  },
} as const satisfies GovernanceEvidence<'synthetic-model-A'>['approval'];

export const runtimeReadError = {
  state: 'error',
  context: activationRequest,
  readStartedAt: '2026-11-01T10:02:00Z',
  readCompletedAt: '2026-11-01T10:02:02Z',
  snapshotToken: null,
  authority: {
    owner: 'model-governance',
    contract: 'RuntimeActivationPanel',
    snapshotToken: 'synthetic-runtime-attempt-3',
    references: ['ready=false', 'model_id=synthetic-model-A'],
  },
  error: structured503,
} as const satisfies GovernanceEvidence<'synthetic-model-A'>['activation'];

export const approvalWithRuntimeReadError = {
  modelId: 'synthetic-model-A',
  approval: approvalRead,
  activation: runtimeReadError,
} as const satisfies GovernanceEvidence<'synthetic-model-A'>;

export const confirmedNoActivation = {
  state: 'ready',
  context: { ...activationRequest, requestGeneration: 4 },
  readStartedAt: '2026-11-01T10:03:00Z',
  readCompletedAt: '2026-11-01T10:03:01Z',
  snapshotToken: 'synthetic-runtime-read-4',
  authority: {
    ...runtimeReadError.authority,
    snapshotToken: 'synthetic-runtime-read-4',
    references: ['ready=true', 'current=null', 'model_id=synthetic-model-A'],
  },
  value: null,
} as const satisfies GovernanceEvidence<'synthetic-model-A'>['activation'];

// Approval A2 and an independently read active A1 are valid, different statements.
export const activeEarlierVersion = {
  ...confirmedNoActivation,
  value: {
    id: 'synthetic-activation-A1',
    model_id: 'synthetic-model-A',
    model_version_id: 'synthetic-version-A1',
    activated_at: '2026-10-30T09:00:00Z',
    activated_by: 'synthetic-actor',
    correlation_id: null,
    model_version: {
      ...approvalRead.value.model_version,
      id: 'synthetic-version-A1',
      version: 1,
      previous_version_id: null,
    },
  },
} as const satisfies GovernanceEvidence<'synthetic-model-A'>['activation'];

export const legacyNullableGovernance: GovernanceEvidence = {
  modelId: 'synthetic-model-A',
  approval: approvalRead,
  // @ts-expect-error Bare null does not distinguish unread, failed and confirmed absent.
  activation: null,
};

// @ts-expect-error An error cannot carry an authoritative current=null result.
export const failedReadAsAbsence: GovernanceEvidence<'synthetic-model-A'>['activation'] = {
  ...runtimeReadError,
  value: null,
};

export const foreignRuntimeContext: GovernanceEvidence<'synthetic-model-A'>['activation'] = {
  ...activeEarlierVersion,
  context: {
    ...activationRequest,
    // @ts-expect-error Model-B read does not belong to Model-A, even with the same UI token.
    modelId: 'synthetic-model-B',
  },
};

export const foreignRuntimePayload: GovernanceEvidence<'synthetic-model-A'>['activation'] = {
  ...activeEarlierVersion,
  value: {
    ...activeEarlierVersion.value,
    // @ts-expect-error A matching request scope does not make a foreign result valid.
    model_id: 'synthetic-model-B',
  },
};

// @ts-expect-error A shared UI token cannot substitute for an individual request generation.
export const missingReadGeneration: ApprovalReadContext<'synthetic-model-A'> = {
  workspaceKey: context.workspaceKey,
  reader: 'proposalApprovalClient.getForProposal',
  modelId: 'synthetic-model-A',
  proposalId: 'synthetic-proposal-A',
  versionPins: {},
};

// Phase-1 precision 4: original population-specific DTOs and their response binding.
// Declarations are synthetic type inputs, not fetched/validated production responses.
export declare const realizedReportA: DeepReadonly<RealizedReportSnapshot<'period-basis-A'>>;
export declare const closedReportA: DeepReadonly<ClosedReportSnapshot<'closed-basis-A'>>;
export declare const realizedItemA: DeepReadonly<RealizedGrossItem>;
export declare const closedItemA: DeepReadonly<ClosedTradeItem>;

export const realizedContext = {
  ...context,
  purpose: 'period-sell-contribution',
  report: {
    kind: 'realized-gross',
    definitionVersion: 'realized-gross-sell-v2',
    filters: {
      from_date: '2026-10-01',
      to_date: '2026-10-31',
      report_currency: 'EUR',
      report_timezone: 'Europe/Vienna',
    },
    basisId: 'period-basis-A',
    validation: { reportValidator: 'verifyRealizedReport', proof: authority },
  },
} as const satisfies NoticeContext;

export const closedContext = {
  ...context,
  purpose: 'closed-trade-lifetime-result',
  report: {
    kind: 'closed-trades',
    definitionVersion: 'closed-trade-gross-v1',
    filters: realizedContext.report.filters,
    basisId: 'closed-basis-A',
    validation: { reportValidator: 'verifyClosedReport', proof: authority },
  },
} as const satisfies NoticeContext;

export const realizedReportNotice = {
  ...currencyNotice,
  context: realizedContext,
  evidence: { authority, snapshot: realizedReportA, conditionFields: ['summary', 'basis'] },
} as const satisfies PerformanceReportNotice<'period-basis-A'>;

export const closedReportNotice = {
  ...currencyNotice,
  context: closedContext,
  evidence: { authority, snapshot: closedReportA, conditionFields: ['summary', 'basis'] },
} as const satisfies PerformanceReportNotice<'closed-basis-A'>;

export const realizedItemNotice = {
  ...currencyNotice,
  context: realizedContext,
  evidence: {
    authority,
    snapshot: {
      report: realizedReportA,
      item: realizedItemA,
      itemBasisId: 'period-basis-A',
      membershipProof: authority,
    },
    conditionFields: ['item', 'itemBasisId'],
  },
} as const satisfies PerformanceItemNotice<'period-basis-A'>;

export const closedItemNotice = {
  ...currencyNotice,
  context: closedContext,
  evidence: {
    authority,
    snapshot: {
      report: closedReportA,
      item: closedItemA,
      itemBasisId: 'closed-basis-A',
      membershipProof: authority,
    },
    conditionFields: ['item', 'itemBasisId'],
  },
} as const satisfies PerformanceItemNotice<'closed-basis-A'>;

export const closedStatisticsNotice = {
  ...currencyNotice,
  context: closedContext,
  evidence: {
    authority,
    snapshot: {
      report: closedReportA,
      statistics: closedReportA.statistics,
      validation: { statisticsValidator: 'verifyClosedStatistics', proof: authority },
    },
    conditionFields: ['statistics'],
  },
} as const satisfies ClosedTradeStatisticsNotice<'closed-basis-A'>;

// @ts-expect-error Structurally compatible filters/basis do not merge the populations.
export const wrongReportPopulation: PerformanceReportNotice<'period-basis-A'> = {
  ...realizedReportNotice,
  context: {
    ...closedContext,
    report: { ...closedContext.report, basisId: 'period-basis-A' },
  },
};

export const wrongDefinition: NoticeContext = {
  ...closedContext,
  // @ts-expect-error A closed-trade context cannot claim the period-SELL definition.
  report: { ...closedContext.report, definitionVersion: 'realized-gross-sell-v2' },
};

export const wrongReportBasisContext: PerformanceReportNotice<'period-basis-A'> = {
  ...realizedReportNotice,
  context: {
    ...realizedContext,
    report: {
      ...realizedContext.report,
      // @ts-expect-error The current report cannot retain another response's context basis.
      basisId: 'period-basis-B',
    },
  },
};

export const wrongItemPopulation: OwnerEvidence<RealizedItemEvidence<'period-basis-A'>> = {
  ...realizedItemNotice.evidence,
  snapshot: {
    ...realizedItemNotice.evidence.snapshot,
    // @ts-expect-error A closed-trade item is not a period SELL contribution.
    item: closedItemA,
  },
};

export const staleItemBasis: OwnerEvidence<RealizedItemEvidence<'period-basis-A'>> = {
  ...realizedItemNotice.evidence,
  snapshot: {
    ...realizedItemNotice.evidence.snapshot,
    // @ts-expect-error A selected item from an older response cannot use the current binding.
    itemBasisId: 'period-basis-B',
  },
};

export const wrongStatisticsBasis: ClosedTradeStatisticsNotice<'closed-basis-A'> = {
  ...closedStatisticsNotice,
  evidence: {
    ...closedStatisticsNotice.evidence,
    snapshot: {
      ...closedStatisticsNotice.evidence.snapshot,
      statistics: {
        ...closedReportA.statistics,
        // @ts-expect-error Statistics remain bound to this exact report basis.
        report_basis_id: 'closed-basis-B',
      },
    },
  },
};

export const wrongStatisticsContext: ClosedTradeStatisticsNotice<'closed-basis-A'> = {
  ...closedStatisticsNotice,
  // @ts-expect-error Closed-cohort statistics cannot use a period-SELL context.
  context: realizedContext,
};

export const missingStatisticsValidation: ClosedTradeStatisticsNotice<'closed-basis-A'> = {
  ...closedStatisticsNotice,
  evidence: {
    ...closedStatisticsNotice.evidence,
    snapshot: {
      ...closedStatisticsNotice.evidence.snapshot,
      // @ts-expect-error A label claiming validation needs the existing validator's proof.
      validation: { statisticsValidator: 'verifyClosedStatistics' },
    },
  },
};

// Presentation/user-need consistency, without introducing another presentation kind.
// @ts-expect-error Information cannot create a required owner decision.
export const mandatoryInformation: CurrencyNotice = {
  ...currencyNotice,
  presentation: { kind: 'information', priority: 'normal' },
  userNeed: {
    kind: 'required-for-operation',
    operation: 'confirm currency',
    explanation: 'Synthetic invalid combination',
    proof: authority,
  },
};

// @ts-expect-error A successful operation alone cannot create a mandatory follow-up.
export const mandatorySuccess: CurrencyNotice = {
  ...currencyNotice,
  presentation: successWithReceipt,
  userNeed: {
    kind: 'required-for-operation',
    operation: 'confirm again',
    explanation: 'Synthetic invalid combination',
    proof: authority,
  },
};
