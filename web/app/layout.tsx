import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PlantPulse",
  description: "Compound-risk plant intelligence for industrial safety.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100">{children}</body>
    </html>
  );
}
