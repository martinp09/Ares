import { UsagePanel } from "../components/UsagePanel";
import type { GovernanceData } from "../lib/api";

interface UsagePageProps {
  usageSummary: GovernanceData["usageSummary"];
  recentUsage: GovernanceData["recentUsage"];
}

export function UsagePage({ usageSummary, recentUsage }: UsagePageProps) {
  return <UsagePanel usageSummary={usageSummary} recentUsage={recentUsage} />;
}
