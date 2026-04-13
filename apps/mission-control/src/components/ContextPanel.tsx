import type { ReactNode } from "react";

interface ContextPanelProps {
  title: string;
  eyebrow?: string;
  items?: string[];
  children?: ReactNode;
}

export function ContextPanel({ title, eyebrow, items = [], children }: ContextPanelProps) {
  return (
    <section className="panel-stack context-panel">
      {eyebrow ? <p className="workspace-header__eyebrow">{eyebrow}</p> : null}
      <h3>{title}</h3>
      {items.length > 0 ? (
        <ul className="detail-list">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
      {children}
    </section>
  );
}
