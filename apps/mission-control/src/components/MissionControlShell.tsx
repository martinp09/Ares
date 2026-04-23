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
  workspaceTitle: string;
  workspaceSubtitle: string;
  headerSlot?: ReactNode;
  statusBadge: string;
  footerNote: string;
  mainContent: ReactNode;
  contextContent: ReactNode;
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
  workspaceTitle,
  workspaceSubtitle,
  headerSlot,
  statusBadge,
  footerNote,
  mainContent,
  contextContent,
}: MissionControlShellProps) {
  return (
    <div className="shell">
      <aside className="shell__rail" aria-label="Mission Control">
        <div className="brand-block">
          <span className="brand-block__eyebrow">Ares</span>
          <h1 className="brand-block__title">Mission Control</h1>
          <p className="brand-block__copy">Agents are the product unit.</p>
        </div>

        <label className="search-field">
          <span className="search-field__label">Search Mission Control</span>
          <input
            aria-label="Search Mission Control"
            className="search-field__input"
            type="search"
            placeholder="Jump to a lead, run, or agent"
            value={searchValue}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </label>

        <nav className="nav-groups">
          {navSections.map((section) => (
            <section className="nav-group" key={section.title}>
              <h2 className="nav-group__title">{section.title}</h2>
              <div className="nav-group__items">
                {section.items.map((item) => {
                  const isActive = item.id === activeItemId;
                  return (
                    <button
                      key={item.id}
                      className={`nav-item${isActive ? " nav-item--active" : ""}`}
                      disabled={item.disabled}
                      onClick={() => onNavigate(item.id)}
                      type="button"
                    >
                      <span>{item.label}</span>
                      {item.badge !== undefined ? <span className="nav-item__badge">{item.badge}</span> : null}
                    </button>
                  );
                })}
              </div>
            </section>
          ))}
        </nav>
      </aside>

      <div className="shell__workspace">
        <header className="workspace-header">
          <div>
            <p className="workspace-header__eyebrow">Active workspace</p>
            <div className="workspace-switcher" role="tablist" aria-label="Workspace switcher">
              {workspaces.map((workspace) => {
                const isActive = workspace.id === activeWorkspaceId;
                return (
                  <button
                    key={workspace.id}
                    aria-selected={isActive}
                    className={`workspace-switcher__item${isActive ? " workspace-switcher__item--active" : ""}`}
                    onClick={() => onSelectWorkspace(workspace.id)}
                    role="tab"
                    type="button"
                  >
                    {workspace.label}
                  </button>
                );
              })}
            </div>
            {headerSlot}
            <h2 className="workspace-header__title">{workspaceTitle}</h2>
            <p className="workspace-header__subtitle">{workspaceSubtitle}</p>
          </div>
          <span className="status-badge">{statusBadge}</span>
        </header>

        <div className="shell__content">
          <main className="workspace-main">{mainContent}</main>
          <aside className="workspace-context">
            {contextContent}
            <p className="workspace-context__footer">{footerNote}</p>
          </aside>
        </div>
      </div>
    </div>
  );
}
