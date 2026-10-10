import { createContext, useContext, useEffect, useState, useCallback } from "react";
import client from "@/lib/api";

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null=checking, false=anon, obj=auth
  const [roles, setRoles] = useState({});

  const refresh = useCallback(async () => {
    const token = localStorage.getItem("sl_token");
    if (!token) { setUser(false); return; }
    try {
      const { data } = await client.get("/auth/me");
      setUser(data.user);
      setRoles(data.roles || {});
      if (!localStorage.getItem("sl_workspace"))
        localStorage.setItem("sl_workspace", data.user.default_org);
    } catch {
      localStorage.removeItem("sl_token");
      setUser(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const login = async (email, password) => {
    const { data } = await client.post("/auth/login", { email, password });
    localStorage.setItem("sl_token", data.access_token);
    localStorage.setItem("sl_workspace", data.user.default_org);
    setUser(data.user);
    await refresh();
    return data.user;
  };
  const register = async (email, password, name) => {
    const { data } = await client.post("/auth/register", { email, password, name });
    localStorage.setItem("sl_token", data.access_token);
    localStorage.setItem("sl_workspace", data.user.default_org);
    setUser(data.user);
    return data.user;
  };
  const logout = async () => {
    try { await client.post("/auth/logout"); } catch {}
    localStorage.removeItem("sl_token");
    setUser(false);
  };

  return (
    <AuthCtx.Provider value={{ user, roles, login, register, logout, refresh, setUser }}>
      {children}
    </AuthCtx.Provider>
  );
}
