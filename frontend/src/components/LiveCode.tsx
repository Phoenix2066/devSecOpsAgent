import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const lines = [
  { t: "$", c: "scope deploy --pipeline=plan-canvas", k: "cmd" },
  { t: "→", c: "resolving graph (6 nodes, 6 edges)", k: "info" },
  { t: "✓", c: "source · github/main @ a9f2e1c", k: "ok" },
  { t: "✓", c: "build · vite 7 · 412ms", k: "ok" },
  { t: "✓", c: "test · 24 passed · 0 failed", k: "ok" },
  { t: "→", c: "deploying to edge.workers.dev", k: "info" },
  { t: "✓", c: "live · https://scope.app · 200 OK", k: "ok" },
  { t: "λ", c: "metrics: p95 41ms · cold 0ms", k: "metric" },
];

const tones: Record<string, string> = {
  cmd: "text-foreground",
  info: "text-[color:var(--color-neon-3)]",
  ok: "text-[color:var(--color-neon)]",
  metric: "text-[color:var(--color-neon-2)]",
};

export function LiveCode() {
  const [visible, setVisible] = useState(0);
  const [typed, setTyped] = useState("");

  useEffect(() => {
    if (visible >= lines.length) {
      const r = setTimeout(() => { setVisible(0); setTyped(""); }, 2400);
      return () => clearTimeout(r);
    }
    const line = lines[visible].c;
    if (typed.length < line.length) {
      const t = setTimeout(() => setTyped(line.slice(0, typed.length + 1)), 18);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => { setVisible(v => v + 1); setTyped(""); }, 320);
    return () => clearTimeout(t);
  }, [visible, typed]);

  return (
    <div className="relative rounded-2xl glass overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border/60">
        <span className="w-3 h-3 rounded-full bg-destructive/70" />
        <span className="w-3 h-3 rounded-full bg-[oklch(0.8_0.15_85)]" />
        <span className="w-3 h-3 rounded-full bg-primary" />
        <span className="ml-3 font-mono text-xs text-muted-foreground">scope ~ runtime.log</span>
        <span className="ml-auto flex items-center gap-2 text-xs text-muted-foreground font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" /> live
        </span>
      </div>
      <div className="p-5 font-mono text-[13px] leading-relaxed min-h-[280px]">
        <AnimatePresence initial={false}>
          {lines.slice(0, visible).map((l, i) => (
            <motion.div
              key={`${l.c}-${i}`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-3"
            >
              <span className="text-muted-foreground/60 w-4">{l.t}</span>
              <span className={tones[l.k]}>{l.c}</span>
            </motion.div>
          ))}
        </AnimatePresence>
        {visible < lines.length && (
          <div className="flex gap-3">
            <span className="text-muted-foreground/60 w-4">{lines[visible].t}</span>
            <span className={tones[lines[visible].k]}>
              {typed}
              <span className="inline-block w-2 h-4 -mb-0.5 bg-primary/80 ml-0.5" style={{ animation: "caret 0.9s steps(1) infinite" }} />
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
