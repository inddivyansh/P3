import React, { useState, useEffect } from "react";
import { Icon } from "../Shared/Icons.jsx";
import { getTopicTrends, getKPIs } from "../../services/api";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  LineChart,
  Line,
  CartesianGrid,
} from "recharts";

const TIMEFRAME_OPTIONS = [
  { label: "7 Days", days: 7 },
  { label: "30 Days", days: 30 },
  { label: "90 Days", days: 90 },
  { label: "6 Months", days: 180 },
  { label: "1 Year", days: 365 },
];

export function TrendsAnalytics() {
  const [selectedDays, setSelectedDays] = useState(30);
  const [trendData, setTrendData] = useState(null);
  const [kpis, setKpis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTrends();
  }, [selectedDays]);

  const loadTrends = async () => {
    try {
      setLoading(true);
      const [tRes, kRes] = await Promise.allSettled([
        getTopicTrends(selectedDays),
        getKPIs(),
      ]);

      if (tRes.status === "fulfilled") {
        setTrendData(tRes.value);
      }
      if (kRes.status === "fulfilled") {
        setKpis(kRes.value);
      }
    } catch (err) {
      console.error("Failed to load trends:", err);
    } finally {
      setLoading(false);
    }
  };

  const categories = (trendData?.top_categories || []).slice(0, 8).map((c) => ({
    name: c.category,
    shortName: c.category.split(" ")[0],
    count: c.count,
  }));

  const timeline = (trendData?.daily_totals || []).map((d) => ({
    time: d.date.slice(5),
    volume: d.count,
  }));

  return (
    <div>
      <div className="page-title-row">
        <div>
          <h1 className="page-heading">Strategic Trends & Comparative Analytics</h1>
          <p className="page-subheading">
            Longitudinal trend detection, reporting volume shifts, and domain distributions derived live from database.
          </p>
        </div>
        <div className="filter-action-buttons">
          <div className="map-layer-selector">
            {TIMEFRAME_OPTIONS.map((opt) => (
              <button
                key={opt.days}
                className={`map-layer-btn ${selectedDays === opt.days ? "active" : ""}`}
                onClick={() => setSelectedDays(opt.days)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20, marginBottom: 20 }}>
        {/* Longitudinal Reporting Volume */}
        <div className="intel-card">
          <div className="intel-card-header">
            <h3 className="intel-card-title">
              <Icon name="trend" size={15} color="var(--accent-secondary)" />
              <span>Article Ingestion Volume Over Time</span>
            </h3>
            <span className="intel-card-badge">{selectedDays} Days Period</span>
          </div>
          <div style={{ height: 260, width: "100%" }}>
            {loading ? (
              <div style={{ padding: 80, textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
                Loading volume timelines...
              </div>
            ) : timeline.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={timeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      background: "#FFFFFF",
                      border: "1px solid #E2E8F0",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="volume"
                    name="Daily Volume"
                    stroke="#1E3A8A"
                    strokeWidth={2.5}
                    dot={{ fill: "#1E3A8A", r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ padding: 80, textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
                No volume records in this timeframe.
              </div>
            )}
          </div>
        </div>

        {/* Domain Distribution */}
        <div className="intel-card">
          <div className="intel-card-header">
            <h3 className="intel-card-title">
              <Icon name="grid" size={15} color="var(--accent-secondary)" />
              <span>Domain Concentration</span>
            </h3>
            <span className="intel-card-badge">Top Categories</span>
          </div>
          <div style={{ height: 260, width: "100%" }}>
            {loading ? (
              <div style={{ padding: 80, textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
                Loading category metrics...
              </div>
            ) : categories.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categories} layout="vertical" margin={{ left: 30 }}>
                  <XAxis type="number" tick={{ fontSize: 10, fill: "#64748B" }} axisLine={false} tickLine={false} />
                  <YAxis dataKey="shortName" type="category" tick={{ fontSize: 10.5, fill: "#475569" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      background: "#FFFFFF",
                      border: "1px solid #E2E8F0",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {categories.map((_, i) => (
                      <Cell key={i} fill="#1E3A8A" fillOpacity={1 - i * 0.12} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ padding: 80, textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
                No category records available.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Strategic Domain Activity Table */}
      <div className="intel-card">
        <div className="intel-card-header">
          <h3 className="intel-card-title">Classified Domain Breakdown</h3>
          <span className="intel-card-badge">{categories.length} Categories</span>
        </div>
        <table className="intel-table">
          <thead>
            <tr>
              <th>Domain Category</th>
              <th>Reported Article Volume</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {categories.map((dom, i) => (
              <tr key={i}>
                <td className="location-name">{dom.name}</td>
                <td className="numeric-val">{dom.count}</td>
                <td>
                  <span className="status-badge normal">
                    Active
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
