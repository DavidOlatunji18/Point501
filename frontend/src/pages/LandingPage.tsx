import { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X } from "lucide-react";
import Footer from "../components/Footer";

export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-canvas">
      {/* Ambient purple/black glow stands in for a hero photo backdrop - see
       * PR discussion for why a real player photo can't be used here. */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/4 h-[32rem] w-[32rem] rounded-full bg-brand/35 blur-[120px]" />
        <div className="absolute top-1/3 -right-20 h-[28rem] w-[28rem] rounded-full bg-violet-900/40 blur-[120px]" />
        <div className="absolute bottom-0 left-1/3 h-[24rem] w-[24rem] rounded-full bg-gold/10 blur-[100px]" />
      </div>

      <header className="relative border-b border-outline">
        <div className="relative mx-auto flex max-w-6xl items-center justify-center px-6 py-5 sm:grid sm:grid-cols-3">
          <button
            onClick={() => setMenuOpen(true)}
            aria-label="Open menu"
            className="absolute left-6 text-slate-200 sm:hidden"
          >
            <Menu className="h-6 w-6" />
          </button>

          <div className="hidden sm:block" />
          <div className="flex items-center gap-2 sm:justify-self-center">
            <img src="/Point501_logo_cropped.png" alt="Point501 logo" className="h-9 w-auto" />
            <span className="text-3xl font-extrabold tracking-tight text-gold">Point501</span>
          </div>
          {/* Placeholder until real auth exists - currently just enters the app */}
          <div className="hidden items-center justify-end gap-6 sm:flex sm:justify-self-end">
            <Link
              to="/rosters"
              className="flex items-center gap-1.5 text-sm font-bold tracking-wide text-slate-100 uppercase transition-colors hover:text-violet-400"
            >
              Log in <span aria-hidden="true">→</span>
            </Link>
            <Link
              to="/rosters"
              className="flex items-center gap-1.5 rounded-full bg-gold px-6 py-2.5 text-sm font-bold tracking-wide text-black uppercase hover:bg-gold-hover"
            >
              Sign up <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      </header>

      {menuOpen && (
        <div className="fixed inset-0 z-50 flex flex-col bg-panel sm:hidden">
          <div className="relative flex items-center justify-center border-b border-outline px-6 py-5">
            <button
              onClick={() => setMenuOpen(false)}
              aria-label="Close menu"
              className="absolute left-6 text-slate-200"
            >
              <X className="h-6 w-6" />
            </button>
            <div className="flex items-center gap-2">
              <img src="/Point501_logo_cropped.png" alt="Point501 logo" className="h-9 w-auto" />
              <span className="text-3xl font-extrabold tracking-tight text-gold">Point501</span>
            </div>
          </div>
          <div className="flex flex-1 flex-col items-center justify-center gap-8">
            <Link
              to="/rosters"
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 text-2xl font-bold tracking-wide text-slate-100 uppercase transition-colors hover:text-violet-400"
            >
              Log in <span aria-hidden="true">→</span>
            </Link>
            <Link
              to="/rosters"
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 rounded-full bg-gold px-8 py-3.5 text-2xl font-bold tracking-wide text-black uppercase hover:bg-gold-hover"
            >
              Sign up <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      )}

      <main className="relative mx-auto flex max-w-4xl flex-1 flex-col items-center px-6 pt-24 pb-32 text-center">
        <h1 className="text-5xl font-extrabold leading-[1.05] tracking-tight text-slate-100 sm:text-6xl">
          Never finish below <span className="animate-gold-glow text-gold">.500</span> again
        </h1>

        <p className="mt-6 max-w-2xl text-lg text-slate-400">
          Tired of losing money. Tired of embarrassing forfeits.{" "}
          <span className="font-bold text-gold">Point501</span> makes sure you stay above .500 -
          and puts you in position to win your league.
        </p>

        <Link
          to="/rosters"
          className="mt-10 rounded-full bg-brand px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-brand/30 hover:bg-brand-hover"
        >
          Get started →
        </Link>
      </main>

      <Footer />
    </div>
  );
}
