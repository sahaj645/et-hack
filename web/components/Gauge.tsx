"use client";

import { motion } from "framer-motion";
import { COLORS, riskColorSmooth, riskLabel } from "@/lib/theme";

interface GaugeProps {
  risk: number;
}

const SIZE = 220;
const CENTER = SIZE / 2;
const RADIUS = 88;
const STROKE = 16;
const HEIGHT = SIZE / 2 + STROKE;

const ARC_PATH = `M ${CENTER - RADIUS},${CENTER} A ${RADIUS},${RADIUS} 0 0 1 ${CENTER + RADIUS},${CENTER}`;

export default function Gauge({ risk }: GaugeProps) {
  const fraction = Math.max(0, Math.min(1, risk / 100));
  const color = riskColorSmooth(risk);
  const band = riskLabel(risk);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: SIZE, height: HEIGHT }}>
        <svg width={SIZE} height={HEIGHT} viewBox={`0 0 ${SIZE} ${HEIGHT}`}>
          <path d={ARC_PATH} fill="none" stroke={COLORS.borderSoft} strokeWidth={STROKE} strokeLinecap="round" />
          <motion.path
            d={ARC_PATH}
            fill="none"
            stroke={color}
            strokeWidth={STROKE}
            strokeLinecap="round"
            initial={false}
            animate={{ pathLength: fraction }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            style={{ filter: `drop-shadow(0 0 6px ${color})` }}
          />
        </svg>
        <div className="absolute inset-x-0 top-[58%] flex -translate-y-1/2 flex-col items-center">
          <motion.span
            key={Math.round(risk)}
            initial={{ opacity: 0.5, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2 }}
            className="font-mono-readout text-5xl font-bold leading-none"
            style={{ color }}
          >
            {risk.toFixed(0)}
          </motion.span>
          <span className="mt-1 text-[11px] font-semibold uppercase tracking-widest text-slate-400">
            {band} Risk
          </span>
        </div>
      </div>
    </div>
  );
}
