import { useState } from "react";
import { useApi } from "../hooks/useApi";

const SEVERITY_COLOR = { low: "#22c55e", medium: "#f59e0b", high: "#ef4444" };

export default function Analyze() {
  const { call, loading, error } = useApi();
  const [file, setFile]     = useState(null);
  const [result, setResult] = useState(null);
  const [drag, setDrag]     = useState(false);

  const handleFile = (f) => { setFile(f); setResult(null); };

  const handleDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.append("fichier", file);
    const res = await call((api) => api.post("/analyze", form, { headers: { "Content-Type": "multipart/form-data" } }));
    if (res) setResult(res);
  };

  return (
    <div>
      <h1 style={styles.h1}>Analyser un fichier</h1>

      <div style={styles.grid}>
        <div style={styles.card}>
          <div
            style={{ ...styles.dropzone, borderColor: drag ? "#6366f1" : "#334155", background: drag ? "#6366f133" : "#0f172a" }}
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById("file-input").click()}
          >
            <div style={{ fontSize: 40 }}>📂</div>
            <p style={styles.dropText}>Glissez un fichier CSV ou JSON ici</p>
            <p style={styles.dropSub}>ou cliquez pour sélectionner (max 10 000 lignes)</p>
            {file && <div style={styles.fileName}>📄 {file.name}</div>}
          </div>
          <input id="file-input" type="file" accept=".csv,.json" style={{ display: "none" }} onChange={(e) => handleFile(e.target.files[0])} />

          {error && <div style={styles.error}>{error}</div>}
          <button
            style={{ ...styles.btn, opacity: loading || !file ? 0.6 : 1 }}
            onClick={handleSubmit}
            disabled={loading || !file}
          >
            {loading ? "Analyse en cours…" : "Lancer l'analyse"}
          </button>
        </div>

        <div>
          {result ? (
            <>
              <div style={styles.kpiRow}>
                <div style={styles.kpi}><div style={styles.kpiVal}>{result.nb_flux_analyses}</div><div style={styles.kpiLabel}>Flux analysés</div></div>
                <div style={{ ...styles.kpi, borderColor: "#ef4444" }}><div style={{ ...styles.kpiVal, color: "#ef4444" }}>{result.nb_anomalies}</div><div style={styles.kpiLabel}>Anomalies</div></div>
                <div style={styles.kpi}><div style={styles.kpiVal}>{result.taux_anomalies}%</div><div style={styles.kpiLabel}>Taux</div></div>
              </div>

              <div style={styles.card}>
                <h2 style={styles.cardTitle}>Résultats ligne par ligne</h2>
                <div style={styles.tableWrap}>
                  <table style={styles.table}>
                    <thead>
                      <tr>
                        {["Ligne", "Score MSE", "Sévérité", "Résultat"].map((h) => <th key={h} style={styles.th}>{h}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {result.resultats.map((r) => (
                        <tr key={r.ligne}>
                          <td style={styles.td}>{r.ligne}</td>
                          <td style={{ ...styles.td, fontFamily: "monospace" }}>{r.score_anomalie.toFixed(4)}</td>
                          <td style={styles.td}>
                            <span style={{ color: SEVERITY_COLOR[r.severite] }}>{r.severite}</span>
                          </td>
                          <td style={styles.td}>
                            <span style={{ color: r.is_anomalie ? "#ef4444" : "#22c55e" }}>
                              {r.is_anomalie ? "⚠️ Anomalie" : "✅ Normal"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div style={styles.empty}><div style={{ fontSize: 48 }}>📊</div><p>Les résultats apparaîtront ici</p></div>
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  h1: { fontSize: 24, fontWeight: 700, color: "#e2e8f0", marginBottom: 24 },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 },
  card: { background: "#1e293b", borderRadius: 12, padding: "24px", border: "1px solid #334155" },
  cardTitle: { fontSize: 15, fontWeight: 600, color: "#e2e8f0", margin: "0 0 12px" },
  dropzone: { borderRadius: 10, border: "2px dashed", padding: "40px 20px", textAlign: "center", cursor: "pointer", transition: "all .2s" },
  dropText: { color: "#e2e8f0", marginTop: 8, fontSize: 14 },
  dropSub: { color: "#64748b", fontSize: 12 },
  fileName: { marginTop: 12, color: "#6366f1", fontSize: 13, fontWeight: 600 },
  error: { color: "#ef4444", fontSize: 13, margin: "10px 0" },
  btn: { width: "100%", marginTop: 16, background: "#6366f1", color: "#fff", border: "none", borderRadius: 8, padding: 12, fontSize: 14, fontWeight: 600, cursor: "pointer" },
  kpiRow: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 12 },
  kpi: { background: "#1e293b", borderRadius: 10, padding: "16px", textAlign: "center", border: "1px solid #334155" },
  kpiVal: { fontSize: 24, fontWeight: 700, color: "#e2e8f0" },
  kpiLabel: { fontSize: 12, color: "#64748b", marginTop: 4 },
  tableWrap: { maxHeight: 380, overflowY: "auto" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { textAlign: "left", padding: "8px 12px", fontSize: 11, color: "#64748b", textTransform: "uppercase", borderBottom: "1px solid #334155" },
  td: { padding: "8px 12px", fontSize: 13, color: "#cbd5e1", borderBottom: "1px solid #0f172a" },
  empty: { background: "#1e293b", borderRadius: 12, border: "1px solid #334155", textAlign: "center", color: "#64748b", padding: "80px 0" },
};
