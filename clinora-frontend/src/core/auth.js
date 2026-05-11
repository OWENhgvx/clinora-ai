import { useCallback, useEffect, useState } from "react";
import { BACKEND } from "./api";

export function useAuth() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(
    () => localStorage.getItem("mc_token") || "",
  );
  const [ready, setReady] = useState(false);

  const logout = useCallback(() => {
    setToken("");
    setUser(null);
    localStorage.removeItem("mc_token");
  }, []);

  const me = useCallback(async () => {
    try {
      const r = await fetch(BACKEND + "/api/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.ok) setUser(await r.json());
      else logout();
    } catch {
      logout();
    }
    setReady(true);
  }, [token, logout]);

  useEffect(() => {
    token ? me() : setReady(true);
  }, [token, me]);

  const login = (t, u) => {
    setToken(t);
    setUser(u);
    localStorage.setItem("mc_token", t);
  };

  return { user, token, ready, login, logout };
}
