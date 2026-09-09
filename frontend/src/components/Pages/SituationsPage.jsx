import React, { useState, useEffect } from "react";
import { Icon } from "../Shared/Icons.jsx";
import { getMapLocations, getIntelligenceArticles, getSituationBrief } from "../../services/api";

export function SituationsPage({ onNavigate }) {
  const [sectors, setSectors] = useState([]);
  const [activeSector, setActiveSector] = useState(null);
  const [sectorArticles, setSectorArticles] = useState([]);
  const [situationBrief, setSituationBrief] = useState(null);
  const [loadingBrief, setLoadingBrief] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSectors();
  }, []);

  const loadSectors = async () => {
    try {
      setLoading(true);
      const data = await getMapLocations();
      const locs = data?.locations || [];
      setSectors(locs);
      if (locs.length > 0) {
        handleSelectSector(locs[0]);
      }
    } catch (err) {
      console.error("Failed to load situation sectors:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSector = async (sector) => {
    setActiveSector(sector);
    setSituationBrief(null);

    // Fetch chronological articles for this sector
    try {
      const artRes = await getIntelligenceArticles({
        state: sector.state || sector.name,
        limit: 10,
      });
      setSectorArticles(artRes.articles || []);
    } catch (err) {
      console.error("Failed to load sector articles:", err);
      setSectorArticles([]);
    }

    // Fetch AI situation brief from backend endpoint
    try {
      setLoadingBrief(true);
      const briefRes = await getSituationBrief(sector.name || sector.state);
      setSituationBrief(briefRes.brief || null);
    } catch (err) {
      console.error("Failed to load situation brief:", err);
    } finally {
      setLoadingBrief(false);
    }
  };

  return (
    <div>
      <div className="page-title-row">
        <div>
          <h1 className="page-heading">Consolidated Situations</h1>
          <p className="page-subheading">
            Sector dossiers synthesizing live article timelines, geographic footprint, and AI situation briefs from database feeds.
          </p>
        </div>
        <div className="filter-action-buttons">
          <button className="btn-secondary-subtle" onClick={loadSectors}>
            <Icon name="refresh" size={13} />
            <span>Refresh Sectors</span>
          </button>
          <button className="btn-primary-dark" onClick={() => onNavigate?.("chat")}>
            <Icon name="bot" size={13} />
            <span>Analyze with AI</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="intel-card" style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
          Loading situation dossiers from database...
        </div>
      ) : sectors.length === 0 ? (
        <div className="intel-card" style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
          <Icon name="radar" size={32} color="var(--text-muted)" />
          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginTop: 12 }}>
            No Active Situations Detected
          </div>
          <p style={{ fontSize: 12.5, color: "var(--text-secondary)", marginTop: 4 }}>
            No geographic clusters or situation dossiers found in database. Run the pipeline to ingest live feeds.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: 20 }}>
          {/* Situation / Sector List */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: "calc(100vh - 240px)", overflowY: "auto" }}>
            {sectors.map((sec) => {
              const isSelected = activeSector?.id === sec.id;
              const isHigh = sec.threatLevel === "CRITICAL" || sec.threatLevel === "HIGH";
              return (
                <div
                  key={sec.id}
                  className="intel-card"
                  style={{
                    padding: "16px 18px",
                    cursor: "pointer",
                    borderLeft: `4px solid ${
                      isHigh
                        ? "var(--threat-red)"
                        : sec.threatLevel === "MODERATE"
                        ? "var(--threat-amber)"
                        : "var(--threat-green)"
                    }`,
                    borderColor: isSelected ? "var(--accent-secondary)" : undefined,
                    background: isSelected ? "#FFFFFF" : "var(--bg-card-muted)",
                    boxShadow: isSelected ? "var(--shadow-md)" : "var(--shadow-sm)",
                  }}
                  onClick={() => handleSelectSector(sec)}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: "var(--accent-secondary)" }}>
                      {sec.state ? `${sec.state}, India` : "Strategic Sector"}
                    </span>
                    <span
                      className={`status-badge ${
                        isHigh ? "immediate" : sec.threatLevel === "MODERATE" ? "surveillance" : "normal"
                      }`}
                    >
                      {sec.threatLevel === "CRITICAL" || sec.threatLevel === "HIGH"
                        ? "Immediate"
                        : sec.threatLevel === "MODERATE"
                        ? "Surveillance"
                        : "Normal"}
                    </span>
                  </div>

                  <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8, lineHeight: 1.35 }}>
                    {sec.name}
                  </div>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 11, color: "var(--text-muted)" }}>
                    <span>{sec.articleCount} Related Articles</span>
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <Icon name="activity" size={11} />
                      <span>{sec.trendText || "Active Feed"}</span>
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Situation Detailed Dossier */}
          {activeSector && (
            <div className="intel-card" style={{ position: "sticky", top: 84, maxHeight: "calc(100vh - 240px)", overflowY: "auto" }}>
              <div className="intel-card-header">
                <div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                    {activeSector.state} Sector • {activeSector.coordinates}
                  </div>
                  <h3 style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                    {activeSector.name}
                  </h3>
                </div>
                <span className={`status-badge ${
                  activeSector.threatLevel === "CRITICAL" || activeSector.threatLevel === "HIGH"
                    ? "immediate"
                    : activeSector.threatLevel === "MODERATE"
                    ? "surveillance"
                    : "normal"
                }`}>
                  {activeSector.threatLevel}
                </span>
              </div>

              {/* AI Situation Brief Box */}
              <div style={{ background: "var(--bg-app)", padding: 14, borderRadius: 8, marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--accent-primary)" }}>
                    AI Situation Assessment
                  </div>
                  <span className="ai-badge-label">Live Synthesis</span>
                </div>
                {loadingBrief ? (
                  <div style={{ fontSize: 12, color: "var(--text-muted)", padding: "10px 0" }}>
                    <Icon name="refresh" size={12} className="spin-animate" /> Generating AI situation analysis...
                  </div>
                ) : situationBrief ? (
                  <div style={{ fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                    {typeof situationBrief === "string" ? (
                      situationBrief
                    ) : (
                      <>
                        {situationBrief.current_assessment && (
                          <div style={{ marginBottom: 6 }}>{situationBrief.current_assessment}</div>
                        )}
                        {situationBrief.security_relevance && (
                          <div style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 4 }}>
                            <strong>Relevance:</strong> {situationBrief.security_relevance}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {activeSector.recentDevelopments?.[0] || "Active reporting tracked in database."}
                  </div>
                )}
              </div>

              {/* Sector Sources */}
              {activeSector.sources?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 6 }}>
                    Reporting Sources ({activeSector.sources.length})
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {activeSector.sources.map((src, i) => (
                      <span key={i} className="source-chip" style={{ fontSize: 11, padding: "3px 8px" }}>
                        {src}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Chronological Article Timeline from Database */}
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 10 }}>
                  Chronological Article Sequence ({sectorArticles.length})
                </div>
                {sectorArticles.length === 0 ? (
                  <div style={{ fontSize: 12, color: "var(--text-muted)", padding: 10 }}>
                    No chronological articles recorded for this sector.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10, paddingLeft: 8, borderLeft: "2px solid var(--border-subtle)" }}>
                    {sectorArticles.map((art, idx) => (
                      <div key={art.article_id || idx} style={{ position: "relative", paddingLeft: 12 }}>
                        <div style={{ position: "absolute", left: -14, top: 4, width: 6, height: 6, borderRadius: "50%", background: "var(--accent-secondary)" }} />
                        <div className="mono" style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 2 }}>
                          {art.published_at ? art.published_at.slice(0, 16) : "Recent"} • {art.source}
                        </div>
                        <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>
                          {art.url ? (
                            <a href={art.url} target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "none" }}>
                              {art.title}
                            </a>
                          ) : (
                            art.title
                          )}
                        </div>
                        {art.ai_summary && (
                          <div style={{ fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.4 }}>
                            {art.ai_summary.slice(0, 140)}...
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
