import { createContext, useContext, useState, useCallback } from "react";
import { getHomePage } from "../utils/rbac";

// Comptes de démonstration (en prod : remplacer par un vrai appel auth)
const DEMO_USERS = [
  { id: 1, username: "admin",      password: "admin123",   role: "admin",          name: "Admin Système" },
  { id: 2, username: "direction",  password: "top123",     role: "top_management", name: "Direction Générale" },
  { id: 3, username: "analyste",   password: "user123",    role: "user",           name: "Analyste Réseau" },
];

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("auth_user");
    return saved ? JSON.parse(saved) : null;
  });

  const login = useCallback((username, password) => {
    const found = DEMO_USERS.find(
      (u) => u.username === username && u.password === password
    );
    if (!found) throw new Error("Identifiants incorrects");
    const { password: _, ...safe } = found;
    setUser(safe);
    localStorage.setItem("auth_user", JSON.stringify(safe));
    return safe;
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem("auth_user");
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
