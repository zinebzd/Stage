/**
 * KpiCard — carte KPI avec barre de progression, tendance et couleur dynamique.
 *
 * Props :
 *   title       — libellé
 *   value       — valeur principale (string ou number)
 *   sub         — sous-texte sous la valeur
 *   icon        — emoji ou caractère
 *   color       — couleur principale (#hex)
 *   progress    — 0-100, affiche une barre de progression si fourni
 *   trend       — { value: number, label: string }  ex: { value: +12, label: "vs hier" }
 *   alert       — "ok" | "warn" | "danger"  colore le bord de la carte
 */

const ALERT_BORDER = {
  ok:     "#22c55e",
  warn:   "#f59e0b",
  danger: "#ef4444",
};

export default function KpiCard({ title, value, sub, icon, color = "#6366f1", progress, trend, alert }) {
  const borderColor = alert ? ALERT_BORDER[alert] : "#334155";

  return (
    <div style={{ ...s.card, borderColor }}>
      {/* Bande colorée en haut */}
      <div style={{ ...s.topBar, background: color }} />

      <div style={s.body}>
        {/* Icône + titre */}
        <div style={s.header}>
          <div style={{ ...s.iconWrap, background: color + "22", color }}>
            {icon}
          </div>
          <span style={s.title}>{title}</span>
          {alert && (
            <div style={{ ...s.alertDot, background: ALERT_BORDER[alert] }} title={alert} />
          )}
        </div>

        {/* Valeur principale */}
        <div style={{ ...s.value, color }}>{value}</div>

        {/* Barre de progression */}
        {progress !== undefined && (
          <div style={s.barTrack}>
            <div style={{
              ...s.barFill,
              width: `${Math.min(progress, 100)}%`,
              background: color,
            }} />
          </div>
        )}

        {/* Sous-texte + tendance */}
        <div style={s.footer}>
          {sub  && <span style={s.sub}>{sub}</span>}
          {trend && (
            <span style={{ ...s.trend, color: trend.value >= 0 ? "#ef4444" : "#22c55e" }}>
              {trend.value >= 0 ? "▲" : "▼"} {Math.abs(trend.value)}% {trend.label}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

const s = {
  card: {
    background: "#1e293b",
    borderRadius: 14,
    border: "1px solid",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
    transition: "transform .15s, box-shadow .15s",
  },
  topBar:  { height: 4, flexShrink: 0 },
  body:    { padding: "16px 20px 18px", flex: 1 },
  header:  { display: "flex", alignItems: "center", gap: 10, marginBottom: 12 },
  iconWrap:{ fontSize: 20, width: 40, height: 40, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 },
  title:   { fontSize: 12, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.8, flex: 1 },
  alertDot:{ width: 8, height: 8, borderRadius: "50%", flexShrink: 0 },
  value:   { fontSize: 28, fontWeight: 800, lineHeight: 1, marginBottom: 10, fontVariantNumeric: "tabular-nums" },
  barTrack:{ height: 5, background: "#0f172a", borderRadius: 99, marginBottom: 10, overflow: "hidden" },
  barFill: { height: "100%", borderRadius: 99, transition: "width .6s ease" },
  footer:  { display: "flex", justifyContent: "space-between", alignItems: "center" },
  sub:     { fontSize: 12, color: "#64748b" },
  trend:   { fontSize: 12, fontWeight: 600 },
};
