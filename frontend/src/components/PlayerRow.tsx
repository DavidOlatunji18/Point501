import { useState } from "react";
import { Armchair, Pencil } from "lucide-react";
import { api, type Player, type SleeperPlayerSearchResult } from "../lib/api";
import { eligibleSlots, playerImageUrl, positionBadgeClass } from "../lib/positions";
import PlayerAutocomplete from "./PlayerAutocomplete";

interface PlayerRowProps {
  teamId: number;
  player: Player;
  onChanged: () => void;
  /** Starting-lineup slots not currently occupied by any starter on this team. */
  availableSlots: string[];
}

export default function PlayerRow({ teamId, player, onChanged, availableSlots }: PlayerRowProps) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(player.name);
  const [position, setPosition] = useState(player.position ?? "");
  const [nflTeam, setNflTeam] = useState(player.nfl_team ?? "");
  const [slot, setSlot] = useState(player.slot ?? "");
  const [sleeperPlayerId, setSleeperPlayerId] = useState<string | null>(
    player.sleeper_player_id,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [moving, setMoving] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  async function handleMoveToSlot(newSlot: string | null) {
    if (!newSlot) return;
    setMoving(true);
    setError(null);
    try {
      await api.updatePlayer(teamId, player.id, { slot: newSlot });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update player");
    } finally {
      setMoving(false);
    }
  }

  async function handleBench() {
    setMoving(true);
    setError(null);
    try {
      await api.updatePlayer(teamId, player.id, { slot: null });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update player");
    } finally {
      setMoving(false);
    }
  }

  function handleNameChange(value: string) {
    setName(value);
    // Typing after a match means they're no longer necessarily referring
    // to that exact player - unlink until they pick a new suggestion.
    setSleeperPlayerId(null);
  }

  function handleSelectPlayer(selected: SleeperPlayerSearchResult) {
    setName(
      selected.full_name || [selected.first_name, selected.last_name].filter(Boolean).join(" "),
    );
    setPosition(selected.position ?? "");
    setNflTeam(selected.team ?? "");
    setSleeperPlayerId(selected.player_id);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await api.updatePlayer(teamId, player.id, {
        name,
        position: position || undefined,
        nfl_team: nflTeam || undefined,
        slot: slot || undefined,
        sleeper_player_id: sleeperPlayerId,
      });
      setEditing(false);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update player");
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove() {
    if (!confirm(`Remove ${player.name} from the roster?`)) return;
    try {
      await api.removePlayer(teamId, player.id);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove player");
    }
  }

  if (editing) {
    return (
      <div className="flex flex-wrap items-center gap-2 rounded-md border border-gold/40 bg-gold/10 px-3 py-2">
        <div>
          {sleeperPlayerId && (
            <span className="mb-0.5 block text-xs text-emerald-400">matched</span>
          )}
          <PlayerAutocomplete
            value={name}
            onChange={handleNameChange}
            onSelectPlayer={handleSelectPlayer}
            placeholder="Name"
            className="w-40 rounded border border-outline bg-panel-alt px-2 py-1 text-sm text-slate-100"
          />
        </div>
        <input
          className="w-20 rounded border border-outline bg-panel-alt px-2 py-1 text-sm text-slate-100"
          value={position}
          onChange={(e) => setPosition(e.target.value.toUpperCase())}
          placeholder="Pos"
        />
        <input
          className="w-20 rounded border border-outline bg-panel-alt px-2 py-1 text-sm text-slate-100"
          value={nflTeam}
          onChange={(e) => setNflTeam(e.target.value.toUpperCase())}
          placeholder="Team"
        />
        <input
          className="w-20 rounded border border-outline bg-panel-alt px-2 py-1 text-sm text-slate-100"
          value={slot}
          onChange={(e) => setSlot(e.target.value.toUpperCase())}
          placeholder="Slot"
        />
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded bg-brand px-3 py-1 text-sm text-white hover:bg-brand-hover disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          onClick={() => setEditing(false)}
          className="rounded-md border border-outline px-3 py-1 text-sm font-medium text-slate-300 hover:bg-panel-alt"
        >
          Cancel
        </button>
        {error && <span className="text-sm text-red-400">{error}</span>}
      </div>
    );
  }

  const badgeValue = player.slot || player.position;
  const moveOptions = eligibleSlots(player.position, availableSlots);
  const imageUrl = playerImageUrl(player);

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-outline bg-panel px-3 py-2">
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
        <span className="font-medium text-slate-100">{player.name}</span>
        <span className="text-sm text-slate-400">{player.nfl_team ?? "No team"}</span>
        {!player.sleeper_player_id && (
          <span
            className="rounded bg-amber-900/40 px-2 py-0.5 text-xs font-medium text-amber-300"
            title="Could not be matched to a Sleeper player - live stats/injury lookups won't work for this entry"
          >
            unmatched
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {error && <span className="text-sm text-red-400">{error}</span>}
        {player.slot ? (
          <button
            onClick={handleBench}
            disabled={moving}
            title="Bench"
            aria-label="Bench"
            className="rounded-md border border-outline p-1.5 text-slate-300 hover:bg-panel-alt disabled:opacity-50"
          >
            <Armchair className="h-3.5 w-3.5" />
          </button>
        ) : (
          <select
            value=""
            onChange={(e) => handleMoveToSlot(e.target.value)}
            disabled={moving || moveOptions.length === 0}
            className="rounded border border-outline bg-panel-alt px-2 py-1 text-sm text-slate-300 disabled:opacity-50"
          >
            <option value="" disabled>
              {moveOptions.length === 0 ? "No open slots" : "Move to slot…"}
            </option>
            {moveOptions.map((s, i) => (
              <option key={`${s}-${i}`} value={s}>
                {s}
              </option>
            ))}
          </select>
        )}
        <button
          onClick={() => setEditing(true)}
          title="Edit"
          aria-label="Edit"
          className="rounded-md border border-outline p-1.5 text-slate-300 hover:bg-panel-alt"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={handleRemove}
          className="rounded-md border border-red-800 px-2.5 py-1 text-xs font-medium text-red-400 hover:bg-red-950/40"
        >
          Remove
        </button>
      </div>
    </div>
  );
}
