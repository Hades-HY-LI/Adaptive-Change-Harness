import type { CodebaseDetail } from '../../lib/types';

interface RepoProfilePanelProps {
  codebase?: CodebaseDetail | null;
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

export function RepoProfilePanel({ codebase }: RepoProfilePanelProps) {
  return (
    <article className="detail-card">
      <div className="section-heading">
        <p className="eyebrow">Repo Profile</p>
        <h3>Execution context</h3>
      </div>
      {!codebase ? (
        <p className="muted">No codebase profile loaded for this run.</p>
      ) : (
        <>
          <dl className="metadata-list">
            <div>
              <dt>Label</dt>
              <dd>{codebase.label}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>{codebase.source_type}</dd>
            </div>
            <div>
              <dt>Language</dt>
              <dd>{codebase.repo_profile.language}</dd>
            </div>
            <div>
              <dt>Framework</dt>
              <dd>{codebase.repo_profile.framework}</dd>
            </div>
            <div>
              <dt>Package manager</dt>
              <dd>{codebase.repo_profile.package_manager || 'unknown'}</dd>
            </div>
            <div>
              <dt>Install</dt>
              <dd>{codebase.repo_profile.install_command || 'unknown'}</dd>
            </div>
            <div>
              <dt>Tests</dt>
              <dd>{codebase.repo_profile.test_command || 'unknown'}</dd>
            </div>
            <div>
              <dt>Workspace</dt>
              <dd className="path-value">{codebase.repo_profile.workspace_path}</dd>
            </div>
          </dl>
          <SignalList title="Source directories" items={codebase.repo_profile.source_dirs} />
          <SignalList title="Test directories" items={codebase.repo_profile.test_dirs} />
          <SignalList title="Entrypoints" items={codebase.repo_profile.entrypoints} />
          <SignalList title="Risk areas" items={codebase.repo_profile.risk_areas} />
        </>
      )}
    </article>
  );
}
