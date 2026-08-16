import { useTeams } from "../context/TeamsContext";

interface TeamSelectorProps {
  allowNone?: boolean;
  label?: string;
}

export default function TeamSelector({ allowNone = false, label = "Team" }: TeamSelectorProps) {
  const { teams, selectedTeamId, setSelectedTeamId, loading } = useTeams();

  if (loading) {
    return <p className="text-sm text-slate-400">Loading teams…</p>;
  }

  if (teams.length === 0) {
    return (
      <p className="text-sm text-slate-400">
        No teams yet — add one on the Rosters page first.
      </p>
    );
  }

  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="font-medium text-slate-300">{label}</span>
      <select
        className="rounded-md border border-outline bg-panel-alt px-3 py-1.5 text-sm text-slate-100 focus:border-gold focus:outline-none"
        value={selectedTeamId ?? ""}
        onChange={(e) => setSelectedTeamId(e.target.value ? Number(e.target.value) : null)}
      >
        {allowNone && <option value="">General (no team)</option>}
        {teams.map((team) => (
          <option key={team.id} value={team.id}>
            {team.name}
          </option>
        ))}
      </select>
    </label>
  );
}
