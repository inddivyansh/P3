import React, { useState, useEffect } from "react";
import { Icon } from "../Shared/Icons.jsx";
import { getSources, getHealth, getIngestionSources, getIngestionDLQ } from "../../services/api";

// ── Source type metadata ──────────────────────────────────────────────────────
const P2_SOURCE_META = {
  CSV:  { label: "GDELT Geopolitical Events", icon: "file-text", color: "var(--accent-primary)",   desc: "GDELT DOC 2.0 API — 16 defence topics, 250 records/topic" },
  JSON: { label: "Defence RSS Feeds",          icon: "activity",  color: "var(--threat-green)",     desc: "6 curated outlets — idrw.org, nationaldefence.in, broadsword, etc." },
  REST: { label: "World Bank Military Data",   icon: "globe",     color: "var(--accent-secondary)", desc: "Military expenditure (% GDP + USD) — 10 countries × 15 years" },
  SQL:  { label: "Strategic Intel Reference DB",icon: "database", color: "var(--warning-amber)",   desc: "15 countries of strategic interest with threat context" },
};

const DLQ_SOURCE_OPTS = ["All", "CSV", "JSON", "REST", "SQL"];

export function DataSourcesPage() {
  // RSS / legacy sources
  const [sources, setSources]     = useState([]);
  const [healthData, setHealthData] = useState(null);

  // P2 ingestion connector status
  const [p2Status, setP2Status]   = useState(null);
  const [p2Loading, setP2Loading] = useState(true);
  const [p2Error, setP2Error]     = useState(null);

  // Dead Letter Queue
  const [dlqEntries, setDlqEntries]   = useState([]);
  const [dlqTotal, setDlqTotal]       = useState(0);
  const [dlqFilter, setDlqFilter]     = useState("All");
  const [dlqLoading, setDlqLoading]   = useState(true);
  const [dlqExpanded, setDlqExpanded] = useState(null);

  const [loading, setLoading] = useState(true);

  useEffect(() => { loadAll(); }, []);
  useEffect(() => { loadDLQ(); }, [dlqFilter]);

  const loadAll = async () => {
    await Promise.all([loadSources(), loadP2Status(), loadDLQ()]);
  };

  const loadSources = async () => {
    try {
      setLoading(true);
      const [srcRes, hRes] = await Promise.allSettled([getSources(), getHealth()]);
      if (srcRes.status === "fulfilled" && srcRes.value?.sources) setSources(srcRes.value.sources);
      if (hRes.status === "fulfilled") setHealthData(hRes.value);
    } catch (err) {
      console.error("Failed to load sources:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadP2Status = async () => {
    try {
      setP2Loading(true);
      setP2Error(null);
      const res = await getIngestionSources();
      setP2Status(res);
    } catch (err) {
      setP2Error("P2 store not yet initialised — run the pipeline first.");
    } finally {
      setP2Loading(false);
    }
  };

  const loadDLQ = async () => {
    try {
      setDlqLoading(true);
      const sourceType = dlqFilter === "All" ? null : dlqFilter;
      const res = await getIngestionDLQ(50, sourceType);
      setDlqEntries(res.entries || []);
      setDlqTotal(res.total || 0);
    } catch (err) {
      setDlqEntries([]);
    } finally {
      setDlqLoading(false);
    }
  };

  const totalArticles = healthData?.total_articles || sources.reduce((acc, s) => acc + (s.articles || 0), 0);
  const p2Total       = p2Status?.total_records || 0;

  const formatTs = (ts) => {
    if (!ts) return "—";
    try { return new Date(ts).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" }); }
    catch { return ts; }
  };

  const dlqErrorColor = (type) => {
    if (type?.includes("Fatal"))      return "var(--threat-red)";
    if (type?.includes("Validation")) return "var(--warning-amber)";
    if (type?.includes("Structural")) return "var(--accent-secondary)";
    return "var(--text-muted)";
  };

  return (
    <div>
      {/* ── Page Header ── */}
      <div className="page-title-row">
        <div>
          <h1 className="page-heading">Data Ingestion Pipeline &amp; Sources</h1>
          <p className="page-subheading">
            Live operational status — D-P2-21 multi-source engine (GDELT · WorldBank · SQL · RSS) +
            57 configured news feeds, full-text extractors, and database sync.
          </p>
        </div>
        <div className="filter-action-buttons">
          <button className="btn-secondary-subtle" onClick={loadAll}>
            <Icon name="refresh" size={13} />
            <span>Refresh All</span>
          </button>
        </div>
      </div>

      {/* ── Pipeline Health Summary ── */}
      <div className="intel-card" style={{ marginBottom: 20 }}>
        <div className="intel-card-header">
          <h3 className="intel-card-title">
            <Icon name="activity" size={15} color="var(--threat-green)" />
            <span>Unified Intelligence Pipeline Health</span>
          </h3>
          <span className="status-badge normal">
            {healthData?.status === "online" ? "All Systems Operational" : "System Synchronizing"}
          </span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 14 }}>
          <div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>Pipeline Engine</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>11-Stage Active</div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>P2 Connectors</div>
            <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: "var(--accent-primary)", marginTop: 2 }}>
              {p2Status?.connectors?.length ?? "—"} Active
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>P2 Raw Records</div>
            <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: "var(--accent-secondary)", marginTop: 2 }}>
              {p2Total.toLocaleString()}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>RSS Feeds Online</div>
            <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: "var(--threat-green)", marginTop: 2 }}>
              {sources.length} Active
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>NLP Articles</div>
            <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
              {totalArticles.toLocaleString()}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>DLQ Entries</div>
            <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: dlqTotal > 0 ? "var(--warning-amber)" : "var(--threat-green)", marginTop: 2 }}>
              {dlqTotal.toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* ── D-P2-21 Multi-Source Connector Status ── */}
      <div className="intel-card" style={{ marginBottom: 20 }}>
        <div className="intel-card-header">
          <h3 className="intel-card-title">
            <Icon name="database" size={15} color="var(--accent-primary)" />
            <span>D-P2-21 Multi-Source Ingestion Engine (Config-Driven)</span>
          </h3>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "monospace" }}>
              config/sources.yaml
            </span>
            <span className="intel-card-badge">
              {p2Status?.status === "ok" ? `${p2Total.toLocaleString()} Unified Records` : "Not Initialised"}
            </span>
          </div>
        </div>

        {p2Loading ? (
          <div style={{ padding: 30, textAlign: "center", color: "var(--text-muted)" }}>
            Querying unified ingestion store…
          </div>
        ) : p2Error ? (
          <div style={{ padding: 20, color: "var(--warning-amber)", fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
            <Icon name="alert" size={14} color="var(--warning-amber)" />
            {p2Error}
          </div>
        ) : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12, marginBottom: 16 }}>
              {(p2Status?.connectors || []).map((c) => {
                const meta = P2_SOURCE_META[c.source_type] || {};
                const displayLabel = c.label || meta.label || c.source_type;
                const displayDesc = c.description || meta.desc || "";
                const isEnabled = c.enabled !== false;

                return (
                  <div
                    key={c.source_key || c.source_type}
                    style={{
                      background: "var(--surface-raised)",
                      borderRadius: 8,
                      padding: "14px 16px",
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 14,
                      border: `1px solid color-mix(in srgb, ${meta.color ?? "var(--border-subtle)"} 25%, transparent)`,
                      opacity: isEnabled ? 1 : 0.6,
                    }}
                  >
                    <div style={{
                      width: 36, height: 36, borderRadius: 8, flexShrink: 0,
                      background: `color-mix(in srgb, ${meta.color ?? "var(--accent-primary)"} 15%, transparent)`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      <Icon name={meta.icon ?? "database"} size={16} color={meta.color ?? "var(--accent-primary)"} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 2 }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
                          {displayLabel}
                        </div>
                        <span className="status-badge normal" style={{ fontSize: 9, padding: "1px 6px" }}>
                          {c.source_type}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8, lineHeight: 1.4 }}>
                        {displayDesc}
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span className="mono" style={{ fontSize: 18, fontWeight: 800, color: meta.color ?? "var(--accent-primary)" }}>
                          {(c.record_count || 0).toLocaleString()}
                        </span>
                        <span style={{ fontSize: 10, color: "var(--text-muted)" }}>records</span>
                        {c.parameters?.query_topics?.length > 0 && (
                          <span style={{ marginLeft: "auto", fontSize: 10, color: "var(--accent-primary)", background: "color-mix(in srgb, var(--accent-primary) 10%, transparent)", padding: "1px 6px", borderRadius: 4 }}>
                            {c.parameters.query_topics.length} topics
                          </span>
                        )}
                        {c.parameters?.countries && (
                          <span style={{ marginLeft: "auto", fontSize: 10, color: "var(--accent-secondary)", background: "color-mix(in srgb, var(--accent-secondary) 10%, transparent)", padding: "1px 6px", borderRadius: 4 }}>
                            {c.parameters.countries.split(";").length} nations
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Intel DB + DLQ path info */}
            <div style={{ display: "flex", gap: 16, fontSize: 11, color: "var(--text-muted)", flexWrap: "wrap" }}>
              <span>
                <span style={{ color: p2Status?.intel_db_seeded ? "var(--threat-green)" : "var(--warning-amber)", marginRight: 4 }}>●</span>
                Strategic Intel DB: {p2Status?.intel_db_seeded ? "Seeded" : "Not seeded — run p2_seed_intelligence_db.py"}
              </span>
              <span style={{ color: "var(--border-subtle)" }}>|</span>
              <span style={{ fontFamily: "monospace" }}>Config: config/sources.yaml</span>
              <span style={{ color: "var(--border-subtle)" }}>|</span>
              <span style={{ fontFamily: "monospace" }}>Store: {p2Status?.store_path?.split(/[\\/]/).slice(-3).join("/")}</span>
            </div>
          </>
        )}
      </div>

      {/* ── Dead Letter Queue Panel ── */}
      <div className="intel-card" style={{ marginBottom: 20 }}>
        <div className="intel-card-header">
          <h3 className="intel-card-title">
            <Icon name="alert" size={15} color="var(--warning-amber)" />
            <span>Dead Letter Queue</span>
            {dlqTotal > 0 && (
              <span style={{
                background: "var(--warning-amber)", color: "#000", fontSize: 10,
                fontWeight: 700, padding: "1px 7px", borderRadius: 10,
              }}>
                {dlqTotal}
              </span>
            )}
          </h3>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {DLQ_SOURCE_OPTS.map((opt) => (
              <button
                key={opt}
                onClick={() => setDlqFilter(opt)}
                style={{
                  fontSize: 11, padding: "3px 10px", borderRadius: 6, cursor: "pointer",
                  border: dlqFilter === opt ? "1px solid var(--accent-primary)" : "1px solid var(--border-subtle)",
                  background: dlqFilter === opt ? "color-mix(in srgb, var(--accent-primary) 15%, transparent)" : "transparent",
                  color: dlqFilter === opt ? "var(--accent-primary)" : "var(--text-muted)",
                }}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>

        {dlqLoading ? (
          <div style={{ padding: 20, textAlign: "center", color: "var(--text-muted)" }}>Loading DLQ entries…</div>
        ) : dlqEntries.length === 0 ? (
          <div style={{ padding: 24, textAlign: "center", color: "var(--threat-green)", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <Icon name="activity" size={14} color="var(--threat-green)" />
            No failed records {dlqFilter !== "All" ? `for source type "${dlqFilter}"` : ""} — ingestion pipeline healthy.
          </div>
        ) : (
          <table className="intel-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Source Type</th>
                <th>Source Name</th>
                <th>Error Type</th>
                <th>Error Message</th>
                <th>Attempts</th>
              </tr>
            </thead>
            <tbody>
              {dlqEntries.map((entry, i) => (
                <React.Fragment key={entry.dlq_id || i}>
                  <tr
                    style={{ cursor: "pointer" }}
                    onClick={() => setDlqExpanded(dlqExpanded === i ? null : i)}
                  >
                    <td className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>{formatTs(entry.timestamp)}</td>
                    <td>
                      <span className="status-badge" style={{ color: P2_SOURCE_META[entry.source_type]?.color }}>
                        {entry.source_type}
                      </span>
                    </td>
                    <td style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 12 }}>
                      {entry.source_name}
                    </td>
                    <td>
                      <span style={{ fontSize: 11, color: dlqErrorColor(entry.error_type), fontWeight: 600 }}>
                        {entry.error_type}
                      </span>
                    </td>
                    <td style={{ maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 11, color: "var(--text-muted)" }}>
                      {entry.error_message}
                    </td>
                    <td className="mono numeric-val">{entry.attempts}</td>
                  </tr>
                  {dlqExpanded === i && (
                    <tr>
                      <td colSpan={6} style={{ padding: 0 }}>
                        <div style={{
                          background: "var(--surface-base)", padding: "12px 16px",
                          fontSize: 11, fontFamily: "monospace",
                          color: "var(--text-muted)", borderTop: "1px solid var(--border-subtle)",
                          whiteSpace: "pre-wrap", wordBreak: "break-word", maxHeight: 200, overflowY: "auto",
                        }}>
                          <div style={{ color: "var(--warning-amber)", marginBottom: 6 }}>— Raw Record —</div>
                          {JSON.stringify(entry.raw_record, null, 2)}
                          {entry.traceback && (
                            <>
                              <div style={{ color: "var(--threat-red)", margin: "8px 0 4px" }}>— Traceback —</div>
                              {entry.traceback}
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── RSS Feed Sources Table ── */}
      <div className="intel-card">
        <div className="intel-card-header">
          <h3 className="intel-card-title">Configured RSS Intelligence Feeds</h3>
          <span className="intel-card-badge">{sources.length} Verified Feeds</span>
        </div>
        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
            Loading live feeds from database…
          </div>
        ) : (
          <table className="intel-table">
            <thead>
              <tr>
                <th>Feed / Publication</th>
                <th>Category</th>
                <th>Status</th>
                <th>Reliability</th>
                <th>Last Ingestion</th>
                <th style={{ textAlign: "right" }}>Articles Captured</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((feed, i) => (
                <tr key={i}>
                  <td className="location-name">{feed.name}</td>
                  <td>{feed.category}</td>
                  <td>
                    <span className="status-badge normal">{feed.status}</span>
                  </td>
                  <td className="mono">{feed.reliability}</td>
                  <td className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>{feed.lastIngestion}</td>
                  <td className="numeric-val">{feed.articles}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
