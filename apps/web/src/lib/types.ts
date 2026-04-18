export type RunMode = 'inject' | 'verify';
export type BreakType = 'logic_regression' | 'contract_violation' | 'invariant_violation';
export type RunStatus = 'queued' | 'running' | 'repairing' | 'completed' | 'failed';
export type Verdict = 'safe' | 'unsafe' | 'needs_review' | null;

export interface ProviderInfo {
  id: string;
  label: string;
  configured: boolean;
  models: string[];
}

export interface RunEvent {
  id: number;
  run_id: string;
  type: string;
  stage: string;
  summary: string;
  created_at: string;
  metadata?: Record<string, unknown> | null;
}

export interface EvaluatorResult {
  name: string;
  passed: boolean;
  summary: string;
  details: string;
  artifact_path?: string | null;
}

export interface EvidencePacket {
  failed_evaluators_before: EvaluatorResult[];
  passed_evaluators_after: EvaluatorResult[];
  root_cause_summary: string;
  patch_summary: string;
  merge_confidence: string;
  artifact_manifest: Record<string, string>;
}

export interface RunSummary {
  id: string;
  created_at: string;
  mode: RunMode;
  break_type: BreakType;
  provider: string;
  model: string;
  seed?: number | null;
  status: RunStatus;
  verdict: Verdict;
  workspace_path?: string | null;
  error?: string | null;
}

export interface RunDetail extends RunSummary {
  events: RunEvent[];
  evidence?: EvidencePacket | null;
}
