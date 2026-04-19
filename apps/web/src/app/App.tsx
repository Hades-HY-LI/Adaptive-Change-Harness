import { useEffect, useMemo, useState } from 'react';

import {
  createRun,
  fetchCodebase,
  fetchFailureCase,
  fetchProviders,
  fetchRun,
  fetchRuns,
  fetchSkills,
  openRunEventStream,
  repairFailureCase,
  uploadCodebase,
} from '../lib/api';
import type { BreakType, CodebaseDetail, FailureCase, ProviderInfo, RepairSkill, RunDetail, RunMode, RunSummary } from '../lib/types';
import { RepoProfilePanel } from '../features/codebases/RepoProfilePanel';
import { DiscoveryConsole } from '../features/discovery/DiscoveryConsole';
import { FailureCasePanel } from '../features/failures/FailureCasePanel';
import { RunCreateForm } from '../features/runs/RunCreateForm';
import { RunDetailPanel } from '../features/runs/RunDetail';
import { RunList } from '../features/runs/RunList';
import { SkillLibraryPanel } from '../features/skills/SkillLibraryPanel';

export default function App() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [skills, setSkills] = useState<RepairSkill[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>();
  const [selectedRun, setSelectedRun] = useState<RunDetail | null>(null);
  const [selectedCodebase, setSelectedCodebase] = useState<CodebaseDetail | null>(null);
  const [selectedFailureCase, setSelectedFailureCase] = useState<FailureCase | null>(null);
  const [creating, setCreating] = useState(false);
  const [repairingFailureCaseId, setRepairingFailureCaseId] = useState<string | null>(null);
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
      const detail = await loadRunContext(selectedRunId);
      setRuns((current) => current.map((run) => (run.id === detail.id ? detail : run)));
    };
    eventSource.addEventListener('complete', () => {
      void refresh();
      eventSource.close();
    });
    ['run_created', 'break_applied', 'evaluation_failed', 'evaluation_passed', 'diagnosis_ready', 'patch_applied', 'verdict_ready', 'run_failed', 'codebase_profiled', 'discovery_started', 'failure_case_captured', 'probe_executed', 'skill_matched', 'skill_created', 'skill_updated', 'skill_reused'].forEach((eventName) => {
      eventSource.addEventListener(eventName, () => {
        void refresh();
        if (eventName.startsWith('skill_')) {
          void loadSkills();
        }
      });
    });
    return () => eventSource.close();
  }, [selectedRunId]);

  const latestRun = useMemo(() => runs[0], [runs]);

  async function loadInitialData() {
    try {
      const [loadedProviders, loadedRuns, loadedSkills] = await Promise.all([fetchProviders(), fetchRuns(), fetchSkills()]);
      setProviders(loadedProviders);
      setRuns(loadedRuns);
      setSkills(loadedSkills);
      if (loadedRuns[0]) {
        setSelectedRunId(loadedRuns[0].id);
        await loadRunContext(loadedRuns[0].id);
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Failed to load application data.');
    }
  }

  async function loadRunContext(runId: string): Promise<RunDetail> {
    const detail = await fetchRun(runId);
    setSelectedRun(detail);
    const failureCaseId = getFailureCaseId(detail);
    const codebaseId = getCodebaseId(detail);
    setSelectedCodebase(null);
    setSelectedFailureCase(null);
    if (codebaseId) {
      try {
        setSelectedCodebase(await fetchCodebase(codebaseId));
      } catch {
        setSelectedCodebase(null);
      }
    }
    if (failureCaseId) {
      try {
        const loadedFailureCase = await fetchFailureCase(failureCaseId);
        setSelectedFailureCase(loadedFailureCase);
        if (!codebaseId) {
          try {
            setSelectedCodebase(await fetchCodebase(loadedFailureCase.codebase_id));
          } catch {
            setSelectedCodebase(null);
          }
        }
      } catch {
        setSelectedFailureCase(null);
      }
    } else {
      setSelectedFailureCase(null);
    }
    return detail;
  }

  async function loadSkills() {
    try {
      setSkills(await fetchSkills());
    } catch {
      setSkills([]);
    }
  }

  async function handleCreate(input: { mode: RunMode; breakType?: BreakType; provider: string; model: string; seed: number; file?: File | null }) {
    setCreating(true);
    setError(null);
    try {
      let codebaseId: string | undefined;
      if (input.mode === 'discover') {
        if (!input.file) {
          throw new Error('Select a repo zip before starting discover mode.');
        }
        const uploaded = await uploadCodebase(input.file);
        codebaseId = uploaded.id;
      }
      const created = await createRun({
        mode: input.mode,
        breakType: input.breakType,
        provider: input.provider,
        model: input.model,
        seed: input.seed,
        codebaseId,
      });
      setRuns((current) => [created, ...current]);
      setSelectedRunId(created.id);
      await loadRunContext(created.id);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Failed to start run.');
    } finally {
      setCreating(false);
    }
  }

  async function handleRepair(failureCaseId: string) {
    const provider = providers[0];
    const model = provider?.models[0];
    if (!provider || !model) {
      setError('A configured provider is required before repairing a saved failure case.');
      return;
    }
    setRepairingFailureCaseId(failureCaseId);
    setError(null);
    try {
      const created = await repairFailureCase({
        failureCaseId,
        provider: provider.id,
        model,
      });
      setRuns((current) => [created, ...current]);
      setSelectedRunId(created.id);
      await loadRunContext(created.id);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Failed to start failure-case repair.');
    } finally {
      setRepairingFailureCaseId(null);
    }
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Adaptive Change Harness</p>
          <h1>Code-change verification, not chat.</h1>
          <p className="hero-copy">
            Upload a real repo zip to discover latent failures, or fall back to injected breaks when you need a deterministic demo path.
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
              await loadRunContext(run.id);
            }}
          />
          <SkillLibraryPanel skills={skills} />
        </div>
        <div className="right-column">
          <RunDetailPanel
            run={selectedRun}
            failureCase={selectedFailureCase}
          />
          <DiscoveryConsole
            run={selectedRun}
            codebase={selectedCodebase}
            failureCase={selectedFailureCase}
          />
          <div className="detail-stack">
            <FailureCasePanel
              failureCase={selectedFailureCase}
              onRepairFailureCase={handleRepair}
              repairingFailureCaseId={repairingFailureCaseId}
            />
            <RepoProfilePanel codebase={selectedCodebase} />
          </div>
        </div>
      </main>
    </div>
  );
}

function getFailureCaseId(run: RunDetail | null): string | undefined {
  if (!run) {
    return undefined;
  }
  return run.failure_case_id ?? run.evidence?.artifact_manifest?.failure_case_id;
}

function getCodebaseId(run: RunDetail | null): string | undefined {
  if (!run) {
    return undefined;
  }
  return run.codebase_id ?? run.evidence?.artifact_manifest?.codebase_id;
}
