import { useState, useCallback } from "react";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, Brush, ResponsiveContainer, ReferenceArea,
} from "recharts";

// Tooltip personnalisé
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={tt.box}>
      <div style={tt.label}>{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ ...tt.row, color: p.color }}>
          <span>{p.name}</span>
          <span style={{ fontFamily: "monospace", fontWeight: 600 }}>{p.value?.toLocaleString()}</span>
        </div>
      ))}
      {payload.length >= 2 && payload[1]?.value > 0 && (
        <div style={tt.ratio}>
          Ratio : {((payload[0].value / payload[1].value) * 100).toFixed(1)}% de menaces
        </div>
      )}
    </div>
  );
}

const tt = {
  box:   { background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "10px 14px", minWidth: 180 },
  label: { color: "#94a3b8", fontSize: 12, marginBottom: 8, borderBottom: "1px solid #1e293b", paddingBottom: 6 },
  row:   { display: "flex", justifyContent: "space-between", gap: 16, fontSize: 13, marginBottom: 4 },
  ratio: { marginTop: 8, fontSize: 12, color: "#f59e0b", borderTop: "1px solid #1e293b", paddingTop: 6 },
};

export default function TimelineChart({ data = [], granularite, onGranulariteChange }) {
  // Zoom par sélection de zone
  const [zoomLeft,  setZoomLeft]  = useState(null);
  const [zoomRight, setZoomRight] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [zoomData,  setZoomData]  = useState(null); // données filtrées pendant zoom

  // Filtres sévérité
  const [showHigh,   setShowHigh]   = useState(true);
  const [showMedium, setShowMedium] = useState(true);
  const [showLow,    setShowLow]    = useState(true);
  const [showTotal,  setShowTotal]  = useState(true);

  const displayed = zoomData ?? data;

  const handleMouseDown = (e) => {
    if (!e?.activeLabel) return;
    setZoomLeft(e.activeLabel);
    setIsDragging(true);
  };

  const handleMouseMove = (e) => {
    if (!isDragging || !e?.activeLabel) return;
    setZoomRight(e.activeLabel);
  };

  const handleMouseUp = useCallback(() => {
    if (!isDragging) return;
    setIsDragging(false);
    if (zoomLeft && zoomRight && zoomLeft !== zoomRight) {
      const [l, r] = [zoomLeft, zoomRight].sort();
      setZoomData(data.filter((d) => d.periode >= l && d.periode <= r));
    }
    setZoomLeft(null);
    setZoomRight(null);
  }, [isDragging, zoomLeft, zoomRight, data]);

  const resetZoom = () => setZoomData(null);

  if (data.length === 0)
    return <div style={s.empty}>Aucune donnée — analysez des flux pour alimenter le graphe</div>;

  return (
    <div>
      {/* Barre de contrôles */}
      <div style={s.controls}>
        <div style={s.granulariteGroup}>
          {["jour", "heure"].map((g) => (
            <button
              key={g}
              style={{ ...s.granBtn, background: granularite === g ? "#6366f1" : "#334155" }}
              onClick={() => { onGranulariteChange(g); setZoomData(null); }}
            >
              Par {g}
            </button>
          ))}
        </div>

        <div style={s.toggleGroup}>
          <ToggleBtn active={showTotal}  color="#6366f1" onClick={() => setShowTotal(v => !v)}>Total flux</ToggleBtn>
          <ToggleBtn active={showHigh}   color="#ef4444" onClick={() => setShowHigh(v => !v)}>Élevée</ToggleBtn>
          <ToggleBtn active={showMedium} color="#f59e0b" onClick={() => setShowMedium(v => !v)}>Moyenne</ToggleBtn>
          <ToggleBtn active={showLow}    color="#22c55e" onClick={() => setShowLow(v => !v)}>Faible</ToggleBtn>
        </div>

        {zoomData && (
          <button style={s.resetBtn} onClick={resetZoom}>
            🔍 Réinitialiser zoom
          </button>
        )}
      </div>

      <div style={s.hint}>
        💡 Sélectionnez une zone sur le graphe pour zoomer · Utilisez le curseur en bas pour naviguer
      </div>

      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart
          data={displayed}
          margin={{ top: 8, right: 20, left: 0, bottom: 0 }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="periode"
            tick={{ fill: "#64748b", fontSize: 11 }}
            tickLine={false}
          />
          <YAxis
            yAxisId="flux"
            orientation="right"
            tick={{ fill: "#6366f1", fontSize: 11 }}
            tickLine={false}
            label={{ value: "Total flux", angle: 90, position: "insideRight", fill: "#6366f1", fontSize: 11, dx: 14 }}
          />
          <YAxis
            yAxisId="anomalies"
            orientation="left"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            label={{ value: "Anomalies", angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 11, dx: -4 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ color: "#94a3b8", fontSize: 12, paddingTop: 12 }}
          />

          {/* Brush — navigateur de période en bas */}
          <Brush
            dataKey="periode"
            height={24}
            stroke="#334155"
            fill="#0f172a"
            travellerWidth={8}
            tickFormatter={(v) => v?.slice(-5)}
          >
            <ComposedChart>
              <Bar dataKey="nb_anomalies" fill="#6366f133" yAxisId="anomalies" />
            </ComposedChart>
          </Brush>

          {/* Barres empilées par sévérité */}
          {showHigh && (
            <Bar yAxisId="anomalies" dataKey="nb_high" name="Élevée" stackId="sev"
              fill="#ef4444" radius={[0,0,0,0]} maxBarSize={40} />
          )}
          {showMedium && (
            <Bar yAxisId="anomalies" dataKey="nb_medium" name="Moyenne" stackId="sev"
              fill="#f59e0b" maxBarSize={40} />
          )}
          {showLow && (
            <Bar yAxisId="anomalies" dataKey="nb_low" name="Faible" stackId="sev"
              fill="#22c55e" radius={[4,4,0,0]} maxBarSize={40} />
          )}

          {/* Ligne overlay — volume total de flux */}
          {showTotal && (
            <Line
              yAxisId="flux"
              type="monotone"
              dataKey="nb_flux_total"
              name="Total flux"
              stroke="#6366f1"
              strokeWidth={2}
              dot={{ fill: "#6366f1", r: 3 }}
              activeDot={{ r: 6, stroke: "#6366f1", strokeWidth: 2, fill: "#0f172a" }}
            />
          )}

          {/* Zone de sélection zoom */}
          {isDragging && zoomLeft && zoomRight && (
            <ReferenceArea
              yAxisId="anomalies"
              x1={zoomLeft}
              x2={zoomRight}
              fill="#6366f1"
              fillOpacity={0.15}
              stroke="#6366f1"
              strokeOpacity={0.5}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function ToggleBtn({ active, color, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? color + "22" : "#1e293b",
        color:      active ? color       : "#64748b",
        border:     `1px solid ${active ? color : "#334155"}`,
        borderRadius: 6, padding: "4px 10px", fontSize: 12,
        cursor: "pointer", transition: "all .15s",
      }}
    >
      {children}
    </button>
  );
}

const s = {
  empty:          { textAlign: "center", color: "#64748b", padding: "60px 0", fontSize: 14 },
  controls:       { display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", marginBottom: 10 },
  granulariteGroup: { display: "flex", gap: 6 },
  granBtn:        { border: "none", color: "#e2e8f0", borderRadius: 6, padding: "5px 12px", fontSize: 12, cursor: "pointer" },
  toggleGroup:    { display: "flex", gap: 6 },
  resetBtn:       { marginLeft: "auto", background: "#334155", border: "none", color: "#e2e8f0", borderRadius: 6, padding: "5px 12px", fontSize: 12, cursor: "pointer" },
  hint:           { fontSize: 11, color: "#475569", marginBottom: 10 },
};
