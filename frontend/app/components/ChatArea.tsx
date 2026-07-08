"use client";

import React, { useRef, useEffect } from "react";
import { Message } from "../types/chat";
import Icon from "./Icon";

interface ChatAreaProps {
  messages: Message[];
  isGenerating: boolean;
  onSelectExample: (text: string) => void;
  activeScheme: string | null;
}

export default function ChatArea({
  messages,
  isGenerating,
  onSelectExample,
  activeScheme,
}: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isGenerating]);

  const exampleQueries = [
    {
      icon: "trending_up",
      text: "What is the exit load and expense ratio of HDFC Nifty 50 Index Fund?",
    },
    {
      icon: "wallet",
      text: "What is the minimum SIP investment amount for HDFC Children's Fund?",
    },
    {
      icon: "clock",
      text: "Show me the lock-in period and tax benefits for HDFC Gold ETF FoF.",
    },
    {
      icon: "equalizer",
      text: "What is the benchmark index for HDFC Banking & Financial Services Fund?",
    },
  ];

  return (
    <div className="chat-scroll-area">
      {messages.length === 0 ? (
        /* Welcome Dashboard Initial State */
        <div className="dashboard-welcome">
          <div className="welcome-logo-glow" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon name="verified_user" size={38} color="var(--accent-cyan)" />
          </div>
          <h2 className="welcome-title">
            {activeScheme ? `Ask About ${activeScheme}` : "HDFC Mutual Fund Facts Assistant"}
          </h2>
          <p className="welcome-subtitle">
            SEBI-compliant, facts-only financial disclosures sourced directly from official Groww
            Scheme Information Documents. Strictly zero advisory or speculative content.
          </p>

          <div className="example-grid">
            {exampleQueries.map((ex, idx) => (
              <button
                key={idx}
                className="example-card"
                onClick={() => onSelectExample(ex.text)}
              >
                <div className="example-icon" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Icon name={ex.icon} size={20} />
                </div>
                <span className="example-text">{ex.text}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        /* Message Log */
        <>
          {messages.map((msg) => (
            <div key={msg.id} className={`message-row ${msg.sender}`}>
              {msg.sender === "user" ? (
                <div className="user-bubble">{msg.text}</div>
              ) : (
                <div
                  className={`bot-card ${
                    msg.type === "refusal"
                      ? "refusal"
                      : msg.type === "security"
                      ? "security"
                      : ""
                  }`}
                >
                  <div className="bot-header">
                    <div className="bot-sender-tag">
                      <span style={{ display: "flex", alignItems: "center" }}>
                        <Icon
                          name={
                            msg.type === "refusal"
                              ? "warning"
                              : msg.type === "security"
                              ? "shield"
                              : "verified"
                          }
                          size={18}
                        />
                      </span>
                      <span>
                        {msg.type === "refusal"
                          ? "SEBI Advisory Refusal Intercepted"
                          : msg.type === "security"
                          ? "PII Security Guardrail Triggered"
                          : "Official Scheme Fact Disclosure"}
                      </span>
                    </div>
                    <span className="bot-timestamp">{msg.timestamp}</span>
                  </div>

                  <div className="bot-text">
                    {msg.text.split("\n").map((line, idx) => (
                      <p key={idx} style={{ marginBottom: line.trim() ? "8px" : "0" }}>
                        {line}
                      </p>
                    ))}
                  </div>

                  {/* Footer Actions & Source Link */}
                  {(msg.sourceUrl || msg.citations) && (
                    <div className="bot-actions">
                      {msg.sourceUrl && (
                        <a
                          href={msg.sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="source-link-btn"
                        >
                          <span>View Official Scheme Page</span>
                          <span style={{ display: "flex", alignItems: "center" }}>
                            <Icon name="open_in_new" size={16} />
                          </span>
                        </a>
                      )}
                      <div className="attribution-tag">
                        <span style={{ display: "flex", alignItems: "center" }}>
                          <Icon name="history" size={14} />
                        </span>
                        <span>Last Updated: Live Groww Corpus Sync</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {/* Typing Indicator */}
          {isGenerating && (
            <div className="message-row bot">
              <div className="bot-card" style={{ padding: "14px 20px" }}>
                <div className="typing-dots">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span
                    style={{
                      fontSize: "0.8rem",
                      color: "var(--text-secondary)",
                      marginLeft: "8px",
                      fontWeight: 500,
                    }}
                  >
                    Synthesizing 3-sentence verified response...
                  </span>
                </div>
              </div>
            </div>
          )}
        </>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
