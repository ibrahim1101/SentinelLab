import { useState } from "react";
import { Shield, Lock, User, Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiErr } from "@/lib/api";

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("admin@sentinellab.io");
  const [password, setPassword] = useState("Sentinel@2026");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try { await login(email, password); }
    catch (ex) { setErr(apiErr(ex)); }
    finally { setBusy(false); }
  };

  const quick = (em, pw) => { setEmail(em); setPassword(pw); };

  return (
    <div className="min-h-screen grid place-items-center p-4" style={{ background: "var(--bg)" }} data-testid="login-screen">
      <div className="absolute inset-0 opacity-[0.04]" style={{ backgroundImage: "radial-gradient(var(--text) 1px, transparent 1px)", backgroundSize: "26px 26px" }} />
      <div className="relative w-full max-w-sm">
        <div className="flex flex-col items-center mb-6">
          <div className="grid place-items-center w-14 h-14 rounded-lg mb-3" style={{ background: "color-mix(in srgb, var(--cyan) 15%, transparent)", border: "1px solid var(--cyan)" }}>
            <Shield size={28} style={{ color: "var(--cyan)" }} />
          </div>
          <h1 className="font-head text-2xl font-bold" style={{ color: "var(--text)" }}>SentinelLab</h1>
          <p className="text-[12px]" style={{ color: "var(--text-3)" }}>Security Operations Center</p>
        </div>

        <form onSubmit={submit} className="card p-5">
          <div className="mb-3">
            <div className="font-head font-semibold text-[15px]" style={{ color: "var(--text)" }}>Welcome back</div>
            <div className="text-[12px]" style={{ color: "var(--text-3)" }}>Sign in to your analyst workspace</div>
          </div>
          {err && <div className="mb-3 text-[12px] px-3 py-2 rounded" style={{ background: "rgba(248,113,113,.12)", color: "#F87171", border: "1px solid rgba(248,113,113,.3)" }} data-testid="login-error">{err}</div>}
          <label className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-3)" }}>Email</label>
          <div className="relative mt-1 mb-3">
            <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-3)" }} />
            <input className="inp pl-9" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email" />
          </div>
          <label className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-3)" }}>Password</label>
          <div className="relative mt-1 mb-4">
            <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-3)" }} />
            <input className="inp pl-9 pr-9" type={show ? "text" : "password"} value={password}
              onChange={(e) => setPassword(e.target.value)} data-testid="login-password" />
            <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2" onClick={() => setShow(!show)} style={{ color: "var(--text-3)" }}>
              {show ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
          <button className="btn btn-primary w-full justify-center" disabled={busy} data-testid="login-submit">
            {busy ? "Authenticating…" : "Sign In"}
          </button>
          <div className="mt-4 pt-3 border-t">
            <div className="text-[10px] uppercase mb-2" style={{ color: "var(--text-3)" }}>Quick demo login</div>
            <div className="flex gap-2">
              <button type="button" className="btn btn-sm flex-1 justify-center" onClick={() => quick("admin@sentinellab.io", "Sentinel@2026")} data-testid="demo-admin">Administrator</button>
              <button type="button" className="btn btn-sm flex-1 justify-center" onClick={() => quick("analyst@sentinellab.io", "Analyst@2026")} data-testid="demo-analyst">SOC Analyst</button>
            </div>
          </div>
        </form>
        <p className="text-center text-[11px] mt-4" style={{ color: "var(--text-3)" }}>
          Self-hosted SOC platform for detection, investigation & research.
        </p>
      </div>
    </div>
  );
}
