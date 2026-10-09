import { createContext, useContext, useEffect, useState } from "react";
import client from "@/lib/api";

const WsCtx = createContext(null);
export const useWorkspace = () => useContext(WsCtx);

export function WorkspaceProvider({ children }) {
  const [workspaces, setWorkspaces] = useState([]);
  const [active, setActive] = useState(localStorage.getItem("sl_workspace") || "");
  const [range, setRange] = useState("24h");

  useEffect(() => {
    client.get("/workspaces").then(({ data }) => {
      setWorkspaces(data.workspaces || []);
      if (!active && data.workspaces?.length) switchWs(data.workspaces[0].id);
    }).catch(() => {});
  }, []);

  const switchWs = (id) => {
    localStorage.setItem("sl_workspace", id);
    setActive(id);
    client.put("/me/workspace", { workspace_id: id }).catch(() => {});
  };

  const current = workspaces.find((w) => w.id === active);
  return (
    <WsCtx.Provider value={{ workspaces, active, current, switchWs, range, setRange }}>
      {children}
    </WsCtx.Provider>
  );
}
