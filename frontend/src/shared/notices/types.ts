/**
 * Pure presentation fields from the canonical UX-3 contract.
 * Feature owners validate facts and destinations before constructing a view.
 * Report contexts, domain DTOs, commands and lifecycle comparisons stay with them.
 */
export interface AuthorityRef {
  readonly owner: string;
  readonly contract: string;
  readonly snapshotToken: string;
  /** Original DTO fields/IDs, never private raw payloads or secret URLs. */
  readonly references: readonly string[];
}

export interface KnownSubjectRef {
  readonly identity: 'known-object';
  readonly kind: string;
  readonly id: string;
  readonly label: string;
  readonly versionId: string | null;
}

export type NoticeCause =
  | {
      readonly known: true;
      readonly explanation: string;
      readonly proof: AuthorityRef;
    }
  | { readonly known: false; readonly explanation: string };

/** A presentation of an existing verified target, not a route/context resolver. */
export interface NoticeDestination {
  readonly availability: 'verified-existing';
  /** An absolute internal application path from the owning navigation builder. */
  readonly href: string;
  readonly builder: string;
  readonly subject: KnownSubjectRef;
  readonly granularity: 'object' | 'section' | 'version';
  readonly relationshipProof: AuthorityRef;
}

/** Both variants navigate only; no reader, mutation or retry callback. */
export type NoticeAction<Destination extends NoticeDestination = NoticeDestination> =
  | {
      readonly kind: 'read';
      readonly label: string;
      readonly destination: Destination;
    }
  | {
      readonly kind: 'open-decision';
      readonly label: string;
      readonly destination: Destination;
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

interface NoticeViewContent<Destination extends NoticeDestination> {
  /** Stable cause identity; not a report basis, read time or render generation. */
  readonly id: string;
  readonly catalogRule: string;
  readonly title: string;
  readonly cause: NoticeCause;
  readonly impact: string;
  readonly automatic: AutomaticResolution;
  readonly time: NoticeTimeContext;
  readonly details: readonly DetailRow[];
  readonly actions: readonly NoticeAction<Destination>[];
}

/** The renderable projection, also reused by the full documentation contract. */
export type NoticeView<Destination extends NoticeDestination = NoticeDestination> =
  NoticeViewContent<Destination> &
    (
      | {
          readonly presentation: Extract<NoticePresentation, { kind: 'information' | 'success' }>;
          readonly userNeed: Exclude<UserNeed, { kind: 'required-for-operation' }>;
        }
      | {
          readonly presentation: Exclude<NoticePresentation, { kind: 'information' | 'success' }>;
          readonly userNeed: UserNeed;
        }
    );

export interface NoticeCardProps {
  readonly notice: NoticeView;
  readonly headingLevel: 2 | 3 | 4;
  readonly detailsId: string;
}

export interface NoticeDetailsProps {
  readonly id: string;
  readonly rows: readonly DetailRow[];
  readonly time: NoticeTimeContext;
  /** Secondary navigation remains in the details, never a command callback. */
  readonly actions?: readonly NoticeAction[];
}

export interface ContextActionLinkProps {
  readonly action: NoticeAction;
}
