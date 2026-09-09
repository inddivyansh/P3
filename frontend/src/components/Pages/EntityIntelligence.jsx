import React, { useState, useEffect } from "react";
import { Icon } from "../Shared/Icons.jsx";
import { getEntityAnalysis, getIntelligenceArticles } from "../../services/api";

export function EntityIntelligence() {
  const [activeType, setActiveType] = useState("organizations");
  const [entities, setEntities] = useState([]);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [relatedArticles, setRelatedArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEntities();
  }, [activeType]);

  const loadEntities = async () => {
    try {
      setLoading(true);
      const data = await getEntityAnalysis(activeType, 30);
      const list = data?.entities || [];
      setEntities(list);
      if (list.length > 0) {
        setSelectedEntity(list[0]);
        loadArticlesForEntity(list[0].name);
      }
    } catch (err) {
      console.error("Failed to load live entities:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadArticlesForEntity = async (name) => {
    try {
      const data = await getIntelligenceArticles({ source: name, limit: 6 });
      setRelatedArticles(data.articles || []);
    } catch (err) {
      console.error("Failed to load entity articles:", err);
    }
  };

  const handleSelect = (ent) => {
    setSelectedEntity(ent);
    loadArticlesForEntity(ent.name);
  };

  return (
    <div>
      <div className="page-title-row">
        <div>
          <h1 className="page-heading">Entity Intelligence Dossier</h1>
          <p className="page-subheading">
            Extract and track defence institutions, armed forces, weapons platforms, and international actors from database.
          </p>
        </div>
      </div>

      {/* Entity Type Filter Tabs */}
      <div className="tab-list" style={{ maxWidth: 540, marginBottom: 18 }}>
        {[
          { id: "organizations", label: "Organizations & Forces", icon: "shield" },
          { id: "equipment", label: "Weapons & Equipment", icon: "radar" },
          { id: "countries", label: "Countries & Actors", icon: "globe" },
          { id: "people", label: "Leadership & Personnel", icon: "users" },
        ].map((t) => (
          <button
            key={t.id}
            className={`tab-btn ${activeType === t.id ? "active" : ""}`}
            onClick={() => setActiveType(t.id)}
          >
            <Icon name={t.icon} size={12} />
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="intel-card" style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
          Loading live entity graph from database...
        </div>
      ) : entities.length === 0 ? (
        <div className="intel-card" style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
          No entities extracted for this category yet. Run the pipeline to extract NLP entities.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: 20 }}>
          {/* Entity List */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: "calc(100vh - 240px)", overflowY: "auto" }}>
            {entities.map((ent) => {
              const isSelected = selectedEntity?.name === ent.name;
              return (
                <div
                  key={ent.name}
                  className="intel-card"
                  style={{
                    padding: "14px 16px",
                    cursor: "pointer",
                    borderLeft: isSelected ? "4px solid var(--accent-primary)" : "4px solid transparent",
                    borderColor: isSelected ? "var(--accent-secondary)" : undefined,
                    background: isSelected ? "#FFFFFF" : "var(--bg-card-muted)",
                    boxShadow: isSelected ? "var(--shadow-sm)" : undefined,
                  }}
                  onClick={() => handleSelect(ent)}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                      {ent.name}
                    </div>
                    <div className="mono" style={{ fontSize: 12, fontWeight: 800, color: "var(--accent-secondary)" }}>
                      {ent.count} <span style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 500 }}>mentions</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Selected Entity Deep Inspector */}
          {selectedEntity && (
            <div className="intel-card" style={{ position: "sticky", top: 84 }}>
              <div className="intel-card-header">
                <div>
                  <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)" }}>
                    {activeType.toUpperCase()} INTELLIGENCE
                  </span>
                  <h2 style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                    {selectedEntity.name}
                  </h2>
                </div>
                <span className="intel-card-badge">{selectedEntity.count} Ingested References</span>
              </div>

              {/* Mentions Frequency Metric */}
              <div style={{ background: "var(--bg-app)", padding: 14, borderRadius: 8, marginBottom: 18 }}>
                <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--accent-primary)", marginBottom: 4 }}>
                  Entity Intelligence Frequency
                </div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                  Extracted in <strong>{selectedEntity.count} distinct news articles</strong> across defence, national security, and geopolitical reports in the active database.
                </div>
              </div>

              {/* Related Ingested Intelligence Items */}
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 8 }}>
                  Recent Ingested Intelligence Items
                </div>
                {relatedArticles.length === 0 ? (
                  <div style={{ fontSize: 12, color: "var(--text-muted)", padding: 10 }}>
                    Cross-referencing active database documents...
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {relatedArticles.map((art) => (
                      <div key={art.article_id} className="intel-dev-row">
                        <div className="intel-dev-header">
                          <span className="intel-dev-location">{art.source}</span>
                          <span className="intel-dev-time">{art.published_at?.slice(0, 10)}</span>
                        </div>
                        <div className="intel-dev-title">{art.title}</div>
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
