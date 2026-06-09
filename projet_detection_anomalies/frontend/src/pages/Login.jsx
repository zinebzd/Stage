import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getHomePage } from "../utils/rbac";

const DEMO_HINTS = [
  { role: "Admin",          user: "admin",     pass: "admin123" },
  { role: "Top Management", user: "direction", pass: "top123"   },
  { role: "Analyste",       user: "analyste",  pass: "user123"  },
];

export default function Login() {
  const { login } = useAuth();
  const navigate  = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");
    try {
      const user = login(username, password);
      navigate(getHomePage(user.role), { replace: true });
    } catch (err) {
      setError(err.message);
    }
  };

  const fillDemo = (u, p) => { setUsername(u); setPassword(p); };

  return (
    <div style={styles.root}>
      <div style={styles.card}>
        <div style={styles.logo}>🛡️</div>
        <h1 style={styles.title}>AnomalyNet</h1>
        <p style={styles.sub}>Plateforme de détection d'anomalies réseau</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            style={styles.input}
            placeholder="Nom d'utilisateur"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
          />
          <input
            style={styles.input}
            type="password"
            placeholder="Mot de passe"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <div style={styles.error}>{error}</div>}
          <button style={styles.btn} type="submit">Se connecter</button>
        </form>

        <div style={styles.hints}>
          <div style={styles.hintsTitle}>Comptes de démonstration</div>
          {DEMO_HINTS.map((h) => (
            <button
              key={h.role}
              style={styles.hintBtn}
              type="button"
              onClick={() => fillDemo(h.user, h.pass)}
            >
              <span style={styles.hintRole}>{h.role}</span>
              <span style={styles.hintCreds}>{h.user} / {h.pass}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles = {
  root: { minHeight: "100vh", background: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Inter', sans-serif" },
  card: { background: "#1e293b", borderRadius: 16, padding: "40px 36px", width: 380, border: "1px solid #334155" },
  logo: { fontSize: 48, textAlign: "center" },
  title: { textAlign: "center", color: "#e2e8f0", margin: "8px 0 4px", fontSize: 24, fontWeight: 700 },
  sub: { textAlign: "center", color: "#64748b", fontSize: 13, marginBottom: 28 },
  form: { display: "flex", flexDirection: "column", gap: 12 },
  input: { background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "11px 14px", color: "#e2e8f0", fontSize: 14, outline: "none" },
  error: { color: "#ef4444", fontSize: 13, textAlign: "center" },
  btn: { background: "#6366f1", color: "#fff", border: "none", borderRadius: 8, padding: "12px", fontSize: 14, fontWeight: 600, cursor: "pointer", marginTop: 4 },
  hints: { marginTop: 28, borderTop: "1px solid #334155", paddingTop: 20 },
  hintsTitle: { fontSize: 12, color: "#64748b", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1 },
  hintBtn: { display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%", background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "9px 12px", marginBottom: 8, cursor: "pointer" },
  hintRole: { color: "#e2e8f0", fontSize: 13, fontWeight: 600 },
  hintCreds: { color: "#64748b", fontSize: 12 },
};
