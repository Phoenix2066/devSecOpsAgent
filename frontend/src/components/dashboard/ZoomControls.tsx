import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

export function ZoomControls({
  zoom, setZoom,
}: { zoom: number; setZoom: (n: number) => void }) {
  const change = (d: number) =>
    setZoom(Math.min(1.6, Math.max(0.5, +(zoom + d).toFixed(2))));

  return (
    <div className="pointer-events-auto fixed bottom-10 right-4 z-50 flex flex-col items-stretch overflow-hidden rounded-md border border-border bg-card/95 shadow-lg backdrop-blur">
      <button
        onClick={() => change(0.1)}
        className="flex h-8 w-10 items-center justify-center text-foreground hover:bg-muted"
        title="Zoom in dashboard"
      >
        <ZoomIn size={14} />
      </button>
      <div className="border-y border-border px-2 py-1 text-center font-mono text-[10px] text-muted-foreground">
        {Math.round(zoom * 100)}%
      </div>
      <button
        onClick={() => change(-0.1)}
        className="flex h-8 w-10 items-center justify-center text-foreground hover:bg-muted"
        title="Zoom out dashboard"
      >
        <ZoomOut size={14} />
      </button>
      <button
        onClick={() => setZoom(1)}
        className="flex h-8 w-10 items-center justify-center border-t border-border text-muted-foreground hover:bg-muted hover:text-foreground"
        title="Reset zoom"
      >
        <Maximize2 size={12} />
      </button>
    </div>
  );
}
