// Mock data for the DevSecOps dashboard
export type PipelineStatus = "running" | "failed" | "healed" | "promoted" | "pending";
export type AgentStatus = "spawned" | "running" | "complete" | "failed";
export type AgentType =
  | "orchestrator" | "coordinator" | "memory" | "monitor"
  | "log_analyzer" | "dependency_inspector" | "web_search"
  | "config_analyzer" | "code_analyzer"
  | "repair_docker" | "repair_yaml" | "repair_imports";

export interface Pipeline {
  id: string;
  repo: string;
  branch: string;
  commit: string;
  status: PipelineStatus;
  iteration: number;
  startedAt: string;
  message: string;
}

export interface AgentNodeData {
  id: string;
  type: AgentType;
  label: string;
  status: AgentStatus;
  detail: string;
}

export interface LogLine {
  ts: string;
  level: "info" | "warn" | "error" | "success" | "debug";
  agent: string;
  msg: string;
}

export interface MemoryHit {
  signature: string;
  similarity: number;
  fix: string;
  successRate: number;
  timesSeen: number;
}

export interface TimelineEvent {
  iter: number;
  title: string;
  status: "ok" | "fail" | "running";
  detail: string;
  duration: string;
}

export interface PipelineDetail {
  nodes: AgentNodeData[];
  edges: { source: string; target: string; animated?: boolean }[];
  logs: LogLine[];
  memory: MemoryHit[];
  timeline: TimelineEvent[];
  problems: { level: "error" | "warn"; agent: string; msg: string }[];
}

export const pipelines: Pipeline[] = [
  { id: "p_8a1f", repo: "acme/checkout-api", branch: "fix/repair-9c2", commit: "9c2f1ad",
    status: "running", iteration: 3, startedAt: "2m ago",
    message: "ModuleNotFoundError: stripe_sdk_v4" },
  { id: "p_71bd", repo: "acme/checkout-api", branch: "main", commit: "ab51e09",
    status: "promoted", iteration: 2, startedAt: "1h ago",
    message: "Yarn lockfile drift — auto-healed" },
  { id: "p_44e2", repo: "acme/auth-svc", branch: "feat/oauth", commit: "7712b3c",
    status: "healed", iteration: 4, startedAt: "3h ago",
    message: "Dockerfile base image EOL" },
  { id: "p_22c0", repo: "acme/billing", branch: "main", commit: "44a09de",
    status: "failed", iteration: 5, startedAt: "5h ago",
    message: "Migration deadlock — escalated" },
  { id: "p_19af", repo: "acme/web", branch: "main", commit: "0fe11b8",
    status: "pending", iteration: 0, startedAt: "just now",
    message: "Webhook received" },
];

const baseEdges: PipelineDetail["edges"] = [
  { source: "orch", target: "log", animated: true },
  { source: "orch", target: "dep", animated: true },
  { source: "orch", target: "mem", animated: true },
  { source: "orch", target: "cfg", animated: true },
  { source: "mem", target: "web", animated: true },
  { source: "log", target: "coord" },
  { source: "dep", target: "coord" },
  { source: "web", target: "coord" },
  { source: "cfg", target: "coord", animated: true },
  { source: "coord", target: "rep_imp", animated: true },
  { source: "coord", target: "rep_yml", animated: true },
];

export const pipelineDetails: Record<string, PipelineDetail> = {
  // === checkout-api iter 3 (running) ===
  p_8a1f: {
    nodes: [
      { id: "orch", type: "orchestrator", label: "Orchestrator", status: "running", detail: "Spawning workers · iter 3" },
      { id: "coord", type: "coordinator", label: "Coordinator", status: "running", detail: "Aggregating 4 reports" },
      { id: "mem", type: "memory", label: "Memory Agent", status: "complete", detail: "0.74 similarity hit" },
      { id: "log", type: "log_analyzer", label: "Log Analyzer", status: "complete", detail: "Parsed 2,481 lines" },
      { id: "dep", type: "dependency_inspector", label: "Dependency Inspector", status: "complete", detail: "stripe_sdk_v4 missing" },
      { id: "web", type: "web_search", label: "Web Search", status: "complete", detail: "GitHub issue #4421" },
      { id: "cfg", type: "config_analyzer", label: "Config Analyzer", status: "running", detail: "Scanning yarn.lock" },
      { id: "rep_imp", type: "repair_imports", label: "Repair · Imports", status: "spawned", detail: "Awaiting plan" },
      { id: "rep_yml", type: "repair_yaml", label: "Repair · YAML", status: "spawned", detail: "Awaiting plan" },
    ],
    edges: baseEdges,
    logs: [
      { ts: "14:02:11", level: "info",    agent: "webhook",      msg: "POST /webhook/github · push acme/checkout-api@9c2f1ad" },
      { ts: "14:02:11", level: "info",    agent: "orchestrator", msg: "Pipeline p_8a1f created · iter=1" },
      { ts: "14:02:14", level: "error",   agent: "shadow.build", msg: "ModuleNotFoundError: No module named 'stripe_sdk_v4'" },
      { ts: "14:02:15", level: "info",    agent: "memory",       msg: "Querying pgvector · k=8 · sig=ModuleNotFoundError:stripe_sdk_v4" },
      { ts: "14:02:18", level: "info",    agent: "web_search",   msg: "Serper API · 12 results · ranking by signal" },
      { ts: "14:02:21", level: "success", agent: "web_search",   msg: "Match: github.com/stripe/stripe-python/issues/4421" },
      { ts: "14:02:24", level: "info",    agent: "orchestrator", msg: "Spawning repair agents: repair_imports, repair_yaml" },
      { ts: "14:02:41", level: "warn",    agent: "shadow.test",  msg: "pytest: 3 failures in tests/integration/test_charges.py" },
      { ts: "14:02:43", level: "info",    agent: "orchestrator", msg: "Iter 3 · respawning code_analyzer with new context" },
    ],
    memory: [
      { signature: "ModuleNotFoundError:stripe_sdk_v4", similarity: 0.74,
        fix: "Replace with stripe>=4.0.0 in requirements.txt + update import paths",
        successRate: 0.83, timesSeen: 4 },
      { signature: "yarn.lock drift on @types/node", similarity: 0.66,
        fix: "Run yarn install --frozen-lockfile then commit regenerated lock",
        successRate: 0.91, timesSeen: 12 },
    ],
    timeline: [
      { iter: 1, title: "Initial build",         status: "fail",    duration: "12s", detail: "ModuleNotFoundError: stripe_sdk_v4" },
      { iter: 1, title: "Investigation fan-out", status: "ok",      duration: "6s",  detail: "4 workers spawned · memory miss" },
      { iter: 2, title: "Repair attempt #1",     status: "fail",    duration: "29s", detail: "Imports patched · 3 tests failed" },
      { iter: 3, title: "Feedback re-plan",      status: "running", duration: "—",   detail: "Coordinator aggregating new context" },
    ],
    problems: [
      { level: "error", agent: "shadow.build", msg: "ModuleNotFoundError: stripe_sdk_v4" },
      { level: "error", agent: "pytest",       msg: "3 integration tests failing" },
      { level: "warn",  agent: "memory",       msg: "top match 0.41 below 0.70 threshold" },
    ],
  },

  // === checkout-api main (promoted) ===
  p_71bd: {
    nodes: [
      { id: "orch", type: "orchestrator", label: "Orchestrator", status: "complete", detail: "Healed in 1 iter · promoted" },
      { id: "coord", type: "coordinator", label: "Coordinator", status: "complete", detail: "Confidence 0.94" },
      { id: "mem", type: "memory", label: "Memory Agent", status: "complete", detail: "0.91 similarity · cached fix" },
      { id: "log", type: "log_analyzer", label: "Log Analyzer", status: "complete", detail: "Parsed 412 lines" },
      { id: "dep", type: "dependency_inspector", label: "Dependency Inspector", status: "complete", detail: "yarn.lock drift" },
      { id: "web", type: "web_search", label: "Web Search", status: "complete", detail: "skipped (memory hit)" },
      { id: "cfg", type: "config_analyzer", label: "Config Analyzer", status: "complete", detail: "lockfile validated" },
      { id: "rep_imp", type: "repair_imports", label: "Repair · Imports", status: "complete", detail: "no-op" },
      { id: "rep_yml", type: "repair_yaml", label: "Repair · YAML", status: "complete", detail: "yarn.lock regenerated" },
    ],
    edges: baseEdges,
    logs: [
      { ts: "13:01:02", level: "info",    agent: "webhook",      msg: "POST /webhook/github · push acme/checkout-api@ab51e09" },
      { ts: "13:01:03", level: "info",    agent: "memory",       msg: "Cache hit · sig=yarn.lock-drift · similarity 0.91" },
      { ts: "13:01:04", level: "success", agent: "repair_yml",   msg: "yarn install --frozen-lockfile · success" },
      { ts: "13:01:18", level: "success", agent: "shadow.test",  msg: "pytest 184/184 passed · coverage 88.2%" },
      { ts: "13:01:22", level: "success", agent: "orchestrator", msg: "Promoted to main · merge_sha=ab51e09" },
    ],
    memory: [
      { signature: "yarn.lock drift on @types/node", similarity: 0.91,
        fix: "Run yarn install --frozen-lockfile then commit regenerated lock",
        successRate: 0.94, timesSeen: 13 },
    ],
    timeline: [
      { iter: 1, title: "Memory hit · skip investigation", status: "ok", duration: "3s",  detail: "Cached fix applied" },
      { iter: 2, title: "Shadow test · all green",         status: "ok", duration: "14s", detail: "184 tests passed" },
      { iter: 2, title: "Promote to main",                 status: "ok", duration: "2s",  detail: "Auto-merged ab51e09" },
    ],
    problems: [],
  },

  // === auth-svc feat/oauth (healed) ===
  p_44e2: {
    nodes: [
      { id: "orch", type: "orchestrator", label: "Orchestrator", status: "complete", detail: "Healed in 4 iters" },
      { id: "coord", type: "coordinator", label: "Coordinator", status: "complete", detail: "Confidence 0.81" },
      { id: "mem", type: "memory", label: "Memory Agent", status: "complete", detail: "0.58 similarity" },
      { id: "log", type: "log_analyzer", label: "Log Analyzer", status: "complete", detail: "Parsed 6,120 lines" },
      { id: "dep", type: "dependency_inspector", label: "Dependency Inspector", status: "complete", detail: "python:3.9 EOL" },
      { id: "web", type: "web_search", label: "Web Search", status: "complete", detail: "Docker hub advisory" },
      { id: "cfg", type: "config_analyzer", label: "Config Analyzer", status: "complete", detail: "Dockerfile rewritten" },
      { id: "rep_imp", type: "repair_imports", label: "Repair · Imports", status: "complete", detail: "wheels rebuilt" },
      { id: "rep_yml", type: "repair_yaml", label: "Repair · YAML", status: "complete", detail: "ci.yml updated" },
    ],
    edges: baseEdges,
    logs: [
      { ts: "11:10:01", level: "error",   agent: "shadow.build", msg: "docker: base python:3.9 reached EOL" },
      { ts: "11:10:08", level: "info",    agent: "web_search",   msg: "Match: hub.docker.com/_/python EOL notice" },
      { ts: "11:11:42", level: "info",    agent: "repair_yml",   msg: "Bumped FROM python:3.9-slim → python:3.12-slim" },
      { ts: "11:14:09", level: "warn",    agent: "shadow.test",  msg: "iter 2 · 7 wheel build failures" },
      { ts: "11:18:31", level: "success", agent: "shadow.test",  msg: "iter 4 · all green · 312/312" },
    ],
    memory: [
      { signature: "docker: base python:3.9 EOL", similarity: 0.58,
        fix: "Bump base image to python:3.12-slim, rebuild wheels",
        successRate: 0.77, timesSeen: 6 },
    ],
    timeline: [
      { iter: 1, title: "EOL detection",        status: "fail", duration: "8s",  detail: "Base image flagged" },
      { iter: 2, title: "Repair · Dockerfile",  status: "fail", duration: "1m",  detail: "wheel build failures" },
      { iter: 3, title: "Repair · pin versions", status: "fail", duration: "47s", detail: "2 wheels still failing" },
      { iter: 4, title: "Repair · system deps", status: "ok",   duration: "1m12s", detail: "All green · healed" },
    ],
    problems: [
      { level: "warn", agent: "memory", msg: "similarity 0.58 below 0.70 — fix recorded for next time" },
    ],
  },

  // === billing main (failed) ===
  p_22c0: {
    nodes: [
      { id: "orch", type: "orchestrator", label: "Orchestrator", status: "failed", detail: "Escalated after 5 iters" },
      { id: "coord", type: "coordinator", label: "Coordinator", status: "failed", detail: "Confidence 0.31 — too low" },
      { id: "mem", type: "memory", label: "Memory Agent", status: "complete", detail: "No prior incidents" },
      { id: "log", type: "log_analyzer", label: "Log Analyzer", status: "complete", detail: "deadlock detected" },
      { id: "dep", type: "dependency_inspector", label: "Dependency Inspector", status: "complete", detail: "no drift" },
      { id: "web", type: "web_search", label: "Web Search", status: "complete", detail: "Postgres docs · DEADLOCK" },
      { id: "cfg", type: "config_analyzer", label: "Config Analyzer", status: "complete", detail: "migration order ok" },
      { id: "rep_imp", type: "repair_imports", label: "Repair · Imports", status: "complete", detail: "no-op" },
      { id: "rep_yml", type: "repair_yaml", label: "Repair · YAML", status: "failed", detail: "Cannot auto-fix migration" },
    ],
    edges: baseEdges,
    logs: [
      { ts: "09:21:02", level: "error",   agent: "shadow.migrate", msg: "ERROR 40P01 deadlock detected on table billing_invoices" },
      { ts: "09:21:14", level: "info",    agent: "memory",         msg: "No prior incidents matching this signature" },
      { ts: "09:24:07", level: "warn",    agent: "coordinator",    msg: "Confidence 0.31 · below 0.50 floor" },
      { ts: "09:31:55", level: "error",   agent: "orchestrator",   msg: "Iter 5 · escalating to on-call · paged @sre-billing" },
    ],
    memory: [],
    timeline: [
      { iter: 1, title: "Deadlock surfaced",   status: "fail", duration: "22s", detail: "40P01 on billing_invoices" },
      { iter: 2, title: "Lock-order rewrite",  status: "fail", duration: "31s", detail: "Still deadlocking" },
      { iter: 3, title: "Retry w/ advisory",   status: "fail", duration: "28s", detail: "Timeout 30s" },
      { iter: 4, title: "Split migration",     status: "fail", duration: "44s", detail: "FK violation" },
      { iter: 5, title: "Escalate to on-call", status: "fail", duration: "—",   detail: "Paged @sre-billing" },
    ],
    problems: [
      { level: "error", agent: "shadow.migrate", msg: "Deadlock 40P01 on billing_invoices" },
      { level: "error", agent: "orchestrator",   msg: "Max iterations reached — escalated" },
      { level: "warn",  agent: "coordinator",    msg: "Confidence 0.31 below 0.50 floor" },
    ],
  },

  // === web main (pending) ===
  p_19af: {
    nodes: [
      { id: "orch", type: "orchestrator", label: "Orchestrator", status: "spawned", detail: "Awaiting webhook payload" },
      { id: "coord", type: "coordinator", label: "Coordinator", status: "spawned", detail: "—" },
      { id: "mem", type: "memory", label: "Memory Agent", status: "spawned", detail: "—" },
      { id: "log", type: "log_analyzer", label: "Log Analyzer", status: "spawned", detail: "—" },
      { id: "dep", type: "dependency_inspector", label: "Dependency Inspector", status: "spawned", detail: "—" },
      { id: "web", type: "web_search", label: "Web Search", status: "spawned", detail: "—" },
      { id: "cfg", type: "config_analyzer", label: "Config Analyzer", status: "spawned", detail: "—" },
      { id: "rep_imp", type: "repair_imports", label: "Repair · Imports", status: "spawned", detail: "—" },
      { id: "rep_yml", type: "repair_yaml", label: "Repair · YAML", status: "spawned", detail: "—" },
    ],
    edges: baseEdges,
    logs: [
      { ts: "14:04:55", level: "info", agent: "webhook",      msg: "POST /webhook/github · push acme/web@0fe11b8" },
      { ts: "14:04:55", level: "info", agent: "orchestrator", msg: "Pipeline p_19af queued · iter=0" },
    ],
    memory: [],
    timeline: [
      { iter: 0, title: "Webhook received", status: "running", duration: "—", detail: "Awaiting orchestrator pickup" },
    ],
    problems: [],
  },
};

export function getPipelineDetail(id: string): PipelineDetail {
  return pipelineDetails[id] ?? pipelineDetails["p_8a1f"];
}

export const fileTree = [
  { type: "folder", name: "Active Pipelines", count: 2, children: [
    { type: "pipeline", id: "p_8a1f", name: "checkout-api · iter 3", status: "running" as const },
    { type: "pipeline", id: "p_19af", name: "web · main",            status: "pending" as const },
  ]},
  { type: "folder", name: "Recent Runs", count: 3, children: [
    { type: "pipeline", id: "p_71bd", name: "checkout-api · main",   status: "promoted" as const },
    { type: "pipeline", id: "p_44e2", name: "auth-svc · feat/oauth", status: "healed" as const },
    { type: "pipeline", id: "p_22c0", name: "billing · main",        status: "failed" as const },
  ]},
  { type: "folder", name: "Shadow Environments", count: 2, children: [
    { type: "shadow", id: "s_1", name: "shadow_p_8a1f_iter3", status: "running" as const },
    { type: "shadow", id: "s_2", name: "shadow_p_44e2_iter4", status: "healed" as const },
  ]},
];
