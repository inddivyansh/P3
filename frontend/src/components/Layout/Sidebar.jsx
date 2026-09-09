import {
  LayoutDashboard,
  BarChart3,
  AlertTriangle,
} from "lucide-react";
import { SidebarItem } from "../Common/SidebarItem.jsx";
import { CATEGORY_CONFIG } from "../../constants/categoryConfig.js";

export function Sidebar({
  activePage,
  onNavigate,
  onCategory,
  categoryCounts,
  reviewCount,
  systemOnline,
  sidebarOpen,
  onClose,
}) {
  return (
    <>
      <aside
        className={`sidebar ${sidebarOpen ? "mobile-open" : ""}`}
      >
        {/* Brand */}
        <div className="brand">
          <div className="brand-mark">◆</div>
          <div>
            <div className="brand-title">NEWS INTELLIGENCE</div>
            <div className="brand-subtitle">D-P1-22 WORKSPACE</div>
          </div>
        </div>

        <div className="sidebar-divider" />

        {/* Workspace */}
        <div className="sidebar-section">
          <div className="sidebar-label">WORKSPACE</div>
          <SidebarItem
            icon={LayoutDashboard}
            label="Overview"
            active={activePage === "overview"}
            onClick={() => {
              onNavigate("overview");
              onClose?.();
            }}
          />
          <SidebarItem
            icon={BarChart3}
            label="Daily Digest"
            active={activePage === "digest"}
            onClick={() => {
              onNavigate("digest");
              onClose?.();
            }}
          />
        </div>

        {/* Categories */}
        <div className="sidebar-section">
          <div className="sidebar-label">CATEGORIES</div>
          {CATEGORY_CONFIG.map((category) => {
            const Icon = category.icon;
            return (
              <SidebarItem
                key={category.name}
                icon={Icon}
                label={category.short}
                active={activePage === category.name}
                count={categoryCounts[category.name] ?? 0}
                onClick={() => {
                  onCategory(category.name);
                  onClose?.();
                }}
              />
            );
          })}
        </div>

        {/* Analysis */}
        <div className="sidebar-section">
          <div className="sidebar-label">ANALYSIS</div>
          <SidebarItem
            icon={AlertTriangle}
            label="Review Queue"
            active={activePage === "review"}
            count={reviewCount}
            onClick={() => {
              onNavigate("review");
              onClose?.();
            }}
          />
          <SidebarItem
            icon={BarChart3}
            label="Evaluation"
            active={activePage === "evaluation"}
            onClick={() => {
              onNavigate("evaluation");
              onClose?.();
            }}
          />
        </div>

        {/* Footer */}
        <div className="sidebar-footer">
          <div className="pipeline-indicator">
            <span
              className={
                systemOnline ? "online-dot" : "offline-dot"
              }
            />
            <div>
              <strong>
                {systemOnline
                  ? "PIPELINE ONLINE"
                  : "PIPELINE OFFLINE"}
              </strong>
              <small>Python processing engine</small>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={onClose}
        />
      )}
    </>
  );
}
