export default function StatCard({ title, value, sub, color = "#6366f1", icon }) {
  return (
    <div style={styles.card}>
      <div style={{ ...styles.icon, background: color + "22", color }}>{icon}</div>
      <div>
        <div style={styles.title}>{title}</div>
        <div style={{ ...styles.value, color }}>{value}</div>
        {sub && <div style={styles.sub}>{sub}</div>}
      </div>
    </div>
  );
}

const styles = {
  card: { background: "#1e293b", borderRadius: 12, padding: "20px 24px", display: "flex", alignItems: "center", gap: 16, border: "1px solid #334155" },
  icon: { fontSize: 28, width: 52, height: 52, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 },
  title: { fontSize: 13, color: "#94a3b8", marginBottom: 4 },
  value: { fontSize: 26, fontWeight: 700 },
  sub: { fontSize: 12, color: "#64748b", marginTop: 2 },
};
