import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "@/App.css";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { WorkspaceProvider } from "@/context/WorkspaceContext";
import { Toaster } from "sonner";
import Layout from "@/components/Layout";
import AIAssistant from "@/components/AIAssistant";
import Login from "@/pages/Login";
import Overview from "@/pages/Overview";
import Events from "@/pages/Events";
import Alerts from "@/pages/Alerts";
import ThreatHunting from "@/pages/ThreatHunting";
import DetectionRules from "@/pages/DetectionRules";
import Sources from "@/pages/Sources";
import Investigations from "@/pages/Investigations";
import Reports from "@/pages/Reports";
import Settings from "@/pages/Settings";
import Mitre from "@/pages/Mitre";
import ThreatIntel from "@/pages/ThreatIntel";
import Playbooks from "@/pages/Playbooks";
import Graph from "@/pages/Graph";
import Replay from "@/pages/Replay";
import Observatory from "@/pages/Observatory";

function Shell() {
  const { user } = useAuth();
  if (user === null) return <div className="min-h-screen grid place-items-center" style={{ background: "var(--bg)", color: "var(--text-3)" }}>Loading SentinelLab…</div>;
  if (!user) return <Login />;
  return (
    <WorkspaceProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/events" element={<Events />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/hunting" element={<ThreatHunting />} />
          <Route path="/rules" element={<DetectionRules />} />
          <Route path="/mitre" element={<Mitre />} />
          <Route path="/replay" element={<Replay />} />
          <Route path="/observatory" element={<Observatory />} />
          <Route path="/graph" element={<Graph />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/intel" element={<ThreatIntel />} />
          <Route path="/investigations" element={<Investigations />} />
          <Route path="/playbooks" element={<Playbooks />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </Layout>
      <AIAssistant />
    </WorkspaceProvider>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Shell />
          <Toaster theme="dark" position="top-right" richColors />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
