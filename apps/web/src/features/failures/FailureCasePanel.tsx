import type { FailureCase } from '../../lib/types';

interface FailureCasePanelProps {
  failureCase?: FailureCase | null;
  onRepairFailureCase: (failureCaseId: string) => Promise<void>;
  repairingFailureCaseId?: string | null;
}

function SignalList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="signal-block">
      <h4>{title}</h4>
      {items.length === 0 ? <p className="muted">None recorded.</p> : null}
      {items.length > 0 ? (
        <div className="signal-list">
          {items.map((item) => (
            <span className="signal-chip" key={`${title}-${item}`}>
              {item}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function FailureCasePanel({ failureCase, onRepairFailureCase, repairingFailureCaseId }: FailureCasePanelProps) {
  return (
    <article className="detail-card">
      <div className="section-heading">
        <p className="eyebrow">Failure Case</p>
        <h3>Saved repro</h3>
      </div>
      {!failureCase ? (
        <p className="muted">No failure case loaded for this run.</p>
      ) : (
        <>
          <dl className="metadata-list">
            <div>
              <dt>Title</dt>
              <dd>{failureCase.title}</dd>
            </div>
            <div>
              <dt>Type</dt>
              <dd>{failureCase.failure_type}</dd>
            </div>
            <div>
              <dt>Severity</dt>
              <dd>{failureCase.severity}</dd>
            </div>
            <div>
              <dt>Confidence</dt>
              <dd>{failureCase.confidence.toFixed(2)}</dd>
            </div>
          </dl>
          <div className="command-block">
            <span>Command</span>
            <code>{failureCase.failing_command}</code>
          </div>
          <div className="command-block">
            <span>Failing output excerpt</span>
            <pre>{failureCase.failing_output || 'No failing output captured.'}</pre>
          </div>
          <SignalList title="Reproduction steps" items={failureCase.reproduction_steps} />
          <SignalList title="Suspect files" items={failureCase.suspect_files} />
          <SignalList title="Deterministic checks" items={failureCase.deterministic_check_ids} />
          <div className="callout-actions">
            <button
              className="secondary-button"
              disabled={repairingFailureCaseId === failureCase.id}
              onClick={() => void onRepairFailureCase(failureCase.id)}
              type="button"
            >
              {repairingFailureCaseId === failureCase.id ? 'Starting replay repair...' : 'Repair this failure'}
            </button>
          </div>
        </>
      )}
    </article>
  );
}
