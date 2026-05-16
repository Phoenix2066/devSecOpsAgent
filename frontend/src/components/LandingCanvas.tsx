import { motion } from "framer-motion";

const nodes = [
  { id: "src", x: 60, y: 80, label: "Source", sub: "github/main", color: "var(--color-neon-3)" },
  { id: "build", x: 280, y: 40, label: "Build", sub: "vite • bun", color: "var(--color-neon)" },
  { id: "test", x: 280, y: 140, label: "Test", sub: "vitest", color: "var(--color-neon)" },
  { id: "deploy", x: 500, y: 60, label: "Deploy", sub: "edge worker", color: "var(--color-neon-2)" },
  { id: "scope", x: 500, y: 160, label: "Scope", sub: "plan canvas", color: "var(--color-neon-2)" },
  { id: "live", x: 720, y: 110, label: "Live", sub: "200 OK", color: "var(--color-neon)" },
];

const edges: [string, string][] = [
  ["src", "build"], ["src", "test"],
  ["build", "deploy"], ["test", "scope"],
  ["deploy", "live"], ["scope", "live"],
];

const pos = (id: string) => nodes.find(n => n.id === id)!;

export function PipelineCanvas() {
  return (
    <div className="relative w-full overflow-hidden rounded-2xl glass p-4">
      <div className="absolute inset-0 grid-bg opacity-50 pointer-events-none" />
      <svg viewBox="0 0 800 220" className="w-full h-auto relative z-10">
        <defs>
          <linearGradient id="edge" x1="0" x2="1">
            <stop offset="0%" stopColor="oklch(0.78 0.18 150 / 0)" />
            <stop offset="50%" stopColor="oklch(0.78 0.18 150 / 0.9)" />
            <stop offset="100%" stopColor="oklch(0.74 0.21 280 / 0.9)" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2.5" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {edges.map(([a, b], i) => {
          const A = pos(a), B = pos(b);
          const mx = (A.x + B.x) / 2;
          const d = `M ${A.x + 70} ${A.y} C ${mx} ${A.y}, ${mx} ${B.y}, ${B.x} ${B.y}`;
          return (
            <g key={i}>
              <path d={d} stroke="oklch(1 0 0 / 0.08)" strokeWidth="1.5" fill="none" />
              <path
                d={d}
                stroke="url(#edge)"
                strokeWidth="2"
                fill="none"
                strokeDasharray="6 8"
                style={{ animation: `flow 2.${i}s linear infinite` }}
                filter="url(#glow)"
              />
            </g>
          );
        })}

        {nodes.map((n, i) => (
          <motion.g
            key={n.id}
            initial={{ opacity: 0, y: 12, scale: 0.9 }}
            whileInView={{ opacity: 1, y: 0, scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.12, type: "spring", stiffness: 200, damping: 18 }}
          >
            <rect
              x={n.x} y={n.y - 18} width="140" height="36" rx="10"
              fill="oklch(0.20 0.02 270 / 0.9)"
              stroke={n.color}
              strokeOpacity="0.5"
            />
            <circle cx={n.x + 14} cy={n.y} r="4" fill={n.color}
              style={{ animation: `pulse-dot 1.8s ease-in-out ${i * 0.2}s infinite` }} />
            <text x={n.x + 26} y={n.y - 2} fill="white" fontSize="11" fontFamily="Space Grotesk" fontWeight="600">{n.label}</text>
            <text x={n.x + 26} y={n.y + 11} fill="oklch(0.7 0.02 270)" fontSize="9" fontFamily="JetBrains Mono">{n.sub}</text>
          </motion.g>
        ))}
      </svg>
    </div>
  );
}
