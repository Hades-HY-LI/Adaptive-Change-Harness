import type { BreakType, CodebaseDetail, FailureCase, ProviderInfo, RepairSkill, RunDetail, RunMode, RunSummary } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_PREFIX = `${API_BASE_URL}/api/v1`;

async function readJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export async function fetchProviders(): Promise<ProviderInfo[]> {
  const payload = await readJson<{ items: ProviderInfo[] }>(`${API_PREFIX}/providers`);
  return payload.items;
}

export async function fetchRuns(): Promise<RunSummary[]> {
  const payload = await readJson<{ items: RunSummary[] }>(`${API_PREFIX}/runs`);
  return payload.items;
}

export async function fetchRun(runId: string): Promise<RunDetail> {
  const payload = await readJson<{ item: RunDetail }>(`${API_PREFIX}/runs/${runId}`);
  return payload.item;
}

export async function fetchFailureCase(failureCaseId: string): Promise<FailureCase> {
  const payload = await readJson<{ item: FailureCase }>(`${API_PREFIX}/failure-cases/${failureCaseId}`);
  return payload.item;
}

export async function fetchCodebase(codebaseId: string): Promise<CodebaseDetail> {
  const payload = await readJson<{ item: CodebaseDetail }>(`${API_PREFIX}/codebases/${codebaseId}`);
  return payload.item;
}

export async function fetchSkills(): Promise<RepairSkill[]> {
  const payload = await readJson<{ items: RepairSkill[] }>(`${API_PREFIX}/skills`);
  return payload.items;
}

export async function uploadCodebase(file: File): Promise<CodebaseDetail> {
  const formData = new FormData();
  formData.append('file', file);
  const payload = await readJson<{ item: CodebaseDetail }>(`${API_PREFIX}/codebases/upload`, {
    method: 'POST',
    body: formData,
  });
  return payload.item;
}

export async function createRun(input: {
  mode: RunMode;
  breakType?: BreakType;
  provider: string;
  model: string;
  seed?: number;
  codebaseId?: string;
  failureCaseId?: string;
}): Promise<RunSummary> {
  const payload = await readJson<{ item: RunSummary }>(`${API_PREFIX}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mode: input.mode,
      break_type: input.breakType,
      provider: input.provider,
      model: input.model,
      seed: input.seed ?? 7,
      codebase_id: input.codebaseId,
      failure_case_id: input.failureCaseId,
    }),
  });
  return payload.item;
}

export function openRunEventStream(runId: string): EventSource {
  return new EventSource(`${API_PREFIX}/runs/${runId}/events`);
}

export async function repairFailureCase(input: {
  failureCaseId: string;
  provider: string;
  model: string;
}): Promise<RunSummary> {
  const payload = await readJson<{ item: RunSummary }>(`${API_PREFIX}/failure-cases/${input.failureCaseId}/repair`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      provider: input.provider,
      model: input.model,
    }),
  });
  return payload.item;
}
