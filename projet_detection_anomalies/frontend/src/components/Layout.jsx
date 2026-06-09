import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getNavItems } from "../utils/rbac";

const ROLE_BADGE = {
  admin:          { label: "Admin",          color: "#ef4444" },
  top_management: { label: "Top Management", color: "#8b5cf6" },
  user:           { label: "Analyste",       color: "#3b82f6" },
};

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const navItems = getNavItems(user.role);
  const badge = ROLE_BADGE[user.role];

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div style={styles.root}>
      {/* Sidebar */}
      <aside style={{ ...styles.sidebar, width: collapsed ? 64 : 220 }}>
        <div style={styles.sidebarHeader}>
          {!collapsed && (
            <div>
              <div style={styles.logo}>🛡️ AnomalyNet</div>
              <div style={styles.logoSub}>Détection réseau</div>
            </div>
          )}
          <button style={styles.collapseBtn} onClick={() => setCollapsed((v) => !v)}>
            {collapsed ? "▶" : "◀"}
          </button>
        </div>

        <nav style={styles.nav}>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              style={({ isActive }) => ({
                ...styles.navItem,
                background: isActive ? "rgba(99,102,241,0.25)" : "transparent",
                borderLeft: isActive ? "3px solid #6366f1" : "3px solid transparent",
              })}
            >
              <span style={styles.navIcon}>{item.icon}</span>
              {!collapsed && <span style={styles.navLabel}>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        <div style={styles.sidebarFooter}>
          {!collapsed && (
            <div>
              <div style={styles.userName}>{user.name}</div>
              <div style={{ ...styles.roleBadge, background: badge.color }}>{badge.label}</div>
            </div>
          )}
          <button style={styles.logoutBtn} onClick={handleLogout} title="Déconnexion">
            🚪
          </button>
        </div>
      </aside>

      {/* Main */}
      <main style={styles.main}>
        {children}
      </main>
    </div>
  );
}

const styles = {
  root: { display: "flex", height: "100vh", background: "#0f172a", color: "#e2e8f0", fontFamily: "'Inter', sans-serif" },
  sidebar: { background: "#1e293b", display: "flex", flexDirection: "column", transition: "width .2s", flexShrink: 0, overflow: "hidden" },
  sidebarHeader: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "20px 12px 16px", borderBottom: "1px solid #334155" },
  logo: { fontSize: 16, fontWeight: 700, color: "#e2e8f0" },
  logoSub: { fontSize: 11, color: "#64748b", marginTop: 2 },
  collapseBtn: { background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: 12, padding: "4px 6px" },
  nav: { flex: 1, padding: "12px 0", overflowY: "auto" },
  navItem: { display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", textDecoration: "none", color: "#cbd5e1", fontSize: 14, transition: "background .15s" },
  navIcon: { fontSize: 18, flexShrink: 0 },
  navLabel: { whiteSpace: "nowrap" },
  sidebarFooter: { padding: "12px 14px", borderTop: "1px solid #334155", display: "flex", alignItems: "center", justifyContent: "space-between" },
  userName: { fontSize: 13, fontWeight: 600, color: "#e2e8f0" },
  roleBadge: { fontSize: 10, padding: "2px 7px", borderRadius: 20, color: "#fff", display: "inline-block", marginTop: 4 },
  logoutBtn: { background: "none", border: "none", cursor: "pointer", fontSize: 18, padding: 4 },
  main: { flex: 1, overflowY: "auto", padding: "28px 32px" },
};
