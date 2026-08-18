import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "../components/AuthLayout";
import PasswordInput from "../components/PasswordInput";
import { useUser } from "../context/UserContext";

export default function SignupPage() {
  const navigate = useNavigate();
  const { login } = useUser();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    // No auth backend yet - this is a placeholder form that just enters the
    // app, tracking the entered name client-side for the profile avatar.
    login({ firstName, lastName });
    navigate("/rosters");
  }

  return (
    <AuthLayout>
      <h1 className="text-center text-2xl font-extrabold text-slate-100">Let's get started</h1>
      <p className="mt-1 text-center text-sm text-slate-400">
        Create your <span className="text-gold">Point501</span> account
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gold">First name</label>
            <input
              required
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="mt-1 w-full rounded-md border border-outline bg-panel-alt px-3 py-2 text-sm text-slate-100 focus:border-gold focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gold">Last name</label>
            <input
              required
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="mt-1 w-full rounded-md border border-outline bg-panel-alt px-3 py-2 text-sm text-slate-100 focus:border-gold focus:outline-none"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gold">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-md border border-outline bg-panel-alt px-3 py-2 text-sm text-slate-100 focus:border-gold focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gold">Password</label>
          <PasswordInput value={password} onChange={setPassword} required />
        </div>
        <div>
          <label className="block text-sm font-medium text-gold">Confirm password</label>
          <PasswordInput value={confirmPassword} onChange={setConfirmPassword} required />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button
          type="submit"
          className="w-full rounded-md bg-gold px-4 py-2.5 text-sm font-semibold text-black hover:bg-gold-hover"
        >
          Create account
        </button>
      </form>

      <div className="my-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-outline" />
        <span className="text-xs text-slate-500">Already have an account?</span>
        <div className="h-px flex-1 bg-outline" />
      </div>

      <Link
        to="/login"
        className="block w-full rounded-md bg-brand px-4 py-2.5 text-center text-sm font-semibold text-white hover:bg-brand-hover"
      >
        Log in
      </Link>
    </AuthLayout>
  );
}
