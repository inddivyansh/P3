import React, { useState, useEffect } from "react";
import { Icon } from "./components/Shared/Icons.jsx";
import { getHealth, getKPIs } from "./services/api";

// Page Views
import { OverviewPage } from "./components/Pages/OverviewPage.jsx";
import { LiveIntelligence } from "./components/Pages/LiveIntelligence.jsx";
import { PriorityThreats } from "./components/Pages/PriorityThreats.jsx";
import { SituationsPage } from "./components/Pages/SituationsPage.jsx";
import { StrategicMapPage } from "./components/Pages/StrategicMapPage.jsx";
import { LocationIntelligence } from "./components/Pages/LocationIntelligence.jsx";
import { EntityIntelligence } from "./components/Pages/EntityIntelligence.jsx";
import { TrendsAnalytics } from "./components/Pages/TrendsAnalytics.jsx";
import { ReportsPage } from "./components/Pages/ReportsPage.jsx";
import { AiAnalystWorkspace } from "./components/Pages/AiAnalystWorkspace.jsx";
import { DataSourcesPage } from "./components/Pages/DataSourcesPage.jsx";

const NAV_ITEMS = [
  { id: "overview", label: "Overview", icon: "overview" },
  { id: "live", label: "Live Intelligence", icon: "file-text" },
  { id: "threats", label: "Priority Threats", icon: "threat", badge: "threat" },
  { id: "situations", label: "Situations", icon: "situations" },
  { id: "map", label: "Strategic Map", icon: "map" },
  { id: "locations", label: "Locations", icon: "location" },
  { id: "entities", label: "Entities", icon: "users" },
  { id: "trends", label: "Trends & Analytics", icon: "trends" },
  { id: "reports", label: "Reports", icon: "reports" },
  { id: "chat", label: "AI Analyst", icon: "bot" },
  { id: "sources", label: "Data Sources", icon: "database" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [kpis, setKpis] = useState(null);
  const [systemOnline, setSystemOnline] = useState(true);
  const [globalSearch, setGlobalSearch] = useState("");
  const [selectedLocationState, setSelectedLocationState] = useState(null);

  // Global filters state (Section 8)
  const [globalRegion, setGlobalRegion] = useState("All Regions");
  const [globalCategory, setGlobalCategory] = useState("All Categories");
  const [globalThreat, setGlobalThreat] = useState("All Threat Levels");
  const [globalTimeframe, setGlobalTimeframe] = useState("Last 7 Days");

  useEffect(() => {
    loadHealthAndKpis();
  }, []);

  const loadHealthAndKpis = async () => {
    try {
      const [healthData, kpiData] = await Promise.allSettled([
        getHealth(),
        getKPIs(),
      ]);

      if (healthData.status === "fulfilled") {
        setSystemOnline(healthData.value?.status === "online");
      }
      if (kpiData.status === "fulfilled") {
        setKpis(kpiData.value);
      }
    } catch (err) {
      console.error("System status check error:", err);
    }
  };

  const handleGlobalSearch = (e) => {
    if (e.key === "Enter" && globalSearch.trim()) {
      setActiveTab("live");
    }
  };

  const criticalCount = kpis?.critical_articles || 0;

  return (
    <div className="app-container">
      {/* Persistent Left Sidebar (Section 6: Deep Navy #101820) */}
      <aside className="intel-sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <Icon name="shield" size={18} color="#FFFFFF" />
          </div>
          <div className="sidebar-brand-text">
            <span className="sidebar-brand-title">INTELSCOPE</span>
            <span className="sidebar-brand-subtitle">Defence & Geopolitical Platform</span>
          </div>
        </div>

        <div className="sidebar-nav-group">
          <div className="sidebar-group-heading">Navigation</div>
          {NAV_ITEMS.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                className={`sidebar-nav-btn ${isActive ? "active" : ""}`}
                onClick={() => setActiveTab(item.id)}
              >
                <div className="sidebar-icon-wrap">
                  <Icon name={item.icon} size={15} />
                </div>
                <span>{item.label}</span>
                {item.badge === "threat" && criticalCount > 0 && (
                  <span className="sidebar-badge threat">{criticalCount}</span>
                )}
              </button>
            );
          })}
        </div>

        <div className="sidebar-footer">
          <div className="sidebar-system-pill">
            <span className="system-status-dot" />
            <span>Live Data Feed Active</span>
          </div>
        </div>
      </aside>

      {/* Main Analytical View Area */}
      <div className="main-wrapper">
        {/* Global Header (Section 7) */}
        <header className="global-header">
          <div className="header-search-container">
            <div className="header-search-icon">
              <Icon name="search" size={16} />
            </div>
            <input
              type="text"
              className="header-search-input"
              placeholder="Search news, locations, people, organizations, topics..."
              value={globalSearch}
              onChange={(e) => setGlobalSearch(e.target.value)}
              onKeyDown={handleGlobalSearch}
            />
          </div>

          <div className="header-actions">
            <button className="header-icon-btn" title="Alerts & Notifications">
              <Icon name="bell" size={16} />
              <span className="notification-badge-dot" />
            </button>

            <div className="header-analyst-profile">
              <div className="analyst-avatar">IA</div>
              <div className="analyst-info">
                <span className="analyst-name">Strategic Analyst</span>
                <span className="analyst-role">National Security Desk</span>
              </div>
            </div>
          </div>
        </header>

        <main className="page-container">
          {/* Global Filter Bar (Section 8) */}
          <div className="global-filters-bar">
            <div className="filter-controls-group">
              <div className="filter-select-wrapper">
                <select
                  className="filter-select"
                  value={globalRegion}
                  onChange={(e) => setGlobalRegion(e.target.value)}
                >
                  <option value="All Regions">All Regions</option>
                  <option value="Northern Frontier">Northern Frontier (Ladakh, J&K)</option>
                  <option value="Northeastern Sector">Northeastern Sector</option>
                  <option value="Western Frontier">Western Frontier (Rajasthan, Punjab)</option>
                  <option value="Indo-Pacific & IOR">Indo-Pacific & IOR</option>
                </select>
                <div className="filter-select-arrow"><Icon name="chevron-down" size={12} /></div>
              </div>

              <div className="filter-select-wrapper">
                <select
                  className="filter-select"
                  value={globalCategory}
                  onChange={(e) => setGlobalCategory(e.target.value)}
                >
                  <option value="All Categories">All Categories</option>
                  <option value="Border Security">Border Security</option>
                  <option value="Defence Procurement">Defence Procurement</option>
                  <option value="Military Exercises">Military Exercises</option>
                  <option value="Geopolitics">Geopolitics</option>
                  <option value="Internal Security">Internal Security</option>
                </select>
                <div className="filter-select-arrow"><Icon name="chevron-down" size={12} /></div>
              </div>

              <div className="filter-select-wrapper">
                <select
                  className="filter-select"
                  value={globalThreat}
                  onChange={(e) => setGlobalThreat(e.target.value)}
                >
                  <option value="All Threat Levels">All Threat Levels</option>
                  <option value="Immediate Threat">Immediate Threat (Red)</option>
                  <option value="Surveillance Required">Surveillance Required (Amber)</option>
                  <option value="Normal Activity">Normal Activity (Green)</option>
                </select>
                <div className="filter-select-arrow"><Icon name="chevron-down" size={12} /></div>
              </div>

              <div className="filter-select-wrapper">
                <select
                  className="filter-select"
                  value={globalTimeframe}
                  onChange={(e) => setGlobalTimeframe(e.target.value)}
                >
                  <option value="Last 24 Hours">Last 24 Hours</option>
                  <option value="Last 7 Days">Last 7 Days</option>
                  <option value="Last 30 Days">Last 30 Days</option>
                  <option value="Last 90 Days">Last 90 Days</option>
                </select>
                <div className="filter-select-arrow"><Icon name="chevron-down" size={12} /></div>
              </div>
            </div>

            <div className="filter-action-buttons">
              <button
                className="btn-secondary-subtle"
                onClick={() => {
                  setGlobalRegion("All Regions");
                  setGlobalCategory("All Categories");
                  setGlobalThreat("All Threat Levels");
                  setGlobalTimeframe("Last 7 Days");
                }}
              >
                <Icon name="filter" size={12} />
                <span>Reset Filters</span>
              </button>
            </div>
          </div>

          {/* Active Navigation View Routing */}
          {activeTab === "overview" && (
            <OverviewPage
              kpis={kpis}
              onNavigate={setActiveTab}
              onSelectLocation={setSelectedLocationState}
            />
          )}

          {activeTab === "live" && (
            <LiveIntelligence onNavigate={setActiveTab} />
          )}

          {activeTab === "threats" && (
            <PriorityThreats onNavigate={setActiveTab} />
          )}

          {activeTab === "situations" && (
            <SituationsPage onNavigate={setActiveTab} />
          )}

          {activeTab === "map" && (
            <StrategicMapPage
              onNavigate={setActiveTab}
              onSelectLocation={setSelectedLocationState}
            />
          )}

          {activeTab === "locations" && (
            <LocationIntelligence
              initialLocation={selectedLocationState}
            />
          )}

          {activeTab === "entities" && (
            <EntityIntelligence />
          )}

          {activeTab === "trends" && (
            <TrendsAnalytics />
          )}

          {activeTab === "reports" && (
            <ReportsPage />
          )}

          {activeTab === "chat" && (
            <AiAnalystWorkspace />
          )}

          {activeTab === "sources" && (
            <DataSourcesPage />
          )}
        </main>
      </div>
    </div>
  );
}
