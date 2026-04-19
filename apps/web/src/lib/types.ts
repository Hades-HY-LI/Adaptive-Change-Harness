export type RunMode = 'discover' | 'inject' | 'replay';
export type BreakType = 'logic_regression' | 'contract_violation' | 'invariant_violation';
export type RunStatus = 'queued' | 'running' | 'repairing' | 'completed' | 'failed';
export type Verdict = 'safe' | 'unsafe' | 'needs_review' | 'no_reproducible_failure_found' | null;

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
  repo_profile_summary?: string;
  failure_case_summary?: string;
  skill_decision?: SkillDecision | null;
  replay_comparison?: ReplayComparison | null;
}

export interface RunSummary {
  id: string;
  created_at: string;
  mode: RunMode;
  break_type?: BreakType | null;
  provider: string;
  model: string;
  seed?: number | null;
  codebase_id?: string | null;
  failure_case_id?: string | null;
  status: RunStatus;
  verdict: Verdict;
  workspace_path?: string | null;
  error?: string | null;
}

export interface RepoProfile {
  id: string;
  source_type: 'zip_upload' | 'demo_repo';
  workspace_path: string;
  language: string;
  framework: string;
  package_manager?: string | null;
  install_command?: string | null;
  test_command?: string | null;
  source_dirs: string[];
  test_dirs: string[];
  entrypoints: string[];
  risk_areas: string[];
}

export interface FailureCase {
  id: string;
  created_at: string;
  codebase_id: string;
  failure_type: string;
  title: string;
  probe_input: Record<string, unknown>;
  failing_command: string;
  failing_output: string;
  reproduction_steps: string[];
  suspect_files: string[];
  severity: string;
  confidence: number;
  deterministic_check_ids: string[];
}

export interface CodebaseDetail {
  id: string;
  created_at: string;
  label: string;
  source_type: 'zip_upload' | 'demo_repo';
  archive_path: string;
  extracted_path: string;
  repo_profile: RepoProfile;
}

export interface RepairSkill {
  id: string;
  created_at: string;
  slug: string;
  title: string;
  bug_family: string;
  version: number;
  status: 'active' | 'draft' | 'deprecated';
  trigger_signals?: string[];
  exemplar_failure_case_ids?: string[];
  usage_count?: number;
  success_count?: number;
}

export interface SkillDecision {
  matched_skill_id?: string | null;
  matched_skill_title?: string | null;
  action: string;
  rationale: string;
}

export interface ReplayComparison {
  failure_case_id: string;
  original_failing_command: string;
  original_failure_type: string;
  original_failure_excerpt: string;
  reproduced_before_repair: boolean;
  reproduced_after_repair: boolean;
  latest_repro_excerpt: string;
  validation_commands: string[];
}

export interface RunDetail extends RunSummary {
  events: RunEvent[];
  evidence?: EvidencePacket | null;
}
