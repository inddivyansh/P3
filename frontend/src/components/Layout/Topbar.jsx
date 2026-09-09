import { Menu, X, Search, Bell, RefreshCw } from "lucide-react";
import { getPageTitle } from "../../utils/helpers.js";

export function Topbar({
  activePage,
  onMenuToggle,
  sidebarOpen,
}) {
  return (
    <header className="topbar">
      <button
        className="mobile-menu"
        onClick={onMenuToggle}
      >
        {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
      </button>

      <div className="breadcrumb">
        <span>D-P1-22</span>
        <span> › </span>
        <strong>{getPageTitle(activePage)}</strong>
      </div>

      <div className="topbar-actions">
        <div className="search-box">
          <Search size={14} />
          <input
            type="text"
            placeholder="Search articles..."
          />
          <div className="search-key">⌘K</div>
        </div>

        <button className="icon-button">
          <RefreshCw size={16} />
        </button>

        <button className="icon-button">
          <Bell size={16} />
          <div className="bell-dot" />
        </button>

        <div className="date-display">
          <strong>{new Date().toLocaleDateString()}</strong>
          <small>
            {new Date().toLocaleTimeString("en-IN", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </small>
        </div>
      </div>
    </header>
  );
}
