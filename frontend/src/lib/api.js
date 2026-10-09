import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL;
export const API = `${BASE}/api`;

const client = axios.create({ baseURL: API, withCredentials: true });

client.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("sl_token");
  const ws = localStorage.getItem("sl_workspace");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  if (ws) cfg.headers["X-Workspace-Id"] = ws;
  return cfg;
});

export function apiErr(e) {
  const d = e?.response?.data?.detail;
  if (d == null) return e?.message || "Request failed";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join(" ");
  return typeof d?.msg === "string" ? d.msg : String(d);
}

export default client;
