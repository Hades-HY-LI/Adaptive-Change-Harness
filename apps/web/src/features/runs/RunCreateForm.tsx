import { useMemo, useState } from 'react';

import type { BreakType, ProviderInfo, RunSummary } from '../../lib/types';

interface RunCreateFormProps {
  providers: ProviderInfo[];
  creating: boolean;
  onCreate: (input: { breakType: BreakType; provider: string; model: string; seed: number }) => Promise<void>;
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
  const [breakType, setBreakType] = useState<BreakType>('logic_regression');
  const [seed, setSeed] = useState(7);
  const provider = providers[0];
  const defaultModel = useMemo(() => provider?.models[0] ?? '', [provider]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!provider || !defaultModel) {
      return;
    }
    await onCreate({ breakType, provider: provider.id, model: defaultModel, seed });
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

          <label>
            <span>Provider</span>
            <input value={provider?.label ?? 'Unavailable'} disabled />
          </label>

          <label>
            <span>Model</span>
            <input value={defaultModel} disabled />
          </label>

          <label>
            <span>Seed</span>
            <input type="number" min={0} value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
          </label>

          <button className="primary-button" type="submit" disabled={creating}>
            {creating ? 'Starting run...' : 'Start run'}
          </button>
        </form>
      )}
    </section>
  );
}
