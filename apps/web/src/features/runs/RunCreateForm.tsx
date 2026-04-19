import { useMemo, useState } from 'react';

import type { BreakType, ProviderInfo, RunMode, RunSummary } from '../../lib/types';

interface RunCreateFormProps {
  providers: ProviderInfo[];
  creating: boolean;
  onCreate: (input: {
    mode: RunMode;
    breakType?: BreakType;
    provider: string;
    model: string;
    seed: number;
    file?: File | null;
  }) => Promise<void>;
  latestRun?: RunSummary;
}

const BREAK_OPTIONS: Array<{ value: BreakType; label: string; description: string }> = [
  {
    value: 'logic_regression',
    label: 'Logic Regression',
    description: 'Flip a pricing decision and validate the repair loop.',
  },
  {
    value: 'contract_violation',
    label: 'Contract Violation',
    description: 'Break an API response shape and watch the contract checker fail.',
  },
  {
    value: 'invariant_violation',
    label: 'Invariant Violation',
    description: 'Bypass a required service call and let the invariant checker catch it.',
  },
];

export function RunCreateForm({ providers, creating, onCreate, latestRun }: RunCreateFormProps) {
  const [mode, setMode] = useState<RunMode>('discover');
  const [breakType, setBreakType] = useState<BreakType>('logic_regression');
  const [seed, setSeed] = useState(7);
  const [file, setFile] = useState<File | null>(null);
  const provider = providers[0];
  const defaultModel = useMemo(() => provider?.models[0] ?? '', [provider]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!provider || !defaultModel) {
      return;
    }
    if (mode === 'discover' && !file) {
      return;
    }
    await onCreate({
      mode,
      breakType: mode === 'inject' ? breakType : undefined,
      provider: provider.id,
      model: defaultModel,
      seed,
      file,
    });
  };

  return (
    <section className="panel panel-form">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Launch Run</p>
          <h2>Break, evaluate, repair, validate.</h2>
        </div>
        {latestRun ? <span className="badge">Latest {latestRun.status}</span> : null}
      </div>
      {providers.length === 0 ? (
        <div className="empty-state">
          <strong>No live providers configured.</strong>
          <p>Add <code>OPENAI_API_KEY</code> to the API environment before creating runs.</p>
        </div>
      ) : (
        <form className="run-form" onSubmit={handleSubmit}>
          <label>
            <span>Mode</span>
            <select value={mode} onChange={(event) => setMode(event.target.value as RunMode)}>
              <option value="discover">Discover</option>
              <option value="inject">Inject</option>
            </select>
            <small>{mode === 'discover' ? 'Upload a repo zip and look for a real latent failure.' : 'Use the fallback injected-bug demo flow.'}</small>
          </label>

          {mode === 'discover' ? (
            <label>
              <span>Repo Zip</span>
              <input type="file" accept=".zip,application/zip" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
              <small>{file ? file.name : 'Select a Python service repo zip.'}</small>
            </label>
          ) : null}

          {mode === 'inject' ? (
          <label>
            <span>Break Type</span>
            <select value={breakType} onChange={(event) => setBreakType(event.target.value as BreakType)}>
              {BREAK_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <small>{BREAK_OPTIONS.find((option) => option.value === breakType)?.description}</small>
          </label>
          ) : null}

          <label>
            <span>Provider</span>
            <input value={provider?.label ?? 'Unavailable'} disabled />
          </label>

          <label>
            <span>Model</span>
            <input value={defaultModel} disabled />
          </label>

          {mode === 'inject' ? (
            <label>
              <span>Seed</span>
              <input type="number" min={0} value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
            </label>
          ) : null}

          <button className="primary-button" type="submit" disabled={creating}>
            {creating ? 'Starting run...' : mode === 'discover' ? 'Upload and discover' : 'Start inject run'}
          </button>
        </form>
      )}
    </section>
  );
}
