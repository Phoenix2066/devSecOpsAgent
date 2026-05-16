import { Handle, Position } from "reactflow";
import {
  Cpu, GitMerge, Brain, Activity, FileSearch, Package, Globe,
  Settings2, Code2, Container, FileCode, FileWarning,
} from "lucide-react";
import type { AgentNodeData, AgentStatus, AgentType } from "@/lib/mock-data";

const ICONS: Record<AgentType, React.ComponentType<{ size?: number }>> = {
  orchestrator: Cpu, coordinator: GitMerge, memory: Brain, monitor: Activity,
  log_analyzer: FileSearch, dependency_inspector: Package, web_search: Globe,
  config_analyzer: Settings2, code_analyzer: Code2,
  repair_docker: Container, repair_yaml: FileCode, repair_imports: FileWarning,
};

const STATUS_STYLES: Record<AgentStatus, { ring: string; dot: string; label: string }> = {
  spawned:  { ring: "border-muted-foreground/40", dot: "bg-muted-foreground", label: "spawned" },
  running:  { ring: "border-info/60 glow-accent", dot: "bg-info pulse-dot",   label: "running" },
  complete: { ring: "border-primary/70 glow-primary", dot: "bg-primary",      label: "ok" },
  failed:   { ring: "border-destructive/70 glow-destructive", dot: "bg-destructive", label: "fail" },
};

export function AgentNode({ data }: { data: AgentNodeData }) {
  if (!data) return null;
  const Icon = ICONS[data.type as AgentType] || Cpu;
  const s = STATUS_STYLES[data.status as AgentStatus] || STATUS_STYLES.spawned;
  return (
    <div className={`w-[210px] rounded-md border bg-card text-card-foreground ${s.ring} transition-all`}>
      <Handle type="target" position={Position.Top} className="!h-1.5 !w-1.5 !border-0 !bg-border" />
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <div className="flex h-7 w-7 items-center justify-center rounded bg-muted text-foreground">
          <Icon size={14} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[13px] font-medium">{data.label}</div>
          <div className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
            {data.type}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
            {s.label}
          </span>
        </div>
      </div>
      <div className="px-3 py-2 font-mono text-[11px] text-muted-foreground">
        {data.detail}
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-1.5 !w-1.5 !border-0 !bg-border" />
    </div>
  );
}
