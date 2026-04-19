import type { RepairSkill } from '../../lib/types';

interface SkillLibraryPanelProps {
  skills: RepairSkill[];
}

export function SkillLibraryPanel({ skills }: SkillLibraryPanelProps) {
  return (
    <section className="panel skill-library-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Skill Assets</p>
          <h2>Learned repairs</h2>
        </div>
        <span className="badge">{skills.length} tracked</span>
      </div>
      {skills.length === 0 ? (
        <div className="empty-state">
          <strong>No validated skills yet.</strong>
          <p>Successful saved-failure repairs will create reusable repair assets here.</p>
        </div>
      ) : (
        <div className="skill-list">
          {skills.map((skill) => (
            <article className="skill-row" key={skill.id}>
              <div>
                <strong>{skill.title}</strong>
                <p>{skill.bug_family.replace(/_/g, ' ')}</p>
              </div>
              <div className="skill-metrics">
                <span>v{skill.version}</span>
                <span>{skill.success_count ?? 0}/{skill.usage_count ?? 0} success</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
