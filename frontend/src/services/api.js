/**
 * Defence & Geopolitical Intelligence Platform — API Service Layer
 * Unified Edition: D-P2-21 Multi-Source Ingestion + NLP Pipeline
 * All endpoints connect to FastAPI backend at localhost:8000
 */

const BASE_URL = "http://localhost:8000";

async function fetchJson(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }
  return res.json();
}

// ============================================================
// LEGACY (backward compat)
// ============================================================

export const getHealth = () => fetchJson("/health");
export const getCategories = () => fetchJson("/categories");
export const getArticles = (category = "All", limit = 500) =>
  fetchJson(`/articles?${category && category !== "All" ? `category=${encodeURIComponent(category)}&` : ""}limit=${limit}`);
export const getEvaluation = () => fetchJson("/evaluation");

// ============================================================
// INTELLIGENCE DASHBOARD
// ============================================================

export const getKPIs = () => fetchJson("/intelligence/kpis");

export const getIntelligenceArticles = (params = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== "") qs.set(k, v);
  });
  return fetchJson(`/intelligence/articles?${qs}`);
};

export const getThreatDashboard = (level = null, limit = 100) => {
  const qs = new URLSearchParams({ limit });
  if (level) qs.set("level", level);
  return fetchJson(`/intelligence/threats?${qs}`);
};

export const getMonitoringQueue = (limit = 100) =>
  fetchJson(`/intelligence/monitoring?limit=${limit}`);

export const getHumanReviewQueue = (limit = 100) =>
  fetchJson(`/intelligence/review?limit=${limit}`);

export const getGeographicIntelligence = () =>
  fetchJson("/intelligence/locations");

export const getEntityAnalysis = (entityType = "organizations", limit = 20) =>
  fetchJson(`/intelligence/entities?entity_type=${entityType}&limit=${limit}`);

export const getTopicTrends = (days = 30) =>
  fetchJson(`/intelligence/trends?days=${days}`);

export const getSources = () => fetchJson("/intelligence/sources");

export const getMapLocations = () => fetchJson("/intelligence/map");

// ============================================================
// AI SITUATION BRIEFS
// ============================================================

export const getDailyBrief = () => fetchJson("/intelligence/brief/daily");

export const getSituationBrief = (topic) =>
  fetchJson(`/intelligence/brief/situation/${encodeURIComponent(topic)}`);

export const getCountryBrief = (countryPair) =>
  fetchJson(`/intelligence/brief/country/${encodeURIComponent(countryPair)}`);

// ============================================================
// SINGLE ARTICLE
// ============================================================

export const getArticleIntelligence = (articleId) =>
  fetchJson(`/articles/${articleId}/intelligence`);

// ============================================================
// CHATBOT
// ============================================================

export const postChatQuery = (query, maxArticles = 15) =>
  fetchJson("/chat/query", {
    method: "POST",
    body: JSON.stringify({ query, max_articles: maxArticles }),
  });

// ============================================================
// D-P2-21 MULTI-SOURCE INGESTION FRAMEWORK
// ============================================================

/**
 * Get status and record counts for each P2 connector
 * (GDELT, RSS, WorldBank, SQL) from the unified raw store.
 */
export const getIngestionSources = () => fetchJson("/api/ingestion/sources");

/**
 * Get active declarative sources configuration from config/sources.yaml.
 */
export const getIngestionConfig = () => fetchJson("/api/ingestion/config");

/**
 * Get Dead Letter Queue entries — records that failed ingestion.
 * @param {number} limit      Max entries to return (1–500)
 * @param {string} sourceType Filter by "CSV" | "JSON" | "REST" | "SQL" | null
 */
export const getIngestionDLQ = (limit = 50, sourceType = null) => {
  const qs = new URLSearchParams({ limit });
  if (sourceType) qs.set("source_type", sourceType);
  return fetchJson(`/api/ingestion/dlq?${qs}`);
};