import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { Capabilities } from "../types";

export function useCapabilities() {
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [offline, setOffline] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setCaps(await api.capabilities());
      setOffline(false);
    } catch (e) {
      setOffline(e instanceof ApiError ? e.kind === "offline" || e.kind === "http" : true);
      setCaps(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);
  return { caps, offline, loading, refresh };
}
