import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

export default function AnomaliesParJour({ data = [] }) {
  if (data.length === 0)
    return <div style={styles.empty}>Aucune donnée sur 7 jours</div>;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="jour" tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} allowDecimals={false} />
        <Tooltip
          contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
          itemStyle={{ color: "#e2e8f0" }}
          labelStyle={{ color: "#94a3b8" }}
        />
        <Bar dataKey="nb_anomalies" name="Anomalies" fill="#6366f1" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

const styles = { empty: { textAlign: "center", color: "#64748b", padding: "60px 0" } };
