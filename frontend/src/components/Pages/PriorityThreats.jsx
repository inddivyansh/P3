import React, { useState, useEffect } from "react";
import { Icon } from "../Shared/Icons.jsx";
import { getIntelligenceArticles } from "../../services/api";

export function PriorityThreats({ onNavigate }) {
  const [threatList, setThreatList] = useState([]);
  const [selectedThreat, setSelectedThreat] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadThreats();
  }, []);

  const loadThreats = async () => {
    try {
      setLoading(true);
      const [criticalRes, highRes] = await Promise.allSettled([
        getIntelligenceArticles({ threat_level: "CRITICAL", limit: 25 }),
        getIntelligenceArticles({ threat_level: "HIGH", limit: 25 }),
      ]);

      const merged = [];
      const seenIds = new Set();

      if (criticalRes.status === "fulfilled" && criticalRes.value?.articles) {
        for (const art of criticalRes.value.articles) {
          if (!seenIds.has(art.article_id)) {
            seenIds.add(art.article_id);
            merged.push(art);
          }
        }
      }

      if (highRes.status === "fulfilled" && highRes.value?.articles) {
        for (const art of highRes.value.articles) {
          if (!seenIds.has(art.article_id)) {
            seenIds.add(art.article_id);
            merged.push(art);
          }
        }
      }

      const formatted = merged.map((item, idx) => {
        const states = Array.isArray(item.states) ? item.states : [];
        const cities = Array.isArray(item.cities) ? item.cities : [];
        const locStr = [...cities, ...states].join(", ") || (item.countries && item.countries.length > 0 ? item.countries.join(", ") : "National / Strategic");
        const level = (item.threat_level || "HIGH").toUpperCase();

        return {
          id: item.article_id || `pt-${idx}`,
          rank: String(idx + 1).padStart(2, "0"),
          title: item.title,
          location: locStr,
          threatLevel: level,
          threatReason: item.threat_reason || item.ai_summary || "Analytical threat indicator flagged during pipeline NLP processing.",
          summary: item.ai_summary || item.summary || "",
          source: item.source || "Intelligence Feed",
          publishedAt: item.published_at ? item.published_at.slice(0, 10) : "Recent",
          category: item.article_type || "National Security",
          nationalSecurityRelevance: item.national_security_relevance || "N/A",
          militaryRelevance: item.military_relevance || "N/A",
          strategicImportance: item.strategic_importance || "High",
          escalationRisk: item.escalation_risk || "N/A",
          monitoringNeeded: item.army_monitoring_needed === "YES",
          url: item.url || "",
          raw: item,
        };
      });

      setThreatList(formatted);
      if (formatted.length > 0) {
        setSelectedThreat(formatted[0]);
      } else {
        setSelectedThreat(null);
      }
    } catch (err) {
      console.error("Failed to load priority threats:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-title-row">
        <div>
          <h1 className="page-heading">Priority Threats</h1>
          <p className="page-subheading">
            Live classified developments flagged as High or Critical threat level based on multi-stage NLP analysis.
          </p>
        </div>
        <div className="filter-action-buttons">
          <div className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
            {threatList.length} Flagged Articles
          </div>
          <button className="btn-secondary-subtle" onClick={loadThreats}>
            <Icon name="refresh" size={13} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div className="ai-brief-card" style={{ padding: "14px 18px", marginBottom: 20, background: "#FEF9EE", borderColor: "#FBECCB" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#92400E" }}>
          <Icon name="alert-triangle" size={14} color="#D69A1D" />
          <span>
            <strong>AI Analytical Indicators:</strong> Threat levels are automated NLP classifications derived from news keywords, operational indicators, and sentiment. They do not constitute official operational assessments.
          </span>
        </div>
      </div>

      {loading ? (
        <div className="intel-card" style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
          Loading priority threats from database...
        </div>
      ) : threatList.length === 0 ? (
        <div className="intel-card" style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
          <Icon name="check-circle" size={32} color="var(--threat-green)" />
          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginTop: 12 }}>
            No Critical or High Priority Threats Flagged
          </div>
          <p style={{ fontSize: 12.5, color: "var(--text-secondary)", marginTop: 4, maxWidth: 500, margin: "6px auto 0" }}>
            All currently ingested articles are operating within normal or moderate baseline parameters. Run the ingestion pipeline to process new RSS feeds.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20 }}>
          {/* Priority List */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {threatList.map((threat) => {
              const isSelected = selectedThreat?.id === threat.id;
              return (
                <div
                  key={threat.id}
                  className="intel-card"
                  style={{
                    padding: "18px 20px",
                    cursor: "pointer",
                    borderLeft: `4px solid ${
                      threat.threatLevel === "CRITICAL"
                        ? "var(--threat-red)"
                        : "var(--threat-red)"
                    }`,
                    borderColor: isSelected ? "var(--accent-secondary)" : undefined,
                    boxShadow: isSelected ? "var(--shadow-md)" : "var(--shadow-sm)",
                    background: isSelected ? "#FFFFFF" : "#FCFDFF",
                  }}
                  onClick={() => setSelectedThreat(threat)}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className="mono" style={{ fontSize: 13, fontWeight: 800, color: "var(--accent-secondary)" }}>
                        #{threat.rank}
                      </span>
                      <span
                        className={`status-badge ${
                          threat.threatLevel === "CRITICAL" ? "immediate" : "immediate"
                        }`}
                      >
                        {threat.threatLevel === "CRITICAL" ? "Critical Priority" : "High Threat"}
                      </span>
                      {threat.monitoringNeeded && (
                        <span className="status-badge surveillance" style={{ fontSize: 10 }}>
                          Monitoring Flagged
                        </span>
                      )}
                    </div>
                    <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
                      {threat.publishedAt}
                    </span>
                  </div>

                  <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 6 }}>
                    {threat.title}
                  </div>

                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 10, lineHeight: 1.45 }}>
                    {threat.threatReason.slice(0, 200)}
                    {threat.threatReason.length > 200 ? "..." : ""}
                  </div>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 11, color: "var(--text-muted)", paddingTop: 8, borderTop: "1px solid var(--border-subtle)" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <Icon name="location" size={12} />
                      <span>{threat.location}</span>
                    </span>
                    <span>{threat.source}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Selected Threat Detailed Inspector */}
          {selectedThreat && (
            <div className="intel-card" style={{ height: "fit-content", position: "sticky", top: 84 }}>
              <div className="intel-card-header">
                <h3 className="intel-card-title">
                  <Icon name="shield" size={15} color="var(--threat-red)" />
                  <span>Threat Intelligence Dossier #{selectedThreat.rank}</span>
                </h3>
                <span className={`status-badge ${selectedThreat.threatLevel === "CRITICAL" ? "immediate" : "immediate"}`}>
                  {selectedThreat.threatLevel}
                </span>
              </div>

              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 2 }}>
                  {selectedThreat.category} • {selectedThreat.publishedAt}
                </div>
                <h4 style={{ fontSize: 15, fontWeight: 800, color: "var(--text-primary)", lineHeight: 1.35 }}>
                  {selectedThreat.title}
                </h4>
              </div>

              {/* Real Analytical Indicators */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 14 }}>
                <div style={{ background: "var(--bg-app)", padding: "8px 10px", borderRadius: 6 }}>
                  <div style={{ fontSize: 9, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
                    Strategic Importance
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
                    {selectedThreat.strategicImportance}
                  </div>
                </div>
                <div style={{ background: "var(--bg-app)", padding: "8px 10px", borderRadius: 6 }}>
                  <div style={{ fontSize: 9, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
                    Escalation Risk
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: selectedThreat.escalationRisk.toLowerCase().includes("high") ? "var(--threat-red)" : "var(--text-primary)", marginTop: 2 }}>
                    {selectedThreat.escalationRisk}
                  </div>
                </div>
                <div style={{ background: "var(--bg-app)", padding: "8px 10px", borderRadius: 6 }}>
                  <div style={{ fontSize: 9, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
                    National Security
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
                    {selectedThreat.nationalSecurityRelevance}
                  </div>
                </div>
                <div style={{ background: "var(--bg-app)", padding: "8px 10px", borderRadius: 6 }}>
                  <div style={{ fontSize: 9, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
                    Military Relevance
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
                    {selectedThreat.militaryRelevance}
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 4 }}>
                  Analytical Assessment Reason
                </div>
                <p style={{ fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.55 }}>
                  {selectedThreat.threatReason}
                </p>
              </div>

              {selectedThreat.summary && selectedThreat.summary !== selectedThreat.threatReason && (
                <div style={{ marginBottom: 14 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 4 }}>
                    Executive Summary
                  </div>
                  <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {selectedThreat.summary}
                  </p>
                </div>
              )}

              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 4 }}>
                  Source Feed
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  <span className="source-chip" style={{ fontSize: 11, padding: "3px 8px" }}>
                    {selectedThreat.source}
                  </span>
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {selectedThreat.url && (
                  <a
                    href={selectedThreat.url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary-subtle"
                    style={{ display: "flex", justifyContent: "center", width: "100%" }}
                  >
                    <span>Read Original Source Article</span>
                    <Icon name="arrow-up-right" size={12} />
                  </a>
                )}
                <button
                  className="btn-primary-dark"
                  style={{ width: "100%", justifyContent: "center" }}
                  onClick={() => onNavigate?.("chat")}
                >
                  <Icon name="bot" size={13} />
                  <span>Analyze with AI Assistant</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
