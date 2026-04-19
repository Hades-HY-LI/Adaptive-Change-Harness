import type { RunSummary } from '../../lib/types';

interface RunListProps {
  runs: RunSummary[];
  selectedRunId?: string;
  onSelect: (run: RunSummary) => void;
}

export function RunList({ runs, selectedRunId, onSelect }: RunListProps) {
  return (
    <section className="panel run-list-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Run Queue</p>
          <h2>Recent runs</h2>
        </div>
      </div>
      <div className="run-list">
        {runs.length === 0 ? (
          <div className="empty-state">
            <strong>No runs yet.</strong>
            <p>Start a run to populate the verification timeline.</p>
          </div>
        ) : (
          runs.map((run) => (
            <button
              className={`run-card ${run.id === selectedRunId ? 'selected' : ''}`}
              key={run.id}
              onClick={() => onSelect(run)}
              type="button"
            >
              <div className="run-card-top">
                <span className={`status-pill status-${run.status}`}>{run.status}</span>
                <span className={`verdict-pill verdict-${run.verdict ?? 'needs_review'}`}>{run.verdict ?? 'pending'}</span>
              </div>
              <strong>{run.mode === 'inject' ? (run.break_type ?? 'inject').replace(/_/g, ' ') : run.mode}</strong>
              <span className="run-card-meta">
                {run.mode === 'discover'
                  ? run.codebase_id
                    ? `codebase ${run.codebase_id.slice(0, 8)}`
                    : 'awaiting codebase'
                  : run.failure_case_id
                    ? `failure ${run.failure_case_id.slice(0, 8)}`
                    : 'demo workspace'}
              </span>
              <span>{new Date(run.created_at).toLocaleString()}</span>
            </button>
          ))
        )}
      </div>
    </section>
  );
}
