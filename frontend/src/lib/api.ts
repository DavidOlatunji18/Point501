const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // response body wasn't JSON - fall back to statusText
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

// ---- Types (mirror app/schemas/*.py) ----

export type TeamSource = "manual" | "sleeper";

export interface Player {
  id: number;
  name: string;
  position: string | null;
  nfl_team: string | null;
  sleeper_player_id: string | null;
  slot: string | null;
}

export interface Team {
  id: number;
  name: string;
  source: TeamSource;
  sleeper_league_id: string | null;
  sleeper_user_id: string | null;
  starting_lineup_slots: string[];
  players: Player[];
}

export interface CreateManualTeamPayload {
  source: "manual";
  name: string;
  starting_lineup_slots?: string[];
  roster_text?: string;
}

export interface CreateSleeperTeamPayload {
  source: "sleeper";
  name?: string;
  starting_lineup_slots?: string[];
  sleeper_username: string;
  sleeper_league_id: string;
}

export type CreateTeamPayload = CreateManualTeamPayload | CreateSleeperTeamPayload;

export interface UpdateTeamPayload {
  name?: string;
  starting_lineup_slots?: string[];
}

export interface CreatePlayerPayload {
  name: string;
  position?: string;
  nfl_team?: string;
  slot?: string;
  sleeper_player_id?: string;
}

// Raw Sleeper player object (from GET /sleeper/players/search) - most
// entries have full_name, but team defenses only set first_name/last_name.
export interface SleeperPlayerSearchResult {
  player_id: string;
  full_name?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  position?: string | null;
  team?: string | null;
  injury_status?: string | null;
}

export function sleeperDisplayName(player: SleeperPlayerSearchResult): string {
  return (
    player.full_name ||
    [player.first_name, player.last_name].filter(Boolean).join(" ") ||
    player.player_id
  );
}

export interface UpdatePlayerPayload {
  name?: string;
  position?: string;
  nfl_team?: string;
  // Omit to leave the existing slot untouched; a string moves the player to
  // that slot; null explicitly benches them (backend distinguishes "key
  // omitted" from "key present" - see PlayerUpdate in app/schemas/team.py).
  slot?: string | null;
  // Omit to leave the existing link untouched; a string re-links to that
  // exact player; null explicitly unlinks (backend distinguishes "key
  // omitted" from "key present" - see PlayerUpdate in app/schemas/team.py).
  sleeper_player_id?: string | null;
}

export interface ChatSource {
  title: string;
  source: string;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
}

export interface LineupAssignment {
  slot: string;
  player_id: number;
  name: string;
  position: string | null;
  nfl_team: string | null;
  sleeper_player_id: string | null;
  reasoning: string;
}

export interface BenchPlayer {
  player_id: number;
  name: string;
  position: string | null;
  nfl_team: string | null;
  sleeper_player_id: string | null;
  reasoning: string;
}

export interface LineupResponse {
  team_id: number;
  week: number;
  season: number;
  summary: string;
  lineup: LineupAssignment[];
  bench: BenchPlayer[];
}

// ---- API ----

export const api = {
  listTeams: () => request<Team[]>("/teams"),
  getTeam: (id: number) => request<Team>(`/teams/${id}`),
  createTeam: (payload: CreateTeamPayload) =>
    request<Team>("/teams", { method: "POST", body: JSON.stringify(payload) }),
  updateTeam: (id: number, payload: UpdateTeamPayload) =>
    request<Team>(`/teams/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteTeam: (id: number) => request<void>(`/teams/${id}`, { method: "DELETE" }),
  syncTeam: (id: number) => request<Team>(`/teams/${id}/sync`, { method: "POST" }),

  addPlayer: (teamId: number, payload: CreatePlayerPayload) =>
    request<Player>(`/teams/${teamId}/players`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  searchSleeperPlayers: (query: string, limit = 8) =>
    request<SleeperPlayerSearchResult[]>(
      `/sleeper/players/search?q=${encodeURIComponent(query)}&limit=${limit}`,
    ),
  updatePlayer: (teamId: number, playerId: number, payload: UpdatePlayerPayload) =>
    request<Player>(`/teams/${teamId}/players/${playerId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  removePlayer: (teamId: number, playerId: number) =>
    request<void>(`/teams/${teamId}/players/${playerId}`, { method: "DELETE" }),
  pasteRoster: (teamId: number, rosterText: string, replace = false) =>
    request<Team>(`/teams/${teamId}/roster/paste?replace=${replace}`, {
      method: "POST",
      body: JSON.stringify({ roster_text: rosterText }),
    }),
  applyLineup: (teamId: number, assignments: { player_id: number; slot: string | null }[]) =>
    request<Team>(`/teams/${teamId}/apply-lineup`, {
      method: "POST",
      body: JSON.stringify({ assignments }),
    }),

  chat: (message: string, teamId?: number) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, team_id: teamId ?? null }),
    }),

  getLineup: (teamId: number, week?: number, season?: number, seasonType?: number) => {
    const params = new URLSearchParams({ team_id: String(teamId) });
    if (week != null) params.set("week", String(week));
    if (season != null) params.set("season", String(season));
    if (seasonType != null) params.set("season_type", String(seasonType));
    return request<LineupResponse>(`/lineup?${params.toString()}`);
  },
};
