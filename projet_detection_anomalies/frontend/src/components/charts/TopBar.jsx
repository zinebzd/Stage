import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

export default function TopBar({ data = [], xKey, yKey, color = "#f59e0b", label = "Occurrences" }) {
  if (data.length === 0)
    return <div style={styles.empty}>Aucune donnée</div>;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <YAxis type="category" dataKey={xKey} tick={{ fill: "#94a3b8", fontSize: 12 }} width={120} />
        <Tooltip
          contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
          itemStyle={{ color: "#e2e8f0" }}
        />
        <Bar dataKey={yKey} name={label} fill={color} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

const styles = { empty: { textAlign: "center", color: "#64748b", padding: "40px 0" } };
