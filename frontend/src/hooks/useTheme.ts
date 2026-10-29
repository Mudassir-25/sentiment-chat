import { useCallback, useEffect, useRef, useState } from "react";

export type ThemePref = "system" | "light" | "dark";
const KEY = "sc-theme";

function readPref(): ThemePref {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}
const systemDark = () => typeof matchMedia === "function" && matchMedia("(prefers-color-scheme: dark)").matches;

export function useTheme() {
  const [pref, setPrefState] = useState<ThemePref>(readPref);
  const [sysDark, setSysDark] = useState(systemDark);
  const resolved: "light" | "dark" = pref === "system" ? (sysDark ? "dark" : "light") : pref;

  useEffect(() => {
    if (typeof matchMedia !== "function") return;
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const on = (e: MediaQueryListEvent) => setSysDark(e.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);

  const first = useRef(true);
  useEffect(() => {
    const root = document.documentElement;
    const reduce = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
    let t: number | undefined;
    if (!first.current && !reduce) {
      // Short-lived class: colours/materials cross-fade only while the theme changes, never permanently.
      root.classList.add("theme-shift");
      t = window.setTimeout(() => root.classList.remove("theme-shift"), 420);
    }
    first.current = false;
    root.dataset.theme = resolved;
    return () => window.clearTimeout(t);
  }, [resolved]);

  const setPref = useCallback((p: ThemePref) => {
    setPrefState(p);
    try {
      if (p === "system") localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, p);
    } catch { /* storage unavailable */ }
  }, []);
  // An explicit toggle always stores an explicit choice, so the OS can no longer override it.
  const toggle = useCallback(() => setPref(resolved === "dark" ? "light" : "dark"), [resolved, setPref]);
  return { pref, resolved, setPref, toggle };
}
