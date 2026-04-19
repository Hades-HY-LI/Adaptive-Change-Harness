import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RunDetailPanel } from './RunDetail';
import type { FailureCase, RunDetail } from '../../lib/types';

const failureCase: FailureCase = {
  id: 'failure-1',
  created_at: '2026-04-18T12:01:00Z',
  codebase_id: 'codebase-1',
  failure_type: 'negative_total_quote',
  title: 'Negative total quote probe',
  probe_input: {},
  failing_command: 'python .harness/probes/negative_total_quote_probe.py',
  failing_output: 'negative total detected',
  reproduction_steps: ['python .harness/probes/negative_total_quote_probe.py'],
  suspect_files: ['app/services/pricing.py'],
  severity: 'high',
  confidence: 0.95,
  deterministic_check_ids: ['negative_total_quote'],
};

const run: RunDetail = {
  id: 'run-1',
  created_at: '2026-04-18T12:00:00Z',
  mode: 'discover',
  provider: 'openai',
  model: 'gpt-5',
  seed: 7,
  codebase_id: 'codebase-1',
  status: 'completed',
  verdict: 'unsafe',
  workspace_path: '/tmp/workspace',
  error: null,
  events: [
    {
      id: 1,
      run_id: 'run-1',
      type: 'run_created',
      stage: 'setup',
      summary: 'Created isolated workspace for codebase discovery.',
      created_at: '2026-04-18T12:00:01Z',
      metadata: {},
    },
    {
      id: 2,
      run_id: 'run-1',
      type: 'codebase_profiled',
      stage: 'profile',
      summary: 'Detected python / fastapi repository profile.',
      created_at: '2026-04-18T12:00:02Z',
      metadata: {},
    },
    {
      id: 3,
      run_id: 'run-1',
      type: 'discovery_started',
      stage: 'discover',
      summary: 'Running deterministic baseline discovery before adaptive probing is added.',
      created_at: '2026-04-18T12:00:03Z',
      metadata: {},
    },
    {
      id: 4,
      run_id: 'run-1',
      type: 'probe_executed',
      stage: 'discover',
      summary: 'Detected a quote request that returns a negative total.',
      created_at: '2026-04-18T12:00:04Z',
      metadata: {
        probe_id: 'negative_total_quote',
        title: 'Negative total quote probe',
      },
    },
    {
      id: 5,
      run_id: 'run-1',
      type: 'failure_case_captured',
      stage: 'discover',
      summary: 'Negative total quote probe',
      created_at: '2026-04-18T12:00:05Z',
      metadata: {},
    },
    {
      id: 6,
      run_id: 'run-1',
      type: 'verdict_ready',
      stage: 'complete',
      summary: 'Captured a reproducible failure case from baseline discovery.',
      created_at: '2026-04-18T12:00:06Z',
      metadata: {},
    },
  ],
  evidence: {
    failed_evaluators_before: [
      {
        name: 'negative_total_quote',
        passed: false,
        summary: 'Detected a quote request that returns a negative total.',
        details: 'negative total detected',
      },
    ],
    passed_evaluators_after: [],
    root_cause_summary: 'A reproducible failure was captured from deterministic discovery probes against the uploaded codebase.',
    patch_summary: 'Repair is not yet enabled for discover mode in this implementation slice.',
    merge_confidence: 'unsafe',
    artifact_manifest: {
      workspace_path: '/tmp/workspace',
      codebase_id: 'codebase-1',
      failure_case_id: 'failure-1',
    },
    repo_profile_summary: 'python / fastapi',
    failure_case_summary: 'Negative total quote probe',
  },
};

describe('RunDetailPanel', () => {
  it('renders the driving path and grouped stage summaries', () => {
    render(<RunDetailPanel run={run} failureCase={failureCase} />);

    expect(screen.getByText('Events that determined the verdict')).toBeInTheDocument();
    expect(screen.getByText('Grouped event flow')).toBeInTheDocument();
    expect(screen.getAllByText('Negative total quote probe').length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: 'discover' })).toBeInTheDocument();
    expect(screen.getByText(/3 events?/i)).toBeInTheDocument();
  });
});
