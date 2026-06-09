import { useEffect, useState } from "react";
import { useApi } from "../hooks/useApi";
import SeveriteDonut from "../components/charts/SeveriteDonut";
import AnomaliesParJour from "../components/charts/AnomaliesParJour";
import TopBar from "../components/charts/TopBar";
import StatCard from "../components/StatCard";

export default function Stats() {
  const { call, loading } = useApi();
  const [stats, setStats] = useState(null);

  useEffect(() => { call((api) => api.get("/stats")).then(setStats); }, []);

  return (
    <div>
      <h1 style={styles.h1}>Statistiques globales</h1>

      {loading && <div style={styles.loading}>Chargement…</div>}

      {stats && (
        <>
          <div style={styles.grid3}>
            <StatCard title="Score moyen" value={stats.score_moyen.toFixed(4)} icon="⚖️" color="#6366f1" />
            <StatCard title="Score max"   value={stats.score_max.toFixed(4)}   icon="🔺" color="#ef4444" />
            <StatCard title="Score min"   value={stats.score_min.toFixed(4)}   icon="🔻" color="#22c55e" />
          </div>

          <div style={styles.grid2}>
            <div style={styles.card}>
              <h2 style={styles.cardTitle}>Répartition par sévérité</h2>
              <SeveriteDonut {...stats} />
            </div>
            <div style={styles.card}>
              <h2 style={styles.cardTitle}>Anomalies 7 derniers jours</h2>
              <AnomaliesParJour data={stats.anomalies_par_jour} />
            </div>
          </div>

          <div style={styles.grid2}>
            <div style={styles.card}>
              <h2 style={styles.cardTitle}>Top IPs suspectes</h2>
              {stats.top_ips.length === 0 ? (
                <p style={styles.empty}>Aucune IP enregistrée</p>
              ) : (
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Rang</th>
                      <th style={styles.th}>Adresse IP</th>
                      <th style={styles.th}>Attaques</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.top_ips.map((row, i) => (
                      <tr key={row.ip}>
                        <td style={styles.td}>#{i + 1}</td>
                        <td style={{ ...styles.td, fontFamily: "monospace", color: "#f87171" }}>{row.ip}</td>
                        <td style={styles.td}>{row.nb_attaques}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div style={styles.card}>
              <h2 style={styles.cardTitle}>Top types d'attaques</h2>
              <TopBar data={stats.top_types} xKey="type" yKey="nb_occurrences" color="#f59e0b" label="Occurrences" />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

const styles = {
  h1: { fontSize: 24, fontWeight: 700, color: "#e2e8f0", marginBottom: 24 },
  loading: { color: "#64748b", textAlign: "center", padding: 40 },
  grid3: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 16 },
  grid2: { display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 16 },
  card: { background: "#1e293b", borderRadius: 12, padding: "20px 24px", border: "1px solid #334155" },
  cardTitle: { fontSize: 15, fontWeight: 600, color: "#e2e8f0", margin: "0 0 16px" },
  empty: { color: "#64748b", textAlign: "center", padding: 20 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { textAlign: "left", padding: "8px 12px", fontSize: 12, color: "#64748b", textTransform: "uppercase", borderBottom: "1px solid #334155" },
  td: { padding: "10px 12px", fontSize: 14, color: "#cbd5e1", borderBottom: "1px solid #1e293b" },
};
