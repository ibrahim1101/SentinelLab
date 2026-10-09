import { createContext, useContext, useEffect, useState } from "react";
import client from "@/lib/api";

const ThemeCtx = createContext(null);
export const useTheme = () => useContext(ThemeCtx);

export const THEMES = [
  { id: "obsidian_dark", name: "Obsidian Dark" },
  { id: "stealth_titanium", name: "Stealth Titanium" },
  { id: "light_professional", name: "Light Professional" },
  { id: "high_contrast", name: "High Contrast" },
];

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(localStorage.getItem("sl_theme") || "obsidian_dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("sl_theme", theme);
  }, [theme]);

  const change = (t) => {
    setTheme(t);
    client.put("/me/theme", { theme: t }).catch(() => {});
  };
  return <ThemeCtx.Provider value={{ theme, setTheme: change }}>{children}</ThemeCtx.Provider>;
}
