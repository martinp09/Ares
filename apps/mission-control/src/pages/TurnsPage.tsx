import { TurnTimeline } from "../components/TurnTimeline";
import type { TurnSummary } from "../lib/api";

interface TurnsPageProps {
  turns: TurnSummary[];
}

export function TurnsPage({ turns }: TurnsPageProps) {
  return <TurnTimeline turns={turns} />;
}
