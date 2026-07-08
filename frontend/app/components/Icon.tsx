"use client";

import React from "react";

export type IconName =
  | "analytics"
  | "search"
  | "fund"
  | "refresh"
  | "verified_user"
  | "shield"
  | "verified"
  | "trending_up"
  | "wallet"
  | "clock"
  | "equalizer"
  | "warning"
  | "open_in_new"
  | "history"
  | "filter"
  | "close"
  | "send"
  | "loading"
  | "database"
  | "bolt";

interface IconProps {
  name: IconName | string;
  size?: number | string;
  color?: string;
  className?: string;
  style?: React.CSSProperties;
}

export default function Icon({ name, size = 18, color = "currentColor", className = "", style = {} }: IconProps) {
  const svgStyle: React.CSSProperties = {
    flexShrink: 0,
    display: "inline-block",
    verticalAlign: "middle",
    transition: "all 0.2s ease",
    ...style,
  };

  const renderPath = () => {
    switch (name) {
      case "analytics":
        return <path d="M18 20V10M12 20V4M6 20v-6" />;
      case "search":
        return (
          <>
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </>
        );
      case "fund":
        return (
          <>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <path d="M16 13H8M16 17H8M10 9H8" />
          </>
        );
      case "refresh":
      case "sync":
      case "sync_saved_locally":
        return (
          <>
            <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
            <path d="M21 3v5h-5" />
          </>
        );
      case "verified_user":
      case "shield":
      case "verified":
        return (
          <>
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
            <path d="m9 12 2 2 4-4" />
          </>
        );
      case "trending_up":
        return (
          <>
            <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
            <polyline points="16 7 22 7 22 13" />
          </>
        );
      case "wallet":
      case "account_balance_wallet":
      case "account_balance":
      case "savings":
      case "leaderboard":
      case "security":
      case "water_drop":
      case "construction":
        return (
          <>
            <path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1" />
            <path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4" />
          </>
        );
      case "clock":
      case "lock_clock":
        return (
          <>
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </>
        );
      case "equalizer":
        return (
          <>
            <line x1="4" x2="4" y1="21" y2="14" />
            <line x1="4" x2="4" y1="10" y2="3" />
            <line x1="12" x2="12" y1="21" y2="12" />
            <line x1="12" x2="12" y1="8" y2="3" />
            <line x1="20" x2="20" y1="21" y2="16" />
            <line x1="20" x2="20" y1="12" y2="3" />
            <line x1="2" x2="6" y1="14" y2="14" />
            <line x1="10" x2="14" y1="8" y2="8" />
            <line x1="18" x2="22" y1="16" y2="16" />
          </>
        );
      case "warning":
        return (
          <>
            <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
            <line x1="12" x2="12" y1="9" y2="13" />
            <line x1="12" x2="12.01" y1="17" y2="17" />
          </>
        );
      case "open_in_new":
        return (
          <>
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" x2="21" y1="14" y2="3" />
          </>
        );
      case "history":
        return (
          <>
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
            <path d="M3 3v5h5" />
            <path d="M12 7v5l4 2" />
          </>
        );
      case "filter":
      case "filter_alt":
        return <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />;
      case "close":
        return (
          <>
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </>
        );
      case "send":
      case "arrow_upward":
        return (
          <>
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5 12 12 5 19 12" />
          </>
        );
      case "loading":
      case "hourglass_top":
        return (
          <>
            <path d="M21 12a9 9 0 1 1-6.21-8.56" />
          </>
        );
      case "database":
        return (
          <>
            <ellipse cx="12" cy="5" rx="9" ry="3" />
            <path d="M3 5V19A9 3 0 0 0 21 19V5" />
            <path d="M3 12A9 3 0 0 0 21 12" />
          </>
        );
      case "bolt":
        return <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />;
      default:
        return <circle cx="12" cy="12" r="10" />;
    }
  };

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={svgStyle}
    >
      {renderPath()}
    </svg>
  );
}
