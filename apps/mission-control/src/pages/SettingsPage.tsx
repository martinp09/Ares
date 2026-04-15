import { ConnectLaterPanel } from "../components/ConnectLaterPanel";
import type { AssetSummary } from "../lib/api";

interface SettingsPageProps {
  assets: AssetSummary[];
}

export function SettingsPage({ assets }: SettingsPageProps) {
  return <ConnectLaterPanel assets={assets} />;
}
