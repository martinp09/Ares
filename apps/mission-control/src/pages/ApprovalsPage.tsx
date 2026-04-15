import { ApprovalQueue } from "../components/ApprovalQueue";
import type { ApprovalItem } from "../lib/api";

interface ApprovalsPageProps {
  approvals: ApprovalItem[];
}

export function ApprovalsPage({ approvals }: ApprovalsPageProps) {
  return <ApprovalQueue approvals={approvals} />;
}
