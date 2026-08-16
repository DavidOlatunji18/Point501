import { createContext, useContext, useState, type ReactNode } from "react";
import type { LineupResponse } from "../lib/api";

interface LineupContextValue {
  lineup: LineupResponse | null;
  setLineup: (lineup: LineupResponse | null) => void;
}

const LineupContext = createContext<LineupContextValue | null>(null);

// Lives above the router outlet (see App.tsx) so the last-built lineup
// survives navigating away from and back to the Lineup page - it only
// resets on an explicit "Clear" or a full page refresh.
export function LineupProvider({ children }: { children: ReactNode }) {
  const [lineup, setLineup] = useState<LineupResponse | null>(null);

  return (
    <LineupContext.Provider value={{ lineup, setLineup }}>{children}</LineupContext.Provider>
  );
}

export function useLineup() {
  const ctx = useContext(LineupContext);
  if (!ctx) throw new Error("useLineup must be used within a LineupProvider");
  return ctx;
}
