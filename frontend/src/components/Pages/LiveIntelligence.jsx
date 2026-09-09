import React, { useState, useEffect } from "react";
import { Icon } from "../Shared/Icons.jsx";
import { getIntelligenceArticles } from "../../services/api";

export function LiveIntelligence({ onNavigate }) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [filters, setFilters] = useState({
    threat_level: "",
    sentiment: "",
    state: "",
    source: "",
    days: "",
    article_type: "",
  });

  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filters.threat_level) params.threat_level = filters.threat_level;
      if (filters.sentiment) params.sentiment = filters.sentiment;
      if (filters.state) params.state = filters.state;
      if (filters.source) params.source = filters.source;
      if (filters.days) params.days = filters.days;
      if (filters.article_type) params.article_type = filters.article_type;
      params.limit = 60;

      const data = await getIntelligenceArticles(params);
      const loaded = data.articles || [];
      setArticles(loaded);
      if (loaded.length > 0 && !selectedArticle) {
        setSelectedArticle(loaded[0]);
      }
    } catch (err) {
      console.error("Live intelligence fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  const getThreatBadge = (level) => {
    const l = (level || "UNCLEAR").toUpperCase();
    if (l === "CRITICAL" || l === "HIGH") {
      return <span className="status-badge immediate">{l}</span>;
    }
    if (l === "MODERATE") {
      return <span className="status-badge surveillance">Surveillance</span>;
    }
    return <span className="status-badge normal">Normal</span>;
  };

  return (
    <div>
      <div className="page-title-row">
        <div>
          <h1 className="page-heading">Live Intelligence Feed</h1>
          <p className="page-subheading">
            Continuous stream — D-P2-21 multi-source ingestion (GDELT · WorldBank · SQL · RSS) + automated NLP enrichment.
          </p>
        </div>
        <div className="filter-action-buttons">
          <button className="btn-secondary-subtle" onClick={loadData}>
            <Icon name="refresh" size={13} />
            <span>Refresh Feed</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="global-filters-bar" style={{ marginBottom: 16 }}>
        <div className="filter-controls-group">
          <div className="filter-select-wrapper">
            <select
              className="filter-select"
              value={filters.threat_level}
              onChange={(e) => setFilters((f) => ({ ...f, threat_level: e.target.value }))}
            >
              <option value="">All Threat Levels</option>
              <option value="CRITICAL">Critical Priority</option>
              <option value="HIGH">High Threat</option>
              <option value="MODERATE">Surveillance Required</option>
              <option value="LOW">Normal Activity</option>
            </select>
            <div className="filter-select-arrow"><Icon name="chevron-down" size={12} /></div>
          </div>

          <div className="filter-select-wrapper">
            <select
              className="filter-select"
              value={filters.days}
              onChange={(e) => setFilters((f) => ({ ...f, days: e.target.value }))}
            >
              <option value="">All Time</option>
              <option value="1">Last 24 Hours</option>
              <option value="3">Last 3 Days</option>
              <option value="7">Last 7 Days</option>
              <option value="30">Last 30 Days</option>
            </select>
            <div className="filter-select-arrow"><Icon name="chevron-down" size={12} /></div>
          </div>

          <input
            type="text"
            className="filter-select"
            style={{ width: 180, paddingRight: 10 }}
            placeholder="Filter location..."
            value={filters.state}
            onChange={(e) => setFilters((f) => ({ ...f, state: e.target.value }))}
          />

          <div className="filter-select-wrapper">
            <select
              className="filter-select"
              value={filters.source}
              onChange={(e) => setFilters((f) => ({ ...f, source: e.target.value }))}
            >
              <option value="">All Sources</option>
              <option value="gdelt">GDELT Geopolitical</option>
              <option value="World Bank / SIPRI">World Bank / SIPRI</option>
              <option value="Strategic Intelligence DB">Strategic Intel DB</option>
            </select>
            <div className="filter-select-arrow"><Icon name="chevron-down" size={12} /></div>
          </div>
        </div>


        <div className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
          {articles.length} Classified Items
        </div>
      </div>

      {/* Split Feed & Article Dossier */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 18, alignItems: "start" }}>
        {/* Left Column: Dense Article Stream */}
        <div className="intel-card" style={{ padding: "12px 14px", maxHeight: "calc(100vh - 240px)", overflowY: "auto" }}>
          {loading ? (
            <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
              Loading intelligence feed...
            </div>
          ) : articles.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
              No intelligence items match the selected criteria.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {articles.map((art) => {
                const isSelected = selectedArticle?.article_id === art.article_id;
                const states = Array.isArray(art.states) ? art.states : [];
                return (
                  <div
                    key={art.article_id}
                    className="intel-dev-row"
                    style={{
                      background: isSelected ? "#FFFFFF" : "var(--bg-card-muted)",
                      borderColor: isSelected ? "var(--accent-secondary)" : undefined,
                      boxShadow: isSelected ? "var(--shadow-sm)" : undefined,
                    }}
                    onClick={() => setSelectedArticle(art)}
                  >
                    <div className="intel-dev-header">
                      <span className="intel-dev-location">
                        {states.length > 0 ? states.join(", ") : art.source || "Intelligence Wire"}
                      </span>
                      <span className="intel-dev-time">
                        {art.published_at?.slice(0, 10) || "Recent"}
                      </span>
                    </div>

                    <div className="intel-dev-title" style={{ fontSize: 13, marginBottom: 4 }}>
                      {art.title}
                    </div>

                    <div className="intel-dev-meta">
                      {getThreatBadge(art.threat_level)}
                      <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                        {art.source}
                      </span>
                      {art.source_category_hint && art.source_category_hint !== "Defence" && (
                        <span style={{
                          fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4,
                          background: art.source_category_hint === "Geopolitics"
                            ? "color-mix(in srgb, var(--accent-primary) 18%, transparent)"
                            : "color-mix(in srgb, var(--accent-secondary) 18%, transparent)",
                          color: art.source_category_hint === "Geopolitics"
                            ? "var(--accent-primary)" : "var(--accent-secondary)",
                        }}>
                          {art.source_category_hint}
                        </span>
                      )}
                      {art.army_monitoring_needed === "YES" && (
                        <span style={{ fontSize: 10, color: "var(--threat-amber)", fontWeight: 700 }}>
                          • MONITORING ACTIVE
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Full Intelligence Dossier Inspector (Section 28) */}
        {selectedArticle ? (
          <div className="intel-card" style={{ position: "sticky", top: 84, maxHeight: "calc(100vh - 240px)", overflowY: "auto" }}>
            <div className="intel-card-header">
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Icon name="file-text" size={15} color="var(--accent-primary)" />
                <span className="intel-card-title">Article Intelligence Record</span>
              </div>
              {getThreatBadge(selectedArticle.threat_level)}
            </div>

            <div style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {selectedArticle.source} • {selectedArticle.published_at || "Recent Reporting"}
                </span>
                {selectedArticle.source_category_hint && (
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: "1px 7px", borderRadius: 4,
                    background: "color-mix(in srgb, var(--accent-primary) 18%, transparent)",
                    color: "var(--accent-primary)",
                  }}>
                    {selectedArticle.source_category_hint}
                  </span>
                )}
                {selectedArticle.p2_source_type && (
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: "1px 7px", borderRadius: 4,
                    background: "color-mix(in srgb, var(--text-muted) 12%, transparent)",
                    color: "var(--text-muted)",
                  }}>
                    P2·{selectedArticle.p2_source_type}
                  </span>
                )}
              </div>
              <h3 style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)", lineHeight: 1.35 }}>
                {selectedArticle.title}
              </h3>
            </div>

            {/* AI Summary */}
            <div style={{ background: "var(--bg-app)", padding: 14, borderRadius: 8, marginBottom: 16 }}>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--accent-primary)", marginBottom: 4 }}>
                AI-Generated Executive Summary
              </div>
              <p style={{ fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                {selectedArticle.ai_summary || selectedArticle.summary || "No executive summary cached."}
              </p>
            </div>

            {/* AI Threat Reasoning */}
            {selectedArticle.threat_reason && (
              <div style={{ borderLeft: "3px solid var(--threat-amber)", paddingLeft: 10, marginBottom: 16 }}>
                <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)" }}>
                  Analytical Assessment Reason
                </div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                  {selectedArticle.threat_reason}
                </div>
              </div>
            )}

            {/* Structured Analytical Indicators Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
              {[
                ["National Security", selectedArticle.national_security_relevance],
                ["Military Relevance", selectedArticle.military_relevance],
                ["Strategic Significance", selectedArticle.strategic_importance],
                ["Escalation Risk", selectedArticle.escalation_risk],
              ].map(([lbl, val]) => (
                <div key={lbl} style={{ background: "var(--bg-card-muted)", padding: "8px 10px", borderRadius: 6, border: "1px solid var(--border-subtle)" }}>
                  <div style={{ fontSize: 9, color: "var(--text-muted)", textTransform: "uppercase" }}>{lbl}</div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
                    {val || "Normal"}
                  </div>
                </div>
              ))}
            </div>

            {/* Entities & Equipment */}
            {Array.isArray(selectedArticle.organizations) && selectedArticle.organizations.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 4 }}>
                  Identified Organizations
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {selectedArticle.organizations.map((org) => (
                    <span key={org} className="analytical-tag">
                      {org}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {Array.isArray(selectedArticle.equipment) && selectedArticle.equipment.length > 0 && (
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 4 }}>
                  Identified Equipment / Assets
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {selectedArticle.equipment.map((eq) => (
                    <span key={eq} className="analytical-tag primary">
                      <Icon name="shield" size={10} />
                      {eq}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* GDELT Topics (if applicable) */}
            {Array.isArray(selectedArticle.gdelt_topics) && selectedArticle.gdelt_topics.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 4 }}>
                  GDELT Matched Topics
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {selectedArticle.gdelt_topics.map((t) => (
                    <span key={t} className="analytical-tag">{t}</span>
                  ))}
                </div>
              </div>
            )}

            {/* WorldBank Data (if applicable) */}
            {selectedArticle.worldbank_data && (
              <div style={{ marginBottom: 12, background: "var(--bg-app)", borderRadius: 8, padding: "10px 12px", border: "1px solid var(--border-subtle)" }}>
                <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--accent-secondary)", marginBottom: 6 }}>World Bank Military Data</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                  {Object.entries(selectedArticle.worldbank_data).map(([k, v]) => (
                    <div key={k}>
                      <div style={{ fontSize: 9, color: "var(--text-muted)", textTransform: "uppercase" }}>{k.replace(/_/g, " ")}</div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>{v || "—"}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Source Reference Link */}
            {selectedArticle.url && (
              <a
                href={selectedArticle.url}
                target="_blank"
                rel="noreferrer"
                className="btn-primary-dark"
                style={{ display: "inline-flex", justifyContent: "center", width: "100%" }}
              >
                <span>Read Original Full Source Document</span>
                <Icon name="arrow-up-right" size={12} />
              </a>
            )}
          </div>
        ) : (
          <div className="intel-card" style={{ textAlign: "center", padding: 40, color: "var(--text-muted)" }}>
            Select an article from the live stream to inspect its intelligence record.
          </div>
        )}
      </div>
    </div>
  );
}
