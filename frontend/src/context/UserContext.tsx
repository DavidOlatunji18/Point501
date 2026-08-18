import { createContext, useContext, useState, type ReactNode } from "react";

export interface AppUser {
  firstName: string;
  lastName: string;
}

interface UserContextValue {
  user: AppUser | null;
  login: (user: AppUser) => void;
  logout: () => void;
}

const UserContext = createContext<UserContextValue | null>(null);

// No real auth backend yet - this only tracks a client-side "logged in"
// state for the dummy Login/Signup flow, so the header can show a profile
// avatar once someone's gone through it. Resets on refresh, same as the
// rest of the app's session-only state (Lineup/Chat context, etc).
export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);

  return (
    <UserContext.Provider value={{ user, login: setUser, logout: () => setUser(null) }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used within a UserProvider");
  return ctx;
}
