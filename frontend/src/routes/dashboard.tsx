import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { ActivityBar } from "@/components/dashboard/ActivityBar";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { TabBar, type Tab } from "@/components/dashboard/TabBar";
import { PipelineCanvas } from "@/components/dashboard/PipelineCanvas";
import { BottomPanel } from "@/components/dashboard/BottomPanel";
import { StatusBar } from "@/components/dashboard/StatusBar";
import { ZoomControls } from "@/components/dashboard/ZoomControls";
import { listProjects, listPipelines, rerunPipeline, promotePipeline } from "@/lib/api";
import { ChevronUp, GitCommit, RotateCw, Play, Plus } from "lucide-react";
import { usePipeline } from "@/hooks/usePipeline";
import type { Pipeline, Project } from "@/lib/types";
import { CreateProjectModal } from "@/components/dashboard/CreateProjectModal";
import { toast } from "sonner";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Self-Healing DevSecOps · Pipeline Console" },
      { name: "description", content: "Interactive multi-agent dashboard for autonomous CI/CD recovery." },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const [zoom, setZoom] = useState(1);
  const [active, setActive] = useState<string>("");
  const [openPipelines, setOpenPipelines] = useState<Pipeline[]>([]);
  const [allPipelines, setAllPipelines] = useState<Pipeline[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [panelOpen, setPanelOpen] = useState(true);

  const [modalOpen, setModalOpen] = useState(false);

  const { status, currentIteration, pipeline: activePipeline } = usePipeline(active);

  useEffect(() => {
    async function load() {
      try {
        const fetchedProjects = await listProjects().catch(() => []) || [];
        setProjects(fetchedProjects);

        const pids = await Promise.all(
          fetchedProjects
            .filter(p => p && p.id)
            .map(p => listPipelines(p.id).catch(() => []))
        );
        const flat = pids.flat().filter(Boolean);
        setAllPipelines(flat);
        
        // If we have pipelines, pick the newest one as active
        if (flat.length > 0) {
          const newest = flat.sort((a, b) => new Date(b.triggered_at).getTime() - new Date(a.triggered_at).getTime())[0];
          setActive(newest.id);
          setOpenPipelines([newest]);
        } else {
          setActive("");
          setOpenPipelines([]);
        }
      } catch (err) {
        console.error("Failed to load pipelines", err);
      }
    }
    load();
  }, [modalOpen]);

  const handleSelect = (id: string) => {
    const p = allPipelines.find(x => x.id === id);
    if (!p) return;
    setActive(id);
    setOpenPipelines(prev => prev.some(x => x.id === id) ? prev : [...prev, p]);
  };

  const handleRerun = async () => {
    if (!active) return;
    try {
      await rerunPipeline(active);
      toast.success("Pipeline rerun triggered");
    } catch (err: any) {
      toast.error(`Failed to rerun: ${err.message}`);
    }
  };

  const handlePromote = async () => {
    if (!active) return;
    try {
      await promotePipeline(active);
      toast.success("Deployment promoted successfully");
    } catch (err: any) {
      toast.error(`Failed to promote: ${err.message}`);
    }
  };

  const tabs: Tab[] = useMemo(
    () => openPipelines.map((p) => ({
      id: p.id,
      label: `${(p.id || "").slice(0, 8)} · ${p.branch || "no-branch"}`,
      dirty: p.status === "running",
    })),
    [openPipelines]
  );

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

  if (active && !activePipeline) return <div className="p-8 text-muted-foreground font-mono text-sm">Initializing dashboard...</div>;
  
  const displayPipeline = activePipeline || allPipelines[0];

  return (
    <>
      <main
        className="origin-top-left bg-background h-screen overflow-hidden"
        style={{
          transform: `scale(${zoom})`,
          width: `${100 / zoom}vw`,
          height: `${100 / zoom}vh`,
        }}
      >
        <h1 className="sr-only">Self-Healing DevSecOps Dashboard</h1>

        <div className="flex h-[calc(100%-1.5rem)] w-full">
          <ActivityBar />
          <Sidebar activeId={active} onSelect={handleSelect} pipelines={allPipelines} projects={projects} />

          <section className="flex min-w-0 flex-1 flex-col">
            <TabBar tabs={tabs} active={active} onSelect={setActive} />

            {/* Pipeline header strip */}
            {displayPipeline ? (
              <div className="flex items-center gap-3 border-b border-border bg-activity px-4 py-2 text-[12px]">
                <GitCommit size={14} className="text-muted-foreground" />
                <span className="font-mono text-muted-foreground">{displayPipeline.project_id || "no-project"}</span>
                <span className="text-muted-foreground/60">·</span>
                <span className="font-mono text-foreground">{displayPipeline.branch || "no-branch"}</span>
                <span className="text-muted-foreground/60">·</span>
                <span className="font-mono text-accent">{(displayPipeline.commit_sha || "").slice(0, 7) || "no-sha"}</span>
                <span className={`ml-2 rounded px-2 py-0.5 text-[10px] uppercase tracking-wider ${
                  status === "running" ? "bg-info/15 text-info" :
                  status === "failed"  ? "bg-destructive/15 text-destructive" :
                  status === "promoted" ? "bg-primary/15 text-primary" :
                  "bg-muted text-muted-foreground"
                }`}>
                  {status} · iter {currentIteration}
                </span>
                <button onClick={() => setModalOpen(true)} className="flex items-center gap-1 rounded border border-border px-2 py-1 text-[11px] text-foreground hover:bg-muted ml-auto">
                  <Plus size={12} /> Add Repository
                </button>
                <button 
                  onClick={handleRerun}
                  className="flex items-center gap-1 rounded border border-border px-2 py-1 text-[11px] text-foreground hover:bg-muted"
                >
                  <RotateCw size={12} /> Re-run
                </button>
                <button 
                  onClick={handlePromote}
                  className="flex items-center gap-1 rounded bg-primary px-2 py-1 text-[11px] font-medium text-primary-foreground hover:opacity-90"
                >
                  <Play size={12} /> Promote
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3 border-b border-border bg-activity px-4 py-2 text-[12px]">
                <span className="text-muted-foreground">Select a pipeline from the explorer or add a repository to get started.</span>
                <button onClick={() => setModalOpen(true)} className="flex items-center gap-1 rounded border border-border px-2 py-1 text-[11px] text-foreground hover:bg-muted ml-auto">
                  <Plus size={12} /> Add Repository
                </button>
              </div>
            )}

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

      <CreateProjectModal open={modalOpen} onOpenChange={setModalOpen} />
    </>
  );
}
