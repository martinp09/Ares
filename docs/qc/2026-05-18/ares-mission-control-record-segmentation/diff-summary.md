diff --git a/CONTEXT.md b/CONTEXT.md
index 932995b..38fee47 100644
--- a/CONTEXT.md
+++ b/CONTEXT.md
@@ -18,13 +18,14 @@
 - Supabase migration file `20260518130327_chief_of_staff_slack_route.sql` is added but not remotely applied in this slice.

 ## Current TODO
-1. Review and merge `feature/ares-chief-of-staff-v0` after final dashboard analytics polish is accepted.
+1. Review and merge `feature/ares-chief-of-staff-v0` after the Mission Control record segmentation slice is accepted.
 2. After merge/deploy, apply the new Slack route migration and configure/create/invite the `#ares-chief-of-staff` Slack channel.
 3. Run `uv run python scripts/slack_notification_readiness.py --json --render-sample --route chief_of_staff_digest` before any live Chief of Staff Slack post.
 4. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.
 5. Later: wire live Chief of Staff queue data into Mission Control analytics once the Slack/artifact report is proven useful.

 ## Recent Change
+- 2026-05-18: Expanded Mission Control record/navigation segmentation after browser QA: richer real-estate left rail, `Operator scope` replacement for `Organization scope`, visible Records / Property Cards / Owner Cards / Skip Trace / Tax-Title pages, and property-owner detail cards. Verification: Mission Control typecheck passed, `25` test files / `85` tests passed, Vite build passed, browser-harness click sweep covered `15` nav clicks with `0` failed clicks, browser smoke had `0` console/JS errors, and `git diff --check` passed. QC: `docs/qc/2026-05-18/ares-mission-control-record-segmentation/`.
 - 2026-05-18: Refreshed Mission Control overview into a segmented analytics dashboard inspired by `builderz-labs/marketing-dashboard`: KPI strip, graph-style lane performance, contact-mix donut, acquisition funnel, blocker chart, and segmented operating cards. Verification: Mission Control typecheck passed, `25` test files / `83` tests passed, Vite build passed, browser smoke had zero console/JS errors, and backstage/admin words were hidden from the visible overview. QC: `docs/qc/2026-05-18/ares-dashboard-analytics-segmentation/`.
 - 2026-05-18: Added Chief of Staff v2 manager-action packet. Verification: focused/regression tests `52 passed`, full backend `1144 passed`, configured artifact-root/source-run-state dry-run side-effect check `dry_run_artifacts_created=0` and `dry_run_source_state_created=0`, and `git diff --check` passed. QC: `docs/qc/2026-05-18/ares-chief-of-staff-v2-manager-actions/`.

diff --git a/TODO.md b/TODO.md
index 42cb956..8a92140 100644
--- a/TODO.md
+++ b/TODO.md
@@ -1,7 +1,7 @@
 ---
 title: "Ares TODO / Handoff"
 status: active
-updated_at: "2026-05-18T16:05:52Z"
+updated_at: "2026-05-18T16:43:35Z"
 repo: "martinp09/Ares"
 local_checkout: "/opt/ares/worktrees/ares-chief-of-staff-v0"
 target_branch: "feature/ares-chief-of-staff-v0"
@@ -20,7 +20,7 @@ supabase_identity_adapter_commit: "6cd2d88"

 Ares Chief of Staff v2 is implemented on `feature/ares-chief-of-staff-v0` for review/merge. It is a read-only lead desk employee report: current Ares leads are bucketed into hot/contact-ready/research/skiptrace/blocked queues, artifacts are written as Markdown/JSON/CSV, Slack delivery uses the dedicated opt-in route `chief_of_staff_digest` / `SLACK_CHANNEL_CHIEF_OF_STAFF`, and the report includes employee identity, worklog, priorities, blockers, approval requests, read-only lead-machine health/latest-brief context, and stable manager action items with `approve/deny cos_action_...` Slack reply commands. Slack text/blocks/payload omit lead names, contact details, property addresses, case numbers, raw lead IDs, and lead-machine operator action reasons; exact record details remain in local artifacts. Safety boundaries remain hard: no seller outreach, paid skiptrace, Instantly enrollment, HubSpot/provider writes, SMS/email/Vapi sends, live county/source pulls, manager approval execution, Slack live post, Supabase remote migration, VPS deploy, or Telegram delivery occurred in this slice. Verification: focused/regression tests `52 passed`, full backend `1144 passed`, configured artifact-root/source-run-state dry-run side-effect check `dry_run_artifacts_created=0` and `dry_run_source_state_created=0`, `git diff --check` passed. QC: `docs/qc/2026-05-18/ares-chief-of-staff-v2-manager-actions/`.

-Mission Control operator UI refresh is also implemented on the same branch. The visible dashboard is now a real-estate operator cockpit inspired by the external Mission Control visual direction and the `builderz-labs/marketing-dashboard` analytics layout: the default overview uses a segmented KPI strip, graph-style lane performance panel, contact-mix donut, acquisition funnel, blocker chart, and segment cards for acquisition lanes/follow-up/deal movement. Backend/admin surfaces are hidden from the primary desk behind the deliberate command/search unlock `backstage`; provider operations no longer render on the primary dashboard. Verification: Mission Control typecheck passed, `25` test files / `83` tests passed, Vite build passed. QC: `docs/qc/2026-05-18/ares-mission-control-operator-ui-refresh/` and `docs/qc/2026-05-18/ares-dashboard-analytics-segmentation/`.
+Mission Control operator UI refresh is also implemented on the same branch. The visible dashboard is now a real-estate operator cockpit inspired by the external Mission Control visual direction and the `builderz-labs/marketing-dashboard` analytics layout: the default overview uses a segmented KPI strip, graph-style lane performance panel, contact-mix donut, acquisition funnel, blocker chart, and segment cards for acquisition lanes/follow-up/deal movement. Backend/admin surfaces are hidden from the primary desk behind the deliberate command/search unlock `backstage`; provider operations no longer render on the primary dashboard. The latest record-navigation continuation adds a richer real-estate left rail, replaces `Organization scope` with `Operator scope` / lane filters, and exposes Records / Property Cards / Owner Cards / Skip Trace / Tax-Title pages with selected-record property-owner detail cards. Verification: Mission Control typecheck passed, `25` test files / `85` tests passed, Vite build passed, browser-harness click sweep covered `15` nav clicks with `0` failed clicks, browser smoke had `0` console/JS errors, and `git diff --check` passed. QC: `docs/qc/2026-05-18/ares-mission-control-operator-ui-refresh/`, `docs/qc/2026-05-18/ares-dashboard-analytics-segmentation/`, and `docs/qc/2026-05-18/ares-mission-control-record-segmentation/`.

 Back Office Spine v0 landed on `main` at `e898ee0` and the local `feature/back-office-spine-v0` branch was deleted. This slice turns qualified leads into canonical deal records with lane-aware task/document/risk templates, stage transition blockers, fire-list read models, Supabase runtime persistence, and a read-only Mission Control Deal Desk page.

diff --git a/apps/mission-control/src/App.test.tsx b/apps/mission-control/src/App.test.tsx
index f5703c8..d9c3931 100644
--- a/apps/mission-control/src/App.test.tsx
+++ b/apps/mission-control/src/App.test.tsx
@@ -1950,9 +1950,17 @@ describe("App", () => {
     await openAgentsBackstage();

     expect(await screen.findByRole("tab", { name: "Lead Machine" })).toBeInTheDocument();
+    expect(screen.getByText("Operator scope")).toBeInTheDocument();
+    expect(screen.queryByText("Organization scope")).not.toBeInTheDocument();
     expect(screen.getByRole("button", { name: /agents/i })).toBeInTheDocument();
     expect(screen.getByRole("heading", { name: /lead machine \/ agents/i, level: 2 })).toBeInTheDocument();
     expect(screen.getByRole("button", { name: /queue/i })).toBeInTheDocument();
+    expect(screen.getByRole("button", { name: /hot leads/i })).toBeInTheDocument();
+    expect(screen.getByRole("button", { name: /records/i })).toBeInTheDocument();
+    expect(screen.getByRole("button", { name: /property cards/i })).toBeInTheDocument();
+    expect(screen.getByRole("button", { name: /owner cards/i })).toBeInTheDocument();
+    expect(screen.getByRole("button", { name: /skip trace/i })).toBeInTheDocument();
+    expect(screen.getByRole("button", { name: /tax \/ title/i })).toBeInTheDocument();
     expect(screen.getByRole("button", { name: /approvals/i })).toBeInTheDocument();
     expect(screen.getByRole("button", { name: /campaign state/i })).toBeInTheDocument();

diff --git a/apps/mission-control/src/App.tsx b/apps/mission-control/src/App.tsx
index 31309ae..a9fe7a5 100644
--- a/apps/mission-control/src/App.tsx
+++ b/apps/mission-control/src/App.tsx
@@ -39,7 +39,7 @@ import { DealDeskPage } from "./pages/DealDeskPage";
 import { InboxPage } from "./pages/InboxPage";
 import { PipelinePage } from "./pages/PipelinePage";
 import { ProbateAutopilotPage } from "./pages/ProbateAutopilotPage";
-import { RecordsPage } from "./pages/RecordsPage";
+import { RecordsPage, countRecordsForMode, type RecordsPageMode } from "./pages/RecordsPage";
 import { RunsPage } from "./pages/RunsPage";
 import { SettingsPage } from "./pages/SettingsPage";
 import { SuppressionPage } from "./pages/SuppressionPage";
@@ -143,9 +143,29 @@ function collectScopeOptionValues(snapshot: MissionControlSnapshot): { businessI
   };
 }

-function toFilterOptions(values: string[], emptyLabel: string, selectedValue: string | null): ScopeFilterOption[] {
+function titleCaseScopeValue(value: string): string {
+  if (/^\d+$/.test(value)) {
+    return `Business ${value}`;
+  }
+  return value;
+}
+
+function toFilterOptions(
+  values: string[],
+  emptyLabel: string,
+  selectedValue: string | null,
+  formatValue: (value: string) => string = titleCaseScopeValue,
+): ScopeFilterOption[] {
   const normalizedValues = selectedValue && !values.includes(selectedValue) ? [...values, selectedValue] : values;
-  return [{ value: "", label: emptyLabel }, ...normalizedValues.map((value) => ({ value, label: value }))];
+  return [{ value: "", label: emptyLabel }, ...normalizedValues.map((value) => ({ value, label: formatValue(value) }))];
+}
+
+function formatOrganizationLabel(organization: OrganizationSummary): string {
+  const normalizedName = organization.name.trim().toLowerCase();
+  if (organization.isInternal || organization.id === "org_internal" || normalizedName === "internal" || normalizedName === "org_internal") {
+    return "Ares Ops";
+  }
+  return organization.name;
 }

 function matchesSecondaryScope(
@@ -840,11 +860,11 @@ export default function App() {

   const normalizedSearchValue = searchValue.trim().toLowerCase();
   const businessFilterOptions = useMemo(
-    () => toFilterOptions(scopeOptionValues.businessIds, "All businesses", selectedBusinessId),
+    () => toFilterOptions(scopeOptionValues.businessIds, "All deal lanes", selectedBusinessId),
     [scopeOptionValues.businessIds, selectedBusinessId],
   );
   const environmentFilterOptions = useMemo(
-    () => toFilterOptions(scopeOptionValues.environments, "All environments", selectedEnvironment),
+    () => toFilterOptions(scopeOptionValues.environments, "All runtimes", selectedEnvironment),
     [scopeOptionValues.environments, selectedEnvironment],
   );
   const organizationOptions = useMemo(() => {
@@ -1303,6 +1323,30 @@ export default function App() {
     },
   ];

+  const renderRecordsPage = (mode: RecordsPageMode): JSX.Element => (
+    <RecordsPage
+      data={snapshot.records}
+      mode={mode}
+      actionState={recordActionState}
+      onRecordStatusChange={handleRecordStatusChange}
+      onRecordSuppress={handleRecordSuppress}
+      onRecordPromote={handleRecordPromote}
+    />
+  );
+
+  const recordInventory = snapshot.records.records;
+  const hotRecordCount = countRecordsForMode(recordInventory, "hot");
+  const propertyRecordCount = countRecordsForMode(recordInventory, "property");
+  const ownerRecordCount = countRecordsForMode(recordInventory, "owner");
+  const skiptraceRecordCount = countRecordsForMode(recordInventory, "skiptrace");
+  const taxTitleRecordCount = countRecordsForMode(recordInventory, "tax-title");
+
+  const recordContextItems = [
+    `${snapshot.records.kpis.totalCount} owner/property records in the current scope`,
+    `${snapshot.records.kpis.needsSkipTraceCount} records need phone enrichment before seller contact`,
+    `${snapshot.records.kpis.promotedCount} records are already linked to downstream opportunities`,
+  ];
+
   const workspaceDefinitions: Record<WorkspaceId, WorkspaceDefinition> = {
     "lead-machine": {
       label: "Lead Machine",
@@ -1316,16 +1360,31 @@ export default function App() {
               label: "Today Desk",
               badge: snapshot.dashboard.outboundProbateSummary?.readyLeadCount ?? snapshot.dashboard.pendingLeadCount ?? 0,
             },
+            {
+              id: "hot-leads",
+              label: "Hot Leads",
+              badge: hotRecordCount,
+            },
             { id: "inbox", label: "Replies", badge: snapshot.dashboard.unreadConversationCount },
-            { id: "approvals", label: "Approvals", badge: filteredApprovals.length },
             {
               id: "tasks",
               label: "To-Do",
               badge: snapshot.dashboard.outboundProbateSummary?.openTaskCount ?? snapshot.dashboard.dueManualCallCount ?? 0,
             },
+            { id: "approvals", label: "Approvals", badge: filteredApprovals.length },
             { id: "suppression", label: "Blocked / Dead", badge: snapshot.dashboard.repliesNeedingReviewCount ?? 0 },
           ],
         },
+        {
+          title: "Records",
+          items: [
+            { id: "records", label: "Records", badge: snapshot.records.kpis.totalCount },
+            { id: "property-cards", label: "Property Cards", badge: propertyRecordCount },
+            { id: "owner-cards", label: "Owner Cards", badge: ownerRecordCount },
+            { id: "skiptrace", label: "Skip Trace", badge: skiptraceRecordCount },
+            { id: "tax-title", label: "Tax / Title", badge: taxTitleRecordCount },
+          ],
+        },
         {
           title: "Reference",
           items: [
@@ -1410,6 +1469,42 @@ export default function App() {
             />
           ),
         },
+        "hot-leads": {
+          title: "Lead Machine / Hot Leads",
+          subtitle: "Contact-ready records and promoted owners that deserve Martin's attention before cold inventory.",
+          mainContent: renderRecordsPage("hot"),
+          contextContent: <ContextPanel eyebrow="Hot records" title="Prioritize contact-ready owners" items={recordContextItems} />,
+        },
+        records: {
+          title: "Lead Machine / Records",
+          subtitle: "Owner and property inventory before records graduate into opportunities.",
+          mainContent: renderRecordsPage("inventory"),
+          contextContent: <ContextPanel eyebrow="Record inventory" title="Property/owner card layer" items={recordContextItems} />,
+        },
+        "property-cards": {
+          title: "Lead Machine / Property Cards",
+          subtitle: "Property-first cards with address, owner, contact, source, pipeline, and missing research details.",
+          mainContent: renderRecordsPage("property"),
+          contextContent: <ContextPanel eyebrow="Property cards" title="Inspect the asset before contact" items={recordContextItems} />,
+        },
+        "owner-cards": {
+          title: "Lead Machine / Owner Cards",
+          subtitle: "Owner-first cards with contact readiness, assignment, quality, and action gates.",
+          mainContent: renderRecordsPage("owner"),
+          contextContent: <ContextPanel eyebrow="Owner cards" title="Know who Martin should contact" items={recordContextItems} />,
+        },
+        skiptrace: {
+          title: "Lead Machine / Skip Trace",
+          subtitle: "Records missing phone coverage or marked for enrichment before seller contact.",
+          mainContent: renderRecordsPage("skiptrace"),
+          contextContent: <ContextPanel eyebrow="Enrichment queue" title="Missing phone coverage blocks calls" items={recordContextItems} />,
+        },
+        "tax-title": {
+          title: "Lead Machine / Tax / Title",
+          subtitle: "Tax, probate, title, and curative-title review cards before outreach or deal advancement.",
+          mainContent: renderRecordsPage("tax-title"),
+          contextContent: <ContextPanel eyebrow="Curative/title lane" title="Title friction stays visible" items={recordContextItems} />,
+        },
         "probate-autopilot": {
           title: "Lead Machine / Probate Autopilot",
           subtitle: "Read-only Harris + Montgomery source-run SLA, anomaly, freshness, and enrichment backlog control panel.",
@@ -1704,9 +1799,13 @@ export default function App() {
             },
             {
               id: "records",
-              label: "Lead Records",
+              label: "Records",
               badge: snapshot.records.kpis.totalCount,
             },
+            { id: "property-cards", label: "Property Cards", badge: propertyRecordCount },
+            { id: "owner-cards", label: "Owner Cards", badge: ownerRecordCount },
+            { id: "tax-title", label: "Title / Curative", badge: taxTitleRecordCount },
+            { id: "skiptrace", label: "Skip Trace", badge: skiptraceRecordCount },
           ],
         },
         {
@@ -1729,25 +1828,32 @@ export default function App() {
         records: {
           title: "Records",
           subtitle: "High-volume owner and prospect inventory before records are promoted into opportunities.",
-          mainContent: (
-            <RecordsPage
-              data={snapshot.records}
-              actionState={recordActionState}
-              onRecordStatusChange={handleRecordStatusChange}
-              onRecordSuppress={handleRecordSuppress}
-              onRecordPromote={handleRecordPromote}
-            />
-          ),
-          contextContent: (
-            <ContextPanel
-              eyebrow="Inventory layer"
-              title="Records feed opportunities"
-              items={[
-                `${snapshot.records.kpis.needsSkipTraceCount} records need phone enrichment before outreach`,
-                `${snapshot.records.kpis.promotedCount} records are linked to downstream opportunities`,
-              ]}
-            />
-          ),
+          mainContent: renderRecordsPage("inventory"),
+          contextContent: <ContextPanel eyebrow="Inventory layer" title="Records feed opportunities" items={recordContextItems} />,
+        },
+        "property-cards": {
+          title: "Property Cards",
+          subtitle: "Property-first detail cards for asset research, title friction, owner context, and missing data.",
+          mainContent: renderRecordsPage("property"),
+          contextContent: <ContextPanel eyebrow="Property detail" title="Asset-level review" items={recordContextItems} />,
+        },
+        "owner-cards": {
+          title: "Owner Cards",
+          subtitle: "Owner-first detail cards for contact readiness, assignments, source identity, and next action.",
+          mainContent: renderRecordsPage("owner"),
+          contextContent: <ContextPanel eyebrow="Owner detail" title="Human contact readiness" items={recordContextItems} />,
+        },
+        "tax-title": {
+          title: "Title / Curative",
+          subtitle: "Tax, probate, title, and curative-title records before a deal advances.",
+          mainContent: renderRecordsPage("tax-title"),
+          contextContent: <ContextPanel eyebrow="Title desk" title="Curative blockers stay visible" items={recordContextItems} />,
+        },
+        skiptrace: {
+          title: "Skip Trace",
+          subtitle: "Records missing phone coverage or marked for enrichment before seller contact.",
+          mainContent: renderRecordsPage("skiptrace"),
+          contextContent: <ContextPanel eyebrow="Enrichment" title="No phone, no call" items={recordContextItems} />,
         },
         pipeline: {
           title: "Pipeline Board",
@@ -1833,7 +1939,7 @@ export default function App() {
     <OrgSwitcher
       orgs={organizationOptions.map((organization) => ({
         id: organization.id,
-        label: organization.name,
+        label: formatOrganizationLabel(organization),
       }))}
       activeOrgId={selectedOrgId ?? organizationOptions[0]?.id ?? ""}
       onSelectOrg={(orgId) => {
diff --git a/apps/mission-control/src/components/MissionControlShell.tsx b/apps/mission-control/src/components/MissionControlShell.tsx
index fdf79ab..e873308 100644
--- a/apps/mission-control/src/components/MissionControlShell.tsx
+++ b/apps/mission-control/src/components/MissionControlShell.tsx
@@ -41,11 +41,16 @@ interface MissionControlShellProps {
 function navGlyph(item: ShellNavItem): string {
   const explicit: Record<string, string> = {
     dashboard: "TD",
+    "hot-leads": "HL",
     "probate-autopilot": "SH",
     inbox: "RP",
     approvals: "OK",
     tasks: "TO",
-    records: "RE",
