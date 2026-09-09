/**
 * Shared UI components for the Intelligence Platform
 */

// ============================================================
// THREAT BADGE
// ============================================================
export function ThreatBadge({ level }) {
  if (!level) return null;
  const l = String(level).toUpperCase();
  const icons = { CRITICAL: "🔴", HIGH: "🟠", MODERATE: "🟡", LOW: "🟢", UNCLEAR: "⚪" };
  return (
    <span className={`threat-badge ${l}`}>
      {icons[l] || "◯"} {l}
    </span>
  );
}

// ============================================================
// MONITORING BADGE
// ============================================================
export function MonitoringBadge({ value, label = "MONITOR" }) {
  if (!value) return null;
  const v = String(value).toUpperCase();
  return (
    <span className={`monitoring-badge ${v}`}>
      {v === "YES" ? "👁️ " : ""}{label}: {v}
    </span>
  );
}

// ============================================================
// SENTIMENT BADGE
// ============================================================
export function SentimentBadge({ sentiment }) {
  if (!sentiment) return null;
  return <span className={`sentiment-badge ${sentiment}`}>{sentiment}</span>;
}

// ============================================================
// AI DISCLAIMER
// ============================================================
export function AiDisclaimer({ short = false }) {
  return (
    <div className="ai-disclaimer">
      <span className="ai-badge">AI Flag</span>
      {short
        ? "All threat indicators are AI-generated analytical flags only."
        : "All threat levels, monitoring flags, and intervention indicators shown are AI-generated analytical flags only. They do NOT constitute official intelligence assessments or operational recommendations."}
    </div>
  );
}

// ============================================================
// LOADING / ERROR / EMPTY
// ============================================================
export function LoadingCard({ label = "Loading..." }) {
  return (
    <div className="loading-state">
      <div className="loading-spinner" />
      <div style={{ color: "var(--text-muted)", fontSize: 12 }}>{label}</div>
    </div>
  );
}

export function ErrorCard({ message, onRetry }) {
  return (
    <div className="empty-state">
      <div style={{ fontSize: 24, marginBottom: 8 }}>⚠️</div>
      <div style={{ color: "var(--threat-high)", marginBottom: 12, fontSize: 13 }}>
        {message || "Failed to load data"}
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            background: "var(--accent-primary)", color: "var(--bg-primary)",
            border: "none", borderRadius: 6, padding: "8px 16px",
            cursor: "pointer", fontSize: 12, fontWeight: 700, fontFamily: "inherit",
          }}
        >
          Retry
        </button>
      )}
    </div>
  );
}

// ============================================================
// ARTICLE CARD
// ============================================================
export function ArticleCard({ article, onClick }) {
  const level = (article.threat_level || "UNCLEAR").toUpperCase();
  const isHighThreat = level === "HIGH";
  const isCritical = level === "CRITICAL";

  const states = Array.isArray(article.states) ? article.states : safeParseJson(article.states);
  const categories = Array.isArray(article.primary_categories)
    ? article.primary_categories
    : safeParseJson(article.primary_categories);

  return (
    <div
      className={`article-card ${isCritical ? "critical-threat" : isHighThreat ? "high-threat" : ""}`}
      onClick={onClick}
    >
      <div className="article-meta">
        <ThreatBadge level={level} />
        {article.sentiment && <SentimentBadge sentiment={article.sentiment} />}
        {article.army_monitoring_needed === "YES" && (
          <MonitoringBadge value="YES" label="MONITOR" />
        )}
      </div>

      <div className="article-title">
        {article.url ? (
          <a href={article.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
            {article.title || "Untitled"}
          </a>
        ) : (
          article.title || "Untitled"
        )}
      </div>

      <div className="article-meta">
        <span className="article-source">{article.source || "Unknown"}</span>
        {article.published_at && (
          <span className="article-date">
            {formatDate(article.published_at)}
          </span>
        )}
        {states.length > 0 && (
          <span className="article-location">📍 {states.slice(0, 2).join(", ")}</span>
        )}
      </div>

      {(article.ai_summary || article.summary) && (
        <div className="article-summary">
          {(article.ai_summary || article.summary).slice(0, 200)}
          {(article.ai_summary || article.summary).length > 200 ? "…" : ""}
        </div>
      )}

      {categories.length > 0 && (
        <div className="article-tags">
          {categories.slice(0, 3).map((cat) => (
            <span key={cat} className="article-tag">{cat}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================
// HELPERS
// ============================================================
export function safeParseJson(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  try { return JSON.parse(value) || []; } catch { return []; }
}

export function formatDate(dateStr) {
  if (!dateStr) return "N/A";
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  } catch { return dateStr; }
}

export function formatThreatForChart(distribution) {
  const order = ["CRITICAL", "HIGH", "MODERATE", "LOW", "UNCLEAR"];
  const colors = {
    CRITICAL: "#ff2d55",
    HIGH: "#ff6b35",
    MODERATE: "#f5a623",
    LOW: "#30d158",
    UNCLEAR: "#636e7e",
  };
  return order
    .filter((k) => distribution?.[k])
    .map((k) => ({ name: k, value: distribution[k], fill: colors[k] }));
}
