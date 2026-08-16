import { useState } from "react";
import { Link } from "react-router-dom";
import { useTeams } from "../context/TeamsContext";
import { useLineup } from "../context/LineupContext";
import { api } from "../lib/api";
import { playerImageUrl, positionBadgeClass } from "../lib/positions";
import TeamSelector from "../components/TeamSelector";

function LineupPlayerCard({
  badgeValue,
  name,
  position,
  nflTeam,
  sleeperPlayerId,
  reasoning,
}: {
  badgeValue: string | null;
  name: string;
  position: string | null;
  nflTeam: string | null;
  sleeperPlayerId: string | null;
  reasoning: string;
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const imageUrl = playerImageUrl({
    position,
    nfl_team: nflTeam,
    sleeper_player_id: sleeperPlayerId,
  });

  return (
    <div className="rounded-md border border-outline p-3">
      <div className="flex flex-wrap items-center gap-3">
        <span
          className={`w-12 shrink-0 rounded px-2 py-0.5 text-center text-xs font-semibold ${positionBadgeClass(badgeValue)}`}
        >
          {badgeValue ?? "?"}
        </span>
        {imageUrl && !imageFailed ? (
          <img
            src={imageUrl}
            alt=""
            onError={() => setImageFailed(true)}
            className="h-8 w-8 shrink-0 rounded-full bg-panel-alt object-cover"
          />
        ) : (
          <span className="h-8 w-8 shrink-0 rounded-full bg-panel-alt" />
        )}
        <span className="font-medium text-slate-100">{name}</span>
        <span className="text-sm text-slate-400">
          {position ?? "?"} · {nflTeam ?? "No team"}
        </span>
      </div>
      <p className="mt-1 text-sm text-slate-400">{reasoning}</p>
    </div>
  );
}

export default function LineupPage() {
  const { selectedTeamId, teams, refresh } = useTeams();
  const { lineup, setLineup } = useLineup();
  const [week, setWeek] = useState("");
  const [season, setSeason] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applied, setApplied] = useState(false);

  async function handleGetLineup() {
    if (selectedTeamId == null) return;
    setLoading(true);
    setError(null);
    setApplied(false);
    setApplyError(null);
    setLineup(null);
    try {
      const result = await api.getLineup(
        selectedTeamId,
        week ? Number(week) : undefined,
        season ? Number(season) : undefined,
      );
      setLineup(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to build lineup");
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setLineup(null);
    setError(null);
    setApplyError(null);
    setApplied(false);
  }

  async function handleApplyLineup() {
    if (!lineup || selectedTeamId == null) return;
    setApplying(true);
    setApplyError(null);
    try {
      const assignments = [
        ...lineup.lineup.map((a) => ({ player_id: a.player_id, slot: a.slot })),
        ...lineup.bench.map((b) => ({ player_id: b.player_id, slot: null })),
      ];
      await api.applyLineup(selectedTeamId, assignments);
      await refresh();
      setApplied(true);
    } catch (err) {
      setApplyError(err instanceof Error ? err.message : "Failed to apply lineup");
    } finally {
      setApplying(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-extrabold text-gold">This Week's Lineup</h1>
        <div className="flex flex-wrap items-center gap-3">
          <TeamSelector />
          <input
            value={week}
            onChange={(e) => setWeek(e.target.value)}
            placeholder="Week (auto)"
            className="w-28 rounded-md border border-outline bg-panel-alt px-3 py-1.5 text-sm text-slate-100 placeholder:text-slate-500"
          />
          <input
            value={season}
            onChange={(e) => setSeason(e.target.value)}
            placeholder="Season (auto)"
            className="w-32 rounded-md border border-outline bg-panel-alt px-3 py-1.5 text-sm text-slate-100 placeholder:text-slate-500"
          />
          <button
            onClick={handleGetLineup}
            disabled={loading || selectedTeamId == null || teams.length === 0}
            className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50"
          >
            {loading ? "Building…" : "Build lineup"}
          </button>
          {lineup && (
            <button
              onClick={handleClear}
              className="rounded-md border border-outline px-4 py-2 text-sm font-medium text-slate-300 hover:bg-panel-alt"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {!lineup && !loading && !error && (
        <p className="text-sm text-slate-400">
          Pick a team and click "Build lineup" to get this week's recommended starters — crunched
          from real season stats, matchups, and injury reports, not vibes.
        </p>
      )}

      {lineup && (
        <div className="space-y-4">
          <div className="rounded-lg border border-outline bg-panel p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-medium text-slate-300">
                Week {lineup.week}, {lineup.season}
              </p>
              <div className="flex items-center gap-3">
                {applyError && <span className="text-sm text-red-400">{applyError}</span>}
                {applied && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gold">Lineup applied</span>
                    <Link
                      to="/rosters"
                      className="rounded-md border border-outline px-3 py-1.5 text-sm font-medium text-slate-300 hover:bg-panel-alt"
                    >
                      View in Rosters
                    </Link>
                  </div>
                )}
                <button
                  onClick={handleApplyLineup}
                  disabled={applying}
                  className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50"
                >
                  {applying ? "Setting…" : "Set lineup"}
                </button>
              </div>
            </div>
            <p className="mt-2 text-sm text-slate-400">{lineup.summary}</p>
          </div>

          <div className="rounded-lg border border-outline bg-panel p-4">
            <h2 className="mb-3 text-sm font-semibold text-slate-300">Starting lineup</h2>
            <div className="space-y-2">
              {lineup.lineup.map((assignment) => (
                <LineupPlayerCard
                  key={assignment.player_id}
                  badgeValue={assignment.slot}
                  name={assignment.name}
                  position={assignment.position}
                  nflTeam={assignment.nfl_team}
                  sleeperPlayerId={assignment.sleeper_player_id}
                  reasoning={assignment.reasoning}
                />
              ))}
            </div>
          </div>

          {lineup.bench.length > 0 && (
            <div className="rounded-lg border border-outline bg-panel p-4">
              <h2 className="mb-3 text-sm font-semibold text-slate-300">Bench</h2>
              <div className="space-y-2">
                {lineup.bench.map((player) => (
                  <LineupPlayerCard
                    key={player.player_id}
                    badgeValue={player.position}
                    name={player.name}
                    position={player.position}
                    nflTeam={player.nfl_team}
                    sleeperPlayerId={player.sleeper_player_id}
                    reasoning={player.reasoning}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
