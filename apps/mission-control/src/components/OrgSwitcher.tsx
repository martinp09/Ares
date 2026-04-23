interface OrgOption {
  id: string;
  label: string;
}

interface FilterOption {
  id: string;
  label: string;
}

interface OrgSwitcherProps {
  orgs: OrgOption[];
  activeOrgId: string;
  onSelectOrg: (orgId: string) => void;
  businessOptions: FilterOption[];
  activeBusinessId: string;
  onSelectBusiness: (businessId: string) => void;
  environmentOptions: FilterOption[];
  activeEnvironment: string;
  onSelectEnvironment: (environment: string) => void;
}

function renderFilterGroup(
  label: string,
  ariaLabel: string,
  options: FilterOption[],
  activeValue: string,
  onSelect: (value: string) => void,
) {
  return (
    <div>
      <span className="status-badge">{label}</span>
      <div className="workspace-switcher" role="group" aria-label={ariaLabel}>
        {options.map((option) => {
          const isActive = option.id === activeValue;
          return (
            <button
              key={option.id}
              aria-pressed={isActive}
              className={`workspace-switcher__item${isActive ? " workspace-switcher__item--active" : ""}`}
              onClick={() => onSelect(option.id)}
              type="button"
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function OrgSwitcher({
  orgs,
  activeOrgId,
  onSelectOrg,
  businessOptions,
  activeBusinessId,
  onSelectBusiness,
  environmentOptions,
  activeEnvironment,
  onSelectEnvironment,
}: OrgSwitcherProps) {
  return (
    <section aria-label="Organization and filters">
      <p className="workspace-header__eyebrow">Organization scope</p>
      <div className="workspace-switcher" role="tablist" aria-label="Organization switcher">
        {orgs.map((org) => {
          const isActive = org.id === activeOrgId;
          return (
            <button
              key={org.id}
              aria-selected={isActive}
              className={`workspace-switcher__item${isActive ? " workspace-switcher__item--active" : ""}`}
              onClick={() => onSelectOrg(org.id)}
              role="tab"
              type="button"
            >
              {org.label}
            </button>
          );
        })}
      </div>

      {renderFilterGroup("Business filter", "Business filter", businessOptions, activeBusinessId, onSelectBusiness)}
      {renderFilterGroup(
        "Environment filter",
        "Environment filter",
        environmentOptions,
        activeEnvironment,
        onSelectEnvironment,
      )}
    </section>
  );
}
