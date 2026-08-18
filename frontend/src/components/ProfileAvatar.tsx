import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { User } from "lucide-react";
import { useUser } from "../context/UserContext";

export default function ProfileAvatar() {
  const { user, logout } = useUser();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  if (!user) return null;

  // Login doesn't collect a name, so it logs in with blank first/last name -
  // fall back to a generic icon instead of blank/single-letter initials.
  const initials = `${user.firstName[0] ?? ""}${user.lastName[0] ?? ""}`.toUpperCase();

  function handleLogout() {
    logout();
    setMenuOpen(false);
    navigate("/");
  }

  return (
    <div className="relative">
      <button
        onClick={() => setMenuOpen((v) => !v)}
        aria-label="Account menu"
        className="flex h-9 w-9 items-center justify-center rounded-full bg-gold text-sm font-bold text-black hover:bg-gold-hover"
      >
        {initials || <User className="h-5 w-5" />}
      </button>

      {menuOpen && (
        <>
          {/* Click-outside catcher */}
          <button
            aria-hidden="true"
            tabIndex={-1}
            onClick={() => setMenuOpen(false)}
            className="fixed inset-0 z-10 cursor-default"
          />
          <div className="absolute right-0 z-20 mt-2 w-40 rounded-md border border-outline bg-panel py-1 shadow-lg">
            <button
              onClick={handleLogout}
              className="block w-full px-4 py-2 text-left text-sm text-slate-200 hover:bg-panel-alt"
            >
              Log out
            </button>
          </div>
        </>
      )}
    </div>
  );
}
