"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

export interface KGNode {
  id: string;
  kind: string;
  label: string;
  [key: string]: unknown;
}
export interface KGEdge {
  source: string;
  target: string;
  relation: string;
}
export interface KGPath {
  event_id: string;
  path_nodes: string[];
  sentence: string;
}
export interface KGData {
  nodes: KGNode[];
  edges: KGEdge[];
  paths: KGPath[];
}

interface KnowledgeGraphProps {
  kg: KGData;
  activeEventId: string | null;
}

const KIND_COLOR: Record<string, string> = {
  zone: "#38bdf8",
  worker: "#e2e8f0",
  permit: "#f59e0b",
  asset: "#2dd4bf",
  channel: "#c084fc",
  maintenance_task: "#f97316",
};

const KIND_LABEL: Record<string, string> = {
  zone: "Zone",
  worker: "Worker",
  permit: "Permit",
  asset: "Asset",
  channel: "Sensor Channel",
  maintenance_task: "Maintenance Task",
};

function endpointId(end: unknown): string {
  if (typeof end === "string") return end;
  if (end && typeof end === "object" && "id" in end) return String((end as { id: unknown }).id);
  return "";
}

export default function KnowledgeGraph({ kg, activeEventId }: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w) setWidth(w);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const activePath = kg.paths.find((p) => p.event_id === activeEventId) ?? null;
  const highlighted = useMemo(() => new Set(activePath?.path_nodes ?? []), [activePath]);

  const graphData = useMemo(
    () => ({
      nodes: kg.nodes.map((n) => ({ ...n })),
      links: kg.edges.map((e) => ({ ...e })),
    }),
    [kg]
  );

  return (
    <div className="rounded-lg border border-[#232a38] bg-[#10141c] p-3">
      <div className="mb-2 flex flex-wrap gap-3 font-mono-readout text-[10px] text-slate-500">
        {Object.entries(KIND_LABEL).map(([kind, label]) => (
          <span key={kind} className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: KIND_COLOR[kind] }} />
            {label}
          </span>
        ))}
      </div>
      <div ref={containerRef} style={{ height: 420 }}>
        <ForceGraph2D
          graphData={graphData}
          width={width}
          height={420}
          backgroundColor="#10141c"
          nodeId="id"
          nodeLabel={(n: { label?: string }) => n.label ?? ""}
          nodeRelSize={4}
          nodeVal={(n: { id: string }) => (highlighted.has(n.id) ? 6 : 3)}
          nodeColor={(n: { id: string; kind: string }) =>
            highlighted.has(n.id) ? "#ef4444" : (KIND_COLOR[n.kind] ?? "#64748b")
          }
          linkColor={(l: { source: unknown; target: unknown }) =>
            highlighted.has(endpointId(l.source)) && highlighted.has(endpointId(l.target)) ? "#ef4444" : "#2a3242"
          }
          linkWidth={(l: { source: unknown; target: unknown }) =>
            highlighted.has(endpointId(l.source)) && highlighted.has(endpointId(l.target)) ? 2.5 : 1
          }
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          cooldownTicks={100}
        />
      </div>
      <div className="mt-3 min-h-[3rem] rounded-md border border-[#232a38] bg-[#161b26] p-3 font-mono-readout text-sm text-slate-300">
        {activePath ? activePath.sentence : "No active incident — graph shows the plant's normal topology."}
      </div>
    </div>
  );
}
