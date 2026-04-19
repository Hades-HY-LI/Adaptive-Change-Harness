import type { CodebaseDetail, FailureCase, RunDetail, RunEvent } from '../../lib/types';

interface DiscoveryConsoleProps {
  run?: RunDetail | null;
  codebase?: CodebaseDetail | null;
  failureCase?: FailureCase | null;
}

const DISCOVERY_STAGES = [
  { key: 'intake', label: 'Intake' },
  { key: 'profile', label: 'Profile' },
  { key: 'baseline', label: 'Baseline' },
  { key: 'probes', label: 'Probes' },
  { key: 'capture', label: 'Capture' },
] as const;

export function DiscoveryConsole({ run, codebase, failureCase }: DiscoveryConsoleProps) {
  if (!run || run.mode !== 'discover') {
    return null;
  }

  const events = run.events;
  const latestSummary = getLatestDiscoverySummary(events);
  const probeEvents = events.filter((event) => event.type === 'probe_executed');
  const stageState = buildStageState(events, run.verdict);
  const baselineEvent = events.find((event) => event.stage === 'discover' && (event.type === 'evaluation_failed' || event.type === 'evaluation_passed'));
  const capturedEvent = [...events].reverse().find((event) => event.type === 'failure_case_captured');
  const baselineResult = getNestedRecord(baselineEvent?.metadata, 'result');
  const baselineDetails = typeof baselineResult?.details === 'string' ? baselineResult.details : undefined;
  const baselineName = typeof baselineResult?.name === 'string' ? baselineResult.name : undefined;
  const captureOutput = typeof capturedEvent?.metadata?.failing_output === 'string' ? capturedEvent.metadata.failing_output : failureCase?.failing_output;
  const captureCommand = typeof capturedEvent?.metadata?.failing_command === 'string' ? capturedEvent.metadata.failing_command : failureCase?.failing_command;

  return (
    <section className="panel discovery-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Discovery Console</p>
          <h2>Active discovery workflow</h2>
          <p className="hero-copy run-subtitle">
            {latestSummary || 'Waiting for profiling and deterministic discovery signals.'}
          </p>
        </div>
        <span className={`verdict-pill verdict-${run.verdict ?? 'needs_review'}`}>{run.verdict ?? 'pending'}</span>
      </div>

      <div className="discovery-stage-row">
        {DISCOVERY_STAGES.map((stage) => (
          <article className={`stage-chip stage-${stageState[stage.key]}`} key={stage.key}>
            <span>{stage.label}</span>
            <strong>{stageState[stage.key]}</strong>
          </article>
        ))}
      </div>

      <div className="discovery-grid">
        <article className="detail-card">
          <div className="section-heading">
            <p className="eyebrow">Codebase</p>
            <h3>Discovery target</h3>
          </div>
          <dl className="metadata-list">
            <div>
              <dt>Label</dt>
              <dd>{codebase?.label || 'unknown'}</dd>
            </div>
            <div>
              <dt>Framework</dt>
              <dd>{codebase?.repo_profile.framework || 'unknown'}</dd>
            </div>
            <div>
              <dt>Test command</dt>
              <dd>{codebase?.repo_profile.test_command || 'unknown'}</dd>
            </div>
            <div>
              <dt>Entrypoints</dt>
              <dd>{codebase?.repo_profile.entrypoints.length || 0}</dd>
            </div>
          </dl>
        </article>

        <article className="detail-card">
          <div className="section-heading">
            <p className="eyebrow">Baseline</p>
            <h3>Deterministic gate</h3>
          </div>
          <p>{baselineEvent?.summary || 'Baseline validation has not reported yet.'}</p>
          {baselineName ? <p className="muted">Evaluator: {baselineName}</p> : null}
          {baselineDetails ? (
            <div className="evidence-block">
              <span>Baseline output</span>
              <pre>{baselineDetails}</pre>
            </div>
          ) : null}
          <p className="muted">
            {run.verdict === 'no_reproducible_failure_found'
              ? 'Baseline and probes did not yield a reproducible stored failure.'
              : failureCase
                ? 'Discovery captured a stored failure after deterministic validation.'
                : 'Discovery is still building evidence.'}
          </p>
        </article>

        <article className="detail-card full-width">
          <div className="section-heading">
            <p className="eyebrow">Probe Execution</p>
            <h3>Candidate failures</h3>
          </div>
          {probeEvents.length === 0 ? (
            <p className="muted">No probes have executed yet in this run.</p>
          ) : (
            <div className="probe-list">
              {probeEvents.map((event) => {
                const passed = event.metadata?.passed === true;
                const command = typeof event.metadata?.command === 'string' ? event.metadata.command : 'unknown';
                const severity = typeof event.metadata?.severity === 'string' ? event.metadata.severity : 'unknown';
                const confidence = typeof event.metadata?.confidence === 'number' ? event.metadata.confidence : undefined;
                const detailsExcerpt = typeof event.metadata?.details_excerpt === 'string' ? event.metadata.details_excerpt : undefined;
                const details = typeof event.metadata?.details === 'string' ? event.metadata.details : undefined;
                return (
                  <article className="probe-row" key={event.id}>
                    <div className="probe-row-top">
                      <strong>{typeof event.metadata?.title === 'string' ? event.metadata.title : event.summary}</strong>
                      <span className={passed ? 'ok' : 'fail'}>{passed ? 'passed' : 'failed'}</span>
                    </div>
                    <p>{event.summary}</p>
                    <p className="muted">{command}</p>
                    <div className="signal-list">
                      <span className="signal-chip">severity {severity}</span>
                      {typeof event.metadata?.probe_id === 'string' ? <span className="signal-chip">{event.metadata.probe_id}</span> : null}
                      {typeof confidence === 'number' ? <span className="signal-chip">confidence {confidence.toFixed(2)}</span> : null}
                    </div>
                    {detailsExcerpt || details ? (
                      <div className="probe-excerpt">
                        <span>Probe output</span>
                        <pre>{detailsExcerpt || details}</pre>
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          )}
        </article>

        <article className="detail-card full-width">
          <div className="section-heading">
            <p className="eyebrow">Capture</p>
            <h3>Selected failure</h3>
          </div>
          {failureCase ? (
            <>
              <div className="capture-summary">
                <div>
                  <span className="capture-label">Title</span>
                  <strong>{failureCase.title}</strong>
                </div>
                <div>
                  <span className="capture-label">Type</span>
                  <strong>{failureCase.failure_type}</strong>
                </div>
                <div>
                  <span className="capture-label">Severity</span>
                  <strong>{failureCase.severity}</strong>
                </div>
                <div>
                  <span className="capture-label">Confidence</span>
                  <strong>{failureCase.confidence.toFixed(2)}</strong>
                </div>
              </div>
              {captureCommand ? (
                <div className="evidence-block">
                  <span>Captured repro command</span>
                  <code>{captureCommand}</code>
                </div>
              ) : null}
              {captureOutput ? (
                <div className="evidence-block">
                  <span>Captured failing output</span>
                  <pre>{captureOutput}</pre>
                </div>
              ) : null}
            </>
          ) : (
            <p className="muted">
              {run.verdict === 'no_reproducible_failure_found'
                ? 'Discovery completed without saving a reproducible failure case.'
                : 'No saved failure case yet.'}
            </p>
          )}
        </article>
      </div>
    </section>
  );
}

function getLatestDiscoverySummary(events: RunEvent[]): string | undefined {
  const relevant = [...events].reverse().find((event) =>
    ['profile', 'discover', 'complete'].includes(event.stage),
  );
  return relevant?.summary;
}

function buildStageState(
  events: RunEvent[],
  verdict: RunDetail['verdict'],
): Record<(typeof DISCOVERY_STAGES)[number]['key'], 'pending' | 'active' | 'done'> {
  const hasRunCreated = events.some((event) => event.type === 'run_created');
  const hasProfile = events.some((event) => event.type === 'codebase_profiled');
  const hasBaseline = events.some((event) => event.stage === 'discover' && (event.type === 'evaluation_failed' || event.type === 'evaluation_passed'));
  const hasProbes = events.some((event) => event.type === 'probe_executed');
  const hasCapture = events.some((event) => event.type === 'failure_case_captured') || verdict === 'no_reproducible_failure_found';

  return {
    intake: resolveStage(hasRunCreated, !hasProfile),
    profile: resolveStage(hasProfile, hasRunCreated && !hasBaseline),
    baseline: resolveStage(hasBaseline, hasProfile && !hasBaseline),
    probes: resolveStage(hasProbes, hasBaseline && !hasCapture),
    capture: resolveStage(hasCapture, hasBaseline && !hasCapture),
  };
}

function resolveStage(done: boolean, active: boolean): 'pending' | 'active' | 'done' {
  if (done) {
    return 'done';
  }
  if (active) {
    return 'active';
  }
  return 'pending';
}

function getNestedRecord(
  source: Record<string, unknown> | null | undefined,
  key: string,
): Record<string, unknown> | undefined {
  const value = source?.[key];
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  return value as Record<string, unknown>;
}
