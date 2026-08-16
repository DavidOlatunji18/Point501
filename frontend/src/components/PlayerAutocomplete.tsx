import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { api, sleeperDisplayName, type SleeperPlayerSearchResult } from "../lib/api";

interface PlayerAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  onSelectPlayer: (player: SleeperPlayerSearchResult) => void;
  placeholder?: string;
  className?: string;
}

/** Debounced typeahead over Sleeper's live player database - lets the user
 * pick an exact player instead of typing a full name and hoping our
 * fuzzy-matching resolves it correctly. */
export default function PlayerAutocomplete({
  value,
  onChange,
  onSelectPlayer,
  placeholder,
  className,
}: PlayerAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<SleeperPlayerSearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const query = value.trim();
    if (query.length < 2) {
      setSuggestions([]);
      setOpen(false);
      return;
    }

    let cancelled = false;
    const timeout = setTimeout(async () => {
      try {
        const results = await api.searchSleeperPlayers(query, 8);
        if (!cancelled) {
          setSuggestions(results);
          setOpen(results.length > 0);
          setHighlighted(0);
        }
      } catch {
        if (!cancelled) {
          setSuggestions([]);
          setOpen(false);
        }
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [value]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function selectPlayer(player: SleeperPlayerSearchResult) {
    onSelectPlayer(player);
    setOpen(false);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (!open || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((h) => (h + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((h) => (h - 1 + suggestions.length) % suggestions.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      selectPlayer(suggestions[highlighted]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        placeholder={placeholder}
        className={className}
        autoComplete="off"
      />
      {open && (
        <ul className="absolute z-10 mt-1 max-h-64 w-64 overflow-y-auto rounded-md border border-outline bg-panel-alt shadow-lg">
          {suggestions.map((player, i) => (
            <li key={player.player_id}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => selectPlayer(player)}
                className={`flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-sm ${
                  i === highlighted ? "bg-brand text-white" : "text-slate-100 hover:bg-panel"
                }`}
              >
                <span className="font-medium">{sleeperDisplayName(player)}</span>
                <span
                  className={`text-xs ${i === highlighted ? "text-white/80" : "text-slate-400"}`}
                >
                  {player.position ?? "?"} · {player.team ?? "FA"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
