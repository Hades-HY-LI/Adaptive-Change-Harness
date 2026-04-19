import type { EvaluatorResult, FailureCase, RunDetail, RunEvent } from '../../lib/types';

interface RunDetailProps {
  run?: RunDetail | null;
  failureCase?: FailureCase | null;
}

interface StageSummary {
  stage: string;
  label: string;
  count: number;
  latestSummary: string;
  eventTypes: string[];
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

export function RunDetailPanel({ run, failureCase }: RunDetailProps) {
  if (!run) {
    return (
      <section className="panel run-detail-panel">
        <div className="empty-state large">
          <strong>Select a run.</strong>
          <p>The right side becomes the live war room for status, repro commands, deterministic gates, and learned skills.</p>
        </div>
      </section>
    );
  }

  const runTitle = run.mode === 'inject'
    ? (run.break_type ?? 'inject').replace(/_/g, ' ')
    : run.mode === 'discover'
      ? 'discover'
      : 'replay';
  const stageSummaries = buildStageSummaries(run.events);
  const focus = buildDrivingPath(run, failureCase);

  return (
    <section className="panel run-detail-panel">
      <div className="panel-header detail-header">
        <div>
          <p className="eyebrow">Run Console</p>
          <h2>{runTitle}</h2>
          <p className="hero-copy run-subtitle">
            {run.mode === 'discover'
              ? 'Profile, probe, and capture a deterministic failure.'
              : run.mode === 'replay'
                ? 'Replay the saved repro, repair it, and compare before versus after.'
                : 'Use the fallback injected break loop for deterministic demo coverage.'}
          </p>
        </div>
        <div className="status-stack">
          <span className={`status-pill status-${run.status}`}>{run.status}</span>
          <span className={`verdict-pill verdict-${run.verdict ?? 'needs_review'}`}>{run.verdict ?? 'pending'}</span>
        </div>
      </div>

      <div className="console-grid">
        <section className="console-section overview-strip">
          <article>
            <span>Mode</span>
            <strong>{run.mode}</strong>
          </article>
          <article>
            <span>Provider</span>
            <strong>{run.provider}</strong>
          </article>
          <article>
            <span>Model</span>
            <strong>{run.model}</strong>
          </article>
          <article>
            <span>Failure Case</span>
            <strong>{run.evidence?.failure_case_summary ?? 'not captured'}</strong>
          </article>
        </section>

        <article className="detail-card full-width callout-card">
          <div className="section-heading">
            <p className="eyebrow">Verdict</p>
            <h3>{run.verdict ?? 'pending'}</h3>
          </div>
          <p>{run.evidence?.patch_summary || 'No patch summary yet.'}</p>
          <div className="callout-actions">
            <span className="muted">
              {run.evidence?.merge_confidence ? `Merge confidence: ${run.evidence.merge_confidence}` : 'Waiting for deterministic validation.'}
            </span>
          </div>
        </article>

        <article className="detail-card">
          <div className="section-heading">
            <p className="eyebrow">Diagnosis</p>
            <h3>Root cause</h3>
          </div>
          <p>{run.evidence?.root_cause_summary || 'Waiting for diagnosis.'}</p>
        </article>

        <article className="detail-card">
          <div className="section-heading">
            <p className="eyebrow">Learning</p>
            <h3>Skill decision</h3>
          </div>
          <p className="skill-action">{run.evidence?.skill_decision?.action ?? 'none'}</p>
          <p>{run.evidence?.skill_decision?.rationale || 'No skill decision recorded yet.'}</p>
          {run.evidence?.skill_decision?.matched_skill_title ? (
            <div className="linked-skill">
              <span>Matched skill</span>
              <strong>{run.evidence.skill_decision.matched_skill_title}</strong>
            </div>
          ) : null}
        </article>

        {run.evidence?.replay_comparison ? (
          <article className="detail-card full-width">
            <div className="section-heading">
              <p className="eyebrow">Replay Comparison</p>
              <h3>Before vs after</h3>
            </div>
            <div className="comparison-grid">
              <div>
                <span className={`comparison-state ${run.evidence.replay_comparison.reproduced_before_repair ? 'comparison-fail' : 'comparison-pass'}`}>
                  {run.evidence.replay_comparison.reproduced_before_repair ? 'failure reproduced' : 'failure did not reproduce'}
                </span>
                <p className="muted">Before repair</p>
                <p>{run.evidence.replay_comparison.original_failure_excerpt}</p>
              </div>
              <div>
                <span className={`comparison-state ${run.evidence.replay_comparison.reproduced_after_repair ? 'comparison-fail' : 'comparison-pass'}`}>
                  {run.evidence.replay_comparison.reproduced_after_repair ? 'still failing' : 'repro cleared'}
                </span>
                <p className="muted">After repair</p>
                <p>{run.evidence.replay_comparison.latest_repro_excerpt}</p>
              </div>
            </div>
            <SignalList title="Validation commands" items={run.evidence.replay_comparison.validation_commands} />
          </article>
        ) : null}

        <article className="detail-card full-width">
          <div className="section-heading">
            <p className="eyebrow">Driving Path</p>
            <h3>Events that determined the verdict</h3>
          </div>
          {focus.events.length === 0 ? (
            <p className="muted">No focus path identified yet.</p>
          ) : (
            <div className="focus-path">
              {focus.events.map((event) => (
                <div className={`focus-path-item ${event.id === focus.highlightedEventId ? 'focus-highlight' : ''}`} key={event.id}>
                  <span className="timeline-stage">{stageLabel(event.stage)}</span>
                  <div>
                    <strong>{event.type}</strong>
                    <p>{event.summary}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="detail-card full-width">
          <div className="section-heading">
            <p className="eyebrow">Stage Summaries</p>
            <h3>Grouped event flow</h3>
          </div>
          <div className="stage-summary-grid">
            {stageSummaries.map((stage) => (
              <article className="stage-summary-card" key={stage.stage}>
                <div className="stage-summary-top">
                  <strong>{stage.label}</strong>
                  <span>{stage.count} event{stage.count === 1 ? '' : 's'}</span>
                </div>
                <p>{stage.latestSummary}</p>
                <div className="signal-list">
                  {stage.eventTypes.map((eventType) => (
                    <span className="signal-chip" key={`${stage.stage}-${eventType}`}>
                      {eventType}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </article>

        <article className="detail-card full-width">
          <div className="section-heading">
            <p className="eyebrow">Evaluator Evidence</p>
            <h3>Deterministic checks</h3>
          </div>
          <div className="evaluator-grid">
            <EvaluatorColumn title="Failures before repair" items={run.evidence?.failed_evaluators_before ?? []} />
            <EvaluatorColumn title="Passing checks after repair" items={run.evidence?.passed_evaluators_after ?? []} />
          </div>
        </article>
      </div>
    </section>
  );
}

function EvaluatorColumn({ title, items }: { title: string; items: EvaluatorResult[] }) {
  return (
    <div className="evaluator-column">
      <div className="section-heading">
        <p className="eyebrow">Deterministic Gate</p>
        <h3>{title}</h3>
      </div>
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

function buildStageSummaries(events: RunEvent[]): StageSummary[] {
  const grouped = new Map<string, RunEvent[]>();
  const order: string[] = [];

  for (const event of events) {
    if (!grouped.has(event.stage)) {
      grouped.set(event.stage, []);
      order.push(event.stage);
    }
    grouped.get(event.stage)?.push(event);
  }

  return order.map((stage) => {
    const stageEvents = grouped.get(stage) ?? [];
    const latest = stageEvents[stageEvents.length - 1];
    return {
      stage,
      label: stageLabel(stage),
      count: stageEvents.length,
      latestSummary: latest?.summary || 'No summary captured.',
      eventTypes: Array.from(new Set(stageEvents.map((event) => event.type))).slice(0, 4),
    };
  });
}

function buildDrivingPath(
  run: RunDetail,
  failureCase?: FailureCase | null,
): { events: RunEvent[]; highlightedEventId?: number } {
  const selected: RunEvent[] = [];
  const push = (event: RunEvent | undefined) => {
    if (!event || selected.some((existing) => existing.id === event.id)) {
      return;
    }
    selected.push(event);
  };

  const first = (predicate: (event: RunEvent) => boolean) => run.events.find(predicate);
  const last = (predicate: (event: RunEvent) => boolean) => [...run.events].reverse().find(predicate);

  push(first((event) => event.type === 'run_created'));

  if (run.mode === 'discover') {
    push(first((event) => event.type === 'codebase_profiled'));
    push(first((event) => event.type === 'discovery_started'));

    const matchedProbe = run.events.find((event) =>
      event.type === 'probe_executed'
      && (
        event.metadata?.probe_id === failureCase?.failure_type
        || event.metadata?.title === failureCase?.title
      ),
    );
    push(matchedProbe);
    push(last((event) => event.type === 'failure_case_captured'));
    push(last((event) => event.type === 'verdict_ready'));

    return {
      events: selected,
      highlightedEventId: matchedProbe?.id ?? last((event) => event.type === 'failure_case_captured')?.id,
    };
  }

  if (run.mode === 'replay') {
    push(first((event) => event.stage === 'replay' && (event.type === 'evaluation_failed' || event.type === 'evaluation_passed')));
    push(first((event) => event.type === 'skill_matched'));
    push(first((event) => event.type === 'diagnosis_ready'));
    push(first((event) => event.type === 'patch_applied'));
    push(first((event) => event.type === 'skill_created' || event.type === 'skill_updated' || event.type === 'skill_reused'));
    push(last((event) => event.type === 'verdict_ready'));

    return {
      events: selected,
      highlightedEventId:
        first((event) => event.type === 'skill_created' || event.type === 'skill_updated' || event.type === 'skill_reused')?.id
        ?? last((event) => event.type === 'verdict_ready')?.id,
    };
  }

  push(first((event) => event.type === 'break_applied'));
  push(first((event) => event.stage === 'evaluate' && (event.type === 'evaluation_failed' || event.type === 'evaluation_passed')));
  push(first((event) => event.type === 'diagnosis_ready'));
  push(first((event) => event.type === 'patch_applied'));
  push(last((event) => event.type === 'verdict_ready'));

  return {
    events: selected,
    highlightedEventId: first((event) => event.type === 'break_applied')?.id ?? last((event) => event.type === 'verdict_ready')?.id,
  };
}

function stageLabel(stage: string): string {
  return {
    setup: 'Setup',
    profile: 'Profile',
    discover: 'Discover',
    break: 'Break',
    evaluate: 'Evaluate',
    diagnose: 'Diagnose',
    repair: 'Repair',
    replay: 'Replay',
    validate: 'Validate',
    complete: 'Complete',
    error: 'Error',
  }[stage] ?? stage;
}
