import { ChevronDown, ChevronRight, GitCommit, Container, CircleDot, Plus } from "lucide-react";
import { useState } from "react";
import { fileTree } from "@/lib/mock-data";
import { CreateProjectModal } from "./CreateProjectModal";

const statusDot: Record<string, string> = {
  running: "bg-running pulse-dot",
  pending: "bg-muted-foreground",
  promoted: "bg-primary",
  healed: "bg-primary/70",
  failed: "bg-destructive",
};

export function Sidebar({ activeId, onSelect }: { activeId: string; onSelect: (id: string) => void }) {
  const [open, setOpen] = useState<Record<string, boolean>>({
    "Active Pipelines": true, "Recent Runs": true, "Shadow Environments": false,
  });
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <aside className="flex h-full w-72 flex-col bg-sidebar border-r border-border text-sidebar-foreground">
      <div className="flex h-9 items-center justify-between px-4 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        <span>Explorer</span>
        <button 
          onClick={() => setModalOpen(true)}
          className="p-1 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          title="Replicate Workflow"
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
                    const Icon = c.type === "shadow" ? Container : GitCommit;
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
                        <span className={`ml-auto h-2 w-2 rounded-full ${statusDot[c.status]}`} />
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
          <span>17 agents alive · 2 shadows running</span>
        </div>
      </div>

      <CreateProjectModal open={modalOpen} onOpenChange={setModalOpen} />
    </aside>
  );
}
