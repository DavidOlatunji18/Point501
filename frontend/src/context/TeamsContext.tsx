import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type Team } from "../lib/api";

interface TeamsContextValue {
  teams: Team[];
  loading: boolean;
  error: string | null;
  selectedTeamId: number | null;
  setSelectedTeamId: (id: number | null) => void;
  refresh: () => Promise<void>;
}

const TeamsContext = createContext<TeamsContextValue | null>(null);

export function TeamsProvider({ children }: { children: ReactNode }) {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listTeams();
      setTeams(data);
      setSelectedTeamId((current) => {
        if (current != null && data.some((t) => t.id === current)) return current;
        return data[0]?.id ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load teams");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <TeamsContext.Provider
      value={{ teams, loading, error, selectedTeamId, setSelectedTeamId, refresh }}
    >
      {children}
    </TeamsContext.Provider>
  );
}

export function useTeams() {
  const ctx = useContext(TeamsContext);
  if (!ctx) throw new Error("useTeams must be used within a TeamsProvider");
  return ctx;
}
