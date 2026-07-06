"use client";

import React, { useState } from "react";
import { HealthStatus } from "../types/chat";

interface SidebarProps {
  schemes: string[];
  activeScheme: string | null;
  onSelectScheme: (scheme: string) => void;
  health: HealthStatus;
  onTriggerIngest: () => void;
  isIngesting: boolean;
}

export default function Sidebar({
  schemes,
  activeScheme,
  onSelectScheme,
  health,
  onTriggerIngest,
  isIngesting,
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredSchemes = schemes.filter((s) =>
    s.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getSchemeIcon = (index: number) => {
    const icons = [
      "trending_up",
      "equalizer",
      "analytics",
      "account_balance_wallet",
      "account_balance",
      "water_drop",
      "security",
      "leaderboard",
      "savings",
      "construction",
    ];
    return icons[index % icons.length];
  };

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="brand-title-group">
          <div className="brand-icon">
            <span className="material-symbols-outlined">analytics</span>
          </div>
          <div>
            <h1 className="brand-title">Mutual Fund FAQ</h1>
            <p className="brand-subtitle">HDFC Facts-Only RAG</p>
          </div>
        </div>

        {/* Status Badge */}
        <div className="status-bar">
          <div className="status-badge">
            <span
              className={`status-dot ${health.status === "offline" ? "offline" : ""}`}
            />
            <span>{health.status === "healthy" ? "SEBI Verified Active" : "Offline"}</span>
          </div>
          <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>
            {health.engine}
          </span>
        </div>
      </div>

      {/* Scheme Search */}
      <div className="sidebar-search">
        <div className="search-input-wrapper">
          <span className="material-symbols-outlined search-icon">search</span>
          <input
            type="text"
            className="search-input"
            placeholder="Filter HDFC Schemes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Scheme Index List */}
      <div className="section-label">
        Indexed Schemes ({filteredSchemes.length})
      </div>
      <div className="sidebar-list-container">
        {filteredSchemes.length === 0 ? (
          <div style={{ padding: "12px", fontSize: "0.8rem", color: "var(--text-muted)" }}>
            No matching schemes found.
          </div>
        ) : (
          filteredSchemes.map((scheme, idx) => {
            const isActive = activeScheme === scheme;
            return (
              <button
                key={scheme}
                onClick={() => onSelectScheme(scheme)}
                className={`scheme-item ${isActive ? "active" : ""}`}
              >
                <span className="material-symbols-outlined scheme-icon">
                  {getSchemeIcon(idx)}
                </span>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {scheme}
                </span>
              </button>
            );
          })
        )}
      </div>

      {/* Footer Admin Action */}
      <div className="sidebar-footer">
        <button
          className="action-btn"
          onClick={onTriggerIngest}
          disabled={isIngesting}
          title="Trigger background re-ingestion of Groww scheme docs"
        >
          <span className="material-symbols-outlined" style={{ fontSize: "18px" }}>
            {isIngesting ? "sync_saved_locally" : "refresh"}
          </span>
          <span>{isIngesting ? "Refreshing Docs..." : "Sync Groww Facts"}</span>
        </button>
      </div>
    </aside>
  );
}
