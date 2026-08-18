import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-canvas px-6 py-12">
      {/* Ambient purple/black glow, slowly drifting so the page doesn't feel static */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="animate-float-glow absolute -top-40 left-1/4 h-[32rem] w-[32rem] rounded-full bg-brand/35 blur-[120px]" />
        <div className="animate-float-glow-delayed absolute top-1/3 -right-20 h-[28rem] w-[28rem] rounded-full bg-violet-900/40 blur-[120px]" />
        <div className="animate-float-glow absolute bottom-0 left-1/3 h-[24rem] w-[24rem] rounded-full bg-gold/10 blur-[100px]" />
      </div>

      <Link to="/" className="relative mb-8 flex items-center gap-2">
        <img src="/Point501_logo_new_cropped.png" alt="Point501 logo" className="h-9 w-auto" />
        <span className="text-3xl font-extrabold tracking-tight text-gold">Point501</span>
      </Link>

      <div className="animate-card-in relative w-full max-w-md rounded-xl border border-outline bg-panel p-8 shadow-2xl shadow-black/40">
        {children}
      </div>
    </div>
  );
}
