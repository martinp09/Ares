import { AuditTimeline } from "../components/AuditTimeline";
import type { GovernanceData } from "../lib/api";

interface AuditPageProps {
  events: GovernanceData["recentAudit"];
}

export function AuditPage({ events }: AuditPageProps) {
  return <AuditTimeline events={events} />;
}
