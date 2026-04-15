import { AgentRegistryTable } from "../components/AgentRegistryTable";
import type { AgentSummary } from "../lib/api";

interface AgentsPageProps {
  agents: AgentSummary[];
}

export function AgentsPage({ agents }: AgentsPageProps) {
  return <AgentRegistryTable agents={agents} />;
}
