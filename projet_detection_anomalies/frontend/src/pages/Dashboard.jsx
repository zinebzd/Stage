import { useEffect, useState } from "react";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../context/AuthContext";
import KpiCard from "../components/KpiCard";
import SeveriteDonut from "../components/charts/SeveriteDonut";
import TopBar from "../components/charts/TopBar";
import TimelineChart from "../components/charts/TimelineChart";
import CategoriesChart from "../components/charts/CategoriesChart";

// Couleur et alerte selon le taux d'anomalies
function alertTaux(taux) {
  if (taux < 10) return { alert: "ok",     color: "#22c55e" };
  if (taux < 40) return { alert: "warn",   color: "#f59e0b" };
  return            { alert: "danger", color: "#ef4444" };
}

// Couleur selon la sévérité dominante
function colorSeverite(sev) {
  return { high: "#ef4444", medium: "#f59e0b", low: "#22c55e" }[sev] ?? "#6366f1";
}

// Format date lisible
function formatDate(d) {
  if (!d || d === "—") return "—";
  return new Date(d).toLocaleString("fr-FR", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

// Format grand nombre
function fmt(n) {
  if (n === undefined || n === null) return "—";
  return Number(n).toLocaleString("fr-FR");
}

export default function Dashboard() {
  const { call, loading, error } = useApi();
  const { user } = useAuth();

  const [kpis,        setKpis]        = useState(null);
  const [stats,       setStats]       = useState(null);
  const [info,        setInfo]        = useState(null);
  const [categories,  setCategories]  = useState([]);
  const [timeline,    setTimeline]    = useState([]);
  const [granularite, setGranularite] = useState("jour");
  const [lastRefresh, setLastRefresh] = useState(null);

  const charger = () => {
    call((api) => api.get("/kpis")).then(setKpis);
    call((api) => api.get("/stats")).then(setStats);
    call((api) => api.get("/info")).then(setInfo);
    call((api) => api.get("/categories")).then((d) => setCategories(d ?? []));
    setLastRefresh(new Date());
  };

  const chargerTimeline = (g) => {
    call((api) => api.get(`/timeline?granularite=${g}`)).then((d) => setTimeline(d ?? []));
  };

  useEffect(() => {
    charger();
    chargerTimeline("jour");
  }, []);

  const handleGranularite = (g) => {
    setGranularite(g);
    chargerTimeline(g);
  };

  const tauxStyle  = kpis ? alertTaux(kpis.taux_anomalies) : {};
  const sevColor   = kpis ? colorSeverite(kpis.severite_dominante) : "#6366f1";

  return (
    <div>
      {/* En-tête */}
      <div style={s.header}>
        <div>
          <h1 style={s.h1}>Dashboard</h1>
          <p style={s.sub}>Bienvenue, {user.name}</p>
        </div>
        <div style={s.headerRight}>
          {info && (
            <div style={s.modelBadge}>
              🤖 <strong>{info.architecture}</strong> · seuil {info.seuil_operationnel}
            </div>
          )}
          <button style={s.refreshBtn} onClick={() => { charger(); chargerTimeline(granularite); }} title="Actualiser">
            🔄
          </button>
          {lastRefresh && (
            <span style={s.refreshTime}>
              Mis à jour {lastRefresh.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
        </div>
      </div>

      {loading && !kpis && <div style={s.loading}>Chargement…</div>}

      {error && !loading && (
        <div style={s.errorBox}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>⚠️</div>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Impossible de joindre l'API</div>
          <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 12 }}>{error}</div>
          <div style={{ fontSize: 13, color: "#64748b", marginBottom: 16 }}>
            Vérifiez que l'API tourne sur <code style={{ color: "#6366f1" }}>http://localhost:8000</code>
          </div>
          <button style={s.retryBtn} onClick={charger}>🔄 Réessayer</button>
        </div>
      )}

      {kpis && (
        <>
          {/* ── KPIs principaux ── */}
          <div style={s.grid5}>

            {/* 1. Total logs analysés */}
            <KpiCard
              title="Logs analysés"
              value={fmt(kpis.total_flux_analyses)}
              icon="📡"
              color="#6366f1"
              sub="flux traités au total"
              progress={100}
            />

            {/* 2. Anomalies détectées */}
            <KpiCard
              title="Anomalies détectées"
              value={fmt(kpis.total_anomalies)}
              icon="🚨"
              color="#ef4444"
              alert={kpis.total_anomalies === 0 ? "ok" : kpis.taux_anomalies < 40 ? "warn" : "danger"}
              sub={`sur ${fmt(kpis.total_flux_analyses)} flux`}
              progress={Math.min(kpis.taux_anomalies * 2, 100)}
            />

            {/* 3. Taux d'anomalies */}
            <KpiCard
              title="Taux d'anomalies"
              value={`${kpis.taux_anomalies}%`}
              icon={kpis.taux_anomalies < 10 ? "✅" : kpis.taux_anomalies < 40 ? "⚠️" : "🔴"}
              color={tauxStyle.color}
              alert={tauxStyle.alert}
              progress={kpis.taux_anomalies}
              sub={
                kpis.taux_anomalies < 10  ? "Situation normale" :
                kpis.taux_anomalies < 40  ? "Surveillance recommandée" :
                                            "Situation critique"
              }
            />

            {/* 4. Score moyen de sévérité */}
            <KpiCard
              title="Score MSE moyen"
              value={kpis.score_moyen.toFixed(4)}
              icon="⚖️"
              color={sevColor}
              sub={`Sévérité dominante : ${kpis.severite_dominante}`}
              alert={
                kpis.severite_dominante === "low"    ? "ok"     :
                kpis.severite_dominante === "medium"  ? "warn"   :
                kpis.severite_dominante === "high"    ? "danger" : undefined
              }
              progress={Math.min((kpis.score_moyen / 200) * 100, 100)}
            />

            {/* 5. Dernière analyse */}
            <KpiCard
              title="Dernière analyse"
              value={kpis.derniere_analyse !== "—"
                ? new Date(kpis.derniere_analyse).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
                : "—"}
              icon="🕐"
              color="#06b6d4"
              sub={kpis.derniere_analyse !== "—"
                ? new Date(kpis.derniere_analyse).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" })
                : "Aucune analyse"}
            />
          </div>

          {/* ── Barre de statut global ── */}
          <div style={{
            ...s.statusBar,
            background: tauxStyle.color + "11",
            borderColor: tauxStyle.color + "44",
          }}>
            <span style={{ ...s.statusDot, background: tauxStyle.color }} />
            <span style={{ color: tauxStyle.color, fontWeight: 600, fontSize: 13 }}>
              {tauxStyle.alert === "ok"     ? "Système nominal"         :
               tauxStyle.alert === "warn"   ? "Activité suspecte détectée" :
                                              "Niveau d'alerte élevé"}
            </span>
            <span style={s.statusDetail}>
              {fmt(kpis.total_anomalies)} anomalies sur {fmt(kpis.total_flux_analyses)} flux analysés
              · Score moyen {kpis.score_moyen.toFixed(4)}
              · Sévérité dominante <strong style={{ color: sevColor }}>{kpis.severite_dominante}</strong>
            </span>
          </div>

          {/* ── Timeline interactive ── */}
          <div style={s.chartCard}>
            <div style={s.chartHeader}>
              <div>
                <h2 style={s.chartTitle}>Volume d'anomalies dans le temps</h2>
                <p style={s.chartSub}>
                  Barres = anomalies par sévérité · Ligne violette = volume total de flux analysés
                </p>
              </div>
              <button style={s.iconBtn} onClick={() => chargerTimeline(granularite)}>🔄</button>
            </div>
            <TimelineChart
              data={timeline}
              granularite={granularite}
              onGranulariteChange={handleGranularite}
            />
          </div>

          {/* ── Donut + Top IPs ── */}
          {stats && (
            <>
              <div style={s.grid2}>
                <div style={s.chartCard}>
                  <h2 style={s.chartTitle}>Répartition par sévérité</h2>
                  <SeveriteDonut
                    total_low={stats.total_low}
                    total_medium={stats.total_medium}
                    total_high={stats.total_high}
                  />
                </div>
                <div style={s.chartCard}>
                  <h2 style={s.chartTitle}>Top 5 adresses IP suspectes</h2>
                  <TopBar data={stats.top_ips} xKey="ip" yKey="nb_attaques" color="#ef4444" label="Attaques" />
                </div>
              </div>

              {/* Graphique catégories d'attaques — pleine largeur */}
              <div style={s.chartCard}>
                <div style={s.chartHeader}>
                  <div>
                    <h2 style={s.chartTitle}>Répartition par catégorie d'attaque</h2>
                    <p style={s.chartSub}>
                      Basé sur les types détectés — bascule Donut / Barres
                    </p>
                  </div>
                </div>
                <CategoriesChart data={categories} />
              </div>

              <div style={s.chartCard}>
                <h2 style={s.chartTitle}>Top 5 types d'attaques</h2>
                <TopBar data={stats.top_types} xKey="type" yKey="nb_occurrences" color="#f59e0b" label="Occurrences" />
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

const s = {
  header:      { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 },
  h1:          { fontSize: 24, fontWeight: 700, color: "#e2e8f0", margin: 0 },
  sub:         { color: "#64748b", fontSize: 14, marginTop: 4 },
  headerRight: { display: "flex", alignItems: "center", gap: 10 },
  modelBadge:  { background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "7px 14px", fontSize: 13, color: "#94a3b8" },
  refreshBtn:  { background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "7px 10px", cursor: "pointer", fontSize: 16 },
  refreshTime: { fontSize: 12, color: "#475569" },
  loading:     { color: "#64748b", textAlign: "center", padding: 60 },
  errorBox:    { background: "#1e293b", border: "1px solid #ef444455", borderRadius: 12, padding: 40, textAlign: "center", color: "#ef4444", marginBottom: 20 },
  retryBtn:    { background: "#6366f1", color: "#fff", border: "none", borderRadius: 8, padding: "10px 20px", cursor: "pointer", fontSize: 14, fontWeight: 600 },

  grid5:       { display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14, marginBottom: 14 },
  grid2:       { display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 16 },

  statusBar:   { display: "flex", alignItems: "center", gap: 12, padding: "12px 18px", borderRadius: 10, border: "1px solid", marginBottom: 16 },
  statusDot:   { width: 10, height: 10, borderRadius: "50%", flexShrink: 0 },
  statusDetail:{ fontSize: 13, color: "#94a3b8", marginLeft: 4 },

  chartCard:   { background: "#1e293b", borderRadius: 12, padding: "20px 24px", border: "1px solid #334155", marginBottom: 16 },
  chartHeader: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 },
  chartTitle:  { fontSize: 15, fontWeight: 600, color: "#e2e8f0", margin: "0 0 4px" },
  chartSub:    { fontSize: 12, color: "#64748b" },
  iconBtn:     { background: "none", border: "none", fontSize: 16, cursor: "pointer", padding: 4 },
};
