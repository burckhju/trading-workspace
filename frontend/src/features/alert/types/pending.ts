/** Optional host navigation contract. This does not create a risk or approval state. */
export interface PositionRiskPending {
  isDirty: () => boolean;
  isBusy: () => boolean;
  discard: () => void;
}
