import type { BreakType, ProviderInfo, RunDetail, RunSummary } from './types';

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

export async function createRun(input: {
  breakType: BreakType;
  provider: string;
  model: string;
  seed?: number;
}): Promise<RunSummary> {
  const payload = await readJson<{ item: RunSummary }>(`${API_PREFIX}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mode: 'inject',
      break_type: input.breakType,
      provider: input.provider,
      model: input.model,
      seed: input.seed ?? 7,
    }),
  });
  return payload.item;
}

export function openRunEventStream(runId: string): EventSource {
  return new EventSource(`${API_PREFIX}/runs/${runId}/events`);
}
