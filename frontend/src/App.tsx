import { useState } from "react";
import { NavLink, Outlet, Route, Routes } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { TeamsProvider } from "./context/TeamsContext";
import { LineupProvider } from "./context/LineupContext";
import { ChatProvider } from "./context/ChatContext";
import { UserProvider } from "./context/UserContext";
import Footer from "./components/Footer";
import ProfileAvatar from "./components/ProfileAvatar";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import RostersPage from "./pages/RostersPage";
import ChatPage from "./pages/ChatPage";
import LineupPage from "./pages/LineupPage";

function navLinkClass({ isActive }: { isActive: boolean }) {
  return `text-sm font-bold tracking-wide uppercase transition-colors ${
    isActive ? "text-gold" : "text-slate-400 hover:text-slate-100"
  }`;
}

function mobileNavLinkClass({ isActive }: { isActive: boolean }) {
  return `text-2xl font-bold tracking-wide uppercase transition-colors ${
    isActive ? "text-gold" : "text-slate-300 hover:text-white"
  }`;
}

function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <header className="border-b border-outline bg-panel">
        <div className="relative mx-auto flex max-w-5xl items-center justify-center px-4 py-3 sm:grid sm:grid-cols-3">
          <button
            onClick={() => setMenuOpen(true)}
            aria-label="Open menu"
            className="absolute left-4 text-slate-200 sm:hidden"
          >
            <Menu className="h-6 w-6" />
          </button>

          <nav className="hidden items-center gap-6 sm:flex sm:justify-self-start">
            <NavLink to="/rosters" className={navLinkClass}>
              Rosters
            </NavLink>
            <NavLink to="/chat" className={navLinkClass}>
              Chat
            </NavLink>
            <NavLink to="/lineup" className={navLinkClass}>
              Lineup
            </NavLink>
          </nav>
          <div className="flex items-center gap-2 sm:justify-self-center">
            <img src="/Point501_logo_new_cropped.png" alt="Point501 logo" className="h-9 w-auto" />
            <span className="text-3xl font-extrabold tracking-tight text-gold">Point501</span>
          </div>
          <div className="absolute right-4 sm:static sm:justify-self-end">
            <ProfileAvatar />
          </div>
        </div>
      </header>

      {menuOpen && (
        <div className="fixed inset-0 z-50 flex flex-col bg-panel sm:hidden">
          <div className="relative flex items-center justify-center border-b border-outline px-4 py-3">
            <button
              onClick={() => setMenuOpen(false)}
              aria-label="Close menu"
              className="absolute left-4 text-slate-200"
            >
              <X className="h-6 w-6" />
            </button>
            <div className="flex items-center gap-2">
              <img src="/Point501_logo_new_cropped.png" alt="Point501 logo" className="h-9 w-auto" />
              <span className="text-3xl font-extrabold tracking-tight text-gold">Point501</span>
            </div>
            <div className="absolute right-4">
              <ProfileAvatar />
            </div>
          </div>
          <nav className="flex flex-1 flex-col items-center justify-center gap-10">
            <NavLink
              to="/rosters"
              className={mobileNavLinkClass}
              onClick={() => setMenuOpen(false)}
            >
              Rosters
            </NavLink>
            <NavLink to="/chat" className={mobileNavLinkClass} onClick={() => setMenuOpen(false)}>
              Chat
            </NavLink>
            <NavLink
              to="/lineup"
              className={mobileNavLinkClass}
              onClick={() => setMenuOpen(false)}
            >
              Lineup
            </NavLink>
          </nav>
        </div>
      )}

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}

function App() {
  return (
    <UserProvider>
      <TeamsProvider>
        <LineupProvider>
          <ChatProvider>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />
              <Route element={<AppShell />}>
                <Route path="/rosters" element={<RostersPage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/lineup" element={<LineupPage />} />
              </Route>
            </Routes>
          </ChatProvider>
        </LineupProvider>
      </TeamsProvider>
    </UserProvider>
  );
}

export default App;
