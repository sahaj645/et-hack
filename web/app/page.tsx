"use client";

import { useState } from "react";
import LiveTab from "@/components/LiveTab";
import KnowledgeTab from "@/components/KnowledgeTab";
import DemoTab from "@/components/DemoTab";
import { useDemoPlayer } from "@/lib/demo";

const TABS = ["Live", "Demo", "Metrics", "Knowledge"] as const;
type Tab = (typeof TABS)[number];

function StubTab({ name, note }: { name: string; note: string }) {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-[#232a38] bg-[#10141c]/50 text-center">
      <div className="font-mono-readout text-sm uppercase tracking-widest text-slate-600">{name}</div>
      <div className="max-w-md text-sm text-slate-500">{note}</div>
    </div>
  );
}

export default function Home() {
  const [tab, setTab] = useState<Tab>("Live");
  const player = useDemoPlayer();

  return (
    <main className="mx-auto min-h-screen max-w-[1400px] px-4 py-5 sm:px-6">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-baseline gap-3">
          <h1 className="text-xl font-bold tracking-tight text-slate-100">PlantPulse</h1>
          <span className="font-mono-readout text-xs text-slate-500">Process Unit 7 · Control Room</span>
        </div>
        <nav className="flex gap-1 rounded-lg border border-[#232a38] bg-[#10141c] p-1">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-md px-3.5 py-1.5 font-mono-readout text-xs font-medium transition ${
                tab === t ? "bg-[#232a38] text-slate-100" : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </header>

      {tab === "Live" && <LiveTab player={player} />}
      {tab === "Demo" && <DemoTab player={player} />}
      {tab === "Metrics" && <StubTab name="Metrics" note="Hero vs. baseline comparison dashboard, sourced from metrics.json, lands in a later session's UI pass." />}
      {tab === "Knowledge" && <KnowledgeTab player={player} />}
    </main>
  );
}
