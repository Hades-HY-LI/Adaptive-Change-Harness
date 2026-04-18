import type { EvaluatorResult, RunDetail } from '../../lib/types';

interface RunDetailProps {
  run?: RunDetail | null;
}

function EvaluatorColumn({ title, items }: { title: string; items: EvaluatorResult[] }) {
  return (
    <div className="evaluator-column">
      <h3>{title}</h3>
      {items.length === 0 ? <p className="muted">No entries.</p> : null}
      {items.map((item) => (
        <article className="evaluator-card" key={`${title}-${item.name}`}>
          <div className="evaluator-card-top">
            <strong>{item.name}</strong>
            <span className={item.passed ? 'ok' : 'fail'}>{item.passed ? 'pass' : 'fail'}</span>
          </div>
          <p>{item.summary}</p>
          <pre>{item.details || 'No details captured.'}</pre>
        </article>
      ))}
    </div>
  );
}

export function RunDetailPanel({ run }: RunDetailProps) {
  if (!run) {
    return (
      <section className="panel run-detail-panel">
        <div className="empty-state large">
          <strong>Select a run.</strong>
          <p>The right side becomes the live war room for status, diff context, and evaluator evidence.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel run-detail-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Run Detail</p>
          <h2>{run.break_type.replace(/_/g, ' ')}</h2>
        </div>
        <span className={`status-pill status-${run.status}`}>{run.status}</span>
      </div>

      <div className="detail-grid">
        <article className="detail-card">
          <h3>Verdict</h3>
          <p className={`verdict-text verdict-${run.verdict ?? 'needs_review'}`}>{run.verdict ?? 'pending'}</p>
          <p>{run.evidence?.patch_summary || 'No patch summary yet.'}</p>
        </article>

        <article className="detail-card">
          <h3>Root Cause</h3>
          <p>{run.evidence?.root_cause_summary || 'Waiting for diagnosis.'}</p>
        </article>

        <article className="detail-card full-width">
          <h3>Timeline</h3>
          <div className="timeline">
            {run.events.map((event) => (
              <div className="timeline-item" key={event.id}>
                <span className="timeline-stage">{event.stage}</span>
                <div>
                  <strong>{event.type}</strong>
                  <p>{event.summary}</p>
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="detail-card full-width">
          <h3>Evaluator Evidence</h3>
          <div className="evaluator-grid">
            <EvaluatorColumn title="Failures Before Repair" items={run.evidence?.failed_evaluators_before ?? []} />
            <EvaluatorColumn title="Passing Checks After Repair" items={run.evidence?.passed_evaluators_after ?? []} />
          </div>
        </article>
      </div>
    </section>
  );
}
