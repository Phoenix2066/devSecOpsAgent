import { ChevronDown, ChevronRight, GitCommit, Container, CircleDot, Plus, Box, Trash2 } from "lucide-react";
import { useState, useMemo } from "react";
import { CreateProjectModal } from "./CreateProjectModal";
import type { Pipeline, Project } from "@/lib/types";
import { deleteProject } from "@/lib/api";
import { toast } from "sonner";

const statusDot: Record<string, string> = {
  running: "bg-running pulse-dot",
  pending: "bg-muted-foreground",
  promoted: "bg-primary",
  healed: "bg-primary/70",
  failed: "bg-destructive",
};

export function Sidebar({ 
  activeId, 
  onSelect, 
  pipelines = [],
  projects = []
}: { 
  activeId: string; 
  onSelect: (id: string) => void;
  pipelines?: Pipeline[];
  projects?: Project[];
}) {
  const [open, setOpen] = useState<Record<string, boolean>>({
    "Repositories": true, "Active Pipelines": true, "Recent Runs": true, "Shadow Environments": false,
  });
  const [modalOpen, setModalOpen] = useState(false);

  const fileTree = useMemo(() => {
    const active = pipelines.filter(p => p.status === "running" || p.status === "pending");
    const recent = pipelines.filter(p => p.status !== "running" && p.status !== "pending");
    
    return [
      {
        type: "folder",
        name: "Repositories",
        count: projects.length,
        children: projects.map(p => ({
          type: "project",
          id: p.id,
          name: p.github_repo,
          status: "pending"
        }))
      },
      { 
        type: "folder", 
        name: "Active Pipelines", 
        count: active.length, 
        children: active.map(p => ({
          type: "pipeline",
          id: p.id,
          name: `${(p.project_id || "unk-").split("-")[0]} · ${p.branch || "no-branch"}`,
          status: p.status
        }))
      },
      { 
        type: "folder", 
        name: "Recent Runs", 
        count: recent.length, 
        children: recent.map(p => ({
          type: "pipeline",
          id: p.id,
          name: `${(p.project_id || "unk-").split("-")[0]} · ${p.branch || "no-branch"}`,
          status: p.status
        }))
      },
      { type: "folder", name: "Shadow Environments", count: 0, children: [] },
    ];
  }, [pipelines, projects]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this project?")) return;
    
    try {
      await deleteProject(id);
      toast.success("Project deleted successfully");
      window.location.reload(); // Quick way to refresh data
    } catch (err: any) {
      toast.error(`Failed to delete project: ${err.message}`);
    }
  };

  return (
    <aside className="flex h-full w-72 flex-col bg-sidebar border-r border-border text-sidebar-foreground">
      <div className="flex h-9 items-center justify-between px-4 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        <span>Explorer</span>
        <button 
          onClick={() => setModalOpen(true)}
          className="p-1 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          title="Add Repository"
        >
          <Plus size={14} />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-1 pb-2 text-sm">
        {fileTree.map((folder) => {
          const isOpen = open[folder.name];
          return (
            <div key={folder.name} className="mb-1">
              <button
                onClick={() => setOpen((s) => ({ ...s, [folder.name]: !s[folder.name] }))}
                className="flex w-full items-center gap-1 px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground"
              >
                {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <span>{folder.name}</span>
                <span className="ml-auto text-muted-foreground/70">{folder.count}</span>
              </button>
              {isOpen && (
                <div className="mt-0.5">
                  {folder.children.map((c: any) => {
                    let Icon = GitCommit;
                    if (c.type === "shadow") Icon = Container;
                    if (c.type === "project") Icon = Box;
                    const active = activeId === c.id;
                    return (
                      <button
                        key={c.id}
                        onClick={() => onSelect(c.id)}
                        className={`group flex w-full items-center gap-2 rounded-sm px-3 py-1 pl-6 text-left text-[13px] transition-colors ${
                          active ? "bg-muted text-foreground" : "hover:bg-muted/60"
                        }`}
                      >
                        <Icon size={13} className="text-muted-foreground" />
                        <span className="truncate">{c.name}</span>
                        {c.type === "project" && (
                          <button 
                            onClick={(e) => handleDelete(e, c.id)}
                            className="ml-auto opacity-0 group-hover:opacity-100 p-0.5 hover:bg-destructive/20 hover:text-destructive rounded transition-all"
                          >
                            <Trash2 size={12} />
                          </button>
                        )}
                        {c.type !== "project" && <span className={`ml-auto h-2 w-2 rounded-full ${statusDot[c.status]}`} />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="border-t border-border px-3 py-2 text-[11px] text-muted-foreground">
        <div className="flex items-center gap-2">
          <CircleDot size={12} className="text-primary" />
          <span>{pipelines.length} pipelines tracked</span>
        </div>
      </div>

      <CreateProjectModal open={modalOpen} onOpenChange={setModalOpen} />
    </aside>
  );
}
