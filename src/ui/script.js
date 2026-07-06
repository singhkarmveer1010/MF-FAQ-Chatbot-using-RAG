/**
 * Mutual Fund FAQ Assistant — Frontend Javascript Module (Phase 6.5 – 6.11)
 *
 * Implements interactive frontend behaviors:
 * 1. Fetches scheme catalog on startup and renders sidebar (§5.4 & §6).
 * 2. Handles example query chip clicks and form submissions (§6.5 & §6.7).
 * 3. Communicates with POST /api/query endpoint via Fetch API (§6.8).
 * 4. Renders distinct chat bubbles for factual, advisory refusal, and PII blocked responses (§6.6).
 * 5. Displays clickable Groww source hyperlinks and last updated attribution footers (§6.9 & §6.10).
 */

document.addEventListener("DOMContentLoaded", () => {
    initHealthCheck();
    initSchemesList();
});

/**
 * Liveness check against GET /api/health
 */
async function initHealthCheck() {
    try {
        const res = await fetch("/api/health");
        if (res.ok) {
            const data = await res.json();
            const badge = document.getElementById("health-badge");
            const engineName = document.getElementById("engine-name");
            if (engineName) engineName.textContent = data.engine || "llama-3.3-70b";
            if (badge) badge.classList.remove("hidden", "opacity-50");
        }
    } catch (err) {
        console.warn("Health check failed:", err);
        const badge = document.getElementById("health-badge");
        if (badge) badge.classList.add("opacity-50");
    }
}

/**
 * Fetch supported schemes from GET /api/schemes and populate sidebar index
 */
async function initSchemesList() {
    const listContainer = document.getElementById("schemes-list");
    const countBadge = document.getElementById("schemes-count");
    if (!listContainer) return;

    try {
        const res = await fetch("/api/schemes");
        if (!res.ok) throw new Error("Network error loading schemes");
        const data = await res.json();
        const schemes = data.schemes || [];
        
        if (countBadge) countBadge.textContent = schemes.length;
        window.supportedSchemes = schemes;

        if (schemes.length === 0) {
            listContainer.innerHTML = `<div class="p-3 text-xs text-gray-400">No schemes found.</div>`;
            return;
        }

        // Generate sidebar items with Material icons
        listContainer.innerHTML = schemes.map((scheme, idx) => {
            const icons = ["trending_up", "equalizer", "analytics", "account_balance_wallet", "account_balance", "water_drop", "security", "leaderboard", "savings", "construction"];
            const icon = icons[idx % icons.length];
            return `
                <a href="#" onclick="selectScheme('${scheme}', event)" class="scheme-item flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-gray-700 hover:text-[#00C853] font-medium transition-all">
                    <span class="material-symbols-outlined text-[#00B386] text-[18px]">${icon}</span>
                    <span class="truncate">${scheme}</span>
                </a>
            `;
        }).join("");
    } catch (err) {
        console.error("Failed to fetch schemes:", err);
        listContainer.innerHTML = `<div class="p-3 text-xs text-red-500">Failed to load schemes catalog.</div>`;
    }
}

/**
 * Clicking a scheme in the sidebar sets active scheme context and prepares input box WITHOUT automatically submitting
 */
function selectScheme(schemeName, event) {
    if (event) event.preventDefault();
    
    // Highlight selected scheme in sidebar
    document.querySelectorAll(".scheme-item").forEach(item => {
        item.classList.remove("bg-emerald-50", "text-[#00C853]", "font-semibold");
        item.classList.add("text-gray-700", "font-medium");
    });
    if (event && event.currentTarget) {
        event.currentTarget.classList.remove("text-gray-700", "font-medium");
        event.currentTarget.classList.add("bg-emerald-50", "text-[#00C853]", "font-semibold");
    }

    const queryInput = document.getElementById("query-input");
    if (queryInput) {
        window.activeSchemeContext = schemeName;
        queryInput.value = `${schemeName} `;
        queryInput.placeholder = `Ask anything about ${schemeName} (e.g., NAV, expense ratio, exit load)...`;
        queryInput.focus();
    }
}

/**
 * Handle clicking on example query chips (§6.5)
 */
function submitExample(queryText) {
    const queryInput = document.getElementById("query-input");
    if (queryInput) queryInput.value = queryText;
    processQuery(queryText);
}

/**
 * Handle query form submission
 */
function handleFormSubmit(event) {
    event.preventDefault();
    const queryInput = document.getElementById("query-input");
    if (!queryInput) return;
    const queryText = queryInput.value.trim();
    if (!queryText) return;
    
    queryInput.value = "";
    processQuery(queryText);
}

/**
 * Main query processing orchestrator (§6.8)
 */
async function processQuery(queryText) {
    const chatContainer = document.getElementById("chat-messages");
    const welcomeBlock = document.getElementById("welcome-block");
    const sendBtn = document.getElementById("send-btn");
    const useLlmCheckbox = document.getElementById("use-llm-intent");
    const useLlmIntent = useLlmCheckbox ? useLlmCheckbox.checked : true;

    if (!chatContainer) return;

    // Track active scheme context for multi-turn follow-up queries
    let effectiveQuery = queryText;
    if (window.supportedSchemes && window.supportedSchemes.length > 0) {
        const queryLower = queryText.toLowerCase();
        const foundScheme = window.supportedSchemes.find(s => 
            queryLower.includes(s.toLowerCase()) ||
            (s.includes("Gold") && queryLower.includes("gold")) ||
            (s.includes("Nifty 50") && queryLower.includes("nifty 50")) ||
            (s.includes("Sensex") && queryLower.includes("sensex")) ||
            (s.includes("Childrens") && queryLower.includes("children")) ||
            (s.includes("Banking") && queryLower.includes("banking")) ||
            (s.includes("Corporate Debt") && queryLower.includes("corporate debt")) ||
            (s.includes("Next 50") && queryLower.includes("next 50")) ||
            (s.includes("Multicap") && queryLower.includes("multicap")) ||
            (s.includes("Diversified") && queryLower.includes("diversified")) ||
            (s.includes("Digital") && queryLower.includes("digital"))
        );
        if (foundScheme) {
            window.activeSchemeContext = foundScheme;
        } else if (window.activeSchemeContext && (
            queryLower.includes("this fund") || queryLower.includes("this scheme") ||
            queryLower.includes("the fund") || queryLower.includes("the scheme") ||
            queryLower.includes("same fund") || queryLower.includes("fund manager") ||
            queryLower.includes("expense ratio") || queryLower.includes("exit load")
        )) {
            effectiveQuery = `${queryText} (regarding ${window.activeSchemeContext})`;
        }
    }

    // Hide welcome block after first query
    if (welcomeBlock && !welcomeBlock.classList.contains("hidden")) {
        welcomeBlock.classList.add("hidden");
    }

    // 1. Append User Message Bubble (§6.6)
    appendUserBubble(queryText);
    scrollToBottom();

    // 2. Append Assistant Loading Bubble
    const loadingId = "loading-" + Date.now();
    appendLoadingBubble(loadingId);
    scrollToBottom();

    if (sendBtn) sendBtn.disabled = true;

    try {
        // 3. Execute POST /api/query (§6.8)
        const response = await fetch("/api/query", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                query: effectiveQuery,
                use_llm_intent: useLlmIntent
            })
        });

        const data = await response.json();

        // Remove loading bubble
        const loadingElem = document.getElementById(loadingId);
        if (loadingElem) loadingElem.remove();

        // 4. Render appropriate Assistant Response Bubble based on status (§6.6, §6.9, §6.10, §6.11)
        if (data.status === "success" || data.intent === "FACTUAL") {
            appendFactualBubble(data);
        } else if (data.status === "refused" || data.intent === "ADVISORY") {
            appendRefusalBubble(data);
        } else if (data.status === "pii_blocked") {
            appendPiiBubble(data);
        } else {
            appendGenericBubble(data);
        }
    } catch (err) {
        console.error("Query request failed:", err);
        const loadingElem = document.getElementById(loadingId);
        if (loadingElem) loadingElem.remove();
        appendErrorBubble("Network communication error: Could not reach the FastAPI server. Please make sure the backend is running on port 8000.");
    } finally {
        if (sendBtn) sendBtn.disabled = false;
        scrollToBottom();
    }
}

/**
 * Append User Message Bubble (§6.6)
 */
function appendUserBubble(text) {
    const chatContainer = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "flex justify-end mb-2 animate-fade-in";
    div.innerHTML = `
        <div class="bubble-user rounded-2xl rounded-tr-sm py-3.5 px-5 max-w-[85%] md:max-w-[75%]">
            <p class="text-sm md:text-base leading-relaxed break-words">${escapeHtml(text)}</p>
        </div>
    `;
    chatContainer.appendChild(div);
}

/**
 * Append Assistant Loading Bubble
 */
function appendLoadingBubble(id) {
    const chatContainer = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.id = id;
    div.className = "flex justify-start mb-2";
    div.innerHTML = `
        <div class="bubble-assistant rounded-2xl rounded-tl-sm p-4 max-w-[85%] md:max-w-[65%] flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-[#00E676]/10 flex items-center justify-center flex-shrink-0 animate-spin">
                <span class="material-symbols-outlined text-[#00E676]">sync</span>
            </div>
            <div class="flex flex-col">
                <span class="text-xs font-bold uppercase tracking-wider text-[#00E676]">Assistant Analyzing</span>
                <span class="text-xs text-[#94a3b8] animate-soft-pulse">Searching vector disclosures... Retrieving facts...</span>
            </div>
        </div>
    `;
    chatContainer.appendChild(div);
}

/**
 * Append Successful Factual Response Bubble (§6.6, §6.9, §6.10)
 */
function appendFactualBubble(data) {
    const chatContainer = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "flex justify-start mb-4";
    
    const sourceUrl = data.source_url || "https://groww.in/mutual-funds";
    const lastUpdated = data.last_updated || "2026-07-05";

    div.innerHTML = `
        <div class="bubble-assistant rounded-2xl rounded-tl-sm p-5 md:p-6 max-w-[95%] lg:max-w-[85%] flex flex-col gap-4">
            <!-- Header Row with Bot Icon & Verification Badges -->
            <div class="flex items-start justify-between gap-4 border-b border-white/10 pb-3">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-[#00E676]/10 text-[#00E676] flex items-center justify-center flex-shrink-0 shadow-sm border border-[#00E676]/20">
                        <span class="material-symbols-outlined text-xl">smart_toy</span>
                    </div>
                    <div>
                        <div class="text-sm font-bold text-[#f8fafc]">Factual RAG Response</div>
                        <div class="text-xs text-[#94a3b8]">Intent: <span class="text-[#00E676] font-semibold">${data.intent}</span></div>
                    </div>
                </div>
                <div class="flex flex-wrap gap-1.5 justify-end">
                    <span class="inline-flex items-center gap-1 px-2.5 py-1 bg-[#00E676]/10 text-[#00E676] font-semibold text-xs rounded-full border border-[#00E676]/20">
                        <span class="material-symbols-outlined text-[14px]">verified</span>
                        <span>Verified Fact</span>
                    </span>
                    <span class="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-500/10 text-blue-400 font-semibold text-xs rounded-full border border-blue-500/20">
                        <span class="material-symbols-outlined text-[14px]">description</span>
                        <span>SEBI Compliant</span>
                    </span>
                </div>
            </div>

            <!-- Answer Body Text -->
            <div class="text-sm md:text-base text-[#f8fafc] leading-relaxed break-words font-normal">
                ${formatAnswerText(data.answer)}
            </div>

            <!-- Interactive Bento Citation Card (§6.9) -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-1">
                <a href="${sourceUrl}" target="_blank" class="bento-card bg-[#0f172a] border border-white/10 p-3.5 rounded-xl flex items-center justify-between group no-underline text-inherit">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-lg bg-[#1e293b] border border-white/10 flex items-center justify-center text-[#00E676] group-hover:bg-[#00E676] group-hover:text-[#0a0e17] transition-colors">
                            <span class="material-symbols-outlined text-[18px]">link</span>
                        </div>
                        <div class="overflow-hidden">
                            <div class="text-xs font-bold uppercase tracking-wider text-[#64748b] group-hover:text-[#00E676] transition-colors">Source Citation (§6.9)</div>
                            <div class="text-xs font-semibold text-[#cbd5e1] truncate max-w-[200px] md:max-w-[260px]">${sourceUrl}</div>
                        </div>
                    </div>
                    <span class="material-symbols-outlined text-gray-400 group-hover:text-[#00E676] transition-colors">open_in_new</span>
                </a>
            </div>

            <!-- Last Updated Footer & Disclaimer (§6.10 & §4.3) -->
            <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-t border-white/10 pt-3 text-xs text-[#94a3b8]">
                <div class="flex items-center gap-1.5 text-[#94a3b8]">
                    <span class="material-symbols-outlined text-[15px] text-gray-500">update</span>
                    <span><strong>Last updated from sources:</strong> ${lastUpdated}</span>
                </div>
                <div class="italic text-gray-500">${data.disclaimer || "Facts-only. No investment advice."}</div>
            </div>
        </div>
    `;
    chatContainer.appendChild(div);
}

/**
 * Append Refusal Response Bubble (§6.6 & §6.11)
 */
function appendRefusalBubble(data) {
    const chatContainer = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "flex justify-start mb-4";
    
    const eduLink = data.educational_link || "https://groww.in/blog/category/mutual-funds";
    const lastUpdated = data.last_updated || "2026-07-05";

    div.innerHTML = `
        <div class="bubble-refusal rounded-2xl rounded-tl-sm p-5 md:p-6 max-w-[95%] lg:max-w-[85%] flex flex-col gap-4 shadow-lg">
            <!-- Header Row -->
            <div class="flex items-center justify-between gap-4 border-b border-amber-500/20 pb-3">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center flex-shrink-0 border border-amber-500/20">
                        <span class="material-symbols-outlined text-xl">shield_person</span>
                    </div>
                    <div>
                        <div class="text-sm font-bold text-amber-300">Zero Advisory Guardrail Triggered</div>
                        <div class="text-xs text-amber-400/80">Intent: <span class="font-bold">${data.intent}</span> (Investment Advice / Comparison Blocked)</div>
                    </div>
                </div>
                <span class="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-500/10 text-amber-400 font-semibold text-xs rounded-full border border-amber-500/20">
                    <span class="material-symbols-outlined text-[14px]">block</span>
                    <span>Refused</span>
                </span>
            </div>

            <!-- Refusal Explanation Text -->
            <div class="text-sm md:text-base text-amber-100 leading-relaxed">
                ${formatAnswerText(data.answer)}
            </div>

            <!-- Educational Resource Button (§6.11) -->
            <div class="bg-[#131b2e] border border-amber-500/20 p-4 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div class="flex items-center gap-2 text-amber-300">
                    <span class="material-symbols-outlined text-amber-400">school</span>
                    <span class="text-xs md:text-sm font-medium">Explore official educational guides and tools on Groww:</span>
                </div>
                <a href="${eduLink}" target="_blank" class="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-[#0a0e17] font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center gap-1.5 whitespace-nowrap no-underline">
                    <span>Groww Mutual Fund Guide</span>
                    <span class="material-symbols-outlined text-[16px]">open_in_new</span>
                </a>
            </div>

            <!-- Footer (§6.10) -->
            <div class="flex justify-between items-center border-t border-amber-500/20 pt-3 text-xs text-amber-400/60">
                <span><strong>Last updated:</strong> ${lastUpdated}</span>
                <span>${data.disclaimer || "Facts-only. No investment advice."}</span>
            </div>
        </div>
    `;
    chatContainer.appendChild(div);
}

/**
 * Append PII Blocked Response Bubble (§5.6 & §6.6)
 */
function appendPiiBubble(data) {
    const chatContainer = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "flex justify-start mb-4";

    div.innerHTML = `
        <div class="bubble-pii rounded-2xl rounded-tl-sm p-5 md:p-6 max-w-[95%] lg:max-w-[85%] flex flex-col gap-3 shadow-lg">
            <div class="flex items-center gap-3 text-red-400 font-bold text-sm md:text-base border-b border-red-500/20 pb-2.5">
                <span class="material-symbols-outlined text-2xl">privacy_tip</span>
                <span>Security Alert: PII Guard Triggered (§5.6)</span>
            </div>
            <div class="text-sm md:text-base text-red-200 leading-relaxed">
                ${escapeHtml(data.answer)}
            </div>
            <div class="text-xs text-red-300/80 italic mt-1 border-t border-red-500/20 pt-2">
                For your security, please never share sensitive numbers like Aadhaar, PAN, phone numbers, or passwords in chat.
            </div>
        </div>
    `;
    chatContainer.appendChild(div);
}

/**
 * Append Generic / Fallback Bubble
 */
function appendGenericBubble(data) {
    const chatContainer = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "flex justify-start mb-4";

    div.innerHTML = `
        <div class="bubble-assistant rounded-2xl rounded-tl-sm p-5 max-w-[90%] md:max-w-[80%] flex flex-col gap-3">
            <div class="flex items-center gap-2 text-[#f8fafc] font-bold text-sm">
                <span class="material-symbols-outlined text-[#00E676]">info</span>
                <span>Assistant Response (${data.status.toUpperCase()})</span>
            </div>
            <p class="text-sm md:text-base text-[#cbd5e1] leading-relaxed">${escapeHtml(data.answer)}</p>
        </div>
    `;
    chatContainer.appendChild(div);
}

/**
 * Append Network / System Error Bubble
 */
function appendErrorBubble(errText) {
    const chatContainer = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "flex justify-start mb-4";

    div.innerHTML = `
        <div class="bg-red-950/40 border border-red-500/30 rounded-2xl rounded-tl-sm p-4 max-w-[85%] text-red-300 text-sm flex items-center gap-3">
            <span class="material-symbols-outlined text-red-400 text-xl">error</span>
            <span>${escapeHtml(errText)}</span>
        </div>
    `;
    chatContainer.appendChild(div);
}

/**
 * Admin Ingestion Trigger
 */
async function triggerIngestion() {
    const btn = document.getElementById("ingest-btn");
    if (!btn) return;
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin text-[16px]">sync</span><span>Indexing...</span>`;

    try {
        const res = await fetch("/api/ingest", { method: "POST" });
        if (res.ok) {
            const data = await res.json();
            alert(`✅ Ingestion Success: ${data.message} (${data.chunks_count} chunks stored in ChromaDB)`);
            initSchemesList();
        } else {
            alert("❌ Ingestion failed. Please check server logs.");
        }
    } catch (err) {
        alert("❌ Error triggering ingestion: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
}

/**
 * Clear Chat Thread
 */
function clearChat() {
    const chatContainer = document.getElementById("chat-messages");
    const welcomeBlock = document.getElementById("welcome-block");
    if (chatContainer) {
        // Remove all appended bubbles while keeping welcome-block
        Array.from(chatContainer.children).forEach(child => {
            if (child.id !== "welcome-block") {
                child.remove();
            }
        });
    }
    if (welcomeBlock && welcomeBlock.classList.contains("hidden")) {
        welcomeBlock.classList.remove("hidden");
    }
}

/**
 * Scroll chat container to bottom
 */
function scrollToBottom() {
    const chatContainer = document.getElementById("chat-messages");
    if (chatContainer) {
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: "smooth"
        });
    }
}

/**
 * Format answer text with basic linkification and line break support
 */
function formatAnswerText(text) {
    if (!text) return "";
    let formatted = escapeHtml(text);
    // Convert newline to <br>
    formatted = formatted.replace(/\n/g, "<br/>");
    // Highlight currency ₹ and percentages automatically
    formatted = formatted.replace(/(₹\s?\d+(?:\.\d+)?)/g, '<strong class="text-[#008a63]">$1</strong>');
    formatted = formatted.replace(/(\d+(?:\.\d+)?%)/g, '<strong class="text-[#008a63]">$1</strong>');
    return formatted;
}

/**
 * HTML escape utility
 */
function escapeHtml(str) {
    if (typeof str !== 'string') return '';
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
