import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { PipelineCanvas } from "@/components/LandingCanvas";
import { LiveCode } from "@/components/LiveCode";
import { MarqueeBadges } from "@/components/MarqueeBadges";
import { ArrowUpRight, GitBranch, Zap, Layers, Workflow } from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Eitri — Self-Healing Pipelines" },
      { name: "description", content: "A live pipeline canvas for shipping fast — built on TanStack Start, edge workers, and Supabase." },
      { property: "og:title", content: "Eitri — Self-Healing Pipelines" },
      { property: "og:description", content: "Plan, canvas and scope your pipelines. Live deploys to the edge." },
    ],
  }),
  component: Index,
});

function Nav() {
  return (
    <header className="fixed top-0 inset-x-0 z-50">
      <div className="mx-auto max-w-6xl px-6 mt-4">
        <div className="glass rounded-full flex items-center justify-between px-5 py-2.5">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-primary to-accent glow-primary" />
            <span className="font-display font-semibold tracking-tight">Eitri</span>
          </div>
          <nav className="hidden md:flex items-center gap-7 text-sm text-muted-foreground">
            <a href="#pipeline" className="hover:text-foreground transition">Pipeline</a>
            <a href="#runtime" className="hover:text-foreground transition">Runtime</a>
            <a href="#stack" className="hover:text-foreground transition">Stack</a>
            <a href="#pricing" className="hover:text-foreground transition">Pricing</a>
          </nav>
          <Link to="/dashboard" className="text-sm bg-primary text-primary-foreground rounded-full px-4 py-1.5 font-medium hover:opacity-90 transition flex items-center gap-1">
            Start free <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative pt-40 pb-20 px-6 overflow-hidden">
      <div className="absolute inset-0 grid-bg pointer-events-none" />
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-primary/10 blur-[140px] pointer-events-none" />
      <div className="relative mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 glass rounded-full px-3 py-1.5 text-xs font-mono text-muted-foreground"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
          v1.4 — pipelines now stream to the edge
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.7 }}
          className="mt-6 text-5xl md:text-7xl font-display font-medium tracking-tight leading-[1.02] max-w-4xl"
        >
          <span className="text-gradient">Plan, canvas</span>
          <br />and ship in one frame.
        </motion.h1>
        <motion.p
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          transition={{ delay: 0.25, duration: 0.6 }}
          className="mt-6 max-w-xl text-lg text-muted-foreground"
        >
          Eitri turns your project plan into a living pipeline. Drag nodes, watch builds run, and deploy to the edge — all from a single canvas.
        </motion.p>
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mt-8 flex flex-wrap gap-3"
        >
          <Link to="/dashboard" className="bg-primary text-primary-foreground rounded-full px-6 py-3 font-medium glow-primary hover:scale-[1.02] transition">
            Open the canvas
          </Link>
          <button className="glass rounded-full px-6 py-3 font-medium hover:border-primary/40 transition">
            Watch a deploy →
          </button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.8 }}
          className="mt-16 grid lg:grid-cols-5 gap-4"
          id="pipeline"
        >
          <div className="lg:col-span-3"><PipelineCanvas /></div>
          <div className="lg:col-span-2" id="runtime"><LiveCode /></div>
        </motion.div>
      </div>
    </section>
  );
}

function Features() {
  const items = [
    { Icon: Workflow, title: "Visual pipelines", body: "Compose builds, tests and deploys as a graph. Re-route on the fly." },
    { Icon: Zap, title: "Edge runtime", body: "Server functions deploy to Cloudflare Workers. Cold start: zero." },
    { Icon: GitBranch, title: "Git native", body: "Every push opens a preview pipeline with isolated state." },
    { Icon: Layers, title: "Typed end-to-end", body: "TanStack Start + TypeScript. Inputs validated, outputs inferred." },
  ];
  return (
    <section className="px-6 py-24" id="stack">
      <div className="mx-auto max-w-6xl">
        <div className="flex items-end justify-between mb-12">
          <h2 className="text-3xl md:text-5xl font-display tracking-tight max-w-xl">
            Built on a stack you can <span className="text-gradient">actually ship on.</span>
          </h2>
          <span className="hidden md:block font-mono text-xs text-muted-foreground">// 04 capabilities</span>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map(({ Icon, title, body }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className="glass rounded-2xl p-6 hover:border-primary/40 transition group relative overflow-hidden"
            >
              <div className="absolute -right-8 -top-8 w-32 h-32 rounded-full bg-primary/10 blur-3xl opacity-0 group-hover:opacity-100 transition" />
              <Icon className="w-5 h-5 text-primary" />
              <h3 className="mt-4 font-medium">{title}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{body}</p>
              <div className="mt-6 font-mono text-[10px] text-muted-foreground/60">0{i + 1}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTA() {
  return (
    <section className="px-6 py-24" id="pricing">
      <div className="mx-auto max-w-4xl glass rounded-3xl p-12 text-center relative overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-px scanline" />
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[400px] h-[400px] rounded-full bg-accent/15 blur-[120px]" />
        <h2 className="relative text-4xl md:text-6xl font-display tracking-tight">
          Your next deploy is <span className="text-gradient">one node away.</span>
        </h2>
        <p className="relative mt-4 text-muted-foreground max-w-lg mx-auto">
          Free tier ships to production. Pay only when your pipelines outgrow it.
        </p>
        <div className="relative mt-8 flex justify-center gap-3">
          <Link to="/dashboard" className="bg-primary text-primary-foreground rounded-full px-7 py-3 font-medium glow-primary">
            Start building
          </Link>
          <button className="glass rounded-full px-7 py-3 font-medium">Read the docs</button>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="px-6 py-10 border-t border-border/60">
      <div className="mx-auto max-w-6xl flex flex-wrap items-center justify-between gap-4 text-xs font-mono text-muted-foreground">
        <span>© 2026 eitri.dev — plan-canvas-scope</span>
        <span>made on the edge · workers @ 41ms p95</span>
      </div>
    </footer>
  );
}

function Index() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <Nav />
      <Hero />
      <MarqueeBadges />
      <Features />
      <CTA />
      <Footer />
    </main>
  );
}
