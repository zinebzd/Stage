import { useState } from "react";
import { useApi } from "../hooks/useApi";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

const SEVERITY_COLOR = { low: "#22c55e", medium: "#f59e0b", high: "#ef4444" };

export default function Batch() {
  const { call, loading, error } = useApi();
  const [raw, setRaw]     = useState("");
  const [result, setResult] = useState(null);
  const [parseError, setParseError] = useState("");

  const parseLines = () => {
    const lines = raw.trim().split("\n").filter(Boolean);
    const parsed = [];
    for (let i = 0; i < lines.length; i++) {
      const vals = lines[i].split(/[\s,;]+/).filter(Boolean).map(Number);
      if (vals.some(isNaN)) { setParseError(`Ligne ${i + 1} : valeurs non numériques`); return null; }
      if (vals.length !== 44) { setParseError(`Ligne ${i + 1} : ${vals.length} features reçues, 44 attendues`); return null; }
      parsed.push({ features: vals });
    }
    setParseError("");
    return parsed;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const flux = parseLines();
    if (!flux) return;
    const res = await call((api) => api.post("/predict/batch", { flux }));
    if (res) setResult(res);
  };

  const fillDemo = () => {
    const normal  = Array(44).fill(0).join(", ");
    const attaque = Array(44).fill(10).join(", ");
    setRaw([...Array(6).fill(normal), ...Array(4).fill(attaque)].join("\n"));
  };

  // Données pour le mini chart
  const severiteData = result
    ? [
        { name: "Normal",  value: result.nb_flux - result.nb_attaques, color: "#22c55e" },
        { name: "Attaque", value: result.nb_attaques,                  color: "#ef4444" },
      ]
    : [];

  return (
    <div>
      <h1 style={styles.h1}>Prédiction — batch</h1>

      <div style={styles.grid}>
        <div style={styles.card}>
          <div style={styles.demoRow}>
            <button style={styles.demoBtn} type="button" onClick={fillDemo}>Charger démo (10 flux)</button>
          </div>
          <form onSubmit={handleSubmit}>
            <label style={styles.label}>Un flux par ligne (44 features par ligne)</label>
            <textarea
              style={styles.textarea}
              rows={12}
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              placeholder={"0.0, 0.0, 1.2, …\n0.5, 0.3, 0.9, …"}
            />
            {parseError && <div style={styles.error}>{parseError}</div>}
            {error && <div style={styles.error}>{error}</div>}
            <button style={{ ...styles.btn, opacity: loading ? 0.6 : 1 }} type="submit" disabled={loading}>
              {loading ? "Analyse…" : "Analyser le batch"}
            </button>
          </form>
        </div>

        <div>
          {result && (
            <>
              <div style={styles.kpiRow}>
                <div style={styles.kpi}>
                  <div style={styles.kpiVal}>{result.nb_flux}</div>
                  <div style={styles.kpiLabel}>Flux analysés</div>
                </div>
                <div style={{ ...styles.kpi, borderColor: "#ef4444" }}>
                  <div style={{ ...styles.kpiVal, color: "#ef4444" }}>{result.nb_attaques}</div>
                  <div style={styles.kpiLabel}>Attaques détectées</div>
                </div>
                <div style={styles.kpi}>
                  <div style={styles.kpiVal}>{result.taux_attaques}%</div>
                  <div style={styles.kpiLabel}>Taux d'attaque</div>
                </div>
              </div>

              <div style={styles.card}>
                <h2 style={styles.cardTitle}>Répartition normal / attaque</h2>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={severiteData}>
                    <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 13 }} />
                    <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
                    <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }} />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {severiteData.map((d) => <Cell key={d.name} fill={d.color} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div style={{ ...styles.card, marginTop: 12 }}>
                <h2 style={styles.cardTitle}>Détail par flux</h2>
                <div style={styles.tableWrap}>
                  <table style={styles.table}>
                    <thead>
                      <tr>
                        {["Flux", "Score MSE", "Sévérité", "Résultat"].map((h) => <th key={h} style={styles.th}>{h}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {result.predictions.map((p, i) => (
                        <tr key={i}>
                          <td style={styles.td}>#{i + 1}</td>
                          <td style={{ ...styles.td, fontFamily: "monospace" }}>{p.score_anomalie.toFixed(4)}</td>
                          <td style={styles.td}>
                            <span style={{ color: SEVERITY_COLOR[p.severite] }}>{p.severite}</span>
                          </td>
                          <td style={styles.td}>
                            <span style={{ color: p.is_anomalie ? "#ef4444" : "#22c55e" }}>
                              {p.is_anomalie ? "Attaque" : "Normal"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
          {!result && (
            <div style={styles.emptyResult}><div style={{ fontSize: 48 }}>📦</div><p>Les résultats batch apparaîtront ici</p></div>
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  h1: { fontSize: 24, fontWeight: 700, color: "#e2e8f0", marginBottom: 24 },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 },
  card: { background: "#1e293b", borderRadius: 12, padding: "20px 24px", border: "1px solid #334155" },
  cardTitle: { fontSize: 15, fontWeight: 600, color: "#e2e8f0", margin: "0 0 12px" },
  demoRow: { marginBottom: 12 },
  demoBtn: { background: "#334155", border: "none", color: "#e2e8f0", borderRadius: 6, padding: "7px 14px", cursor: "pointer", fontSize: 13 },
  label: { display: "block", fontSize: 13, color: "#94a3b8", marginBottom: 6 },
  textarea: { width: "100%", background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "10px 12px", color: "#e2e8f0", fontSize: 12, fontFamily: "monospace", resize: "vertical", boxSizing: "border-box" },
  error: { color: "#ef4444", fontSize: 13, margin: "8px 0" },
  btn: { width: "100%", marginTop: 14, background: "#6366f1", color: "#fff", border: "none", borderRadius: 8, padding: 12, fontSize: 14, fontWeight: 600, cursor: "pointer" },
  kpiRow: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 12 },
  kpi: { background: "#1e293b", borderRadius: 10, padding: "16px", textAlign: "center", border: "1px solid #334155" },
  kpiVal: { fontSize: 24, fontWeight: 700, color: "#e2e8f0" },
  kpiLabel: { fontSize: 12, color: "#64748b", marginTop: 4 },
  tableWrap: { maxHeight: 300, overflowY: "auto" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { textAlign: "left", padding: "8px 12px", fontSize: 11, color: "#64748b", textTransform: "uppercase", borderBottom: "1px solid #334155" },
  td: { padding: "8px 12px", fontSize: 13, color: "#cbd5e1", borderBottom: "1px solid #0f172a" },
  emptyResult: { background: "#1e293b", borderRadius: 12, border: "1px solid #334155", textAlign: "center", color: "#64748b", padding: "80px 0" },
};
