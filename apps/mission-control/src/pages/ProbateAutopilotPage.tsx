import { ProbateAutopilotHealthPanel } from "../components/ProbateAutopilotHealthPanel";
import type { MissionControlDataSource, ProbateAutopilotHealthData } from "../lib/api";

export interface ProbateAutopilotPageProps {
  data: ProbateAutopilotHealthData;
  dataSource: MissionControlDataSource;
}

export function ProbateAutopilotPage({ data, dataSource }: ProbateAutopilotPageProps) {
  return (
    <div className="page-stack">
      <ProbateAutopilotHealthPanel data={data} dataSource={dataSource} />
    </div>
  );
}
