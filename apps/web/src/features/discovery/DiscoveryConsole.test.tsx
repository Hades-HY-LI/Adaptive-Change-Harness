import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DiscoveryConsole } from './DiscoveryConsole';
import type { CodebaseDetail, FailureCase, RunDetail } from '../../lib/types';

const codebase: CodebaseDetail = {
  id: 'codebase-1',
  created_at: '2026-04-18T12:00:00Z',
  label: 'billing-service',
  source_type: 'zip_upload',
  archive_path: '/tmp/source.zip',
  extracted_path: '/tmp/repo',
  repo_profile: {
    id: 'codebase-1',
    source_type: 'zip_upload',
    workspace_path: '/tmp/repo',
    language: 'python',
    framework: 'fastapi',
    package_manager: 'pyproject',
    install_command: 'python -m pip install -e .',
    test_command: 'python -m pytest',
    source_dirs: ['app'],
    test_dirs: ['tests'],
    entrypoints: ['app/main.py'],
    risk_areas: ['app/services/pricing.py'],
  },
};

const failureCase: FailureCase = {
  id: 'failure-1',
  created_at: '2026-04-18T12:01:00Z',
  codebase_id: 'codebase-1',
  failure_type: 'negative_total_quote',
  title: 'Negative total quote probe',
  probe_input: {},
  failing_command: 'python .harness/probes/negative_total_quote_probe.py',
  failing_output: 'negative total detected for plan=starter discount=MEGAFLAT total=-3850',
  reproduction_steps: ['python .harness/probes/negative_total_quote_probe.py'],
  suspect_files: ['app/services/pricing.py'],
  severity: 'high',
  confidence: 0.95,
  deterministic_check_ids: ['negative_total_quote'],
};

const discoverRun: RunDetail = {
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
      metadata: codebase.repo_profile as unknown as Record<string, unknown>,
    },
    {
      id: 3,
      run_id: 'run-1',
      type: 'discovery_started',
      stage: 'discover',
      summary: 'Running deterministic baseline discovery before adaptive probing is added.',
      created_at: '2026-04-18T12:00:03Z',
      metadata: { test_command: 'python -m pytest' },
    },
    {
      id: 4,
      run_id: 'run-1',
      type: 'evaluation_passed',
      stage: 'discover',
      summary: 'Baseline tests passed.',
      created_at: '2026-04-18T12:00:04Z',
      metadata: {
        result: {
          name: 'baseline_tests',
          passed: true,
          summary: 'Baseline tests passed.',
          details: '1 passed in 0.02s',
        },
      },
    },
    {
      id: 5,
      run_id: 'run-1',
      type: 'probe_executed',
      stage: 'discover',
      summary: 'Detected a quote request that returns a negative total.',
      created_at: '2026-04-18T12:00:05Z',
      metadata: {
        probe_id: 'negative_total_quote',
        title: 'Negative total quote probe',
        passed: false,
        severity: 'high',
        confidence: 0.95,
        command: 'python .harness/probes/negative_total_quote_probe.py',
        details_excerpt: 'negative total detected for plan=starter discount=MEGAFLAT total=-3850',
        details: 'negative total detected for plan=starter discount=MEGAFLAT total=-3850',
      },
    },
    {
      id: 6,
      run_id: 'run-1',
      type: 'failure_case_captured',
      stage: 'discover',
      summary: 'Negative total quote probe',
      created_at: '2026-04-18T12:00:06Z',
      metadata: failureCase as unknown as Record<string, unknown>,
    },
  ],
  evidence: {
    failed_evaluators_before: [],
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

describe('DiscoveryConsole', () => {
  it('renders baseline output, probe evidence, and captured failure output', () => {
    render(<DiscoveryConsole run={discoverRun} codebase={codebase} failureCase={failureCase} />);

    expect(screen.getByText('Active discovery workflow')).toBeInTheDocument();
    expect(screen.getByText('Baseline tests passed.')).toBeInTheDocument();
    expect(screen.getByText('Evaluator: baseline_tests')).toBeInTheDocument();
    expect(screen.getAllByText(/negative total detected/i).length).toBeGreaterThan(0);
    expect(screen.getByText('Captured repro command')).toBeInTheDocument();
    expect(screen.getAllByText('Negative total quote probe').length).toBeGreaterThan(1);
  });
});
