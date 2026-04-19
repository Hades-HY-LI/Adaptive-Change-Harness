import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { CodebaseDetail, FailureCase, ProviderInfo, RepairSkill, RunDetail, RunSummary } from '../lib/types';

const apiMocks = vi.hoisted(() => ({
  createRun: vi.fn(),
  fetchCodebase: vi.fn(),
  fetchFailureCase: vi.fn(),
  fetchProviders: vi.fn(),
  fetchRun: vi.fn(),
  fetchRuns: vi.fn(),
  fetchSkills: vi.fn(),
  openRunEventStream: vi.fn(),
  repairFailureCase: vi.fn(),
  uploadCodebase: vi.fn(),
}));

vi.mock('../lib/api', () => apiMocks);

import App from './App';

const provider: ProviderInfo = {
  id: 'openai',
  label: 'OpenAI',
  configured: true,
  models: ['gpt-5'],
};

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

const skills: RepairSkill[] = [
  {
    id: 'skill-1',
    created_at: '2026-04-18T12:05:00Z',
    slug: 'negative-total-quote',
    title: 'Negative total quote repair',
    bug_family: 'negative_total_quote',
    version: 1,
    status: 'active',
    usage_count: 1,
    success_count: 1,
  },
];

const discoverSummary: RunSummary = {
  id: 'run-discover',
  created_at: '2026-04-18T12:10:00Z',
  mode: 'discover',
  provider: 'openai',
  model: 'gpt-5',
  seed: 7,
  codebase_id: 'codebase-1',
  status: 'completed',
  verdict: 'unsafe',
  workspace_path: '/tmp/workspace-discover',
  error: null,
};

const replaySummary: RunSummary = {
  id: 'run-replay',
  created_at: '2026-04-18T12:11:00Z',
  mode: 'replay',
  provider: 'openai',
  model: 'gpt-5',
  seed: 7,
  codebase_id: 'codebase-1',
  failure_case_id: 'failure-1',
  status: 'completed',
  verdict: 'safe',
  workspace_path: '/tmp/workspace-replay',
  error: null,
};

const discoverDetail: RunDetail = {
  ...discoverSummary,
  events: [
    {
      id: 1,
      run_id: 'run-discover',
      type: 'run_created',
      stage: 'setup',
      summary: 'Created isolated workspace for codebase discovery.',
      created_at: '2026-04-18T12:10:01Z',
      metadata: {},
    },
    {
      id: 2,
      run_id: 'run-discover',
      type: 'codebase_profiled',
      stage: 'profile',
      summary: 'Detected python / fastapi repository profile.',
      created_at: '2026-04-18T12:10:02Z',
      metadata: codebase.repo_profile as unknown as Record<string, unknown>,
    },
    {
      id: 3,
      run_id: 'run-discover',
      type: 'discovery_started',
      stage: 'discover',
      summary: 'Running deterministic baseline discovery before adaptive probing is added.',
      created_at: '2026-04-18T12:10:03Z',
      metadata: { test_command: 'python -m pytest' },
    },
    {
      id: 4,
      run_id: 'run-discover',
      type: 'evaluation_passed',
      stage: 'discover',
      summary: 'Baseline tests passed.',
      created_at: '2026-04-18T12:10:04Z',
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
      run_id: 'run-discover',
      type: 'probe_executed',
      stage: 'discover',
      summary: 'Detected a quote request that returns a negative total.',
      created_at: '2026-04-18T12:10:05Z',
      metadata: {
        probe_id: 'negative_total_quote',
        title: 'Negative total quote probe',
        passed: false,
        severity: 'high',
        confidence: 0.95,
        command: failureCase.failing_command,
        details_excerpt: failureCase.failing_output,
        details: failureCase.failing_output,
      },
    },
    {
      id: 6,
      run_id: 'run-discover',
      type: 'failure_case_captured',
      stage: 'discover',
      summary: failureCase.title,
      created_at: '2026-04-18T12:10:06Z',
      metadata: failureCase as unknown as Record<string, unknown>,
    },
    {
      id: 7,
      run_id: 'run-discover',
      type: 'verdict_ready',
      stage: 'complete',
      summary: 'Captured a reproducible failure case from baseline discovery.',
      created_at: '2026-04-18T12:10:07Z',
      metadata: {},
    },
  ],
  evidence: {
    failed_evaluators_before: [
      {
        name: 'negative_total_quote',
        passed: false,
        summary: 'Detected a quote request that returns a negative total.',
        details: failureCase.failing_output,
      },
    ],
    passed_evaluators_after: [],
    root_cause_summary: 'A reproducible failure was captured from deterministic discovery probes against the uploaded codebase.',
    patch_summary: 'Repair is not yet enabled for discover mode in this implementation slice.',
    merge_confidence: 'unsafe',
    artifact_manifest: {
      workspace_path: '/tmp/workspace-discover',
      codebase_id: 'codebase-1',
      failure_case_id: 'failure-1',
    },
    repo_profile_summary: 'python / fastapi',
    failure_case_summary: failureCase.title,
  },
};

const replayDetail: RunDetail = {
  ...replaySummary,
  events: [
    {
      id: 10,
      run_id: 'run-replay',
      type: 'run_created',
      stage: 'setup',
      summary: 'Created isolated workspace for saved failure-case repair.',
      created_at: '2026-04-18T12:11:01Z',
      metadata: {},
    },
    {
      id: 11,
      run_id: 'run-replay',
      type: 'evaluation_failed',
      stage: 'replay',
      summary: 'Saved failure case reproduced successfully.',
      created_at: '2026-04-18T12:11:02Z',
      metadata: {},
    },
    {
      id: 12,
      run_id: 'run-replay',
      type: 'skill_reused',
      stage: 'learn',
      summary: 'Matched skill guidance was sufficient without creating a new revision.',
      created_at: '2026-04-18T12:11:03Z',
      metadata: {},
    },
    {
      id: 13,
      run_id: 'run-replay',
      type: 'verdict_ready',
      stage: 'validate',
      summary: 'Saved repro and baseline checks passed after repair.',
      created_at: '2026-04-18T12:11:04Z',
      metadata: {},
    },
  ],
  evidence: {
    failed_evaluators_before: [
      {
        name: 'saved_repro',
        passed: false,
        summary: 'Saved failure case reproduced successfully.',
        details: failureCase.failing_output,
      },
    ],
    passed_evaluators_after: [
      {
        name: 'saved_repro',
        passed: true,
        summary: 'Saved repro no longer fails after repair.',
        details: 'no negative total detected',
      },
    ],
    root_cause_summary: 'Flat discounts were not bounded before tax was calculated.',
    patch_summary: 'Clamp the taxable total to zero before tax is calculated.',
    merge_confidence: 'safe',
    artifact_manifest: {
      workspace_path: '/tmp/workspace-replay',
      codebase_id: 'codebase-1',
      failure_case_id: 'failure-1',
    },
    repo_profile_summary: 'python / fastapi',
    failure_case_summary: failureCase.title,
    skill_decision: {
      matched_skill_id: 'skill-1',
      matched_skill_title: 'Negative total quote repair',
      action: 'reused',
      rationale: 'Matched skill guidance was sufficient without creating a new revision.',
    },
    replay_comparison: {
      failure_case_id: 'failure-1',
      original_failing_command: failureCase.failing_command,
      original_failure_type: failureCase.failure_type,
      original_failure_excerpt: failureCase.failing_output,
      reproduced_before_repair: true,
      reproduced_after_repair: false,
      latest_repro_excerpt: 'no negative total detected',
      validation_commands: [failureCase.failing_command, 'python -m pytest'],
    },
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.openRunEventStream.mockImplementation(() => ({
    onmessage: null,
    onerror: null,
    addEventListener: vi.fn(),
    close: vi.fn(),
  }));
});

describe('App', () => {
  it('creates a discover run from an uploaded zip and loads the V2 workspace panels', async () => {
    const user = userEvent.setup();

    apiMocks.fetchProviders.mockResolvedValue([provider]);
    apiMocks.fetchRuns.mockResolvedValue([]);
    apiMocks.fetchSkills.mockResolvedValue(skills);
    apiMocks.uploadCodebase.mockResolvedValue(codebase);
    apiMocks.createRun.mockResolvedValue(discoverSummary);
    apiMocks.fetchRun.mockResolvedValue(discoverDetail);
    apiMocks.fetchFailureCase.mockResolvedValue(failureCase);
    apiMocks.fetchCodebase.mockResolvedValue(codebase);

    const { container } = render(<App />);

    await screen.findByRole('button', { name: 'Upload and discover' });
    const fileInput = container.querySelector('input[type="file"]');
    expect(fileInput).not.toBeNull();
    const zipFile = new File(['zip-content'], 'billing-service.zip', { type: 'application/zip' });
    await user.upload(fileInput as HTMLInputElement, zipFile);
    await user.click(screen.getByRole('button', { name: 'Upload and discover' }));

    await waitFor(() => {
      expect(apiMocks.uploadCodebase).toHaveBeenCalledTimes(1);
      expect(apiMocks.createRun).toHaveBeenCalledWith({
        mode: 'discover',
        breakType: undefined,
        provider: 'openai',
        model: 'gpt-5',
        seed: 7,
        codebaseId: 'codebase-1',
      });
    });

    expect(await screen.findByText('Active discovery workflow')).toBeInTheDocument();
    expect(screen.getByText('Saved repro')).toBeInTheDocument();
    expect(screen.getByText('Execution context')).toBeInTheDocument();
    expect(screen.getByText('Learned repairs')).toBeInTheDocument();
    expect(screen.getAllByText('Negative total quote probe').length).toBeGreaterThan(0);
  });

  it('switches the right-side workspace when selecting a different run from the queue', async () => {
    const user = userEvent.setup();

    apiMocks.fetchProviders.mockResolvedValue([provider]);
    apiMocks.fetchRuns.mockResolvedValue([discoverSummary, replaySummary]);
    apiMocks.fetchSkills.mockResolvedValue(skills);
    apiMocks.fetchRun
      .mockResolvedValueOnce(discoverDetail)
      .mockResolvedValueOnce(replayDetail);
    apiMocks.fetchFailureCase.mockResolvedValue(failureCase);
    apiMocks.fetchCodebase.mockResolvedValue(codebase);

    render(<App />);

    expect(await screen.findByText('Active discovery workflow')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /replay/i }));

    await waitFor(() => {
      expect(apiMocks.fetchRun).toHaveBeenLastCalledWith('run-replay');
    });

    expect(await screen.findByText('Before vs after')).toBeInTheDocument();
    expect(screen.getByText('Matched skill')).toBeInTheDocument();
    expect(screen.getAllByText('Negative total quote repair').length).toBeGreaterThan(0);
  });
});
