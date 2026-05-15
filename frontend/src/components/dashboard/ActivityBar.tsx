import { GitBranch, Boxes, Brain, Activity, Settings, Users, Search } from "lucide-react";

const items = [
  { icon: GitBranch, label: "Pipelines", active: true },
  { icon: Boxes, label: "Shadow Envs" },
  { icon: Brain, label: "Memory" },
  { icon: Activity, label: "Telemetry" },
  { icon: Search, label: "Search" },
  { icon: Users, label: "Agents" },
];

export function ActivityBar() {
  return (
    <div className="flex h-full w-12 flex-col items-center justify-between bg-activity py-2 border-r border-border">
      <div className="flex flex-col items-center gap-1">
        {items.map(({ icon: Icon, label, active }) => (
          <button
            key={label}
            title={label}
            className={`relative flex h-10 w-10 items-center justify-center rounded-md text-activity-foreground transition-colors hover:text-foreground ${
              active ? "text-foreground" : ""
            }`}
          >
            {active && (
              <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r bg-primary" />
            )}
            <Icon size={20} strokeWidth={1.6} />
          </button>
        ))}
      </div>
      <button className="flex h-10 w-10 items-center justify-center rounded-md text-activity-foreground hover:text-foreground">
        <Settings size={20} strokeWidth={1.6} />
      </button>
    </div>
  );
}
