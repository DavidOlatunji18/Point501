/** Tailwind class pairs for each position/slot badge, colors defined as
 * theme tokens in index.css (--color-pos-*). Used for both a player's real
 * position and their assigned starting slot (FLEX included) since both use
 * the same vocabulary (QB/RB/WR/TE/FLEX/K/DST). */
const POSITION_BADGE_CLASSES: Record<string, string> = {
  QB: "bg-pos-qb/15 text-pos-qb",
  RB: "bg-pos-rb/15 text-pos-rb",
  WR: "bg-pos-wr/15 text-pos-wr",
  TE: "bg-pos-te/15 text-pos-te",
  FLEX: "bg-pos-flex/15 text-pos-flex",
  K: "bg-pos-k/15 text-pos-k",
  DST: "bg-pos-dst/15 text-pos-dst",
  DEF: "bg-pos-dst/15 text-pos-dst",
};

const FALLBACK_BADGE_CLASSES = "bg-panel-alt text-slate-300";

/** Positions that can fill a FLEX slot (mirrors FLEX_ELIGIBLE_POSITIONS in
 * app/services/roster_import.py). */
export const FLEX_ELIGIBLE_POSITIONS = new Set(["RB", "WR", "TE"]);

/** Starting-lineup slots a player is actually eligible to occupy, given
 * their real position - a QB can't fill FLEX, etc. */
export function eligibleSlots(position: string | null | undefined, slots: string[]): string[] {
  if (!position) return [];
  const upper = position.toUpperCase();
  return slots.filter((slot) => slot === upper || (slot === "FLEX" && FLEX_ELIGIBLE_POSITIONS.has(upper)));
}

export function positionBadgeClass(value: string | null | undefined): string {
  if (!value) return FALLBACK_BADGE_CLASSES;
  return POSITION_BADGE_CLASSES[value.toUpperCase()] ?? FALLBACK_BADGE_CLASSES;
}

/** Sleeper's CDN serves headshots by numeric player_id, but DST entries use
 * the team abbreviation as their "player_id" and have no headshot there -
 * those need the team logo endpoint instead (lowercase team code). */
export function playerImageUrl(player: {
  position: string | null;
  nfl_team: string | null;
  sleeper_player_id: string | null;
}): string | null {
  if (!player.sleeper_player_id) return null;
  if (player.position === "DST" || player.position === "DEF") {
    const team = (player.nfl_team || player.sleeper_player_id).toLowerCase();
    return `https://sleepercdn.com/images/team_logos/nfl/${team}.png`;
  }
  return `https://sleepercdn.com/content/nfl/players/${player.sleeper_player_id}.jpg`;
}
