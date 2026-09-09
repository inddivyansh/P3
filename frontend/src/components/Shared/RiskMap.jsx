import React, { useState, useEffect, useMemo } from "react";
import { Icon } from "./Icons.jsx";
import { getMapLocations } from "../../services/api";

export function RiskMap({
  selectedLocation,
  onSelectLocation,
  onViewLocationDetails,
  filterThreat = "ALL",
}) {
  const [locations, setLocations] = useState([]);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [activePinId, setActivePinId] = useState(selectedLocation?.id || null);
  const [activeLayer, setActiveLayer] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMapData();
  }, []);

  const loadMapData = async () => {
    try {
      setLoading(true);
      const data = await getMapLocations();
      if (data?.locations?.length > 0) {
        setLocations(data.locations);
        if (!activePinId) {
          setActivePinId(data.locations[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to load live map locations:", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredLocations = useMemo(() => {
    return locations.filter((loc) => {
      if (filterThreat !== "ALL") {
        if (filterThreat === "CRITICAL" && loc.threatLevel !== "CRITICAL") return false;
        if (filterThreat === "HIGH" && loc.threatLevel !== "HIGH" && loc.threatLevel !== "CRITICAL") return false;
        if (filterThreat === "MODERATE" && loc.threatLevel !== "MODERATE") return false;
        if (filterThreat === "LOW" && loc.threatLevel !== "LOW") return false;
      }
      return true;
    });
  }, [locations, filterThreat]);

  const activeLocation = useMemo(() => {
    if (!locations.length) return null;
    return locations.find((l) => l.id === activePinId) || locations[0];
  }, [locations, activePinId]);

  const getPinColor = (level) => {
    switch (level) {
      case "CRITICAL":
      case "HIGH":
        return "#C93434"; // Immediate Threat - Red
      case "MODERATE":
        return "#D69A1D"; // Surveillance Required - Amber
      case "LOW":
      default:
        return "#3B8F5A"; // Normal / Low - Green
    }
  };

  const getThreatLabel = (level) => {
    switch (level) {
      case "CRITICAL":
      case "HIGH":
        return "Immediate Threat";
      case "MODERATE":
        return "Surveillance Required";
      case "LOW":
      default:
        return "Normal Activity";
    }
  };

  return (
    <div className="risk-map-wrapper">
      {/* Map Header */}
      <div className="risk-map-top-bar">
        <div>
          <h2 className="risk-map-title">Strategic Activity Map</h2>
          <p className="risk-map-subtitle">
            Geographic distribution of defence, security, and geopolitical developments computed live from database
          </p>
        </div>
        <div className="risk-map-controls">
          <div className="map-layer-selector">
            <button
              className={`map-layer-btn ${activeLayer === "all" ? "active" : ""}`}
              onClick={() => setActiveLayer("all")}
            >
              All Assets ({locations.length})
            </button>
            <button
              className={`map-layer-btn ${activeLayer === "borders" ? "active" : ""}`}
              onClick={() => setActiveLayer("borders")}
            >
              Frontiers & LAC
            </button>
            <button
              className={`map-layer-btn ${activeLayer === "maritime" ? "active" : ""}`}
              onClick={() => setActiveLayer("maritime")}
            >
              Maritime & IOR
            </button>
          </div>
          <div className="map-zoom-buttons">
            <button
              className="map-btn"
              onClick={() => setZoomLevel((z) => Math.min(1.4, z + 0.1))}
              title="Zoom In"
            >
              +
            </button>
            <button
              className="map-btn"
              onClick={() => setZoomLevel((z) => Math.max(0.8, z - 0.1))}
              title="Zoom Out"
            >
              -
            </button>
            <button
              className="map-btn"
              onClick={() => {
                setZoomLevel(1);
                loadMapData();
              }}
              title="Reset & Refresh View"
            >
              <Icon name="refresh" size={12} />
            </button>
          </div>
        </div>
      </div>

      {/* Main Map Visual Canvas */}
      <div className="risk-map-canvas-container">
        <div
          className="risk-map-viewport"
          style={{ transform: `scale(${zoomLevel})`, transformOrigin: "50% 45%" }}
        >
          {/* Subtle Vector Geography Render (India, South Asia & Indo-Pacific contour) */}
          <svg className="risk-map-svg" viewBox="0 0 1000 650" preserveAspectRatio="xMidYMid slice">
            <defs>
              <radialGradient id="landGlow" cx="50%" cy="45%" r="50%">
                <stop offset="0%" stopColor="#EBF0F5" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#F5F6F7" stopOpacity="0.1" />
              </radialGradient>
              <filter id="subtleShadow" x="-10%" y="-10%" width="130%" height="130%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#101820" floodOpacity="0.06" />
              </filter>
            </defs>

            {/* Ocean background pattern */}
            <rect width="1000" height="650" fill="#F8FAFC" />
            <circle cx="520" cy="360" r="380" fill="url(#landGlow)" />

            {/* Subtle Longitude/Latitude lines */}
            <line x1="100" y1="200" x2="900" y2="200" stroke="#E2E8F0" strokeWidth="0.5" strokeDasharray="4 4" />
            <line x1="100" y1="350" x2="900" y2="350" stroke="#E2E8F0" strokeWidth="0.5" strokeDasharray="4 4" />
            <line x1="100" y1="500" x2="900" y2="500" stroke="#E2E8F0" strokeWidth="0.5" strokeDasharray="4 4" />
            <line x1="300" y1="50" x2="300" y2="600" stroke="#E2E8F0" strokeWidth="0.5" strokeDasharray="4 4" />
            <line x1="500" y1="50" x2="500" y2="600" stroke="#E2E8F0" strokeWidth="0.5" strokeDasharray="4 4" />
            <line x1="700" y1="50" x2="700" y2="600" stroke="#E2E8F0" strokeWidth="0.5" strokeDasharray="4 4" />

            {/* Landmass Paths with topographic elevation aesthetic */}
            <path
              d="M 180 120 Q 300 90 480 85 T 780 100 T 920 140 L 940 220 Q 860 210 760 230 T 600 220 Q 420 200 320 210 T 160 200 Z"
              fill="#E2E8F0"
              stroke="#CBD5E1"
              strokeWidth="0.75"
              filter="url(#subtleShadow)"
            />

            {/* India Subcontinent Master Boundary */}
            <path
              d="M 450 140
                 C 470 120, 510 120, 530 140
                 C 550 160, 590 190, 620 210
                 C 650 230, 710 240, 740 260
                 C 720 280, 690 310, 660 300
                 C 630 320, 600 360, 580 400
                 C 560 440, 530 500, 500 560
                 C 480 500, 440 440, 420 390
                 C 400 350, 370 320, 380 290
                 C 390 260, 410 220, 430 180
                 Z"
              fill="#FFFFFF"
              stroke="#94A3B8"
              strokeWidth="1.2"
              filter="url(#subtleShadow)"
            />

            {/* Northern Sector */}
            <path
              d="M 450 140 C 470 130, 510 130, 530 140 C 520 180, 470 190, 450 180 Z"
              fill="#F1F5F9"
              stroke="#CBD5E1"
              strokeWidth="0.8"
            />
            {/* Northeast Sector */}
            <path
              d="M 620 210 C 650 220, 720 230, 740 260 C 710 290, 660 280, 640 250 Z"
              fill="#F8FAFC"
              stroke="#CBD5E1"
              strokeWidth="0.8"
            />
            {/* Western Frontier */}
            <path
              d="M 430 180 C 400 220, 380 270, 390 320 C 430 300, 440 240, 440 200 Z"
              fill="#F1F5F9"
              stroke="#CBD5E1"
              strokeWidth="0.8"
            />
            {/* Peninsular Sector */}
            <path
              d="M 420 390 C 460 420, 540 420, 580 400 C 560 440, 530 500, 500 560 C 480 500, 440 440, 420 390 Z"
              fill="#F8FAFC"
              stroke="#CBD5E1"
              strokeWidth="0.8"
            />

            {/* Andaman & Nicobar */}
            <g transform="translate(710, 440)">
              <ellipse cx="0" cy="0" rx="4" ry="14" fill="#E2E8F0" stroke="#94A3B8" strokeWidth="0.75" />
              <ellipse cx="5" cy="25" rx="3" ry="8" fill="#E2E8F0" stroke="#94A3B8" strokeWidth="0.75" />
            </g>

            {/* Line of Actual Control Line */}
            <path
              d="M 490 145 Q 530 160 560 190 T 630 220 T 730 240"
              fill="none"
              stroke="#C93434"
              strokeWidth="1.2"
              strokeDasharray="4 3"
              opacity="0.6"
            />
          </svg>

          {/* Interactive HTML Pins Layer from Backend */}
          {filteredLocations.map((loc) => {
            const isSelected = activePinId === loc.id;
            const color = getPinColor(loc.threatLevel);

            return (
              <div
                key={loc.id}
                className={`map-pin-container ${isSelected ? "selected" : ""}`}
                style={{
                  left: `${loc.x}%`,
                  top: `${loc.y}%`,
                }}
                onClick={() => {
                  setActivePinId(loc.id);
                  onSelectLocation?.(loc);
                }}
              >
                {(loc.threatLevel === "CRITICAL" || loc.threatLevel === "HIGH") && (
                  <div
                    className="map-pin-pulse"
                    style={{ borderColor: color, backgroundColor: `${color}15` }}
                  />
                )}

                <div
                  className="map-pin-circle"
                  style={{
                    backgroundColor: color,
                    boxShadow: `0 2px 8px ${color}55`,
                  }}
                >
                  <span className="map-pin-count">{loc.articleCount > 0 ? loc.articleCount : 1}</span>
                </div>

                <div className={`map-pin-label ${isSelected ? "active" : ""}`}>
                  <span className="map-pin-name">{loc.name}</span>
                  <span className="map-pin-status-dot" style={{ backgroundColor: color }} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Floating Location Analytical Card */}
        {activeLocation && (
          <div className="floating-risk-card">
            <button
              className="floating-card-close"
              onClick={() => setActivePinId(null)}
              title="Close Details"
            >
              <Icon name="x" size={14} />
            </button>

            <div className="floating-card-header">
              <div>
                <div className="floating-card-subtitle">
                  {activeLocation.state ? `${activeLocation.state}, ${activeLocation.country}` : activeLocation.country}
                </div>
                <h3 className="floating-card-title">{activeLocation.name}</h3>
              </div>
              <div className="floating-risk-score-box">
                <span className="risk-score-label">AI Priority</span>
                <div className="risk-score-value" style={{ color: getPinColor(activeLocation.threatLevel) }}>
                  {activeLocation.riskScore}
                  <span className="risk-score-denom">/100</span>
                </div>
              </div>
            </div>

            {/* Analytical Metadata */}
            <div className="floating-card-tags">
              <div className="analytical-tag threat" style={{ color: getPinColor(activeLocation.threatLevel) }}>
                <span className="tag-dot" style={{ backgroundColor: getPinColor(activeLocation.threatLevel) }} />
                {getThreatLabel(activeLocation.threatLevel)}
              </div>
              <div className="analytical-tag primary">
                <Icon name="shield" size={11} />
                {activeLocation.primaryRisk}
              </div>
              <div className="analytical-tag trend">
                <Icon name={activeLocation.trend === "increasing" ? "trending-up" : "activity"} size={11} />
                {activeLocation.trendText}
              </div>
            </div>

            {/* Recent Key Developments */}
            <div className="floating-card-section">
              <div className="floating-section-title">Recent Developments ({activeLocation.articleCount} Articles)</div>
              <ul className="floating-developments-list">
                {activeLocation.recentDevelopments.map((dev, i) => (
                  <li key={i} className="floating-development-item">
                    <span className="dev-bullet" />
                    <span>{dev}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Reporting Sources Breakdown */}
            {activeLocation.sources?.length > 0 && (
              <div className="floating-card-sources">
                <div className="sources-label">Reporting Sources ({activeLocation.sources.length}):</div>
                <div className="sources-chips">
                  {activeLocation.sources.map((src, i) => (
                    <span key={i} className="source-chip">
                      {src}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="floating-card-footer">
              <button
                className="btn-primary-analytical"
                onClick={() => onViewLocationDetails?.(activeLocation)}
              >
                <span>View Location Intelligence</span>
                <Icon name="arrow-up-right" size={13} />
              </button>
            </div>
          </div>
        )}

        {/* Map Legend */}
        <div className="risk-map-legend">
          <div className="legend-header">Threat Status</div>
          <div className="legend-items">
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: "#C93434" }} />
              <span>Immediate Threat</span>
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: "#D69A1D" }} />
              <span>Surveillance Required</span>
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ backgroundColor: "#3B8F5A" }} />
              <span>Normal Activity</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
