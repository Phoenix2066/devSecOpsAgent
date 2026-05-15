import { GitBranch, Bell, Cloud, ShieldCheck, Wifi } from "lucide-react";

export function StatusBar({ zoom }: { zoom: number }) {
  return (
    <div className="flex h-6 items-center gap-3 bg-statusbar px-3 text-[11px] text-statusbar-foreground">
      <span className="flex items-center gap-1"><GitBranch size={12} /> fix/repair-9c2</span>
      <span className="flex items-center gap-1"><Cloud size={12} /> shadow_p_8a1f_iter3</span>
      <span className="flex items-center gap-1">
        <span className="h-1.5 w-1.5 rounded-full bg-white/90 pulse-dot" />
        17 agents · iter 3
      </span>
      <span className="ml-auto flex items-center gap-1"><ShieldCheck size={12} /> HMAC verified</span>
      <span className="flex items-center gap-1"><Wifi size={12} /> ws connected</span>
      <span>UTC 14:02:46</span>
      <span className="rounded bg-white/15 px-1.5 font-mono">{Math.round(zoom * 100)}%</span>
      <Bell size={12} />
    </div>
  );
}
