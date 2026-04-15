import { RunTimeline } from "../components/RunTimeline";
import type { RunSummary } from "../lib/api";

interface RunsPageProps {
  runs: RunSummary[];
}

export function RunsPage({ runs }: RunsPageProps) {
  return <RunTimeline runs={runs} />;
}
