"use client";

import React, { useState, useEffect, useRef } from "react";
import Sidebar from "./components/Sidebar";
import ChatArea from "./components/ChatArea";
import InputBar from "./components/InputBar";
import { Message, HealthStatus } from "./types/chat";

const DEFAULT_SCHEMES = [
  "HDFC Nifty 50 Index Fund",
  "HDFC BSE Sensex Index Fund",
  "HDFC Children's Fund",
  "HDFC Banking & Financial Services Fund",
  "HDFC Corporate Debt Opportunities Fund",
  "HDFC Gold ETF Fund of Fund",
  "HDFC Nifty Next 50 Index Fund",
  "HDFC Nifty500 Multicap 50:25:25 Index Fund",
  "HDFC Diversified Equity All Cap Active FoF",
  "HDFC Nifty India Digital Index Fund",
];

export default function Home() {
  const [schemes, setSchemes] = useState<string[]>(DEFAULT_SCHEMES);
  const [activeScheme, setActiveScheme] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isIngesting, setIsIngesting] = useState<boolean>(false);
  const [health, setHealth] = useState<HealthStatus>({
    status: "checking",
    engine: "llama-3.3-70b",
  });

  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Initial Data Fetching
  useEffect(() => {
    fetchHealth();
    fetchSchemes();
  }, []);

  async function fetchHealth() {
    try {
      const res = await fetch("/api/health");
      if (res.ok) {
        const data = await res.json();
        setHealth({
          status: "healthy",
          engine: data.engine || "llama-3.3-70b",
        });
      } else {
        setHealth((prev) => ({ ...prev, status: "offline" }));
      }
    } catch {
      setHealth((prev) => ({ ...prev, status: "offline" }));
    }
  }

  async function fetchSchemes() {
    try {
      const res = await fetch("/api/schemes");
      if (res.ok) {
        const data = await res.json();
        if (data.schemes && data.schemes.length > 0) {
          setSchemes(data.schemes);
        }
      }
    } catch {
      // Keep DEFAULT_SCHEMES on network error / static preview
      console.warn("Using default scheme catalog fallback.");
    }
  }

  const handleSelectScheme = (scheme: string) => {
    setActiveScheme(scheme);
    inputRef.current?.focus();
  };

  const handleSendMessage = async (queryText: string) => {
    if (!queryText.trim() || isGenerating) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      sender: "user",
      type: "factual",
      text: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsGenerating(true);

    try {
      // If an active scheme is selected and user query doesn't already name a scheme, prepend context
      const payloadQuery =
        activeScheme && !queryText.toLowerCase().includes(activeScheme.toLowerCase().split(" ")[1])
          ? `[Context: ${activeScheme}] ${queryText}`
          : queryText;

      const response = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: payloadQuery }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();

      const botMsg: Message = {
        id: `bot-${Date.now()}`,
        sender: "bot",
        type: data.type || "factual",
        text: data.answer || data.message || "No factual disclosure found in indexed documents.",
        citations: data.citations,
        sourceUrl: data.source_url,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error("Query execution error:", err);
      const errorMsg: Message = {
        id: `err-${Date.now()}`,
        sender: "bot",
        type: "error",
        text:
          "⚠️ Unable to connect to the backend server. Please verify that the Railway FastAPI server is running or check your Vercel API rewrite settings.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleTriggerIngest = async () => {
    if (isIngesting) return;
    setIsIngesting(true);
    try {
      const res = await fetch("/api/ingest?background=true", { method: "POST" });
      if (res.ok) {
        alert("✅ Background ingestion triggered successfully! Corpus will refresh shortly.");
        fetchSchemes();
      } else {
        alert("⚠️ Ingestion trigger failed or requires admin token authentication.");
      }
    } catch {
      alert("⚠️ Network error while attempting to trigger ingestion.");
    } finally {
      setIsIngesting(false);
    }
  };

  return (
    <div className="app-container">
      {/* Left Scheme Index Sidebar */}
      <Sidebar
        schemes={schemes}
        activeScheme={activeScheme}
        onSelectScheme={handleSelectScheme}
        health={health}
        onTriggerIngest={handleTriggerIngest}
        isIngesting={isIngesting}
      />

      {/* Main Interactive Workspace */}
      <main className="main-content">
        {/* Top Navigation Bar */}
        <header className="top-navbar">
          <div className="nav-title">
            <span>HDFC Mutual Fund Facts</span>
            <span className="sebi-tag">SEBI Compliant Facts-Only</span>
          </div>
          <div className="nav-stats">
            <div className="stat-pill">
              <span className="material-symbols-outlined" style={{ fontSize: "16px", color: "var(--accent-cyan)" }}>
                database
              </span>
              <span>ChromaDB Vector Store</span>
            </div>
            <div className="stat-pill">
              <span className="material-symbols-outlined" style={{ fontSize: "16px", color: "var(--accent-emerald)" }}>
                bolt
              </span>
              <span>Llama 3.3 70B (Temp 0.0)</span>
            </div>
          </div>
        </header>

        {/* Chat Feed */}
        <ChatArea
          messages={messages}
          isGenerating={isGenerating}
          onSelectExample={(text) => handleSendMessage(text)}
          activeScheme={activeScheme}
        />

        {/* Bottom Input Area */}
        <InputBar
          onSendMessage={handleSendMessage}
          isGenerating={isGenerating}
          activeScheme={activeScheme}
          onClearScheme={() => setActiveScheme(null)}
          inputRef={inputRef}
        />
      </main>
    </div>
  );
}
