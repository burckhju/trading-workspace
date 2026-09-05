export type OperationalPriority = 'ACTION' | 'REVIEW' | 'BLOCKED';
export type OperationalState = 'ACTIONABLE' | 'BLOCKED';

export interface OperationalAction {
  id: string;
  source_feature: string;
  action_type: string;
  priority: OperationalPriority;
  state: OperationalState;
  title: string;
  detail: string;
  resource_type: string;
  resource_id: string;
  next_action: string;
  target: string;
  occurred_at: string | null;
}

export interface OperationalWorkspaceResponse {
  generated_at: string;
  actions: OperationalAction[];
}
