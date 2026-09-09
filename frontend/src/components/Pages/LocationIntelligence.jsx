import React, { useState, useEffect } from "react";
import { Icon } from "../Shared/Icons.jsx";
import { getMapLocations, getGeographicIntelligence, getIntelligenceArticles } from "../../services/api";

export function LocationIntelligence({ initialLocation }) {
  const [locationsList, setLocationsList] = useState([]);
  const [selectedLoc, setSelectedLoc] = useState(null);
  const [locationArticles, setLocationArticles] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLocations();
  }, []);

  const loadLocations = async () => {
    try {
      setLoading(true);
      const data = await getMapLocations();
      const locs = data?.locations || [];
      setLocationsList(locs);

      let target = null;
      if (initialLocation?.name) {
        target = locs.find((l) => l.name.toLowerCase().includes(initialLocation.name.toLowerCase()));
      }
      if (!target && locs.length > 0) {
        target = locs[0];
      }
      setSelectedLoc(target);
      if (target) {
        setSearchQuery(target.name);
        loadArticlesForLoc(target.state || target.name);
      }
    } catch (err) {
      console.error("Failed to load location intelligence:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadArticlesForLoc = async (stateOrCity) => {
    try {
      const data = await getIntelligenceArticles({ state: stateOrCity, limit: 10 });
      setLocationArticles(data.articles || []);
    } catch (err) {
      console.error("Failed to load location articles:", err);
    }
  };

  const handleSelect = (loc) => {
    setSelectedLoc(loc);
    setSearchQuery(loc.name);
    loadArticlesForLoc(loc.state || loc.name);
  };

  const handleSearch = (name) => {
    setSearchQuery(name);
    const found = locationsList.find(
      (l) =>
        l.name.toLowerCase().includes(name.toLowerCase()) ||
        l.state.toLowerCase().includes(name.toLowerCase())
    );
    if (found) {
      setSelectedLoc(found);
      loadArticlesForLoc(found.state || found.name);
    }
  };

  return (
    <div>
      <div className="page-title-row">
        <div>
          <h1 className="page-heading">Location Intelligence Dossier</h1>
          <p className="page-subheading">
            Granular geographic profile, threat assessment, reporting volume, and strategic installation monitoring.
          </p>
        </div>
      </div>

      {/* Location Search Bar & Quick Location Chips */}
      <div className="intel-card" style={{ padding: "16px 20px", marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
          <div className="header-search-container" style={{ width: "100%" }}>
            <div className="header-search-icon"><Icon name="search" size={16} /></div>
            <input
              type="text"
              className="header-search-input"
              placeholder="Search active location or sector..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
            />
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
            Active Sectors:
          </span>
          {locationsList.slice(0, 10).map((loc) => (
            <button
              key={loc.id}
              className="btn-secondary-subtle"
              style={{
                height: 26,
                padding: "0 8px",
                fontSize: 11,
                background: selectedLoc?.id === loc.id ? "var(--bg-app)" : "#FFFFFF",
                borderColor: selectedLoc?.id === loc.id ? "var(--accent-secondary)" : undefined,
              }}
              onClick={() => handleSelect(loc)}
            >
              <span>{loc.name.split("&")[0].trim()}</span>
            </button>
          ))}
        </div>
      </div>

      {loading || !selectedLoc ? (
        <div className="intel-card" style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
          Loading location intelligence data...
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 20 }}>
          {/* Left Column: Location Assessment */}
          <div className="intel-card">
            <div className="intel-card-header">
              <div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {selectedLoc.state}, {selectedLoc.country} • {selectedLoc.coordinates}
                </div>
                <h2 style={{ fontSize: 20, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                  {selectedLoc.name}
                </h2>
              </div>
              <span
                className={`status-badge ${
                  selectedLoc.threatLevel === "CRITICAL" || selectedLoc.threatLevel === "HIGH"
                    ? "immediate"
                    : selectedLoc.threatLevel === "MODERATE"
                    ? "surveillance"
                    : "normal"
                }`}
              >
                {selectedLoc.threatLevel === "CRITICAL" || selectedLoc.threatLevel === "HIGH"
                  ? "Immediate Threat"
                  : selectedLoc.threatLevel === "MODERATE"
                  ? "Surveillance Required"
                  : "Normal Activity"}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 18 }}>
              <div style={{ background: "var(--bg-app)", padding: "10px 12px", borderRadius: 8 }}>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>Articles</div>
                <div className="mono" style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                  {selectedLoc.articleCount}
                </div>
              </div>
              <div style={{ background: "var(--bg-app)", padding: "10px 12px", borderRadius: 8 }}>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>AI Priority</div>
                <div className="mono" style={{ fontSize: 18, fontWeight: 800, color: selectedLoc.riskScore > 75 ? "var(--threat-red)" : "var(--accent-secondary)", marginTop: 2 }}>
                  {selectedLoc.riskScore}/100
                </div>
              </div>
              <div style={{ background: "var(--bg-app)", padding: "10px 12px", borderRadius: 8 }}>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>Trend</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
                  {selectedLoc.trendText}
                </div>
              </div>
            </div>

            {/* Recent Activity Developments from Database */}
            <div style={{ marginBottom: 18 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 8 }}>
                Recent Operational Developments
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {selectedLoc.recentDevelopments.map((dev, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    <div className="dev-bullet" style={{ marginTop: 7 }} />
                    <div>{dev}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Primary Strategic Focus */}
            <div style={{ background: "var(--bg-card-muted)", padding: 12, borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--accent-primary)", marginBottom: 3 }}>
                Sector Focus & Security Domain
              </div>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>
                {selectedLoc.primaryRisk}
              </div>
            </div>
          </div>

          {/* Right Column: Reporting Feeds & Articles */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Top Sources for Location */}
            <div className="intel-card">
              <div className="intel-card-header">
                <h3 className="intel-card-title">
                  <Icon name="database" size={15} color="var(--accent-secondary)" />
                  <span>Reporting Feeds ({selectedLoc.sources?.length || 0})</span>
                </h3>
              </div>
              <div className="intel-rank-list">
                {(selectedLoc.sources || []).map((src, i) => (
                  <div key={i} className="intel-rank-item">
                    <span className="rank-item-label">{src}</span>
                    <span className="rank-item-val" style={{ color: "var(--accent-secondary)" }}>
                      Live Feed
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Location Hierarchy Chain */}
            <div className="intel-card">
              <div className="intel-card-header">
                <h3 className="intel-card-title">
                  <Icon name="location" size={15} color="var(--accent-primary)" />
                  <span>Administrative Hierarchy</span>
                </h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ color: "var(--text-muted)", width: 70 }}>Country:</span>
                  <span style={{ fontWeight: 600 }}>{selectedLoc.country}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ color: "var(--text-muted)", width: 70 }}>State / UT:</span>
                  <span style={{ fontWeight: 600 }}>{selectedLoc.state}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ color: "var(--text-muted)", width: 70 }}>City / Sector:</span>
                  <span style={{ fontWeight: 600, color: "var(--accent-secondary)" }}>{selectedLoc.name}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
