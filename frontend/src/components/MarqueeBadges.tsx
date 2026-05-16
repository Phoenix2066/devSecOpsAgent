const items = [
  "TanStack Start", "React 19", "Vite 7", "Tailwind v4",
  "Cloudflare Workers", "Supabase", "Bun", "Motion",
  "TypeScript", "Edge Runtime",
];

export function MarqueeBadges() {
  return (
    <div className="relative overflow-hidden py-6 border-y border-border/60">
      <div className="flex gap-3 animate-[marquee_28s_linear_infinite] whitespace-nowrap">
        {[...items, ...items, ...items].map((t, i) => (
          <span
            key={i}
            className="px-4 py-2 rounded-full border border-border/80 text-xs font-mono text-muted-foreground bg-card/40"
          >
            {t}
          </span>
        ))}
      </div>
      <style>{`@keyframes marquee { to { transform: translateX(-33.33%); } }`}</style>
    </div>
  );
}
