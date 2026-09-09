import React, { useState } from "react";
import { RiskMap } from "../Shared/RiskMap.jsx";

export function StrategicMapPage({ onNavigate, onSelectLocation }) {
  const [filterThreat, setFilterThreat] = useState("ALL");

  return (
    <div>
      <div className="page-title-row">
        <div>
          <h1 className="page-heading">Strategic Activity Map</h1>
          <p className="page-subheading">
            Geographic distribution of defence, security, and geopolitical developments across sectors and frontiers.
          </p>
        </div>
        <div className="filter-action-buttons">
          <div className="filter-select-wrapper">
            <select
              className="filter-select"
              value={filterThreat}
              onChange={(e) => setFilterThreat(e.target.value)}
            >
              <option value="ALL">All Threat Levels</option>
              <option value="CRITICAL">Immediate Threats Only</option>
              <option value="MODERATE">Surveillance Required Only</option>
              <option value="LOW">Normal Activity Only</option>
            </select>
          </div>
        </div>
      </div>

      <RiskMap
        filterThreat={filterThreat}
        onSelectLocation={onSelectLocation}
        onViewLocationDetails={(loc) => {
          onSelectLocation?.(loc);
          onNavigate?.("locations");
        }}
      />
    </div>
  );
}
