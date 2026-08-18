import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "../components/AuthLayout";
import PasswordInput from "../components/PasswordInput";
import { useUser } from "../context/UserContext";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useUser();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    // No auth backend yet - this is a placeholder form that just enters the
    // app. Login doesn't collect a name, so the profile avatar falls back
    // to a generic icon instead of initials.
    login({ firstName: "", lastName: "" });
    navigate("/rosters");
  }

  return (
    <AuthLayout>
      <h1 className="text-center text-2xl font-extrabold text-slate-100">
        Welcome back <span className="text-violet-400">Coach</span>
      </h1>
      <p className="mt-1 text-center text-sm text-slate-400">
        Log in to your <span className="text-gold">Point501</span> account
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-300">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-md border border-outline bg-panel-alt px-3 py-2 text-sm text-slate-100 focus:border-gold focus:outline-none"
          />
        </div>
        <div>
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-slate-300">Password</label>
            <a href="#" className="text-xs font-medium text-gold hover:underline">
              Forgot password?
            </a>
          </div>
          <PasswordInput value={password} onChange={setPassword} required />
        </div>
        <button
          type="submit"
          className="w-full rounded-md bg-brand px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-hover"
        >
          Log in
        </button>
      </form>

      <div className="my-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-outline" />
        <span className="text-xs tracking-wide text-slate-500 uppercase">Or</span>
        <div className="h-px flex-1 bg-outline" />
      </div>

      <Link
        to="/signup"
        className="block w-full rounded-md border border-outline px-4 py-2.5 text-center text-sm font-semibold text-slate-200 hover:bg-panel-alt"
      >
        Create account
      </Link>
    </AuthLayout>
  );
}
