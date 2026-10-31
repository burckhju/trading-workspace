/**
 * UX-3 proposal, documentation only. No runtime imports or implementation.
 * Domain owners keep authority; these types describe presentation inputs.
 * See notice-contract.md for runtime validation that types cannot prove.
 */
import type { ExecutionCurrencyResolution } from '../../../frontend/src/features/trade/types/api';
import type {
  RealizedGrossItem,
  RealizedGrossReport,
} from '../../../frontend/src/features/performance/types/api';
import type { ApiErrorResponse } from '../../../frontend/src/features/market/types/api';
import type { TradePlanVersionResponse } from '../../../frontend/src/features/trade_plan/types/api';
import type { ProductEvaluationResponse } from '../../../frontend/src/features/product_selection/types/api';
import type { Ft011MaterializationStatus } from '../../../frontend/src/features/learning/types/materialization';
import type { ProposalApprovalResult } from '../../../frontend/src/features/model/types/proposalApproval';
import type { RuntimeActivation } from '../../../frontend/src/features/model/types/runtimeActivation';

export type DeepReadonly<T> = T extends object
  ? { readonly [K in keyof T]: DeepReadonly<T[K]> }
  : T;

export interface SubjectRef {
  readonly kind: string;
  readonly id: string;
  readonly label: string;
  readonly versionId: string | null;
}

/** Local validated read context, never an API/DB status or a trusted URL claim. */
export interface NoticeContext {
  readonly workspaceKey: string;
  readonly subject: SubjectRef;
  readonly relatedSubjects: readonly SubjectRef[];
  readonly purpose: string;
  readonly versionPins: Readonly<Record<string, string>>;
  readonly report: {
    readonly kind: 'realized-gross' | 'closed-trades';
    readonly definitionVersion: string;
    readonly filters: Readonly<RealizedGrossReport['filters']>;
    readonly basisId: RealizedGrossReport['basis']['id'];
  } | null;
  readonly sourceIdentity: string | null;
  readonly requestGeneration: number;
  readonly snapshotToken: string;
}

export interface AuthorityRef {
  readonly owner: string;
  readonly contract: string;
  readonly snapshotToken: string;
  /** Original DTO field paths/IDs; no private raw payload or secret URL. */
  readonly references: readonly string[];
}

/** Original owner DTO and fields, rather than a cloned list of domain states. */
export interface OwnerEvidence<Facts extends object> {
  readonly authority: AuthorityRef;
  readonly snapshot: DeepReadonly<Facts>;
  readonly conditionFields: readonly (keyof Facts & string)[];
}

export type NoticeCause =
  | {
      readonly known: true;
      readonly explanation: string;
      readonly proof: AuthorityRef;
    }
  | { readonly known: false; readonly explanation: string };

export interface ExistingDestination {
  readonly availability: 'verified-existing';
  readonly href: string;
  readonly builder: string;
  readonly subject: SubjectRef;
  readonly granularity: 'object' | 'section' | 'version';
  /** Source context; destination may be a proven parent (execution -> trade). */
  readonly context: NoticeContext;
  readonly relationshipProof: AuthorityRef;
}

export interface UnavailableDestination {
  readonly availability: 'integration-required';
  readonly explanation: string;
  readonly owner: 'UX-2';
}

/** Both variants only navigate. Writes remain in explicit owner workflows. */
export type NoticeAction =
  | {
      readonly kind: 'read';
      readonly label: string;
      readonly destination: ExistingDestination;
    }
  | {
      readonly kind: 'open-decision';
      readonly label: string;
      readonly destination: ExistingDestination;
      readonly decision: 'confirm' | 'correct' | 'review' | 'approve';
      readonly confirmation: 'explicit-in-owner';
    };

export type UserNeed =
  | { readonly kind: 'none'; readonly explanation: string }
  | { readonly kind: 'optional-inspection'; readonly explanation: string }
  | {
      readonly kind: 'required-for-operation';
      readonly operation: string;
      readonly explanation: string;
      readonly proof: AuthorityRef;
    };

export type AutomaticResolution =
  | { readonly kind: 'none-evidenced'; readonly explanation: string }
  | {
      readonly kind: 'owner-result-reused';
      readonly explanation: string;
      readonly proof: AuthorityRef;
    }
  | {
      readonly kind: 'owner-retry-scheduled';
      readonly explanation: string;
      readonly notBefore: string;
      readonly proof: AuthorityRef;
    };

/** A proof reference is necessary, not sufficient: owner validation is mandatory. */
export interface ResolutionProof {
  readonly authority: AuthorityRef;
  readonly sameConditionId: string;
  readonly checkedAt: string;
  readonly resolvedImpact: string;
}

export type NoticeLifecycle =
  | {
      readonly kind: 'active';
      readonly change: 'uncompared';
      readonly comparisonSnapshotToken: null;
    }
  | {
      readonly kind: 'active';
      readonly change: 'new-in-session' | 'unchanged' | 'worsened';
      readonly comparisonSnapshotToken: string;
      readonly comparisonProof: AuthorityRef;
    }
  | { readonly kind: 'resolved'; readonly proof: ResolutionProof }
  | {
      readonly kind: 'historical';
      readonly occurredAt: string | null;
      readonly historicalContext: string;
    };

export type NoticePresentation =
  | {
      readonly kind: 'information';
      readonly priority: 'data-quality-information' | 'normal';
    }
  | {
      readonly kind: 'warning';
      readonly priority: 'decision-required' | 'relevant-problem' | 'data-quality-information';
    }
  | {
      readonly kind: 'blocker';
      readonly priority: 'blocked-operation';
      readonly blockedOperation: string;
      readonly proof: AuthorityRef;
    }
  | {
      readonly kind: 'error';
      readonly priority: 'blocked-operation' | 'decision-required' | 'relevant-problem';
      readonly failedOperation: string;
      readonly proof: AuthorityRef;
    }
  | {
      readonly kind: 'success';
      readonly priority: 'normal';
      readonly completedOperation: string;
      readonly proof: AuthorityRef;
    };

export interface NoticeTimeContext {
  readonly observedAt: string | null;
  readonly checkedAt: string | null;
  readonly validFrom: string | null;
  readonly validTo: string | null;
  readonly explanation: string;
}

export interface DetailRow {
  readonly label: string;
  readonly value: string;
  readonly proof: AuthorityRef | null;
}

export interface Notice<Facts extends object> {
  /** Stable identity excludes translated text, poll time and request generation. */
  readonly id: string;
  readonly catalogRule: string;
  readonly context: NoticeContext;
  readonly evidence: OwnerEvidence<Facts>;
  readonly presentation: NoticePresentation;
  readonly title: string;
  readonly cause: NoticeCause;
  readonly impact: string;
  readonly automatic: AutomaticResolution;
  readonly userNeed: UserNeed;
  readonly lifecycle: NoticeLifecycle;
  readonly time: NoticeTimeContext;
  readonly details: readonly DetailRow[];
  readonly actions: readonly NoticeAction[];
  readonly missingDestination: UnavailableDestination | null;
}

export interface NoticeCardProps<Facts extends object> {
  readonly notice: Notice<Facts>;
  readonly headingLevel: 2 | 3 | 4;
  readonly detailsId: string;
  readonly onNavigate: (destination: ExistingDestination) => void;
}

export interface NoticeGroup {
  readonly id: string;
  readonly title: string;
  readonly noticeIds: readonly string[];
  readonly affectedSubjects: readonly SubjectRef[];
  readonly primaryNoticeId: string;
}

export interface NoticeSummaryProps {
  /** Host deduplicates, orders and counts distinct subjects before rendering. */
  readonly groups: readonly NoticeGroup[];
  readonly onOpenGroup: (groupId: string) => void;
}

export interface NoticeDetailsProps {
  readonly id: string;
  readonly rows: readonly DetailRow[];
  readonly time: NoticeTimeContext;
}

export interface ContextActionLinkProps {
  readonly action: NoticeAction;
  readonly onNavigate: (destination: ExistingDestination) => void;
}

export interface NoticeStatusProps {
  readonly presentation: NoticePresentation;
  readonly label: string;
  readonly time: NoticeTimeContext | null;
}

/** Examples bind to existing public types; they introduce no domain enums. */
export type CurrencyNotice = Notice<ExecutionCurrencyResolution>;
export type PerformanceItemNotice = Notice<RealizedGrossItem>;
export type PerformanceReportNotice = Notice<RealizedGrossReport>;
export type PlanNotice = Notice<TradePlanVersionResponse>;
export type ProductEvaluationNotice = Notice<ProductEvaluationResponse>;
export type MaterializationNotice = Notice<Ft011MaterializationStatus>;
export type ApiFailureNotice = Notice<ApiErrorResponse>;

/** Approval and activation remain separate original evidence, never one status. */
export interface GovernanceEvidence {
  readonly approval: ProposalApprovalResult | null;
  readonly activation: RuntimeActivation | null;
}
export type GovernanceNotice = Notice<GovernanceEvidence>;

// RefreshCheck is private in MarketDataRefreshPanel.tsx at the audited commit.
// A follow-up must expose its existing owner read contract before a typed adapter.
// Do not copy its enums here or mistake qualified_success for HTTP reachability.
