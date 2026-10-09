import { useEffect, useState, useRef } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  Shield, LayoutDashboard, ScrollText, Crosshair, Bell, FileSearch, Cpu,
  Radio, FolderSearch, FileBarChart, Settings as SettingsIcon, Search,
  Palette, LogOut, ChevronDown, Activity, Bot, Check,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useTheme, THEMES } from "@/context/ThemeContext";
import { useWorkspace } from "@/context/WorkspaceContext";
import client from "@/lib/api";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/events", label: "Events Explorer", icon: ScrollText },
  { to: "/hunting", label: "Threat Hunting", icon: Crosshair },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/rules", label: "Detection Rules", icon: Cpu },
  { to: "/sources", label: "Sources & Ingestion", icon: Radio },
  { to: "/investigations", label: "Investigations", icon: FolderSearch },
  { to: "/reports", label: "Reports", icon: FileBarChart },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];
const RANGES = ["15m", "1h", "24h", "7d", "30d"];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const { workspaces, active, current, switchWs, range, setRange } = useWorkspace();
  const nav = useNavigate();
  const [unread, setUnread] = useState(0);
  const [notifs, setNotifs] = useState([]);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState(null);
  const [open, setOpen] = useState("");

  const loadNotifs = () => client.get("/notifications").then(({ data }) => {
    setUnread(data.unread); setNotifs(data.notifications);
  }).catch(() => {});

  useEffect(() => { loadNotifs(); const i = setInterval(loadNotifs, 20000); return () => clearInterval(i); }, [active]);

  const doSearch = async (v) => {
    setSearch(v);
    if (v.length < 2) { setResults(null); return; }
    try { const { data } = await client.get(`/search?q=${encodeURIComponent(v)}`); setResults(data); }
    catch { setResults(null); }
  };

  const toggle = (k) => setOpen(open === k ? "" : k);

  return (
    <div className="min-h-screen flex" style={{ background: "var(--bg)" }}>
      {/* sidebar */}
      <aside className="w-60 shrink-0 surface border-r flex flex-col fixed h-screen z-30" data-testid="sidebar">
        <div className="h-14 flex items-center gap-2.5 px-4 border-b">
          <div className="grid place-items-center w-8 h-8 rounded-md" style={{ background: "color-mix(in srgb, var(--cyan) 18%, transparent)", border: "1px solid var(--cyan)" }}>
            <Shield size={17} style={{ color: "var(--cyan)" }} />
          </div>
          <div>
            <div className="font-head font-bold text-[15px] leading-none" style={{ color: "var(--text)" }}>SentinelLab</div>
            <div className="text-[10px] mt-0.5" style={{ color: "var(--text-3)" }}>Security Operations Center</div>
          </div>
        </div>
        <div className="px-3 py-2.5 border-b">
          <div className="pill w-full justify-start" data-testid="soc-status">
            <span className="status-dot" style={{ background: "#22c55e" }} />
            <span style={{ color: "var(--text-2)" }}>System Health: Operational</span>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto px-2.5 py-3 space-y-0.5">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
              data-testid={`nav-${n.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
              <n.icon size={16} /> {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-3 py-2.5 border-t flex items-center gap-2">
          <div className="pill flex-1" style={{ color: "var(--cyan)" }}>
            <Activity size={12} /> Live Telemetry
          </div>
        </div>
      </aside>

      {/* main */}
      <div className="flex-1 ml-60 flex flex-col min-w-0">
        <header className="h-14 sticky top-0 z-20 border-b flex items-center gap-3 px-4 backdrop-blur-md"
          style={{ background: "color-mix(in srgb, var(--bg) 82%, transparent)" }} data-testid="topbar">
          {/* search */}
          <div className="relative flex-1 max-w-md">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-3)" }} />
            <input className="inp pl-8 font-mono text-[12.5px]" placeholder="Search events, alerts, hosts, IPs…"
              value={search} onChange={(e) => doSearch(e.target.value)}
              onBlur={() => setTimeout(() => setResults(null), 200)} data-testid="global-search" />
            {results && (
              <div className="absolute top-11 left-0 right-0 card p-2 max-h-96 overflow-auto z-50 fade-in" data-testid="search-results">
                {["alerts", "events", "investigations", "rules", "assets"].map((cat) => (results[cat]?.length ? (
                  <div key={cat} className="mb-2">
                    <div className="text-[10px] uppercase px-2 py-1" style={{ color: "var(--text-3)" }}>{cat}</div>
                    {results[cat].map((r, i) => (
                      <div key={i} className="row-hover px-2 py-1.5 rounded text-[12.5px] cursor-pointer font-mono"
                        onMouseDown={() => {
                          const route = { alerts: "/alerts", events: "/events", investigations: "/investigations", rules: "/rules", assets: "/events" }[cat];
                          nav(route); setResults(null); setSearch("");
                        }}>
                        {r.title || r.name || r.host || r.src_ip || r.id}
                      </div>
                    ))}
                  </div>
                ) : null))}
                {!["alerts", "events", "investigations", "rules", "assets"].some((c) => results[c]?.length) &&
                  <div className="px-2 py-3 text-[12px]" style={{ color: "var(--text-3)" }}>No matches</div>}
              </div>
            )}
          </div>

          {/* workspace */}
          <Dropdown open={open === "ws"} onToggle={() => toggle("ws")} testId="workspace-selector"
            trigger={<><span style={{ color: current?.is_demo ? "var(--cyan)" : "var(--text-2)" }}>{current?.name || "Workspace"}</span><ChevronDown size={13} /></>}>
            {workspaces.map((w) => (
              <button key={w.id} className="dd-item" onClick={() => { switchWs(w.id); setOpen(""); window.location.reload(); }}
                data-testid={`ws-${w.id}`}>
                {w.id === active && <Check size={13} />} <span className={w.id === active ? "" : "ml-[18px]"}>{w.name}</span>
              </button>
            ))}
          </Dropdown>

          {/* time range */}
          <Dropdown open={open === "tr"} onToggle={() => toggle("tr")} testId="time-range"
            trigger={<><span className="font-mono">Last {range}</span><ChevronDown size={13} /></>}>
            {RANGES.map((r) => (
              <button key={r} className="dd-item" onClick={() => { setRange(r); setOpen(""); window.dispatchEvent(new Event("sl-range")); }}
                data-testid={`range-${r}`}>Last {r}</button>
            ))}
          </Dropdown>

          {/* notifications */}
          <div className="relative">
            <button className="btn btn-sm relative" onClick={() => { toggle("nt"); client.post("/notifications/read").then(loadNotifs); }} data-testid="notif-bell">
              <Bell size={15} />
              {unread > 0 && <span className="absolute -top-1.5 -right-1.5 text-[9px] font-bold rounded-full px-1.5 py-0.5" style={{ background: "#F87171", color: "#1a0505" }}>{unread}</span>}
            </button>
            {open === "nt" && (
              <div className="absolute right-0 top-10 card p-2 w-80 max-h-96 overflow-auto z-50 fade-in" data-testid="notif-panel">
                <div className="text-[10px] uppercase px-2 py-1" style={{ color: "var(--text-3)" }}>Notifications</div>
                {notifs.length ? notifs.map((n) => (
                  <div key={n.id} className="px-2 py-2 rounded row-hover text-[12px] border-b" style={{ color: "var(--text-2)" }}>
                    {n.text}
                  </div>
                )) : <div className="px-2 py-3 text-[12px]" style={{ color: "var(--text-3)" }}>No notifications</div>}
              </div>
            )}
          </div>

          {/* theme */}
          <Dropdown open={open === "th"} onToggle={() => toggle("th")} testId="theme-switcher" icon={<Palette size={15} />}>
            {THEMES.map((t) => (
              <button key={t.id} className="dd-item" onClick={() => { setTheme(t.id); setOpen(""); }} data-testid={`theme-${t.id}`}>
                {theme === t.id && <Check size={13} />} <span className={theme === t.id ? "" : "ml-[18px]"}>{t.name}</span>
              </button>
            ))}
          </Dropdown>

          {/* user */}
          <Dropdown open={open === "usr"} onToggle={() => toggle("usr")} testId="user-menu"
            trigger={<><div className="w-6 h-6 rounded-full grid place-items-center text-[11px] font-bold" style={{ background: "var(--cyan)", color: "#04161c" }}>{(user?.name || "A")[0]}</div><ChevronDown size={13} /></>}>
            <div className="px-3 py-2 border-b">
              <div className="text-[13px] font-semibold" style={{ color: "var(--text)" }}>{user?.name}</div>
              <div className="text-[11px]" style={{ color: "var(--text-3)" }}>{user?.email}</div>
              <div className="pill mt-1.5" style={{ color: "var(--cyan)" }}>{user?.role?.replace(/_/g, " ")}</div>
            </div>
            <button className="dd-item" onClick={logout} data-testid="logout-btn"><LogOut size={13} /> Sign out</button>
          </Dropdown>
        </header>

        <main className="p-4 md:p-5 flex-1 min-w-0" data-testid="main-content">{children}</main>
      </div>
      <style>{`.dd-item{display:flex;align-items:center;gap:8px;width:100%;text-align:left;padding:7px 12px;font-size:12.5px;color:var(--text-2);border-radius:5px;cursor:pointer;background:none;border:none}.dd-item:hover{background:var(--hover);color:var(--text)}`}</style>
    </div>
  );
}

function Dropdown({ open, onToggle, trigger, children, testId, icon }) {
  const ref = useRef();
  return (
    <div className="relative" ref={ref}>
      <button className="btn btn-sm" onClick={onToggle} data-testid={testId}>{icon || trigger}</button>
      {open && <div className="absolute right-0 top-10 card p-1.5 min-w-[180px] z-50 fade-in">{children}</div>}
    </div>
  );
}
