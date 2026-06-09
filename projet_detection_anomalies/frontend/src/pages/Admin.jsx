import { useState } from "react";
import { useAuth } from "../context/AuthContext";

const INITIAL_USERS = [
  { id: 1, username: "admin",     name: "Admin Système",      role: "admin",          active: true  },
  { id: 2, username: "direction", name: "Direction Générale", role: "top_management", active: true  },
  { id: 3, username: "analyste",  name: "Analyste Réseau",    role: "user",           active: true  },
  { id: 4, username: "analyste2", name: "Analyste SOC",       role: "user",           active: false },
];

const ROLE_LABELS  = { admin: "Admin", top_management: "Top Management", user: "Analyste" };
const ROLE_COLORS  = { admin: "#ef4444", top_management: "#8b5cf6", user: "#3b82f6" };

export default function Admin() {
  const { user: me } = useAuth();
  const [users, setUsers]       = useState(INITIAL_USERS);
  const [editId, setEditId]     = useState(null);
  const [showAdd, setShowAdd]   = useState(false);
  const [newUser, setNewUser]   = useState({ username: "", name: "", role: "user", password: "" });
  const [addError, setAddError] = useState("");

  const toggleActive = (id) => {
    if (id === me.id) return; // ne peut pas se désactiver soi-même
    setUsers((u) => u.map((u) => u.id === id ? { ...u, active: !u.active } : u));
  };

  const changeRole = (id, role) => {
    if (id === me.id) return;
    setUsers((u) => u.map((u) => u.id === id ? { ...u, role } : u));
    setEditId(null);
  };

  const addUser = () => {
    if (!newUser.username.trim() || !newUser.name.trim() || !newUser.password.trim()) {
      setAddError("Tous les champs sont obligatoires"); return;
    }
    if (users.find((u) => u.username === newUser.username)) {
      setAddError("Ce nom d'utilisateur existe déjà"); return;
    }
    setUsers((u) => [...u, { ...newUser, id: Date.now(), active: true }]);
    setNewUser({ username: "", name: "", role: "user", password: "" });
    setShowAdd(false);
    setAddError("");
  };

  const stats = {
    total:   users.length,
    active:  users.filter((u) => u.active).length,
    admins:  users.filter((u) => u.role === "admin").length,
    mgmt:    users.filter((u) => u.role === "top_management").length,
    regular: users.filter((u) => u.role === "user").length,
  };

  return (
    <div>
      <h1 style={styles.h1}>Administration</h1>

      {/* Stats */}
      <div style={styles.grid4}>
        {[
          { label: "Utilisateurs", val: stats.total,   color: "#6366f1" },
          { label: "Actifs",       val: stats.active,  color: "#22c55e" },
          { label: "Admins",       val: stats.admins,  color: "#ef4444" },
          { label: "Analystes",    val: stats.regular, color: "#3b82f6" },
        ].map((s) => (
          <div key={s.label} style={styles.kpi}>
            <div style={{ ...styles.kpiVal, color: s.color }}>{s.val}</div>
            <div style={styles.kpiLabel}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Gestion utilisateurs */}
      <div style={styles.card}>
        <div style={styles.cardHeader}>
          <h2 style={styles.cardTitle}>Gestion des utilisateurs</h2>
          <button style={styles.btnAdd} onClick={() => setShowAdd((v) => !v)}>
            {showAdd ? "Annuler" : "+ Ajouter"}
          </button>
        </div>

        {showAdd && (
          <div style={styles.addForm}>
            <input style={styles.input} placeholder="Nom d'utilisateur" value={newUser.username} onChange={(e) => setNewUser((u) => ({ ...u, username: e.target.value }))} />
            <input style={styles.input} placeholder="Nom complet" value={newUser.name} onChange={(e) => setNewUser((u) => ({ ...u, name: e.target.value }))} />
            <input style={styles.input} type="password" placeholder="Mot de passe" value={newUser.password} onChange={(e) => setNewUser((u) => ({ ...u, password: e.target.value }))} />
            <select style={styles.select} value={newUser.role} onChange={(e) => setNewUser((u) => ({ ...u, role: e.target.value }))}>
              <option value="user">Analyste</option>
              <option value="top_management">Top Management</option>
              <option value="admin">Admin</option>
            </select>
            <button style={styles.btnPrimary} onClick={addUser}>Créer</button>
            {addError && <div style={styles.error}>{addError}</div>}
          </div>
        )}

        <table style={styles.table}>
          <thead>
            <tr>
              {["Utilisateur", "Nom", "Rôle", "Statut", "Actions"].map((h) => (
                <th key={h} style={styles.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td style={{ ...styles.td, fontFamily: "monospace", color: "#94a3b8" }}>{u.username}</td>
                <td style={styles.td}>{u.name} {u.id === me.id && <span style={styles.meTag}>vous</span>}</td>
                <td style={styles.td}>
                  {editId === u.id && u.id !== me.id ? (
                    <select
                      style={{ ...styles.select, fontSize: 12, padding: "4px 8px" }}
                      value={u.role}
                      onChange={(e) => changeRole(u.id, e.target.value)}
                      onBlur={() => setEditId(null)}
                      autoFocus
                    >
                      <option value="user">Analyste</option>
                      <option value="top_management">Top Management</option>
                      <option value="admin">Admin</option>
                    </select>
                  ) : (
                    <span
                      style={{ ...styles.roleBadge, background: ROLE_COLORS[u.role] + "22", color: ROLE_COLORS[u.role], cursor: u.id !== me.id ? "pointer" : "default" }}
                      onClick={() => u.id !== me.id && setEditId(u.id)}
                      title={u.id !== me.id ? "Cliquer pour modifier" : ""}
                    >
                      {ROLE_LABELS[u.role]}
                    </span>
                  )}
                </td>
                <td style={styles.td}>
                  <span style={{ color: u.active ? "#22c55e" : "#64748b" }}>
                    {u.active ? "● Actif" : "○ Inactif"}
                  </span>
                </td>
                <td style={styles.td}>
                  <button
                    style={{ ...styles.actionBtn, opacity: u.id === me.id ? 0.4 : 1 }}
                    disabled={u.id === me.id}
                    onClick={() => toggleActive(u.id)}
                  >
                    {u.active ? "Désactiver" : "Activer"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Info RBAC */}
      <div style={styles.card}>
        <h2 style={styles.cardTitle}>Matrice des permissions (RBAC)</h2>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Permission</th>
              <th style={styles.th}>Admin</th>
              <th style={styles.th}>Top Management</th>
              <th style={styles.th}>Analyste</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["Dashboard",        true, true,  false],
              ["Statistiques",     true, true,  false],
              ["Historique",       true, true,  true ],
              ["Prédiction",       true, false, true ],
              ["Batch",            true, false, true ],
              ["Analyser fichier", true, false, true ],
              ["Administration",   true, false, false],
            ].map(([perm, admin, mgmt, user]) => (
              <tr key={perm}>
                <td style={styles.td}>{perm}</td>
                {[admin, mgmt, user].map((v, i) => (
                  <td key={i} style={{ ...styles.td, textAlign: "center" }}>
                    {v ? <span style={{ color: "#22c55e", fontSize: 18 }}>✓</span> : <span style={{ color: "#334155", fontSize: 18 }}>—</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const styles = {
  h1: { fontSize: 24, fontWeight: 700, color: "#e2e8f0", marginBottom: 24 },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 20 },
  kpi: { background: "#1e293b", borderRadius: 10, padding: "18px", textAlign: "center", border: "1px solid #334155" },
  kpiVal: { fontSize: 28, fontWeight: 700 },
  kpiLabel: { fontSize: 13, color: "#64748b", marginTop: 4 },
  card: { background: "#1e293b", borderRadius: 12, padding: "20px 24px", border: "1px solid #334155", marginBottom: 16 },
  cardHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  cardTitle: { fontSize: 16, fontWeight: 600, color: "#e2e8f0", margin: 0 },
  btnAdd: { background: "#6366f1", color: "#fff", border: "none", borderRadius: 8, padding: "8px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600 },
  addForm: { display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16, padding: "14px", background: "#0f172a", borderRadius: 8 },
  input: { background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "8px 12px", color: "#e2e8f0", fontSize: 13 },
  select: { background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "8px 12px", color: "#e2e8f0", fontSize: 13 },
  btnPrimary: { background: "#6366f1", color: "#fff", border: "none", borderRadius: 8, padding: "8px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600 },
  error: { color: "#ef4444", fontSize: 13 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { textAlign: "left", padding: "10px 14px", fontSize: 12, color: "#64748b", textTransform: "uppercase", borderBottom: "1px solid #334155" },
  td: { padding: "11px 14px", fontSize: 13, color: "#cbd5e1", borderBottom: "1px solid #0f172a" },
  roleBadge: { padding: "3px 10px", borderRadius: 20, fontSize: 12, fontWeight: 600 },
  actionBtn: { background: "#334155", border: "none", color: "#e2e8f0", borderRadius: 6, padding: "5px 12px", cursor: "pointer", fontSize: 12 },
  meTag: { background: "#6366f133", color: "#6366f1", fontSize: 10, padding: "2px 6px", borderRadius: 20, marginLeft: 6 },
};
