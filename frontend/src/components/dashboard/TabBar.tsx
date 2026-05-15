import { X, Circle } from "lucide-react";

export interface Tab { id: string; label: string; dirty?: boolean; }

export function TabBar({ tabs, active, onSelect }: {
  tabs: Tab[]; active: string; onSelect: (id: string) => void;
}) {
  return (
    <div className="flex h-9 items-stretch border-b border-border bg-activity">
      {tabs.map((t) => {
        const isActive = t.id === active;
        return (
          <button
            key={t.id}
            onClick={() => onSelect(t.id)}
            className={`group relative flex items-center gap-2 border-r border-border px-3 text-[13px] transition-colors ${
              isActive
                ? "bg-background text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {isActive && (
              <span className="absolute left-0 right-0 top-0 h-0.5 bg-primary" />
            )}
            <span>{t.label}</span>
            {t.dirty ? (
              <Circle size={8} className="fill-foreground text-foreground" />
            ) : (
              <X size={13} className="opacity-0 group-hover:opacity-60" />
            )}
          </button>
        );
      })}
    </div>
  );
}
