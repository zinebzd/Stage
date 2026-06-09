import { useState } from "react";
import { useApi } from "../hooks/useApi";

const SEVERITY_COLOR = { low: "#22c55e", medium: "#f59e0b", high: "#ef4444" };
const NB_FEATURES = 44;

export default function Predict() {
  const { call, loading, error } = useApi();
  const [raw, setRaw]         = useState("");
  const [ip, setIp]           = useState("");
  const [type, setType]       = useState("");
  const [result, setResult]   = useState(null);
  const [inputError, setInputError] = useState("");

  const parseFeatures = () => {
    const vals = raw
      .trim()
      .split(/[\s,;]+/)
      .filter(Boolean)
      .map(Number);
    if (vals.some(isNaN)) { setInputError("Toutes les valeurs doivent être numériques"); return null; }
    if (vals.length !== NB_FEATURES) { setInputError(`${vals.length} features reçues, ${NB_FEATURES} attendues`); return null; }
    setInputError("");
    return vals;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const features = parseFeatures();
    if (!features) return;
    const payload = { features, ip_source: ip || null, type_attaque: type || null };
    const res = await call((api) => api.post("/predict", payload));
    if (res) setResult(res);
  };

  const fillDemo = (normal) => {
    const val = normal ? 0 : 10;
    setRaw(Array(NB_FEATURES).fill(val).join(", "));
  };

  return (
    <div>
      <h1 style={styles.h1}>Prédiction — flux unique</h1>

      <div style={styles.grid}>
        {/* Formulaire */}
        <div style={styles.card}>
          <div style={styles.demoRow}>
            <span style={styles.demoLabel}>Données démo :</span>
            <button style={styles.demoBtn} type="button" onClick={() => fillDemo(true)}>Flux normal</button>
            <button style={styles.demoBtn} type="button" onClick={() => fillDemo(false)}>Flux attaque</button>
          </div>

          <form onSubmit={handleSubmit}>
            <label style={styles.label}>44 features numériques <span style={styles.hint}>(séparées par des espaces ou virgules)</span></label>
            <textarea
              style={styles.textarea}
              rows={6}
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              placeholder="0.0, 0.0, 1.2, 0.8, …"
            />
            {inputError && <div style={styles.error}>{inputError}</div>}

            <div style={styles.row2}>
              <div style={{ flex: 1 }}>
                <label style={styles.label}>IP source <span style={styles.hint}>(optionnel)</span></label>
                <input style={styles.input} value={ip} onChange={(e) => setIp(e.target.value)} placeholder="192.168.1.1" />
              </div>
              <div style={{ flex: 1 }}>
                <label style={styles.label}>Type d'attaque <span style={styles.hint}>(optionnel)</span></label>
                <input style={styles.input} value={type} onChange={(e) => setType(e.target.value)} placeholder="DoS, Scan, …" />
              </div>
            </div>

            {error && <div style={styles.error}>{error}</div>}
            <button style={{ ...styles.btn, opacity: loading ? 0.6 : 1 }} type="submit" disabled={loading}>
              {loading ? "Analyse en cours…" : "Analyser"}
            </button>
          </form>
        </div>

        {/* Résultat */}
        <div style={styles.card}>
          {!result ? (
            <div style={styles.emptyResult}>
              <div style={{ fontSize: 48 }}>🔍</div>
              <p>Le résultat apparaîtra ici</p>
            </div>
          ) : (
            <div>
              <div style={{ ...styles.verdict, background: result.is_anomalie ? "#ef444422" : "#22c55e22", borderColor: result.is_anomalie ? "#ef4444" : "#22c55e" }}>
                <span style={{ fontSize: 40 }}>{result.is_anomalie ? "🚨" : "✅"}</span>
                <div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: result.is_anomalie ? "#ef4444" : "#22c55e" }}>
                    {result.is_anomalie ? "ANOMALIE DÉTECTÉE" : "Trafic normal"}
                  </div>
                  <div style={{ color: "#94a3b8", marginTop: 4 }}>
                    Prédiction : {result.prediction}
                  </div>
                </div>
              </div>

              <div style={styles.metaGrid}>
                <ResultRow label="Score MSE"  value={result.score_anomalie.toFixed(6)} />
                <ResultRow label="Seuil"      value={result.seuil_utilise} />
                <ResultRow label="Sévérité"   value={
                  <span style={{ color: SEVERITY_COLOR[result.severite], fontWeight: 600 }}>{result.severite}</span>
                } />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ResultRow({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid #334155" }}>
      <span style={{ color: "#64748b", fontSize: 13 }}>{label}</span>
      <span style={{ color: "#e2e8f0", fontSize: 13, fontFamily: "monospace" }}>{value}</span>
    </div>
  );
}

const styles = {
  h1: { fontSize: 24, fontWeight: 700, color: "#e2e8f0", marginBottom: 24 },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 },
  card: { background: "#1e293b", borderRadius: 12, padding: "24px", border: "1px solid #334155" },
  demoRow: { display: "flex", gap: 8, alignItems: "center", marginBottom: 16 },
  demoLabel: { fontSize: 13, color: "#64748b" },
  demoBtn: { background: "#334155", border: "none", color: "#e2e8f0", borderRadius: 6, padding: "6px 12px", cursor: "pointer", fontSize: 12 },
  label: { display: "block", fontSize: 13, color: "#94a3b8", marginBottom: 6 },
  hint: { color: "#64748b", fontSize: 11 },
  textarea: { width: "100%", background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "10px 12px", color: "#e2e8f0", fontSize: 13, fontFamily: "monospace", resize: "vertical", boxSizing: "border-box" },
  row2: { display: "flex", gap: 12, marginTop: 12 },
  input: { width: "100%", background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "9px 12px", color: "#e2e8f0", fontSize: 13, boxSizing: "border-box" },
  error: { color: "#ef4444", fontSize: 13, margin: "8px 0" },
  btn: { width: "100%", marginTop: 16, background: "#6366f1", color: "#fff", border: "none", borderRadius: 8, padding: 12, fontSize: 14, fontWeight: 600, cursor: "pointer" },
  emptyResult: { textAlign: "center", color: "#64748b", padding: "60px 0" },
  verdict: { display: "flex", alignItems: "center", gap: 16, padding: 20, borderRadius: 10, border: "1px solid", marginBottom: 20 },
  metaGrid: { marginTop: 4 },
};
