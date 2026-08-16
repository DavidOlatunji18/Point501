import { useState, type FormEvent } from "react";
import { Pencil } from "lucide-react";
import { useTeams } from "../context/TeamsContext";
import {
  api,
  type CreateTeamPayload,
  type Player,
  type SleeperPlayerSearchResult,
  type Team,
} from "../lib/api";
import PlayerRow from "../components/PlayerRow";
import PlayerAutocomplete from "../components/PlayerAutocomplete";
import { positionBadgeClass } from "../lib/positions";

/** Orders starters to match the team's configured slot order (QB, RB, RB, ...)
 * instead of insertion order, so benching/restoring a player doesn't shuffle
 * their row to the bottom of the list. */
function sortBySlotOrder(starters: Player[], slotOrder: string[]): Player[] {
  const bySlot = new Map<string, Player[]>();
  for (const player of starters) {
    const list = bySlot.get(player.slot!) ?? [];
    list.push(player);
    bySlot.set(player.slot!, list);
  }
  const sorted: Player[] = [];
  for (const slot of slotOrder) {
    sorted.push(...(bySlot.get(slot)?.splice(0, 1) ?? []));
  }
  // Any starter whose slot isn't in slotOrder (shouldn't normally happen)
  // still gets rendered, appended in its original order.
  for (const list of bySlot.values()) {
    sorted.push(...list);
  }
  return sorted;
}

/** Starting lineup slots not currently occupied by any starter on this team. */
function getAvailableSlots(team: Team): string[] {
  const remaining = [...team.starting_lineup_slots];
  for (const player of team.players) {
    if (!player.slot) continue;
    const idx = remaining.indexOf(player.slot);
    if (idx !== -1) remaining.splice(idx, 1);
  }
  return remaining;
}

const DEFAULT_SLOTS = "QB, RB, RB, WR, WR, TE, FLEX, DST, K";

export default function RostersPage() {
  const { teams, setSelectedTeamId, loading, error, refresh } = useTeams();
  const [showCreate, setShowCreate] = useState(false);
  const [activeSlot, setActiveSlot] = useState<number | null>(null);
  const [viewingTeamId, setViewingTeamId] = useState<number | null>(null);

  const viewingTeam = teams.find((t) => t.id === viewingTeamId) ?? null;

  function handleSelectTeam(id: number) {
    setSelectedTeamId(id);
    setViewingTeamId(id);
  }

  function handleAddSlotClick(i: number) {
    if (showCreate && activeSlot === i) {
      setShowCreate(false);
      setActiveSlot(null);
    } else {
      setShowCreate(true);
      setActiveSlot(i);
    }
  }

  function handleCancelCreate() {
    setShowCreate(false);
    setActiveSlot(null);
  }

  return (
    <div className="space-y-6">
      <div className="relative flex items-center justify-center">
        {viewingTeam && (
          <button
            onClick={() => setViewingTeamId(null)}
            className="absolute left-0 rounded-md border border-outline px-3 py-1.5 text-sm font-medium text-slate-300 hover:bg-panel-alt"
          >
            ← Back
          </button>
        )}
        <h1 className="text-xl font-extrabold tracking-tight text-gold">Rosters</h1>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {loading ? (
        <p className="text-sm text-slate-400">Loading…</p>
      ) : viewingTeam ? (
        <TeamDetail key={viewingTeam.id} team={viewingTeam} onChanged={refresh} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {teams.map((team) => (
              <TeamCard key={team.id} team={team} onSelect={() => handleSelectTeam(team.id)} />
            ))}
            {Array.from({ length: 3 - teams.length }).map((_, i) => (
              <button
                key={i}
                onClick={() => handleAddSlotClick(i)}
                className={`flex min-h-32 flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed p-6 text-slate-400 hover:border-gold hover:text-gold ${
                  showCreate && activeSlot === i ? "border-gold text-gold" : "border-outline"
                }`}
              >
                <span className="text-2xl font-bold leading-none">+</span>
                <span className="text-sm font-medium">Add a new roster</span>
              </button>
            ))}
          </div>

          {teams.length === 0 && !showCreate && (
            <p className="text-sm text-slate-400">No teams yet. Add one to get started.</p>
          )}

          {showCreate && (
            <CreateTeamForm
              onCreated={() => {
                setShowCreate(false);
                setActiveSlot(null);
                refresh();
              }}
              onCancel={handleCancelCreate}
            />
          )}
        </>
      )}
    </div>
  );
}

function TeamCard({ team, onSelect }: { team: Team; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className="flex flex-col items-start gap-2 rounded-lg border border-outline bg-panel p-4 text-left hover:border-gold"
    >
      <h2 className="text-lg font-semibold text-slate-100">{team.name}</h2>
      <p className="text-sm text-slate-400">
        {team.source === "sleeper" ? "Imported from Sleeper" : "Manually entered"} ·{" "}
        {team.players.length} player{team.players.length === 1 ? "" : "s"}
      </p>
      <div className="flex flex-wrap gap-1">
        {team.starting_lineup_slots.map((slot, i) => (
          <span
            key={i}
            className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${positionBadgeClass(slot)}`}
          >
            {slot}
          </span>
        ))}
      </div>
    </button>
  );
}

function CreateTeamForm({
  onCreated,
  onCancel,
}: {
  onCreated: () => void;
  onCancel: () => void;
}) {
  const [mode, setMode] = useState<"manual" | "sleeper">("manual");
  const [name, setName] = useState("");
  const [rosterText, setRosterText] = useState("");
  const [slots, setSlots] = useState(DEFAULT_SLOTS);
  const [sleeperUsername, setSleeperUsername] = useState("");
  const [sleeperLeagueId, setSleeperLeagueId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const starting_lineup_slots = slots
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean);

      const payload: CreateTeamPayload =
        mode === "manual"
          ? {
              source: "manual",
              name,
              roster_text: rosterText || undefined,
              starting_lineup_slots,
            }
          : {
              source: "sleeper",
              name: name || undefined,
              sleeper_username: sleeperUsername,
              sleeper_league_id: sleeperLeagueId,
            };

      await api.createTeam(payload);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create team");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-lg border border-outline bg-panel p-4"
    >
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setMode("manual")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium ${
            mode === "manual" ? "bg-brand text-white" : "bg-panel-alt text-slate-300"
          }`}
        >
          Paste roster
        </button>
        <button
          type="button"
          onClick={() => setMode("sleeper")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium ${
            mode === "sleeper" ? "bg-brand text-white" : "bg-panel-alt text-slate-300"
          }`}
        >
          Import from Sleeper
        </button>
      </div>

      {mode === "manual" ? (
        <>
          <div>
            <label className="block text-sm font-medium text-slate-300">Team name</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-md border border-outline bg-panel-alt px-3 py-2 text-sm text-slate-100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300">
              Roster (paste, one player per line - optional)
            </label>
            <textarea
              value={rosterText}
              onChange={(e) => setRosterText(e.target.value)}
              rows={5}
              placeholder={"QB Patrick Mahomes\nRB Christian McCaffrey\nSF DST"}
              className="mt-1 w-full rounded-md border border-outline bg-panel-alt px-3 py-2 text-sm font-mono text-slate-100 placeholder:text-slate-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300">
              Starting lineup slots
            </label>
            <input
              value={slots}
              onChange={(e) => setSlots(e.target.value)}
              className="mt-1 w-full rounded-md border border-outline bg-panel-alt px-3 py-2 text-sm text-slate-100"
            />
            <p className="mt-1 text-xs text-slate-500">Comma-separated.</p>
          </div>
        </>
      ) : (
        <>
          <div>
            <label className="block text-sm font-medium text-slate-300">
              Team name (optional)
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-md border border-outline bg-panel-alt px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500"
              placeholder="Defaults to your Sleeper team name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300">Sleeper username</label>
            <input
              required
              value={sleeperUsername}
              onChange={(e) => setSleeperUsername(e.target.value)}
              className="mt-1 w-full rounded-md border border-outline bg-panel-alt px-3 py-2 text-sm text-slate-100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300">Sleeper league ID</label>
            <input
              required
              value={sleeperLeagueId}
              onChange={(e) => setSleeperLeagueId(e.target.value)}
              className="mt-1 w-full rounded-md border border-outline bg-panel-alt px-3 py-2 text-sm text-slate-100"
            />
          </div>
        </>
      )}

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50"
        >
          {submitting ? "Creating…" : "Create team"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={submitting}
          className="rounded-md border border-red-800 px-4 py-2 text-sm font-medium text-red-400 hover:bg-red-950/40 disabled:opacity-50"
        >
          Nevermind
        </button>
      </div>
    </form>
  );
}

function TeamDetail({ team, onChanged }: { team: Team; onChanged: () => void }) {
  const [showAddPlayer, setShowAddPlayer] = useState(false);
  const [showPasteMore, setShowPasteMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(team.name);

  async function handleSaveName() {
    const trimmed = nameInput.trim();
    if (!trimmed || trimmed === team.name) {
      setEditingName(false);
      setNameInput(team.name);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.updateTeam(team.id, { name: trimmed });
      setEditingName(false);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rename team");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteTeam() {
    if (!confirm(`Delete team "${team.name}"? This can't be undone.`)) return;
    setBusy(true);
    try {
      await api.deleteTeam(team.id);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete team");
    } finally {
      setBusy(false);
    }
  }

  async function handleSync() {
    setBusy(true);
    setError(null);
    try {
      await api.syncTeam(team.id);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to sync team");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4 rounded-lg border border-outline bg-panel p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          {editingName ? (
            <div className="flex items-center gap-2">
              <input
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSaveName();
                  if (e.key === "Escape") {
                    setEditingName(false);
                    setNameInput(team.name);
                  }
                }}
                autoFocus
                className="rounded-md border border-outline bg-panel-alt px-2 py-1 text-lg font-semibold text-slate-100"
              />
              <button
                onClick={handleSaveName}
                disabled={busy}
                className="rounded-md bg-brand px-3 py-1 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50"
              >
                Save
              </button>
              <button
                onClick={() => {
                  setEditingName(false);
                  setNameInput(team.name);
                }}
                className="rounded-md border border-outline px-3 py-1 text-sm font-medium text-slate-300 hover:bg-panel-alt"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-slate-100">{team.name}</h2>
              <button
                onClick={() => setEditingName(true)}
                title="Edit team name"
                aria-label="Edit team name"
                className="rounded-md border border-outline p-1.5 text-slate-300 hover:bg-panel-alt"
              >
                <Pencil className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
          <p className="text-sm text-slate-400">
            {team.source === "sleeper" ? "Imported from Sleeper" : "Manually entered"} ·{" "}
            {team.players.length} player{team.players.length === 1 ? "" : "s"}
          </p>
        </div>
        <div className="flex gap-2">
          {team.source === "sleeper" && (
            <button
              onClick={handleSync}
              disabled={busy}
              className="rounded-md border border-outline px-3 py-1.5 text-sm font-medium text-slate-300 hover:bg-panel-alt disabled:opacity-50"
            >
              Sync from Sleeper
            </button>
          )}
          <button
            onClick={handleDeleteTeam}
            disabled={busy}
            className="rounded-md border border-red-800 px-3 py-1.5 text-sm font-medium text-red-400 hover:bg-red-950/40 disabled:opacity-50"
          >
            Nuke team
          </button>
        </div>
      </div>

      <div>
        <p className="mb-1 text-sm font-medium text-slate-300">Starting lineup slots</p>
        <div className="flex flex-wrap gap-1.5">
          {team.starting_lineup_slots.length === 0 ? (
            <span className="text-sm text-slate-400">None configured</span>
          ) : (
            team.starting_lineup_slots.map((slot, i) => (
              <span
                key={i}
                className={`rounded-full px-2.5 py-1 text-xs font-medium ${positionBadgeClass(slot)}`}
              >
                {slot}
              </span>
            ))
          )}
        </div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm font-medium text-slate-300">Roster ({team.players.length})</p>
          <div className="flex gap-2">
            <button
              onClick={() => setShowAddPlayer((v) => !v)}
              className={`rounded-md border px-3 py-1.5 text-sm font-medium ${
                showAddPlayer
                  ? "border-gold text-gold"
                  : "border-outline text-slate-300 hover:bg-panel-alt"
              }`}
            >
              {showAddPlayer ? "Cancel" : "+ Add player"}
            </button>
            <button
              onClick={() => setShowPasteMore((v) => !v)}
              className={`rounded-md border px-3 py-1.5 text-sm font-medium ${
                showPasteMore
                  ? "border-gold text-gold"
                  : "border-outline text-slate-300 hover:bg-panel-alt"
              }`}
            >
              {showPasteMore ? "Cancel" : "+ Paste more"}
            </button>
          </div>
        </div>

        {showAddPlayer && (
          <AddPlayerForm
            teamId={team.id}
            onAdded={() => {
              setShowAddPlayer(false);
              onChanged();
            }}
          />
        )}
        {showPasteMore && (
          <PasteMoreForm
            teamId={team.id}
            onAdded={() => {
              setShowPasteMore(false);
              onChanged();
            }}
          />
        )}

        {team.players.length === 0 ? (
          <p className="text-sm text-slate-400">No players yet.</p>
        ) : (
          <RosterSections team={team} onChanged={onChanged} />
        )}
      </div>
    </div>
  );
}

function RosterSections({ team, onChanged }: { team: Team; onChanged: () => void }) {
  const starters = sortBySlotOrder(
    team.players.filter((p) => p.slot),
    team.starting_lineup_slots,
  );
  const bench = team.players.filter((p) => !p.slot);
  const availableSlots = getAvailableSlots(team);

  return (
    <div className="space-y-4">
      <div>
        <p className="mb-1.5 text-xs font-semibold tracking-wide text-slate-500 uppercase">
          Starters
        </p>
        {starters.length === 0 ? (
          <p className="text-sm text-slate-500">
            No starters assigned yet - edit a player to set their slot, or use the Lineup page
            for a recommendation.
          </p>
        ) : (
          <div className="space-y-1.5">
            {starters.map((player) => (
              <PlayerRow
                key={player.id}
                teamId={team.id}
                player={player}
                onChanged={onChanged}
                availableSlots={availableSlots}
              />
            ))}
          </div>
        )}
      </div>

      <div>
        <p className="mb-1.5 text-xs font-semibold tracking-wide text-slate-500 uppercase">
          Bench
        </p>
        {bench.length === 0 ? (
          <p className="text-sm text-slate-500">No bench players.</p>
        ) : (
          <div className="space-y-1.5">
            {bench.map((player) => (
              <PlayerRow
                key={player.id}
                teamId={team.id}
                player={player}
                onChanged={onChanged}
                availableSlots={availableSlots}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function AddPlayerForm({ teamId, onAdded }: { teamId: number; onAdded: () => void }) {
  const [name, setName] = useState("");
  const [position, setPosition] = useState("");
  const [nflTeam, setNflTeam] = useState("");
  const [sleeperPlayerId, setSleeperPlayerId] = useState<string | undefined>(undefined);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleNameChange(value: string) {
    setName(value);
    // Typing after a selection means they're no longer necessarily
    // referring to that exact player - drop the pinned ID.
    setSleeperPlayerId(undefined);
  }

  function handleSelectPlayer(player: SleeperPlayerSearchResult) {
    setName(
      player.full_name || [player.first_name, player.last_name].filter(Boolean).join(" "),
    );
    setPosition(player.position ?? "");
    setNflTeam(player.team ?? "");
    setSleeperPlayerId(player.player_id);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.addPlayer(teamId, {
        name,
        position: position || undefined,
        nfl_team: nflTeam || undefined,
        sleeper_player_id: sleeperPlayerId,
      });
      onAdded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add player");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-2 flex flex-wrap items-end gap-2 rounded-md bg-panel-alt p-3"
    >
      <div>
        <label className="block text-xs font-medium text-slate-400">
          Name {sleeperPlayerId && <span className="text-emerald-400">(matched)</span>}
        </label>
        <PlayerAutocomplete
          value={name}
          onChange={handleNameChange}
          onSelectPlayer={handleSelectPlayer}
          placeholder="Start typing a player name…"
          className="w-52 rounded border border-outline bg-panel px-2 py-1 text-sm text-slate-100"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-400">Position</label>
        <input
          value={position}
          onChange={(e) => setPosition(e.target.value.toUpperCase())}
          className="w-20 rounded border border-outline bg-panel px-2 py-1 text-sm text-slate-100"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-400">NFL team</label>
        <input
          value={nflTeam}
          onChange={(e) => setNflTeam(e.target.value.toUpperCase())}
          className="w-20 rounded border border-outline bg-panel px-2 py-1 text-sm text-slate-100"
        />
      </div>
      <button
        type="submit"
        disabled={submitting || !name}
        className="rounded bg-brand px-3 py-1.5 text-sm text-white hover:bg-brand-hover disabled:opacity-50"
      >
        {submitting ? "Adding…" : "Add"}
      </button>
      {error && <span className="text-sm text-red-400">{error}</span>}
    </form>
  );
}

function PasteMoreForm({ teamId, onAdded }: { teamId: number; onAdded: () => void }) {
  const [text, setText] = useState("");
  const [replace, setReplace] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.pasteRoster(teamId, text, replace);
      onAdded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to paste roster");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-2 space-y-2 rounded-md bg-panel-alt p-3">
      <textarea
        required
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={4}
        placeholder={"WR Tyreek Hill\nK Justin Tucker"}
        className="w-full rounded border border-outline bg-panel px-2 py-1.5 text-sm font-mono text-slate-100 placeholder:text-slate-500"
      />
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-1.5 text-sm text-slate-400">
          <input
            type="checkbox"
            checked={replace}
            onChange={(e) => setReplace(e.target.checked)}
          />
          Nuke entire roster
        </label>
        <button
          type="submit"
          disabled={submitting}
          className="rounded bg-brand px-3 py-1.5 text-sm text-white hover:bg-brand-hover disabled:opacity-50"
        >
          {submitting ? "Saving…" : "Save"}
        </button>
        {error && <span className="text-sm text-red-400">{error}</span>}
      </div>
    </form>
  );
}
