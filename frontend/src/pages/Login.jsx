import { useEffect, useState } from "react";
import axios from "axios";
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
  const [setup, setSetup] = useState(false);
  const [setupEmail, setSetupEmail] = useState("");
  const [setupUsername, setSetupUsername] = useState("");
  const [status, setStatus] = useState(null);
  const [checking, setChecking] = useState(true);
  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const { data } = await axios.get("http://127.0.0.1:18766/status", { timeout: 3500 });
        if (!mounted) return;
        setStatus(data);
        if (data.mongodb_reachable) {
          try {
            const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/api/desktop/setup-status`, { timeout: 3500 });
            if (mounted) setSetup(Boolean(response.data.setup_required));
          } catch {
            if (mounted) setStatus(prev => ({ ...prev, api_unavailable: true }));
          }
        }
      } catch {
        if (mounted) setStatus({ backend: "unavailable", mongodb_installed: null, mongodb_reachable: false });
      } finally {
        if (mounted) setChecking(false);
      }
    };
    check();
    const interval = setInterval(check, 5000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      if (setup) {
        await axios.post(`${process.env.REACT_APP_BACKEND_URL}/api/desktop/setup`, {
          email: setupEmail, username: setupUsername, password
        });
        setSetup(false);
        setEmail(setupUsername);
        setPassword("");
        setErr("Administrator created. Sign in using your new credentials.");
        return;
      }
      await login(email, password);
    }
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

        <div className="card p-3 mb-3 text-[12px]" role="status" aria-live="polite" data-testid="desktop-service-status">
          <div className="font-semibold mb-2" style={{ color: "var(--text)" }}>Local service status</div>
          <div className="flex items-center gap-2 mb-1">
            <span className={`inline-block w-2 h-2 rounded-full ${!checking && status?.backend === "running" ? "bg-green-500" : "bg-red-500"}`} />
            SentinelLab backend: {checking ? "Checking…" : status?.backend === "running" ? "Diagnostic service online" : "Unavailable"}
          </div>
          <div className="flex items-center gap-2 mb-1">
            <span className={`inline-block w-2 h-2 rounded-full ${status?.mongodb_reachable ? "bg-green-500" : "bg-red-500"}`} />
            MongoDB: {checking ? "Checking…" : status?.mongodb_reachable ? "Connected and responding" : status?.mongodb_installed === true ? "Installed, but not reachable" : status?.mongodb_installed === false ? "Windows MongoDB service not found" : "Not reachable (installation unknown)"}
          </div>
          {status?.api_unavailable && <p className="mt-2 text-amber-400">Database responds, but the SentinelLab API is not ready. Restart the application.</p>}
          {!checking && !status?.mongodb_reachable && <p className="mt-2" style={{ color: "var(--text-3)" }}>Install or start MongoDB Community Server on port 27017, then restart SentinelLab. Status refreshes every 5 seconds.</p>}
          {!checking && status?.mongodb_reachable && !status?.api_unavailable && <p className="mt-2" style={{ color: "var(--text-3)" }}>Database online. First-time administrator setup will appear automatically if needed.</p>}
        </div>
        <form onSubmit={submit} className="card p-5">
          <div className="mb-3">
            <div className="font-head font-semibold text-[15px]" style={{ color: "var(--text)" }}>{setup ? "Initial setup" : "Welcome back"}</div>
            <div className="text-[12px]" style={{ color: "var(--text-3)" }}>{setup ? "Create your first administrator account" : "Sign in to your analyst workspace"}</div>
          </div>
          {err && <div className="mb-3 text-[12px] px-3 py-2 rounded" style={{ background: "rgba(248,113,113,.12)", color: "#F87171", border: "1px solid rgba(248,113,113,.3)" }} data-testid="login-error">{err}</div>}
          {setup && <div className="mb-3 space-y-2"><input className="inp w-full" type="email" required placeholder="Administrator email" value={setupEmail} onChange={e => setSetupEmail(e.target.value)} /><input className="inp w-full" required placeholder="Administrator username" value={setupUsername} onChange={e => setSetupUsername(e.target.value)} /></div>}
          {!setup && <label className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-3)" }}>Email or username</label>}
          {!setup && <div className="relative mt-1 mb-3">
            <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-3)" }} />
            <input className="inp" style={{ paddingLeft: "2.5rem" }} autoComplete="username" type="text" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email" placeholder="Email or username" />
          </div>}
          <label className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-3)" }}>Password</label>
          <div className="relative mt-1 mb-4">
            <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-3)" }} />
            <input className="inp" style={{ paddingLeft: "2.5rem", paddingRight: "2.5rem" }} autoComplete={setup ? "new-password" : "current-password"} minLength={setup ? 12 : undefined} required type={show ? "text" : "password"} value={password}
              onChange={(e) => setPassword(e.target.value)} data-testid="login-password" />
            <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2" onClick={() => setShow(!show)} style={{ color: "var(--text-3)" }}>
              {show ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
          {setup && <p className="text-[11px] mb-3" style={{ color: "var(--text-3)" }}>Choose a unique password of at least 12 characters. Setup is available only before the first administrator is created.</p>}
          <button className="btn btn-primary w-full justify-center" disabled={busy} data-testid="login-submit">
            {busy ? "Please wait…" : setup ? "Create Administrator" : "Sign In"}
          </button>

        </form>
        <p className="text-center text-[11px] mt-4" style={{ color: "var(--text-3)" }}>
          Requires MongoDB Community Server running locally on port 27017.
        </p>
      </div>
    </div>
  );
}
