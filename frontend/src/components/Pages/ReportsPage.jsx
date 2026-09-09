import React, { useState } from "react";
import { Icon } from "../Shared/Icons.jsx";
import { getDailyBrief, getSituationBrief, getCountryBrief } from "../../services/api";

export function ReportsPage() {
  const [activeTab, setActiveTab] = useState("daily");
  const [briefText, setBriefText] = useState("");
  const [loading, setLoading] = useState(false);
  const [topic, setTopic] = useState("Manipur Security Situation");

  const generateReport = async (type) => {
    try {
      setLoading(true);
      setBriefText("");
      let result;
      if (type === "daily") {
        result = await getDailyBrief();
        setBriefText(result.brief || "Strategic brief synthesized successfully.");
      } else if (type === "situation") {
        result = await getSituationBrief(topic);
        const b = result.brief || {};
        setBriefText(
          `## Executive Assessment\n${b.current_assessment || "Under observation."}\n\n## Security Relevance\n${b.security_relevance || "Routine."}\n\n## Trend\n${b.trend || "Stable"}`
        );
      } else if (type === "country") {
        result = await getCountryBrief("India-China");
        setBriefText(result.brief || "Bilateral relations brief generated.");
      }
    } catch (err) {
      setBriefText(`Report generation could not be completed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-title-row">
        <div>
          <h1 className="page-heading">Strategic Intelligence Reports & Digests</h1>
          <p className="page-subheading">
            AI-synthesized situation briefs, daily operational intelligence summaries, and bilateral security assessments.
          </p>
        </div>
        <div className="filter-action-buttons">
          <button className="btn-primary-dark" onClick={() => generateReport("daily")}>
            <Icon name="download" size={13} />
            <span>Generate Daily Brief</span>
          </button>
        </div>
      </div>

      <div className="tab-list" style={{ maxWidth: 460, marginBottom: 20 }}>
        <button
          className={`tab-btn ${activeTab === "daily" ? "active" : ""}`}
          onClick={() => { setActiveTab("daily"); generateReport("daily"); }}
        >
          Daily Strategic Digest
        </button>
        <button
          className={`tab-btn ${activeTab === "situation" ? "active" : ""}`}
          onClick={() => { setActiveTab("situation"); generateReport("situation"); }}
        >
          Situation Report
        </button>
        <button
          className={`tab-btn ${activeTab === "bilateral" ? "active" : ""}`}
          onClick={() => { setActiveTab("bilateral"); generateReport("country"); }}
        >
          Bilateral Dossier
        </button>
      </div>

      <div className="intel-card">
        <div className="intel-card-header">
          <div className="intel-card-title">
            <Icon name="file-text" size={15} color="var(--accent-primary)" />
            <span>
              {activeTab === "daily"
                ? "Daily Operational Intelligence Digest"
                : activeTab === "situation"
                ? `Situation Report: ${topic}`
                : "Bilateral Security Relations Dossier"}
            </span>
          </div>
          <span className="ai-badge-label">Gemini 2.5 Analysis</span>
        </div>

        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)", fontSize: 13 }}>
            <Icon name="refresh" size={16} className="spin-animate" color="var(--accent-secondary)" />
            <div style={{ marginTop: 8 }}>Synthesizing multi-source intelligence digest...</div>
          </div>
        ) : briefText ? (
          <div style={{ fontSize: 13.5, lineHeight: 1.7, color: "var(--text-secondary)", whiteSpace: "pre-line" }}>
            {briefText}
          </div>
        ) : (
          <div style={{ padding: 30, textAlign: "center", color: "var(--text-muted)", fontSize: 13 }}>
            Click above to generate the latest synthesized intelligence report from the active news database.
          </div>
        )}
      </div>
    </div>
  );
}
