import { useEffect, useState } from "react";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../context/AuthContext";
import { can } from "../utils/rbac";

const SEVERITY_COLOR = { low: "#22c55e", medium: "#f59e0b", high: "#ef4444" };

export default function Historique() {
  const { call, loading } = useApi();
  const { user } = useAuth();
  const isAdmin = can(user.role, "manage_users");

  const [data, setData]         = useState(null);
  const [page, setPage]         = useState(1);
  const [filters, setFilters]   = useState({ date: "", severite: "", ip: "", type_attaque: "" });
  const [applied, setApplied]   = useState({});

  const fetchData = (p = page, f = applied) => {
    const params = new URLSearchParams({ page: p, limite: 15 });
    if (f.date)         params.set("date", f.date);
    if (f.severite)     params.set("severite", f.severite);
    if (f.ip)           params.set("ip", f.ip);
    if (f.type_attaque) params.set("type_attaque", f.type_attaque);
    call((api) => api.get(`/anomalies?${params}`)).then(setData);
  };

  useEffect(() => { fetchData(); }, [page]);

  const applyFilters = () => { setApplied({ ...filters }); setPage(1); fetchData(1, filters); };
  const resetFilters = () => { const e = {}; setFilters({ date: "", severite: "", ip: "", type_attaque: "" }); setApplied(e); setPage(1); fetchData(1, e); };

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.h1}>Historique des anomalies</h1>
        {data && <span style={styles.total}>{data.total} anomalie(s) au total</span>}
      </div>

      {/* Filtres */}
      <div style={styles.filterBar}>
        <input
          style={styles.input}
          placeholder="Date (ex: 2026-06)"
          value={filters.date}
          onChange={(e) => setFilters((f) => ({ ...f, date: e.target.value }))}
        />
        <select
          style={styles.select}
          value={filters.severite}
          onChange={(e) => setFilters((f) => ({ ...f, severite: e.target.value }))}
        >
          <option value="">Toutes sévérités</option>
          <option value="low">Faible</option>
          <option value="medium">Moyenne</option>
          <option value="high">Élevée</option>
        </select>
        {isAdmin && (
          <>
            <input
              style={styles.input}
              placeholder="IP source"
              value={filters.ip}
              onChange={(e) => setFilters((f) => ({ ...f, ip: e.target.value }))}
            />
            <input
              style={styles.input}
              placeholder="Type d'attaque"
              value={filters.type_attaque}
              onChange={(e) => setFilters((f) => ({ ...f, type_attaque: e.target.value }))}
            />
          </>
        )}
        <button style={styles.btnPrimary} onClick={applyFilters}>Filtrer</button>
        <button style={styles.btnSecondary} onClick={resetFilters}>Réinitialiser</button>
      </div>

      {loading && <div style={styles.loading}>Chargement…</div>}

      {data && (
        <>
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {["#", "Date", "IP source", "Type d'attaque", "Sévérité", "Score MSE", "Préd."].map((h) => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.anomalies.length === 0 ? (
                  <tr><td colSpan={7} style={styles.empty}>Aucun résultat</td></tr>
                ) : (
                  data.anomalies.map((row) => (
                    <tr key={row.id} style={styles.row}>
                      <td style={styles.td}>{row.id}</td>
                      <td style={styles.td}>{row.date}</td>
                      <td style={{ ...styles.td, fontFamily: "monospace", color: "#f87171" }}>{row.ip_source ?? "—"}</td>
                      <td style={styles.td}>{row.type_attaque ?? "—"}</td>
                      <td style={styles.td}>
                        <span style={{ ...styles.badge, background: SEVERITY_COLOR[row.severite] + "22", color: SEVERITY_COLOR[row.severite] }}>
                          {row.severite}
                        </span>
                      </td>
                      <td style={{ ...styles.td, fontFamily: "monospace" }}>{row.score_anomalie.toFixed(4)}</td>
                      <td style={styles.td}>
                        <span style={{ color: row.prediction === 1 ? "#ef4444" : "#22c55e" }}>
                          {row.prediction === 1 ? "Attaque" : "Normal"}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div style={styles.pagination}>
            <button style={styles.pageBtn} disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>◀ Préc.</button>
            <span style={styles.pageInfo}>Page {data.page} / {data.nb_pages}</span>
            <button style={styles.pageBtn} disabled={page >= data.nb_pages} onClick={() => setPage((p) => p + 1)}>Suiv. ▶</button>
          </div>
        </>
      )}
    </div>
  );
}

const styles = {
  header: { display: "flex", alignItems: "baseline", gap: 16, marginBottom: 20 },
  h1: { fontSize: 24, fontWeight: 700, color: "#e2e8f0", margin: 0 },
  total: { fontSize: 14, color: "#64748b" },
  filterBar: { display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" },
  input: { background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "9px 12px", color: "#e2e8f0", fontSize: 13 },
  select: { background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "9px 12px", color: "#e2e8f0", fontSize: 13 },
  btnPrimary: { background: "#6366f1", color: "#fff", border: "none", borderRadius: 8, padding: "9px 18px", cursor: "pointer", fontWeight: 600, fontSize: 13 },
  btnSecondary: { background: "#334155", color: "#e2e8f0", border: "none", borderRadius: 8, padding: "9px 18px", cursor: "pointer", fontSize: 13 },
  loading: { color: "#64748b", textAlign: "center", padding: 40 },
  tableWrap: { background: "#1e293b", borderRadius: 12, border: "1px solid #334155", overflow: "auto" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { textAlign: "left", padding: "12px 16px", fontSize: 12, color: "#64748b", textTransform: "uppercase", borderBottom: "1px solid #334155", whiteSpace: "nowrap" },
  td: { padding: "11px 16px", fontSize: 13, color: "#cbd5e1", borderBottom: "1px solid #0f172a" },
  row: { transition: "background .1s" },
  badge: { padding: "3px 8px", borderRadius: 20, fontSize: 12, fontWeight: 600 },
  empty: { textAlign: "center", color: "#64748b", padding: "40px 0" },
  pagination: { display: "flex", justifyContent: "center", alignItems: "center", gap: 16, marginTop: 20 },
  pageBtn: { background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", borderRadius: 8, padding: "8px 16px", cursor: "pointer", fontSize: 13 },
  pageInfo: { color: "#94a3b8", fontSize: 14 },
};
