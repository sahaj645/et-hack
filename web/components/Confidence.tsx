"use client";

import { motion } from "framer-motion";
import { COLORS } from "@/lib/theme";

interface ConfidenceProps {
  confidence: number; // 0-1, from risk_agent: 0.5*model_margin + 0.5*cross-agent agreement
}

function band(confidence: number): { label: string; color: string } {
  if (confidence >= 0.6) return { label: "High confidence", color: COLORS.safe };
  if (confidence >= 0.3) return { label: "Moderate confidence — monitor", color: COLORS.elevated };
  return { label: "Low confidence — recommend human review", color: COLORS.textMuted };
}

/** Plain-language readout of risk_agent's confidence value. Confidence is
 * never random — it blends how far the fused score sits above the alert
 * threshold with how many of the six agents independently agree.
 */
export default function Confidence({ confidence }: ConfidenceProps) {
  const { label, color } = band(confidence);

  return (
    <div className="w-full">
      <div className="mb-1 flex justify-between font-mono-readout text-[10px] text-slate-500">
        <span>CONFIDENCE</span>
        <span>{(confidence * 100).toFixed(0)}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#1a202c]">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          initial={false}
          animate={{ width: `${confidence * 100}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>
      <div className="mt-1 font-mono-readout text-[10px]" style={{ color }}>
        {label}
      </div>
    </div>
  );
}
