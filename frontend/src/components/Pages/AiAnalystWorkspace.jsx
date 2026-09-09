import React, { useState, useRef, useEffect } from "react";
import { Icon } from "../Shared/Icons.jsx";
import { postChatQuery } from "../../services/api";

function cleanTagsList(arr) {
  if (!Array.isArray(arr)) return [];
  const out = [];
  for (const item of arr) {
    if (!item) continue;
    let str = String(item).trim();
    if (str.startsWith("[") && str.endsWith("]")) {
      try {
        const parsed = JSON.parse(str);
        if (Array.isArray(parsed)) {
          out.push(...cleanTagsList(parsed));
          continue;
        }
      } catch (e) {
        // ignore
      }
    }
    str = str.replace(/^[\[\]"']+|[\[\]"']+$/g, "").trim();
    if (str && !out.includes(str)) {
      out.push(str);
    }
  }
  return out;
}

export function AiAnalystWorkspace() {
  const [messages, setMessages] = useState([]);
  const [queryHistory, setQueryHistory] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeEvidenceArticles, setActiveEvidenceArticles] = useState([]);
  const chatScrollRef = useRef(null);

  useEffect(() => {
    chatScrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (q = query) => {
    const text = q.trim();
    if (!text || loading) return;

    const userMsg = { role: "user", text, timestamp: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    if (!queryHistory.includes(text)) {
      setQueryHistory((prev) => [text, ...prev.slice(0, 9)]);
    }
    setQuery("");
    setLoading(true);

    try {
      const response = await postChatQuery(text);
      const supporting = response.supporting_articles || [];
      setActiveEvidenceArticles(supporting);

      const assistantMsg = {
        role: "assistant",
        content: response,
        evidence: supporting,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: {
            current_assessment: `Analysis request could not be completed: ${err.message}. Please verify the FastAPI backend server is online at port 8000.`,
          },
          evidence: [],
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="analyst-workspace-root">
      <div className="page-title-row" style={{ marginBottom: 14 }}>
        <div>
          <h1 className="page-heading">AI Analyst Research Workspace</h1>
          <p className="page-subheading">
            Natural language intelligence query engine grounded in full-text news database with hybrid search and synthesis.
          </p>
        </div>
        <div className="filter-action-buttons">
          <div className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
            RAG Pipeline: FTS5 + ChromaDB + LLM Synthesis
          </div>
        </div>
      </div>

      {/* 3-Pane Research Workspace */}
      <div className="analyst-workspace">
        {/* Left Pane: Session History */}
        <div className="analyst-history-pane">
          <div className="pane-header">
            <span>Session Inquiries</span>
            <Icon name="clipboard" size={13} color="var(--text-muted)" />
          </div>

          <div style={{ padding: "12px 14px", flex: 1, overflowY: "auto" }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 8 }}>
              Active Session Queries ({queryHistory.length})
            </div>
            {queryHistory.length === 0 ? (
              <div style={{ fontSize: 11.5, color: "var(--text-muted)", lineHeight: 1.5, padding: "8px 0" }}>
                Your submitted queries in this session will appear here for quick reference.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {queryHistory.map((h, i) => (
                  <button
                    key={i}
                    className="btn-secondary-subtle"
                    style={{
                      height: "auto",
                      padding: "6px 8px",
                      textAlign: "left",
                      fontSize: 11,
                      lineHeight: 1.3,
                      justifyContent: "flex-start",
                      width: "100%",
                      whiteSpace: "normal",
                    }}
                    onClick={() => handleSend(h)}
                    disabled={loading}
                  >
                    <Icon name="search" size={11} color="var(--accent-secondary)" />
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{h}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div style={{ padding: "12px 14px", borderTop: "1px solid var(--border-subtle)", background: "var(--bg-card-muted)" }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 4 }}>
              System Grounding
            </div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.4 }}>
              All responses are synthesized directly from retrieved news articles in the database.
            </div>
          </div>
        </div>

        {/* Center Pane: Analytical Dialogue Area */}
        <div className="analyst-chat-pane">
          <div className="pane-header">
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Icon name="bot" size={15} color="var(--accent-primary)" />
              <span>Analytical Dialogue</span>
            </div>
            <span className="ai-badge-label">Live RAG Engine</span>
          </div>

          <div className="chat-conversation-area">
            {messages.length === 0 ? (
              <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
                <Icon name="bot" size={36} color="var(--accent-secondary)" />
                <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", marginTop: 12 }}>
                  AI Intelligence Analyst
                </div>
                <p style={{ fontSize: 12.5, color: "var(--text-secondary)", maxWidth: 460, margin: "8px auto 0", lineHeight: 1.5 }}>
                  Ask questions regarding defence procurement, military exercises, border security, bilateral developments, or specific locations. The engine searches indexed news articles and provides structured, evidence-grounded assessments.
                </p>
              </div>
            ) : (
              messages.map((msg, idx) => {
                if (msg.role === "user") {
                  return (
                    <div key={idx} className="chat-bubble-container user">
                      <div className="chat-bubble-user">{msg.text}</div>
                      <span className="mono" style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 4, alignSelf: "flex-end" }}>
                        Analyst Query
                      </span>
                    </div>
                  );
                }

                const data = msg.content || {};

                return (
                  <div key={idx} className="chat-bubble-container assistant">
                    <div className="chat-bubble-assistant">
                      {/* Header */}
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, paddingBottom: 8, borderBottom: "1px solid var(--border-subtle)" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--accent-primary)" }}>
                            Intelligence Assessment
                          </span>
                        </div>
                        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                          {data.trend && (
                            <span style={{ fontSize: 10, fontWeight: 600, color: "var(--text-muted)" }}>
                              Trend: <strong>{data.trend}</strong>
                            </span>
                          )}
                          {data.confidence && (
                            <span style={{ fontSize: 10, fontWeight: 600, color: "var(--threat-green)" }}>
                              Confidence: <strong>{data.confidence}</strong>
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Assessment */}
                      {data.current_assessment && (
                        <div style={{ marginBottom: 12 }}>
                          <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 4 }}>
                            Current Assessment
                          </div>
                          <div style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-primary)" }}>
                            {data.current_assessment}
                          </div>
                        </div>
                      )}

                      {/* Key Developments */}
                      {data.recent_developments?.length > 0 && (
                        <div style={{ marginBottom: 12 }}>
                          <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 4 }}>
                            Key Developments & Findings
                          </div>
                          <ul style={{ paddingLeft: 18, margin: 0 }}>
                            {data.recent_developments.map((dev, i) => (
                              <li key={i} style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>
                                {dev}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Security Relevance */}
                      {data.security_relevance && (
                        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 10 }}>
                          <strong>Relevance:</strong> {data.security_relevance}
                        </div>
                      )}

                      {/* Tags & Metadata */}
                      {(() => {
                        const cleanLocs = cleanTagsList(data.key_locations);
                        const cleanActs = cleanTagsList(data.key_actors);
                        if (cleanLocs.length === 0 && cleanActs.length === 0) return null;
                        return (
                          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", margin: "10px 0", paddingTop: 8, borderTop: "1px solid var(--border-subtle)" }}>
                            {cleanLocs.length > 0 && (
                              <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
                                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>Locations:</span>
                                {cleanLocs.map((loc) => (
                                  <span key={loc} className="analytical-tag">
                                    {loc}
                                  </span>
                                ))}
                              </div>
                            )}
                            {cleanActs.length > 0 && (
                              <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
                                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>Actors:</span>
                                {cleanActs.map((act) => (
                                  <span key={act} className="analytical-tag primary">
                                    {act}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })()}

                      {msg.evidence?.length > 0 && (
                        <button
                          className="btn-secondary-subtle"
                          style={{ height: 26, fontSize: 11, marginTop: 6 }}
                          onClick={() => setActiveEvidenceArticles(msg.evidence)}
                        >
                          <Icon name="file-text" size={11} />
                          <span>View {msg.evidence.length} Supporting Evidence Articles</span>
                        </button>
                      )}
                    </div>
                    <span className="mono" style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 4, alignSelf: "flex-start" }}>
                      Synthesized via Database Articles
                    </span>
                  </div>
                );
              })
            )}

            {loading && (
              <div className="chat-bubble-container assistant">
                <div className="chat-bubble-assistant" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Icon name="refresh" size={14} className="spin-animate" color="var(--accent-secondary)" />
                  <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                    Searching database articles and synthesizing assessment...
                  </span>
                </div>
              </div>
            )}
            <div ref={chatScrollRef} />
          </div>

          <div className="chat-input-bar">
            <input
              type="text"
              className="chat-text-input"
              placeholder="Enter inquiry (e.g., Manipur status, defence procurement, Ladakh frontier, LAC developments)..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              disabled={loading}
            />
            <button
              className="btn-primary-dark"
              onClick={() => handleSend()}
              disabled={loading || !query.trim()}
              style={{ padding: "0 18px" }}
            >
              <Icon name="send" size={13} />
              <span>Query</span>
            </button>
          </div>
        </div>

        {/* Right Pane: Evidence & Source Inspection */}
        <div className="analyst-evidence-pane">
          <div className="pane-header">
            <span>Retrieved Evidence Panel</span>
            <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
              {activeEvidenceArticles.length} Sources
            </span>
          </div>

          <div className="evidence-items-scroll">
            {activeEvidenceArticles.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 16px", color: "var(--text-muted)", fontSize: 12 }}>
                <Icon name="file-text" size={24} color="var(--text-muted)" />
                <div style={{ marginTop: 8 }}>No active query evidence.</div>
                <div style={{ fontSize: 11, marginTop: 4 }}>
                  Articles retrieved during query synthesis will appear here as clickable evidence cards.
                </div>
              </div>
            ) : (
              activeEvidenceArticles.map((art, i) => (
                <div key={art.article_id || i} className="evidence-article-card">
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                    <span className="evidence-source-tag">{art.source || "News Source"}</span>
                    <span className="mono" style={{ fontSize: 10, color: "var(--text-muted)" }}>
                      {art.published_at?.slice(0, 10) || "Recent"}
                    </span>
                  </div>
                  <div className="evidence-title">
                    {art.url ? (
                      <a href={art.url} target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "none" }}>
                        {art.title}
                      </a>
                    ) : (
                      art.title
                    )}
                  </div>
                  {(art.summary || art.ai_summary) && (
                    <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4, lineHeight: 1.4 }}>
                      {(art.ai_summary || art.summary).slice(0, 140)}...
                    </div>
                  )}
                  {art.threat_level && (
                    <div style={{ marginTop: 6 }}>
                      <span
                        className={`status-badge ${
                          art.threat_level === "CRITICAL" || art.threat_level === "HIGH"
                            ? "immediate"
                            : art.threat_level === "MODERATE"
                            ? "surveillance"
                            : "normal"
                        }`}
                      >
                        {art.threat_level}
                      </span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
