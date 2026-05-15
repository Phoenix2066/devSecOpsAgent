import { useState } from "react";
import { Terminal, ScrollText, AlertOctagon, Brain, X } from "lucide-react";
import { getPipelineDetail, type LogLine } from "@/lib/mock-data";
import { useLiveLogs } from "@/hooks/useLiveLogs";

const levelColor: Record<LogLine["level"], string> = {
  info:    "text-info",
  warn:    "text-warning",
  error:   "text-destructive",
  success: "text-primary",
  debug:   "text-muted-foreground",
};

export function BottomPanel({ pipelineId, onClose }: { pipelineId: string; onClose: () => void }) {
  const [active, setActive] = useState("logs");
  const detail = getPipelineDetail(pipelineId);
  const { logs } = useLiveLogs(pipelineId);

  const tabs = [
    { id: "logs",     label: "Live Logs",       icon: Terminal,     count: undefined as number | undefined },
    { id: "timeline", label: "Repair Timeline", icon: ScrollText,   count: undefined },
    { id: "memory",   label: "Memory Hits",     icon: Brain,        count: detail.memory.length || undefined },
    { id: "problems", label: "Problems",        icon: AlertOctagon, count: detail.problems.length || undefined },
  ];

  return (
    <div className="flex h-full w-full flex-col bg-panel">
      <div className="flex h-9 items-stretch border-b border-border">
        {tabs.map((t) => {
          const Icon = t.icon;
          const isActive = t.id === active;
          return (
            <button
              key={t.id}
              onClick={() => setActive(t.id)}
              className={`relative flex items-center gap-2 px-4 text-[12px] uppercase tracking-wider transition-colors ${
                isActive ? "text-foreground" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {isActive && <span className="absolute inset-x-3 bottom-0 h-0.5 bg-primary" />}
              <Icon size={13} />
              {t.label}
              {t.count !== undefined && (
                <span className="ml-1 rounded-full bg-destructive/20 px-1.5 text-[10px] text-destructive">
                  {t.count}
                </span>
              )}
            </button>
          );
        })}
        <div className="ml-auto flex items-center pr-2">
          <button onClick={onClose} className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground">
            <X size={14} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto font-mono text-[12px]">
        {active === "logs" && (
          <div className="px-3 py-2">
            {logs.map((l, i) => (
              <div key={i} className="flex gap-3 py-0.5 hover:bg-muted/40">
                <span className="text-muted-foreground/70">{l.ts}</span>
                <span className={`w-12 uppercase ${levelColor[l.level]}`}>{l.level}</span>
                <span className="w-32 truncate text-accent">{l.agent}</span>
                <span className="flex-1 text-foreground">{l.msg}</span>
              </div>
            ))}
            <div className="flex items-center gap-2 py-1 text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-primary pulse-dot" />
              streaming…
            </div>
          </div>
        )}

        {active === "timeline" && (
          <div className="space-y-2 p-4">
            {detail.timeline.map((e, i) => (
              <div key={i} className="flex items-start gap-3 rounded-md border border-border bg-card p-3">
                <div className="font-mono text-[11px] text-muted-foreground">iter {e.iter}</div>
                <div className="flex-1">
                  <div className="text-[13px] font-medium text-foreground">{e.title}</div>
                  <div className="text-[11px] text-muted-foreground">{e.detail}</div>
                </div>
                <div className="text-[11px] text-muted-foreground">{e.duration}</div>
                <span className={`h-2 w-2 rounded-full ${
                  e.status === "ok" ? "bg-primary" :
                  e.status === "fail" ? "bg-destructive" :
                  "bg-running pulse-dot"
                }`} />
              </div>
            ))}
          </div>
        )}

        {active === "memory" && (
          <div className="space-y-2 p-4">
            {detail.memory.length === 0 && (
              <div className="font-sans text-[13px] text-muted-foreground">No memory hits for this pipeline.</div>
            )}
            {detail.memory.map((m, i) => (
              <div key={i} className="rounded-md border border-border bg-card p-3">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-primary/15 px-2 py-0.5 font-mono text-[11px] text-primary">
                    {(m.similarity * 100).toFixed(0)}% sim
                  </span>
                  <span className="font-mono text-[12px] text-foreground">{m.signature}</span>
                  <span className="ml-auto text-[11px] text-muted-foreground">
                    seen {m.timesSeen}× · success {(m.successRate * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="mt-1.5 text-[12px] text-muted-foreground">{m.fix}</div>
              </div>
            ))}
          </div>
        )}

        {active === "problems" && (
          <div className="p-4 font-sans text-[13px] text-muted-foreground">
            {detail.problems.length === 0 ? (
              <div>No problems reported. </div>
            ) : (
              <div className="space-y-1.5">
                {detail.problems.map((p, i) => (
                  <div key={i}>
                    <span className={p.level === "error" ? "text-destructive" : "text-warning"}>{p.level}</span>
                    {" · "}{p.agent}{" · "}{p.msg}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
