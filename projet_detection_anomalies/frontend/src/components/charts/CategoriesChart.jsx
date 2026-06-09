import { useState } from "react";
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from "recharts";

const COLORS = [
  "#ef4444", "#f59e0b", "#8b5cf6", "#06b6d4",
  "#22c55e", "#f97316", "#ec4899",
];

const ICONS = {
  Reconnaissance: "🔍",
  DoS:            "💥",
  Exploits:       "🐛",
  Backdoor:       "🚪",
  Fuzzers:        "🎲",
  Shellcode:      "💻",
  Worms:          "🪱",
};

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div style={tt.box}>
      <div style={{ ...tt.title, color: d.payload.fill }}>
        {ICONS[d.name] ?? "⚠️"} {d.name}
      </div>
      <div style={tt.row}>
        <span style={tt.label}>Occurrences</span>
        <span style={{ ...tt.val, color: d.payload.fill }}>{d.value}</span>
      </div>
      <div style={tt.row}>
        <span style={tt.label}>Part</span>
        <span style={{ ...tt.val, color: d.payload.fill }}>
          {d.payload.pct}%
        </span>
      </div>
    </div>
  );
}

const tt = {
  box:   { background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "10px 14px", minWidth: 160 },
  title: { fontWeight: 700, fontSize: 14, marginBottom: 8 },
  row:   { display: "flex", justifyContent: "space-between", gap: 16, fontSize: 13, marginBottom: 3 },
  label: { color: "#64748b" },
  val:   { fontWeight: 600, fontFamily: "monospace" },
};

export default function CategoriesChart({ data = [] }) {
  const [mode, setMode] = useState("donut"); // "donut" | "bar"

  if (!data.length)
    return <div style={s.empty}>Aucune catégorie enregistrée</div>;

  const total = data.reduce((acc, d) => acc + d.value, 0);
  const enriched = data.map((d, i) => ({
    ...d,
    fill: COLORS[i % COLORS.length],
    pct:  ((d.value / total) * 100).toFixed(1),
  }));

  return (
    <div>
      {/* Toggle donut / bar */}
      <div style={s.toggle}>
        {["donut", "bar"].map((m) => (
          <button
            key={m}
            style={{ ...s.btn, background: mode === m ? "#6366f1" : "#334155" }}
            onClick={() => setMode(m)}
          >
            {m === "donut" ? "🍩 Donut" : "📊 Barres"}
          </button>
        ))}
        <span style={s.total}>{total.toLocaleString("fr-FR")} attaques au total</span>
      </div>

      {mode === "donut" ? (
        <div style={{ display: "flex", gap: 0 }}>
          <ResponsiveContainer width="55%" height={280}>
            <PieChart>
              <Pie
                data={enriched}
                cx="50%" cy="50%"
                innerRadius={70} outerRadius={110}
                paddingAngle={3}
                dataKey="value"
              >
                {enriched.map((d) => (
                  <Cell key={d.name} fill={d.fill} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>

          {/* Légende custom à droite */}
          <div style={s.legend}>
            {enriched.map((d) => (
              <div key={d.name} style={s.legendRow}>
                <div style={{ ...s.legendDot, background: d.fill }} />
                <span style={s.legendIcon}>{ICONS[d.name] ?? "⚠️"}</span>
                <div style={{ flex: 1 }}>
                  <div style={s.legendName}>{d.name}</div>
                  <div style={s.legendBar}>
                    <div style={{ ...s.legendFill, width: `${d.pct}%`, background: d.fill }} />
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ ...s.legendVal, color: d.fill }}>{d.value}</div>
                  <div style={s.legendPct}>{d.pct}%</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={enriched} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" name="Occurrences" radius={[4, 4, 0, 0]} maxBarSize={50}>
              {enriched.map((d) => (
                <Cell key={d.name} fill={d.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

const s = {
  empty:      { textAlign: "center", color: "#64748b", padding: "60px 0" },
  toggle:     { display: "flex", gap: 8, alignItems: "center", marginBottom: 12 },
  btn:        { border: "none", color: "#e2e8f0", borderRadius: 6, padding: "5px 12px", fontSize: 12, cursor: "pointer" },
  total:      { marginLeft: "auto", fontSize: 12, color: "#64748b" },
  legend:     { flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 10, paddingLeft: 8 },
  legendRow:  { display: "flex", alignItems: "center", gap: 8 },
  legendDot:  { width: 8, height: 8, borderRadius: "50%", flexShrink: 0 },
  legendIcon: { fontSize: 14, flexShrink: 0 },
  legendName: { fontSize: 12, color: "#e2e8f0", marginBottom: 3 },
  legendBar:  { height: 4, background: "#0f172a", borderRadius: 99, overflow: "hidden" },
  legendFill: { height: "100%", borderRadius: 99, transition: "width .6s ease" },
  legendVal:  { fontSize: 13, fontWeight: 700, fontFamily: "monospace" },
  legendPct:  { fontSize: 11, color: "#64748b" },
};
