import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

const COLORS = { low: "#22c55e", medium: "#f59e0b", high: "#ef4444" };
const LABELS = { low: "Faible", medium: "Moyenne", high: "Élevée" };

export default function SeveriteDonut({ total_low, total_medium, total_high }) {
  const data = [
    { name: LABELS.low,    value: total_low,    key: "low"    },
    { name: LABELS.medium, value: total_medium, key: "medium" },
    { name: LABELS.high,   value: total_high,   key: "high"   },
  ].filter((d) => d.value > 0);

  if (data.length === 0)
    return <div style={styles.empty}>Aucune anomalie enregistrée</div>;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={65}
          outerRadius={100}
          paddingAngle={3}
          dataKey="value"
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          labelLine={false}
        >
          {data.map((entry) => (
            <Cell key={entry.key} fill={COLORS[entry.key]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
          itemStyle={{ color: "#e2e8f0" }}
        />
        <Legend wrapperStyle={{ color: "#94a3b8", fontSize: 13 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

const styles = { empty: { textAlign: "center", color: "#64748b", padding: "60px 0" } };
