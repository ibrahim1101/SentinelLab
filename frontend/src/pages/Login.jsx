import { useState } from "react";
import { Shield, Lock, User, Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiErr } from "@/lib/api";

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try { await login(email, password); }
    catch (ex) {
      setErr(!ex.response
        ? "SentinelLab cannot connect to its local backend. MongoDB Community Server must be installed and running on localhost:27017. Check the MongoDB service, then restart SentinelLab."
        : apiErr(ex));
    }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen grid place-items-center p-4" style={{ background: "var(--bg)" }} data-testid="login-screen">
      <div className="absolute inset-0 opacity-[0.04]" style={{ backgroundImage: "radial-gradient(var(--text) 1px, transparent 1px)", backgroundSize: "26px 26px" }} />
      <div className="relative w-full max-w-sm">
        <div className="flex flex-col items-center mb-6">
          <img src="/Neon%20Global%20Shield%20Emblem.png" alt="SentinelLab shield" className="w-24 h-24 object-contain mb-3" />
          <h1 className="font-head text-2xl font-bold" style={{ color: "var(--text)" }}>SentinelLab</h1>
          <p className="text-[12px]" style={{ color: "var(--text-3)" }}>Security Operations Center</p>
        </div>

        <form onSubmit={submit} className="card p-5">
          <div className="mb-3">
            <div className="font-head font-semibold text-[15px]" style={{ color: "var(--text)" }}>Welcome back</div>
            <div className="text-[12px]" style={{ color: "var(--text-3)" }}>Sign in to your analyst workspace</div>
          </div>
          {err && <div className="mb-3 text-[12px] px-3 py-2 rounded" style={{ background: "rgba(248,113,113,.12)", color: "#F87171", border: "1px solid rgba(248,113,113,.3)" }} data-testid="login-error">{err}</div>}
          <label className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-3)" }}>Email or username</label>
          <div className="relative mt-1 mb-3">
            <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-3)" }} />
            <input className="inp" style={{ paddingLeft: "2.5rem" }} autoComplete="username" type="text" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email" placeholder="Email or username" />
          </div>
          <label className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-3)" }}>Password</label>
          <div className="relative mt-1 mb-4">
            <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-3)" }} />
            <input className="inp" style={{ paddingLeft: "2.5rem", paddingRight: "2.5rem" }} autoComplete="current-password" type={show ? "text" : "password"} value={password}
              onChange={(e) => setPassword(e.target.value)} data-testid="login-password" />
            <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2" onClick={() => setShow(!show)} style={{ color: "var(--text-3)" }}>
              {show ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
          <button className="btn btn-primary w-full justify-center" disabled={busy} data-testid="login-submit">
            {busy ? "Authenticating…" : "Sign In"}
          </button>

        </form>
        <p className="text-center text-[11px] mt-4" style={{ color: "var(--text-3)" }}>
          Requires MongoDB Community Server running locally on port 27017.
        </p>
      </div>
    </div>
  );
}
