import { createFileRoute, redirect } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { ActivityBar } from "@/components/dashboard/ActivityBar";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { TabBar, type Tab } from "@/components/dashboard/TabBar";
import { PipelineCanvas } from "@/components/dashboard/PipelineCanvas";
import { BottomPanel } from "@/components/dashboard/BottomPanel";
import { StatusBar } from "@/components/dashboard/StatusBar";
import { ZoomControls } from "@/components/dashboard/ZoomControls";
import { pipelines } from "@/lib/mock-data";
import { supabase } from "@/integrations/supabase/client";
import { ChevronUp, GitCommit, RotateCw, Play, LogOut } from "lucide-react";
import { usePipeline } from "@/hooks/usePipeline";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Self-Healing DevSecOps · Pipeline Console" },
      { name: "description", content: "Interactive multi-agent dashboard for autonomous CI/CD recovery." },
    ],
  }),
  beforeLoad: async () => {
    const { data } = await supabase.auth.getSession();
    if (!data.session) {
      throw redirect({ to: "/login" });
    }
  },
  component: Dashboard,
});

function pipelineLabel(id: string) {
  const p = pipelines.find((x) => x.id === id);
  if (!p) return id;
  const repo = p.repo.split("/").pop() ?? p.repo;
  return p.iteration > 0 ? `${repo} · iter ${p.iteration}` : `${repo} · ${p.branch}`;
}

function Dashboard() {
  const [zoom, setZoom] = useState(1);
  const [active, setActive] = useState("p_8a1f");
  const [openIds, setOpenIds] = useState<string[]>(["p_8a1f", "p_71bd", "p_44e2"]);
  const [panelOpen, setPanelOpen] = useState(true);

  const { status, currentIteration } = usePipeline(active);

  const handleSelect = (id: string) => {
    if (!pipelines.some((p) => p.id === id)) return; // ignore non-pipeline (e.g. shadow)
    setActive(id);
    setOpenIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
  };

  const tabs: Tab[] = useMemo(
    () => openIds.map((id) => ({
      id,
      label: pipelineLabel(id),
      dirty: pipelines.find((p) => p.id === id)?.status === "running",
    })),
    [openIds]
  );

  const pipeline = pipelines.find((p) => p.id === active) ?? pipelines[0];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      if (e.key === "=" || e.key === "+") { e.preventDefault(); setZoom((z) => Math.min(1.6, +(z + 0.1).toFixed(2))); }
      else if (e.key === "-") { e.preventDefault(); setZoom((z) => Math.max(0.5, +(z - 0.1).toFixed(2))); }
      else if (e.key === "0") { e.preventDefault(); setZoom(1); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const signOut = async () => {
    await supabase.auth.signOut();
    window.location.href = "/login";
  };

  return (
    <>
      <main
        className="origin-top-left bg-background"
        style={{
          transform: `scale(${zoom})`,
          width: `${100 / zoom}vw`,
          height: `${100 / zoom}vh`,
        }}
      >
        <h1 className="sr-only">Self-Healing DevSecOps Dashboard</h1>

        <div className="flex h-[calc(100%-1.5rem)] w-full">
          <ActivityBar />
          <Sidebar activeId={active} onSelect={handleSelect} />

          <section className="flex min-w-0 flex-1 flex-col">
            <TabBar tabs={tabs} active={active} onSelect={setActive} />

            {/* Pipeline header strip */}
            <div className="flex items-center gap-3 border-b border-border bg-activity px-4 py-2 text-[12px]">
              <GitCommit size={14} className="text-muted-foreground" />
              <span className="font-mono text-muted-foreground">{pipeline.repo}</span>
              <span className="text-muted-foreground/60">·</span>
              <span className="font-mono text-foreground">{pipeline.branch}</span>
              <span className="text-muted-foreground/60">·</span>
              <span className="font-mono text-accent">{pipeline.commit}</span>
              <span className={`ml-2 rounded px-2 py-0.5 text-[10px] uppercase tracking-wider ${
                status === "running" ? "bg-info/15 text-info" :
                status === "failed"  ? "bg-destructive/15 text-destructive" :
                status === "promoted" || status === "healed" ? "bg-primary/15 text-primary" :
                "bg-muted text-muted-foreground"
              }`}>
                {status} · iter {currentIteration}
              </span>
              <span className="ml-auto text-muted-foreground">{pipeline.message}</span>
              <button className="flex items-center gap-1 rounded border border-border px-2 py-1 text-[11px] text-foreground hover:bg-muted">
                <RotateCw size={12} /> Re-run
              </button>
              <button className="flex items-center gap-1 rounded bg-primary px-2 py-1 text-[11px] font-medium text-primary-foreground hover:opacity-90">
                <Play size={12} /> Promote
              </button>
              <button onClick={signOut} className="flex items-center gap-1 rounded border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground">
                <LogOut size={12} /> Sign out
              </button>
            </div>

            {/* Canvas + bottom panel split */}
            <div className="flex min-h-0 flex-1 flex-col">
              <div className={panelOpen ? "h-[58%] min-h-0" : "flex-1 min-h-0"}>
                <PipelineCanvas pipelineId={active} />
              </div>
              {panelOpen ? (
                <div className="h-[42%] min-h-0 border-t border-border">
                  <BottomPanel pipelineId={active} onClose={() => setPanelOpen(false)} />
                </div>
              ) : (
                <button
                  onClick={() => setPanelOpen(true)}
                  className="flex h-7 items-center gap-2 border-t border-border bg-panel px-3 text-[11px] text-muted-foreground hover:text-foreground"
                >
                  <ChevronUp size={12} /> Open panel
                </button>
              )}
            </div>
          </section>
        </div>

        <StatusBar zoom={zoom} />
      </main>

      <ZoomControls zoom={zoom} setZoom={setZoom} />
    </>
  );
}
