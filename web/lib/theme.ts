/**
 * Dark control-room palette. Risk color scale thresholds are anchored to
 * the actual exported data: baseline/quiet-day risk sits roughly 0-40,
 * the hero model's calibrated alert threshold is ~97 (see
 * risk_timeline.json -> operating_threshold), so "critical" starts there,
 * not at an arbitrary round number.
 */

export const COLORS = {
  bg: "#0a0e14",
  panel: "#10141c",
  panelRaised: "#161b26",
  border: "#232a38",
  borderSoft: "#1a202c",
  textPrimary: "#e2e8f0",
  textMuted: "#64748b",
  textDim: "#3f4a5e",
  calm: "#22d3ee", // cyan
  watch: "#38bdf8", // sky
  elevated: "#f59e0b", // amber
  high: "#f97316", // orange
  critical: "#ef4444", // red
  safe: "#10b981", // green (used for zones/assets explicitly "fine")
} as const;

export type RiskBand = "calm" | "watch" | "elevated" | "high" | "critical";

export function riskBand(risk: number): RiskBand {
  if (risk >= 97) return "critical";
  if (risk >= 85) return "high";
  if (risk >= 65) return "elevated";
  if (risk >= 40) return "watch";
  return "calm";
}

export function riskLabel(risk: number): string {
  const band = riskBand(risk);
  return { calm: "Calm", watch: "Watch", elevated: "Elevated", high: "High", critical: "Critical" }[band];
}

export function riskColor(risk: number): string {
  return COLORS[riskBand(risk)];
}

/** Smooth interpolation across the same band boundaries, for glow/heat
 * intensity rather than discrete badges. Returns a CSS color string. */
export function riskColorSmooth(risk: number): string {
  const stops: [number, string][] = [
    [0, COLORS.calm],
    [40, COLORS.watch],
    [65, COLORS.elevated],
    [85, COLORS.high],
    [97, COLORS.critical],
    [100, COLORS.critical],
  ];
  const clamped = Math.max(0, Math.min(100, risk));
  for (let i = 0; i < stops.length - 1; i++) {
    const [lo, loColor] = stops[i];
    const [hi, hiColor] = stops[i + 1];
    if (clamped >= lo && clamped <= hi) {
      const t = hi === lo ? 0 : (clamped - lo) / (hi - lo);
      return mixHex(loColor, hiColor, t);
    }
  }
  return COLORS.critical;
}

function mixHex(a: string, b: string, t: number): string {
  const pa = hexToRgb(a);
  const pb = hexToRgb(b);
  const r = Math.round(pa.r + (pb.r - pa.r) * t);
  const g = Math.round(pa.g + (pb.g - pa.g) * t);
  const bl = Math.round(pa.b + (pb.b - pa.b) * t);
  return `rgb(${r}, ${g}, ${bl})`;
}

function hexToRgb(hex: string) {
  const clean = hex.replace("#", "");
  return {
    r: parseInt(clean.substring(0, 2), 16),
    g: parseInt(clean.substring(2, 4), 16),
    b: parseInt(clean.substring(4, 6), 16),
  };
}

export const ZONE_TYPE_LABEL: Record<string, string> = {
  normal: "Normal",
  caution: "Caution",
  restricted: "Restricted",
};
