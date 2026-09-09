import React, { useState, useEffect } from "react";
import { RiskMap } from "../Shared/RiskMap.jsx";
import { Icon } from "../Shared/Icons.jsx";
import {
  getIntelligenceArticles,
  getGeographicIntelligence,
  getSources,
  getTopicTrends,
  getDailyBrief,
} from "../../services/api";
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

export function OverviewPage({ kpis, onNavigate, onSelectLocation }) {
  const [selectedMapLocation, setSelectedMapLocation] = useState(null);
  const [recentDevelopments, setRecentDevelopments] = useState([]);
  const [topLocations, setTopLocations] = useState([]);
  const [topSources, setTopSources] = useState([]);
  const [categoryData, setCategoryData] = useState([]);
  const [dailyTrendData, setDailyTrendData] = useState([]);
  const [aiBriefText, setAiBriefText] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAllOverviewData();
  }, [kpis]);

  const loadAllOverviewData = async () => {
    try {
      setLoading(true);
      const [
        devsRes,
        geoRes,
        sourcesRes,
        trendsRes,
        briefRes,
      ] = await Promise.allSettled([
        getIntelligenceArticles({ limit: 4, threat_level: "HIGH" }),
        getGeographicIntelligence(),
        getSources(),
        getTopicTrends(30),
        getDailyBrief(),
      ]);

      // 1. High Priority Recent Developments
      if (devsRes.status === "fulfilled" && devsRes.value?.articles?.length > 0) {
        setRecentDevelopments(devsRes.value.articles);
      } else {
        // Fallback to recent articles
        const fallbackArts = await getIntelligenceArticles({ limit: 4 });
        setRecentDevelopments(fallbackArts.articles || []);
      }

      // 2. Top Active Locations Table
      if (geoRes.status === "fulfilled") {
        const states = geoRes.value?.states || [];
        const cities = geoRes.value?.cities || [];
        const merged = [...states, ...cities]
          .sort((a, b) => (b.total || 0) - (a.total || 0))
          .slice(0, 7);
        setTopLocations(merged);
      }

      // 3. Top Sources List
      if (sourcesRes.status === "fulfilled") {
        setTopSources((sourcesRes.value?.sources || []).slice(0, 6));
      }

      // 4. Category Intensity
      if (kpis?.category_distribution) {
        const cats = Object.entries(kpis.category_distribution)
          .map(([name, count]) => ({ name: name.split(" ")[0], fullName: name, count }))
          .slice(0, 6);
        setCategoryData(cats);
      } else if (trendsRes.status === "fulfilled" && trendsRes.value?.top_categories) {
        setCategoryData(
          trendsRes.value.top_categories.slice(0, 6).map((c) => ({
            name: c.category.split(" ")[0],
            fullName: c.category,
            count: c.count,
          }))
        );
      }

      // 5. Trend Line
      if (trendsRes.status === "fulfilled" && trendsRes.value?.daily_totals) {
        setDailyTrendData(
          trendsRes.value.daily_totals.slice(-10).map((d) => ({
            time: d.date.slice(5),
            volume: d.count,
          }))
        );
      }

      // 6. AI Situation Brief
      if (briefRes.status === "fulfilled" && briefRes.value?.brief) {
        setAiBriefText(briefRes.value.brief);
      }
    } catch (err) {
      console.error("Overview data loading error:", err);
    } finally {
      setLoading(false);
    }
  };

  const totalArticles = kpis?.total_articles || 0;
  const criticalThreats = kpis?.critical_articles || 0;
  const monitoringReq = kpis?.monitoring_required || 0;
  const normalActivity = Math.max(0, totalArticles - criticalThreats - monitoringReq);
  const emergingCount = kpis?.emerging_situations || 0;
  const activeSourcesCount = topSources.length;

  const handleLocationDetail = (location) => {
    onSelectLocation?.(location);
    onNavigate?.("locations");
  };

  return (
    <div className="overview-page-root">
      {/* Overview Title Header */}
      <div className="page-title-row">
        <div>
          <h1 className="page-heading">Strategic Intelligence Overview</h1>
          <p className="page-subheading">
            Monitor defence, geopolitical and national-security developments across regions, locations, and strategic actors.
          </p>
        </div>
        <div className="filter-action-buttons">
          <div className="mono" style={{ fontSize: 11, color: "var(--text-muted)", marginRight: 8 }}>
            Realtime Database Ingestion
          </div>
          <button className="btn-secondary-subtle" onClick={loadAllOverviewData}>
            <Icon name="refresh" size={13} />
            <span>Refresh</span>
          </button>
          <button className="btn-primary-dark" onClick={() => onNavigate?.("reports")}>
            <Icon name="download" size={13} />
            <span>Generate Brief</span>
          </button>
        </div>
      </div>

      {/* KPI Metric Cards Row (Dynamically populated from backend) */}
      <div className="kpi-row-grid">
        <div className="kpi-metric-card">
          <div className="kpi-header">
            <span className="kpi-title">Total Relevant Articles</span>
            <div className="kpi-icon-box"><Icon name="file-text" size={15} /></div>
          </div>
          <div className="kpi-number-val">{totalArticles.toLocaleString()}</div>
          <div className="kpi-delta increase">
            <Icon name="trending-up" size={12} />
            <span>Indexed in Database</span>
          </div>
        </div>

        <div className="kpi-metric-card">
          <div className="kpi-header">
            <span className="kpi-title">Immediate Threats</span>
            <div className="kpi-icon-box" style={{ color: "var(--threat-red)" }}><Icon name="threat" size={15} /></div>
          </div>
          <div className="kpi-number-val threat-red">{criticalThreats}</div>
          <div className="kpi-delta increase">
            <span>High priority classified</span>
          </div>
        </div>

        <div className="kpi-metric-card">
          <div className="kpi-header">
            <span className="kpi-title">Surveillance Required</span>
            <div className="kpi-icon-box" style={{ color: "var(--threat-amber)" }}><Icon name="eye" size={15} /></div>
          </div>
          <div className="kpi-number-val threat-amber">{monitoringReq}</div>
          <div className="kpi-delta">
            <span>Active monitoring flags</span>
          </div>
        </div>

        <div className="kpi-metric-card">
          <div className="kpi-header">
            <span className="kpi-title">Normal Activity</span>
            <div className="kpi-icon-box" style={{ color: "var(--threat-green)" }}><Icon name="check-circle" size={15} /></div>
          </div>
          <div className="kpi-number-val threat-green">{normalActivity}</div>
          <div className="kpi-delta decrease">
            <span>Baseline parameters</span>
          </div>
        </div>

        <div className="kpi-metric-card">
          <div className="kpi-header">
            <span className="kpi-title">Emerging Situations</span>
            <div className="kpi-icon-box"><Icon name="radar" size={15} /></div>
          </div>
          <div className="kpi-number-val">{emergingCount}</div>
          <div className="kpi-delta">
            <span>Active clusters</span>
          </div>
        </div>

        <div className="kpi-metric-card">
          <div className="kpi-header">
            <span className="kpi-title">Active Sources</span>
            <div className="kpi-icon-box"><Icon name="database" size={15} /></div>
          </div>
          <div className="kpi-number-val">{activeSourcesCount}</div>
          <div className="kpi-delta">
            <span>Configured feeds</span>
          </div>
        </div>
      </div>

      {/* Hero Visual Centerpiece: Strategic Activity Map */}
      <RiskMap
        selectedLocation={selectedMapLocation}
        onSelectLocation={setSelectedMapLocation}
        onViewLocationDetails={handleLocationDetail}
      />

      {/* Below-Map 3-Column Analytical Grid */}
      <div className="analytical-grid-3">
        {/* Card 1: Recent High-Priority Developments */}
        <div className="intel-card">
          <div className="intel-card-header">
            <h3 className="intel-card-title">
              <Icon name="alert-triangle" size={15} color="var(--threat-red)" />
              <span>Recent High-Priority Developments</span>
            </h3>
            <span className="intel-card-badge">Live Feeds</span>
          </div>
          <div className="intel-list-stack">
            {recentDevelopments.length === 0 ? (
              <div style={{ padding: 20, textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
                No high-priority developments flagged currently.
              </div>
            ) : (
              recentDevelopments.map((dev) => {
                const states = Array.isArray(dev.states) ? dev.states : [];
                return (
                  <div
                    key={dev.article_id}
                    className="intel-dev-row"
                    onClick={() => onNavigate?.("live")}
                  >
                    <div className="intel-dev-header">
                      <span className="intel-dev-location">
                        {states.length > 0 ? states.join(", ") : dev.source}
                      </span>
                      <span className="intel-dev-time">
                        {dev.published_at?.slice(0, 10) || "Recent"}
                      </span>
                    </div>
                    <div className="intel-dev-title">{dev.title}</div>
                    <div className="intel-dev-meta">
                      <span className={`status-badge ${(dev.threat_level || "normal").toLowerCase()}`}>
                        {dev.threat_level || "Normal"}
                      </span>
                      <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                        {dev.source}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Card 2: Top Active Locations Table */}
        <div className="intel-card">
          <div className="intel-card-header">
            <h3 className="intel-card-title">
              <Icon name="location" size={15} color="var(--accent-secondary)" />
              <span>Top Active Locations</span>
            </h3>
            <button
              className="btn-secondary-subtle"
              style={{ height: 26, padding: "0 8px", fontSize: 11 }}
              onClick={() => onNavigate?.("locations")}
            >
              View All
            </button>
          </div>
          <table className="intel-table">
            <thead>
              <tr>
                <th>Location</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Articles</th>
              </tr>
            </thead>
            <tbody>
              {topLocations.length === 0 ? (
                <tr>
                  <td colSpan="3" style={{ textAlign: "center", color: "var(--text-muted)", padding: 20 }}>
                    Loading geographic activity...
                  </td>
                </tr>
              ) : (
                topLocations.map((loc) => (
                  <tr
                    key={loc.name}
                    style={{ cursor: "pointer" }}
                    onClick={() => {
                      onSelectLocation?.({ name: loc.name, state: loc.name });
                      onNavigate?.("locations");
                    }}
                  >
                    <td className="location-name">{loc.name}</td>
                    <td>
                      <span
                        className={`status-badge ${
                          loc.high_threat > 0 ? "immediate" : loc.monitoring > 0 ? "surveillance" : "normal"
                        }`}
                      >
                        {loc.high_threat > 0 ? "Immediate" : loc.monitoring > 0 ? "Surveillance" : "Normal"}
                      </span>
                    </td>
                    <td className="numeric-val">{loc.total}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Card 3: Top Reporting Sources */}
        <div className="intel-card">
          <div className="intel-card-header">
            <h3 className="intel-card-title">
              <Icon name="database" size={15} color="var(--text-secondary)" />
              <span>Top Verified Sources</span>
            </h3>
            <span className="intel-card-badge">Ingested Feeds</span>
          </div>
          <div className="intel-rank-list">
            {topSources.length === 0 ? (
              <div style={{ padding: 20, textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
                Loading source ingestion stats...
              </div>
            ) : (
              topSources.map((src) => (
                <div key={src.name} className="intel-rank-item">
                  <div>
                    <div className="rank-item-label">{src.name}</div>
                    <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{src.category}</div>
                  </div>
                  <div className="rank-item-val">{src.articles}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Analytics & Trend Visualizations */}
      <div className="analytical-grid-3" style={{ gridTemplateColumns: "1.3fr 1fr" }}>
        {/* Live Reporting Volume Trend */}
        <div className="intel-card">
          <div className="intel-card-header">
            <h3 className="intel-card-title">
              <Icon name="trend" size={15} color="var(--accent-secondary)" />
              <span>Article Ingestion Activity Trend</span>
            </h3>
            <span className="intel-card-badge">Recent Volume</span>
          </div>
          <div style={{ height: 220, width: "100%" }}>
            {dailyTrendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dailyTrendData} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
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
                    name="Daily Articles"
                    stroke="#1E3A8A"
                    strokeWidth={2.5}
                    dot={{ fill: "#1E3A8A", r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ padding: 60, textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
                Aggregating activity trends...
              </div>
            )}
          </div>
        </div>

        {/* Live Category Distribution */}
        <div className="intel-card">
          <div className="intel-card-header">
            <h3 className="intel-card-title">
              <Icon name="grid" size={15} color="var(--accent-secondary)" />
              <span>Category Distribution</span>
            </h3>
            <span className="intel-card-badge">Classified Domains</span>
          </div>
          <div style={{ height: 220, width: "100%" }}>
            {categoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryData} layout="vertical" margin={{ top: 0, right: 20, left: 30, bottom: 0 }}>
                  <XAxis type="number" tick={{ fontSize: 10, fill: "#64748B" }} axisLine={false} tickLine={false} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: "#475569" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      background: "#FFFFFF",
                      border: "1px solid #E2E8F0",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {categoryData.map((_, index) => (
                      <Cell key={index} fill="#1E3A8A" fillOpacity={1 - index * 0.12} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ padding: 60, textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
                Loading categories...
              </div>
            )}
          </div>
        </div>
      </div>

      {/* AI Situation Brief Card */}
      <div className="ai-brief-card">
        <div className="ai-brief-header">
          <div className="ai-brief-title-box">
            <h3 className="intel-card-title">AI Situation Brief</h3>
            <span className="ai-badge-label">Gemini 2.5 Analysis</span>
          </div>
          <button
            className="btn-secondary-subtle"
            onClick={() => onNavigate?.("reports")}
          >
            <span>View Detailed Strategic Brief</span>
            <Icon name="arrow-up-right" size={12} />
          </button>
        </div>

        <div className="ai-brief-text-content">
          {aiBriefText || (
            "No daily strategic brief synthesized yet. Click 'View Detailed Strategic Brief' or navigate to Reports to generate real-time AI synthesis from current database articles."
          )}
        </div>

        <div className="ai-brief-meta-bar">
          <div>
            Based on <strong>{totalArticles.toLocaleString()} articles</strong> across {activeSourcesCount} configured sources
          </div>
          <div style={{ display: "flex", gap: 16 }}>
            <span>Confidence: <strong style={{ color: "var(--threat-green)" }}>High</strong></span>
            <span>Live Analysis</span>
          </div>
        </div>
      </div>
    </div>
  );
}
