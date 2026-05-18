import type { ReactNode } from "react";

export interface ShellNavItem {
  id: string;
  label: string;
  badge?: number | string;
  disabled?: boolean;
}

export interface ShellNavSection {
  title: string;
  items: ShellNavItem[];
}

export interface ShellWorkspace {
  id: string;
  label: string;
}

interface MissionControlShellProps {
  navSections: ShellNavSection[];
  workspaces: ShellWorkspace[];
  activeWorkspaceId: string;
  onSelectWorkspace: (workspaceId: string) => void;
  activeItemId: string;
  onNavigate: (itemId: string) => void;
  searchValue: string;
  onSearchChange: (value: string) => void;
  backstageUnlocked?: boolean;
  onUnlockBackstage?: () => void;
  workspaceTitle: string;
  workspaceSubtitle: string;
  headerSlot?: ReactNode;
  statusBadge: string;
  footerNote: string;
  mainContent: ReactNode;
  contextContent: ReactNode;
  surface?: "default" | "crm";
}

function navGlyph(item: ShellNavItem): string {
  const explicit: Record<string, string> = {
    dashboard: "TD",
    "hot-leads": "HL",
    "probate-autopilot": "SH",
    inbox: "RP",
    approvals: "OK",
    tasks: "TO",
    records: "RC",
    "property-cards": "PR",
    "owner-cards": "OW",
    skiptrace: "SK",
    "tax-title": "TT",
    pipeline: "DB",
    "deal-desk": "DD",
    agents: "AI",
    catalog: "CT",
    runs: "EV",
    settings: "ST",
    suppression: "BL",
  };
  if (explicit[item.id]) return explicit[item.id];
  return item.label
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "MC";
}

function flattenNavSections(navSections: ShellNavSection[]): ShellNavItem[] {
  return navSections.flatMap((section) => section.items);
}

export function MissionControlShell({
  navSections,
  workspaces,
  activeWorkspaceId,
  onSelectWorkspace,
  activeItemId,
  onNavigate,
  searchValue,
  onSearchChange,
  backstageUnlocked = false,
  onUnlockBackstage,
  workspaceTitle,
  workspaceSubtitle,
  headerSlot,
  statusBadge,
  footerNote,
  mainContent,
  contextContent,
  surface = "default",
}: MissionControlShellProps) {
  const flatNavItems = flattenNavSections(navSections);
  const activeWorkspace = workspaces.find((workspace) => workspace.id === activeWorkspaceId);
  const activeItem = flatNavItems.find((item) => item.id === activeItemId);
  const pendingApprovalBadge = flatNavItems.find((item) => item.id === "approvals")?.badge ?? 0;
  const primaryQueueBadge = flatNavItems.find((item) => item.id === "dashboard")?.badge ?? 0;

  return (
    <div className={`shell shell--operator${surface === "crm" ? " shell--crm" : ""}`}>
      <aside className="shell__rail" aria-label="Mission Control">
        <div className="brand-block">
          <span className="brand-block__mark" aria-hidden="true">A</span>
          <span className="brand-block__eyebrow">Ares</span>
          <h1 className="brand-block__title">Mission Control</h1>
          <p className="brand-block__copy">Lead desk, approvals, and deal flow only.</p>
        </div>

        <nav className="workspace-rail" role="tablist" aria-label="Real estate workspaces">
          {workspaces.map((workspace) => {
            const isActive = workspace.id === activeWorkspaceId;
            return (
              <button
                key={workspace.id}
                aria-current={isActive ? "page" : undefined}
                aria-selected={isActive}
                className={`workspace-rail__item${isActive ? " workspace-rail__item--active" : ""}`}
                onClick={() => onSelectWorkspace(workspace.id)}
                role="tab"
                type="button"
              >
                <span className="workspace-rail__glyph" aria-hidden="true">
                  {workspace.label.slice(0, 2).toUpperCase()}
                </span>
                <span>{workspace.label}</span>
              </button>
            );
          })}
        </nav>

        <nav className="nav-groups" aria-label="Operator queues">
          {navSections.map((section) => {
            const isBackstage = section.title === "Backstage";
            return (
              <section
                className={`nav-group${isBackstage ? " nav-group--backstage" : ""}${isBackstage && backstageUnlocked ? " nav-group--backstage-open" : ""}`}
                hidden={isBackstage && !backstageUnlocked}
                key={section.title}
              >
              <h2 className="nav-group__title">{section.title}</h2>
              <div className="nav-group__items">
                {section.items.map((item) => {
                  const isActive = item.id === activeItemId;
                  return (
                    <button
                      key={item.id}
                      aria-current={isActive ? "page" : undefined}
                      aria-label={item.id === "dashboard" ? `${item.label} Queue` : undefined}
                      className={`nav-item${isActive ? " nav-item--active" : ""}`}
                      disabled={item.disabled}
                      onClick={() => onNavigate(item.id)}
                      type="button"
                    >
                      <span className="nav-item__glyph" aria-hidden="true">{navGlyph(item)}</span>
                      <span className="nav-item__label">{item.label}</span>
                      {item.badge !== undefined ? <span className="nav-item__badge">{item.badge}</span> : null}
                    </button>
                  );
                })}
              </div>
              </section>
            );
          })}
        </nav>

        <div className="rail-footer" aria-label="Safety posture">
          <span className="rail-footer__label">Safety posture</span>
          <strong>No-send locked</strong>
          <span>Backstage diagnostics stay out of the operator desk.</span>
        </div>
      </aside>

      <div className="shell__workspace">
        <header className="workspace-header">
          <div className="topbar">
            <span className="status-badge status-badge--green">{statusBadge}</span>
            <span className="topbar__metric">Workspace: {activeWorkspace?.label ?? "Ares"}</span>
            <span className="topbar__metric">Queue: {primaryQueueBadge}</span>
            <span className="topbar__metric">Approvals: {pendingApprovalBadge}</span>
          </div>

          <div className="command-bar">
            <label className="search-field command-bar__search">
              <span className="search-field__label">Command / search</span>
              <input
                aria-label="Search Mission Control"
                className="search-field__input"
                type="search"
                placeholder="Find a lead, reply, approval, deal, or daily action"
                value={searchValue}
                onChange={(event) => {
                  const nextValue = event.target.value;
                  if (nextValue.trim().toLowerCase() === "backstage") {
                    onUnlockBackstage?.();
                    onSearchChange("");
                    return;
                  }
                  onSearchChange(nextValue);
                }}
              />
            </label>
            <div className="command-bar__active">
              <span>Current desk</span>
              <strong>{activeItem?.label ?? workspaceTitle}</strong>
            </div>
          </div>

          <div className="workspace-header__main">
            <div>
              <p className="workspace-header__eyebrow">Operator desk</p>
              <h2 className="workspace-header__title">{workspaceTitle}</h2>
              <p className="workspace-header__subtitle">{workspaceSubtitle}</p>
            </div>
            {headerSlot ? <div className="workspace-header__scope">{headerSlot}</div> : null}
          </div>
        </header>

        <div className="shell__content">
          <main className="workspace-main">{mainContent}</main>
          <aside className="workspace-context" aria-label="Manager brief">
            {contextContent}
            <p className="workspace-context__footer">{footerNote}</p>
          </aside>
        </div>
      </div>
    </div>
  );
}
