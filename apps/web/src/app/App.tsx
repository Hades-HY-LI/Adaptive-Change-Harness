import { useEffect, useMemo, useState } from 'react';

import { createRun, fetchProviders, fetchRun, fetchRuns, openRunEventStream } from '../lib/api';
import type { ProviderInfo, RunDetail, RunSummary } from '../lib/types';
import { RunCreateForm } from '../features/runs/RunCreateForm';
import { RunDetailPanel } from '../features/runs/RunDetail';
import { RunList } from '../features/runs/RunList';

export default function App() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>();
  const [selectedRun, setSelectedRun] = useState<RunDetail | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadInitialData();
  }, []);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }
    const eventSource = openRunEventStream(selectedRunId);
    eventSource.onmessage = () => undefined;
    eventSource.onerror = () => {
      eventSource.close();
    };
    const refresh = async () => {
      const detail = await fetchRun(selectedRunId);
      setSelectedRun(detail);
      setRuns((current) => current.map((run) => (run.id === detail.id ? detail : run)));
    };
    eventSource.addEventListener('complete', () => {
      void refresh();
      eventSource.close();
    });
    ['run_created', 'break_applied', 'evaluation_failed', 'diagnosis_ready', 'patch_applied', 'verdict_ready', 'run_failed'].forEach((eventName) => {
      eventSource.addEventListener(eventName, () => {
        void refresh();
      });
    });
    return () => eventSource.close();
  }, [selectedRunId]);

  const latestRun = useMemo(() => runs[0], [runs]);

  async function loadInitialData() {
    try {
      const [loadedProviders, loadedRuns] = await Promise.all([fetchProviders(), fetchRuns()]);
      setProviders(loadedProviders);
      setRuns(loadedRuns);
      if (loadedRuns[0]) {
        setSelectedRunId(loadedRuns[0].id);
        setSelectedRun(await fetchRun(loadedRuns[0].id));
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Failed to load application data.');
    }
  }

  async function handleCreate(input: { breakType: 'logic_regression' | 'contract_violation' | 'invariant_violation'; provider: string; model: string; seed: number }) {
    setCreating(true);
    setError(null);
    try {
      const created = await createRun(input);
      const detail = await fetchRun(created.id);
      setRuns((current) => [created, ...current]);
      setSelectedRunId(created.id);
      setSelectedRun(detail);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Failed to start run.');
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Adaptive Change Harness</p>
          <h1>Code-change verification, not chat.</h1>
          <p className="hero-copy">
            Inject a break, watch deterministic evaluators fail, route the evidence through a repair provider, then validate whether the patch is safe to merge.
          </p>
        </div>
        {error ? <div className="error-banner">{error}</div> : null}
      </header>

      <main className="main-grid">
        <div className="left-column">
          <RunCreateForm providers={providers} creating={creating} onCreate={handleCreate} latestRun={latestRun} />
          <RunList
            runs={runs}
            selectedRunId={selectedRunId}
            onSelect={async (run) => {
              setSelectedRunId(run.id);
              setSelectedRun(await fetchRun(run.id));
            }}
          />
        </div>
        <RunDetailPanel run={selectedRun} />
      </main>
    </div>
  );
}
