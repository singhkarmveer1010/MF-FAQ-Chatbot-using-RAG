"use client";

import React, { useState, KeyboardEvent } from "react";
import Icon from "./Icon";

interface InputBarProps {
  onSendMessage: (query: string) => void;
  isGenerating: boolean;
  activeScheme: string | null;
  onClearScheme: () => void;
  inputRef?: React.RefObject<HTMLTextAreaElement | null>;
}

export default function InputBar({
  onSendMessage,
  isGenerating,
  activeScheme,
  onClearScheme,
  inputRef,
}: InputBarProps) {
  const [text, setText] = useState("");

  const handleSend = () => {
    if (!text.trim() || isGenerating) return;
    onSendMessage(text.trim());
    setText("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <footer className="input-section">
      <div className="input-container">
        {/* Active Scheme Context Badge */}
        {activeScheme && (
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span className="active-scheme-tag">
              <span style={{ display: "flex", alignItems: "center" }}>
                <Icon name="filter" size={14} />
              </span>
              <span>Context: {activeScheme}</span>
              <button
                onClick={onClearScheme}
                className="clear-scheme-btn"
                title="Clear scheme filter"
                style={{ marginLeft: "4px", display: "flex", alignItems: "center" }}
              >
                <Icon name="close" size={14} />
              </button>
            </span>
          </div>
        )}

        {/* Input Box */}
        <div className="input-box-wrapper">
          <textarea
            ref={inputRef}
            rows={1}
            className="chat-textarea"
            placeholder={
              activeScheme
                ? `Ask factual questions about ${activeScheme} (e.g., NAV, expense ratio, exit load)...`
                : "Ask about any HDFC Mutual Fund scheme (e.g., minimum SIP, exit load, benchmark)..."
            }
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isGenerating}
          />
          <button
            onClick={handleSend}
            disabled={!text.trim() || isGenerating}
            className="send-btn"
            title="Send query (Enter)"
            style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
          >
            <Icon
              name={isGenerating ? "loading" : "send"}
              size={20}
              className={isGenerating ? "animate-spin" : ""}
            />
          </button>
        </div>

        {/* SEBI Compliance Disclaimer */}
        <p className="disclaimer-text">
          Disclaimer: Facts-only. No investment advice is provided by this software. Always refer to
          official Scheme Information Documents (SID) and Key Information Memorandums (KIM) before investing.
        </p>
      </div>
    </footer>
  );
}
