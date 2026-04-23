import { SecretHealthPanel } from "../components/SecretHealthPanel";
import type { GovernanceData } from "../lib/api";

interface SecretsPageProps {
  secretsHealth: GovernanceData["secretsHealth"];
}

export function SecretsPage({ secretsHealth }: SecretsPageProps) {
  return <SecretHealthPanel secretsHealth={secretsHealth} />;
}
