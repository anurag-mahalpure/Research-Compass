const API_URL = "http://localhost:8000";
const sessionId = crypto.randomUUID();

// State
let selectedDois = new Set();
let currentPapers = [];
let attachedFile = null;
let isStreaming = false;
let isActionRequest = false; 
let activeMode = "search"; // "search" | "upload"

// DOM Elements - General & Sidebar
const themeToggle = document.getElementById("theme-toggle");
const navSearch = document.getElementById("nav-search");
const navUpload = document.getElementById("nav-upload");
const searchView = document.getElementById("search-view");
const uploadView = document.getElementById("upload-view");

// DOM Elements - Search Mode
const promptInput = document.getElementById("prompt-input");
const sendBtn = document.getElementById("send-btn");
const chatFeed = document.getElementById("chat-feed");
const welcomeArea = document.getElementById("welcome-area");

// DOM Elements - Action Bar (Search Mode)
const actionBar = document.getElementById("action-bar");
const selectionCount = document.getElementById("selection-count");
const btnSummarize = document.getElementById("btn-summarize");
const btnCompare = document.getElementById("btn-compare");
const btnAsk = document.getElementById("btn-ask");
const paperCardTemplate = document.getElementById("paper-card-template");

// DOM Elements - Upload Mode
const pdfUploadInput = document.getElementById("pdf-upload-input");
const emptyUploadPanel = document.getElementById("empty-upload-panel");
const uploadWelcome = document.getElementById("upload-welcome");
const uploadChatFeed = document.getElementById("upload-chat-feed");
const uploadPromptInput = document.getElementById("upload-prompt-input");
const uploadSendBtn = document.getElementById("upload-send-btn");
const uploadInputContainer = document.getElementById("upload-input-container");
const uploadAttachBtn = document.getElementById("upload-attach-btn");

// --- Initialization & Theme ---
document.addEventListener("DOMContentLoaded", () => {
    // Check local storage for theme
    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }

    // Auto-resize textarea
    promptInput.addEventListener("input", function () {
        this.style.height = "auto";
        this.style.height = (this.scrollHeight) + "px";
        sendBtn.disabled = this.value.trim() === "" && !attachedFile;
    });

    // Enter to send (Search)
    promptInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) handleSend();
        }
    });

    // Auto-resize textarea (Upload)
    uploadPromptInput.addEventListener("input", function () {
        this.style.height = "auto";
        this.style.height = (this.scrollHeight) + "px";
        uploadSendBtn.disabled = this.value.trim() === "";
    });

    // Enter to send (Upload)
    uploadPromptInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!uploadSendBtn.disabled) handleSend();
        }
    });
});

themeToggle.addEventListener("click", () => {
    document.documentElement.classList.toggle("dark");
    localStorage.theme = document.documentElement.classList.contains("dark") ? "dark" : "light";
});

// --- Mode Switching ---
function switchMode(mode) {
    if (activeMode === mode) return;
    activeMode = mode;
    
    if (mode === "search") {
        navSearch.classList.add("active", "bg-accent/10", "text-accent");
        navSearch.classList.remove("text-slate-600", "dark:text-slate-400", "hover:bg-slate-100", "dark:hover:bg-navy-800");
        navUpload.classList.remove("active", "bg-accent/10", "text-accent");
        navUpload.classList.add("text-slate-600", "dark:text-slate-400", "hover:bg-slate-100", "dark:hover:bg-navy-800");
        
        searchView.classList.remove("hidden");
        uploadView.classList.add("hidden");
    } else if (mode === "upload") {
        navUpload.classList.add("active", "bg-accent/10", "text-accent");
        navUpload.classList.remove("text-slate-600", "dark:text-slate-400", "hover:bg-slate-100", "dark:hover:bg-navy-800");
        navSearch.classList.remove("active", "bg-accent/10", "text-accent");
        navSearch.classList.add("text-slate-600", "dark:text-slate-400", "hover:bg-slate-100", "dark:hover:bg-navy-800");
        
        uploadView.classList.remove("hidden");
        searchView.classList.add("hidden");
    }
}

navSearch.addEventListener("click", () => switchMode("search"));
navUpload.addEventListener("click", () => switchMode("upload"));

// --- File Handling (Upload View Only) ---
if (emptyUploadPanel) emptyUploadPanel.addEventListener("click", () => pdfUploadInput.click());
if (uploadAttachBtn) uploadAttachBtn.addEventListener("click", () => pdfUploadInput.click());

pdfUploadInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
        attachFileAndUpload(e.target.files[0]);
    }
});

// Drag & Drop
if (emptyUploadPanel) {
    emptyUploadPanel.addEventListener("dragover", (e) => e.preventDefault());
    emptyUploadPanel.addEventListener("drop", (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length > 0 && e.dataTransfer.files[0].type === "application/pdf") {
            attachFileAndUpload(e.dataTransfer.files[0]);
        }
    });
}

function attachFileAndUpload(file) {
    if (attachedFile && attachedFile.name !== file.name) {
        if (uploadChatFeed) {
            uploadChatFeed.innerHTML = "";
            uploadInputContainer.classList.add("hidden", "opacity-0", "pointer-events-none");
            uploadInputContainer.classList.remove("opacity-100", "z-[60]"); // hide compose box during new analysis processing
        }
    }
    
    attachedFile = file;
    // Shrink intro area
    uploadWelcome.style.height = "0";
    uploadWelcome.style.opacity = "0";
    uploadWelcome.style.overflow = "hidden";
    uploadWelcome.style.padding = "0";
    uploadWelcome.style.marginTop = "0";
    
    // Auto-trigger the backend request to begin analysis
    handleSend(true /* isAutoUpload */);
}

// --- Action Bar Logic ---
function updateActionBar() {
    const count = selectedDois.size;
    selectionCount.textContent = count;

    if (count > 0) {
        actionBar.classList.remove("translate-y-[150%]", "opacity-0");
        btnCompare.disabled = count < 2;
    } else {
        actionBar.classList.add("translate-y-[150%]", "opacity-0");
    }
}

function togglePaperSelection(doi, cardEl) {
    if (selectedDois.has(doi)) {
        selectedDois.delete(doi);
        cardEl.classList.remove("selected");
    } else {
        selectedDois.add(doi);
        cardEl.classList.add("selected");
    }
    updateActionBar();
}

// Action button triggers
btnSummarize.addEventListener("click", () => {
    isActionRequest = true;
    promptInput.value = "Summarize the selected papers.";
    handleSend();
});

btnCompare.addEventListener("click", () => {
    if (selectedDois.size < 2) return;
    isActionRequest = true;
    promptInput.value = "Compare the selected papers' methodologies and results.";
    handleSend();
});

btnAsk.addEventListener("click", () => {
    promptInput.focus();
    promptInput.placeholder = `Ask a question about the ${selectedDois.size} selected papers...`;
});

// --- Chat & SSE Logic ---
sendBtn.addEventListener("click", () => handleSend());
uploadSendBtn.addEventListener("click", () => handleSend());

async function handleSend(isAutoUpload = false) {
    if (isStreaming) return;

    let message = "";
    let activeInput = null;
    let activeFeed = null;
    let activeSendBtn = null;

    if (activeMode === "search") {
        message = promptInput.value.trim();
        activeInput = promptInput;
        activeFeed = chatFeed;
        activeSendBtn = sendBtn;
        if (!message) return;
        welcomeArea.style.display = "none";
        chatFeed.classList.remove("hidden");
    } else {
        if (isAutoUpload) {
            message = "Analyze this document."; // Internal prompt for the file payload
            activeFeed = uploadChatFeed;
        } else {
            message = uploadPromptInput.value.trim();
            activeInput = uploadPromptInput;
            activeFeed = uploadChatFeed;
            activeSendBtn = uploadSendBtn;
            if (!message) return;
        }
    }

    // Add User Message bubble
    appendUserMessage(activeMode === "upload" && isAutoUpload ? "" : message, isAutoUpload ? attachedFile : null, activeFeed);

    // Prepare FormData
    const formData = new FormData();
    formData.append("message", message);
    formData.append("session_id", sessionId);
    formData.append("app_mode", activeMode); // Let backend know which pipeline to use
    
    if (activeMode === "search") {
        formData.append("selected_dois", JSON.stringify(Array.from(selectedDois)));
        formData.append("fetched_papers", JSON.stringify(currentPapers));
    } else {
        // Upload mode: send the file if it's the auto-upload pass
        if (isAutoUpload && attachedFile) {
            formData.append("file", attachedFile);
        }
    }

    // Reset Input
    if (activeInput) {
        activeInput.value = "";
        activeInput.style.height = "auto";
        if (activeSendBtn) activeSendBtn.disabled = true;
    }
    
    // Clear the attached file variable ONLY for search mode (which was removed, but just for safety)
    // In upload mode, we keep the attached file logic in the backend context so we don't need to re-upload on Q&A
    if (isAutoUpload) {
        attachedFile = null;
        pdfUploadInput.value = "";
    }

    isStreaming = true;

    // Check if this is a search mode action request
    if (activeMode === "search" && selectedDois.size > 0) {
        isActionRequest = true;
        renderSelectedPapersStrip(selectedDois, activeFeed);
    } else if (activeMode === "upload") {
        isActionRequest = true; // For upload, we just render action results (analysis or QA)
    }

    // Create assistant response container
    const { container, contentDiv } = createAssistantContainer(activeFeed);
    contentDiv.classList.add("blinking-cursor");

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) throw new Error("Network response was not ok");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop(); // Keep incomplete line in buffer

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                try {
                    const payload = JSON.parse(line.slice(6));

                    if (payload.type === "token") {
                        appendToken(contentDiv, payload.data);
                    } else if (payload.type === "papers") {
                        contentDiv.classList.remove("blinking-cursor");
                        if (!isActionRequest) {
                            renderPaperGrid(container, payload.data, payload.source_event);
                        }
                    } else if (payload.type === "action_result") {
                        contentDiv.classList.remove("blinking-cursor");
                        renderActionResult(container, payload.data, activeFeed);
                        if (activeMode === "search") clearSelectionState(); 
                        
                        // For upload mode: reveal QA chatbox once analysis report finishes rendering
                        if (activeMode === "upload") {
                            uploadInputContainer.classList.remove("hidden", "opacity-0", "pointer-events-none");
                            uploadInputContainer.classList.add("opacity-100");
                        }
                    } else if (payload.type === "done") {
                        contentDiv.classList.remove("blinking-cursor");
                    } else if (payload.type === "error") {
                        contentDiv.classList.remove("blinking-cursor");
                        contentDiv.innerHTML += `<div class="text-red-500 mt-2"><i class="ph ph-warning"></i> Error: ${payload.data}</div>`;
                    }
                } catch (e) {
                    console.error("Error parsing SSE data:", e);
                }
            }
        }
    } catch (error) {
        contentDiv.classList.remove("blinking-cursor");
        contentDiv.innerHTML = `<div class="text-red-500"><i class="ph ph-warning"></i> Connection failed. Is the backend running?</div>`;
    } finally {
        isStreaming = false;
        if (activeMode === "search") {
            isActionRequest = false;
            sendBtn.disabled = promptInput.value.trim() === "";
        } else {
            uploadSendBtn.disabled = uploadPromptInput.value.trim() === "";
        }
    }
}

// --- Rendering functions ---

function appendUserMessage(text, file, targetFeed = chatFeed) {
    const div = document.createElement("div");
    div.className = "flex justify-end mb-6 animate-fade-in";

    let fileHTML = "";
    if (file) {
        fileHTML = `
        <div class="flex items-center gap-2 bg-white/20 p-2 rounded-lg mb-2 text-sm max-w-[200px]">
            <i class="ph-fill ph-file-pdf text-white text-xl"></i>
            <span class="truncate font-medium">${file.name}</span>
        </div>`;
    }

    // Don't render empty bubbles if it's just an auto-upload with no extra text
    if (!text && !file) return;

    div.innerHTML = `
        <div class="max-w-[80%] bg-accent text-white px-5 py-3 rounded-2xl rounded-tr-sm shadow-sm inline-block">
            ${fileHTML}
            ${text ? `<p class="leading-relaxed whitespace-pre-wrap">${text}</p>` : ''}
        </div>
    `;
    targetFeed.appendChild(div);
    scrollToBottom();
}

function createAssistantContainer(targetFeed = chatFeed) {
    const div = document.createElement("div");
    div.className = "flex items-start gap-4 mb-8 animate-fade-in w-full";

    const iconDiv = document.createElement("div");
    iconDiv.className = "w-8 h-8 rounded-full bg-slate-200 dark:bg-navy-800 flex items-center justify-center flex-shrink-0 mt-1";
    iconDiv.innerHTML = `<i class="ph-fill ph-sparkle text-accent"></i>`;

    const contentWrapper = document.createElement("div");
    contentWrapper.className = "flex-1 min-w-0 flex flex-col gap-4";

    const textContentDiv = document.createElement("div");
    textContentDiv.className = "text-slate-800 dark:text-slate-200 leading-relaxed max-w-[85%] prose prose-slate dark:prose-invert markdown-content";
    // Using a span inside to collect tokens
    const span = document.createElement("span");
    span.className = "stream-text font-body";
    textContentDiv.appendChild(span);

    contentWrapper.appendChild(textContentDiv);
    div.appendChild(iconDiv);
    div.appendChild(contentWrapper);

    targetFeed.appendChild(div);
    scrollToBottom();

    return { container: contentWrapper, contentDiv: textContentDiv, span: span };
}

function appendToken(contentDiv, token) {
    const span = contentDiv.querySelector('.stream-text');
    if (span) {
        // Collect tokens as markdown text, then convert
        span.dataset.raw = (span.dataset.raw || "") + token;
        span.innerHTML = marked.parse(span.dataset.raw);
    }
    scrollToBottom();
}

function renderPaperGrid(container, papers, sourceEvent) {
    if (papers) {
        currentPapers = papers;
    }

    // We only rely on currentPapers if papers is suddenly missing, though papers should be passed from event
    const papersToRender = papers || [];

    if (!papersToRender || papersToRender.length === 0) {
        const msg = document.createElement("div");
        msg.className = "text-slate-500 italic text-sm";
        msg.textContent = "No relevant papers found.";
        container.appendChild(msg);
        return;
    }

    // Isolate grid re-rendering so we don't append indefinitely
    let gridWrapper = container.querySelector(".paper-grid-wrapper");
    if (!gridWrapper) {
        gridWrapper = document.createElement("div");
        gridWrapper.className = "paper-grid-wrapper w-full mt-4";
        container.appendChild(gridWrapper);
    }
    gridWrapper.innerHTML = ""; // Clear existing grid layout

    // "Found X papers" header + Status
    let statusText = "";
    if (sourceEvent === 'papers_fetched') statusText = " — Reranking by relevance...";
    else if (sourceEvent === 'reranked') statusText = " — Sorted by relevance.";

    const header = document.createElement("p");
    header.className = "text-sm text-slate-500 dark:text-slate-400 font-medium mb-3";
    header.innerHTML = `Found ${papersToRender.length} relevant papers<span class="text-accent animate-pulse font-bold">${statusText}</span> Select to summarize or compare.`;
    gridWrapper.appendChild(header);

    const grid = document.createElement("div");
    grid.className = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full";

    papersToRender.forEach(p => {
        const clone = paperCardTemplate.content.cloneNode(true);
        const card = clone.querySelector(".paper-card");

        // Populate data
        card.querySelector(".paper-title").textContent = p.title;
        card.querySelector(".paper-authors").textContent = (p.authors || []).join(", ") || "Unknown Authors";

        card.querySelector(".paper-doi").textContent = p.doi ? `DOI: ${p.doi}` : "";

        const journalEl = card.querySelector(".paper-journal");
        if (journalEl) journalEl.textContent = p.journal ? `Journal: ${p.journal}` : "";

        const issnEl = card.querySelector(".paper-issn");
        if (issnEl) issnEl.textContent = p.issn ? `ISSN: ${p.issn}` : "";

        const yearBadge = card.querySelector(".year-badge");
        if (p.year) yearBadge.textContent = p.year; else yearBadge.style.display = 'none';

        const sourceBadge = card.querySelector(".source-badge");
        sourceBadge.textContent = p.source;
        card.classList.add(`source-${p.source.toLowerCase().replace(' ', '-')}`);

        const citBadge = card.querySelector(".citation-badge");
        if (citBadge && p.citationCount !== undefined && p.citationCount > 0) {
            citBadge.querySelector(".citation-count").textContent = p.citationCount;
            citBadge.style.display = 'flex';
        } else if (citBadge) {
            citBadge.style.display = 'none';
        }

        if (p.url) {
            card.querySelector(".paper-link").href = p.url;
        } else {
            card.querySelector(".paper-link").style.display = "none";
        }

        // Selection logic
        // Use DOI or title as unique key
        const uniqueKey = p.doi || p.title;

        if (selectedDois.has(uniqueKey)) {
            card.classList.add("selected");
        }

        card.addEventListener("click", (e) => {
            if (e.target.closest("a")) return; // Don't toggle if clicking the external link
            togglePaperSelection(uniqueKey, card);
        });

        grid.appendChild(card);
    });

    gridWrapper.appendChild(grid);
    scrollToBottom();
}

function renderActionResult(container, result) {
    const wrap = document.createElement("div");
    wrap.className = "mt-4 w-full";

    if (result.type === "analysis") {
        wrap.innerHTML = buildAnalysisHTML(result.data);
    } else if (result.type === "summaries") {
        let html = `<div class="flex flex-col gap-6">`;
        for (const [key, text] of Object.entries(result.data)) {
            // Look up paper metadata from currentPapers
            const paper = currentPapers.find(p => p.doi === key || p.title === key);
            const title = paper ? paper.title : key;
            const doi = paper && paper.doi ? paper.doi : "";
            const source = paper ? paper.source : "";
            const year = paper ? paper.year : "";
            const citCount = paper ? (paper.citationCount || 0) : 0;
            const url = paper ? paper.url : (doi ? `https://doi.org/${doi}` : "");

            html += `
            <div class="bg-white dark:bg-navy-900 border border-slate-200 dark:border-navy-700 rounded-2xl overflow-hidden shadow-sm">
                <div class="px-6 py-4 border-b-2 border-accent/30">
                    <div class="flex items-start justify-between gap-4">
                        <div class="flex-1 min-w-0">
                            <h3 class="font-heading font-semibold text-lg text-slate-900 dark:text-white leading-snug mb-2">${title}</h3>
                            <div class="flex items-center gap-2">
                                    ${source ? `<span class="source-badge text-[10px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded-sm">${source}</span>` : ''}
                            </div>
                        </div>
                        <div class="flex-shrink-0">
                            ${url ? `<a href="${url}" target="_blank" class="text-sm font-semibold text-accent hover:underline flex items-center gap-1">View <i class="ph-bold ph-arrow-up-right"></i></a>` : ''}
                    </div>
                </div>
                <div class="p-6 markdown-content prose prose-slate dark:prose-invert max-w-none summary-content">${marked.parse(text)}</div>
            </div>`;
        }
        html += `</div>`;
        wrap.innerHTML = html;
    } else if (result.type === "comparison") {
        // Section icon mapping
        const sectionIcons = {
            "problem statement": "ph-crosshair",
            "methodology": "ph-gear",
            "results": "ph-chart-bar",
            "strengths & weaknesses": "ph-scales",
            "strengths and weaknesses": "ph-scales",
            "best use case": "ph-lightbulb",
            "verdict": "ph-trophy",
        };

        // Split the markdown by ## headers
        const sections = result.data.split(/^## /m).filter(s => s.trim());
        let html = `<div class="flex flex-col gap-4">`;

        sections.forEach(section => {
            const newlineIdx = section.indexOf("\n");
            const heading = newlineIdx > -1 ? section.substring(0, newlineIdx).trim() : section.trim();
            const body = newlineIdx > -1 ? section.substring(newlineIdx).trim() : "";
            const icon = sectionIcons[heading.toLowerCase()] || "ph-note";
            const isVerdict = heading.toLowerCase() === "verdict";

            html += `
            <div class="bg-white dark:bg-navy-900 border ${isVerdict ? 'border-accent/30' : 'border-slate-200 dark:border-navy-700'} rounded-xl overflow-hidden shadow-sm">
                <div class="flex items-center gap-2 px-5 py-3 ${isVerdict ? 'bg-accent/5 dark:bg-accent/10' : 'bg-slate-50 dark:bg-navy-800/50'} border-b border-slate-200 dark:border-navy-700">
                    <i class="ph-bold ${icon} text-accent text-lg"></i>
                    <span class="font-semibold text-sm text-slate-800 dark:text-white tracking-wide">${heading}</span>
                </div>
                <div class="px-5 py-4 markdown-content prose prose-sm prose-slate dark:prose-invert max-w-none">${marked.parse(body)}</div>
            </div>`;
        });

        html += `</div>`;
        wrap.innerHTML = html;
    } else if (result.type === "qa") {
        wrap.innerHTML = `<div class="markdown-content bg-white dark:bg-navy-900 border border-slate-200 dark:border-navy-700 rounded-xl p-6 shadow-sm">${marked.parse(result.data)}</div>`;
    } else if (result.type === "error") {
        wrap.innerHTML = `<div class="text-red-500 bg-red-50 dark:bg-red-500/10 p-4 rounded-xl border border-red-200 dark:border-red-900/30"><i class="ph ph-warning"></i> ${result.data}</div>`;
    }

    container.appendChild(wrap);
    scrollToBottom();
}

function buildAnalysisHTML(data) {
    const renderList = (items, iconClass, colorClass) => {
        if (!items || items.length === 0) return "";
        return items.map(p => `
            <div class="flex gap-3 items-start mb-3">
                <i class="ph-fill ${iconClass} ${colorClass} mt-1 flex-shrink-0 text-lg"></i>
                <div class="text-slate-700 dark:text-slate-300 text-sm leading-relaxed">${p}</div>
            </div>`).join("");
    };

    return `
    <div class="bg-white dark:bg-navy-900 border border-slate-200 dark:border-navy-700 rounded-2xl overflow-hidden shadow-sm">
        <div class="bg-slate-50 dark:bg-navy-800/50 p-6 border-b border-slate-200 dark:border-navy-700">
            <div class="flex items-center gap-2 text-accent mb-2">
                <i class="ph-bold ph-chart-bar text-xl"></i>
                <span class="text-sm font-bold tracking-wide uppercase">Deep Analysis Report</span>
            </div>
            <h3 class="font-heading font-semibold text-2xl text-slate-900 dark:text-white leading-tight mb-4">${data.title || "Document Analysis"}</h3>
            <div class="flex flex-col gap-1.5 mb-2 text-sm text-slate-600 dark:text-slate-400">
                <p><strong class="text-slate-700 dark:text-slate-300">Authors:</strong> ${(data.authors || []).join(", ") || "Not specified"}</p>
                <p><strong class="text-slate-700 dark:text-slate-300">Journal/Publisher:</strong> ${data.journal || "Not specified"}</p>
            </div>
            ${data.keywords && data.keywords.length > 0 ? `<div class="flex flex-wrap gap-2 mt-4">${data.keywords.map(k => `<span class="bg-white dark:bg-navy-950 border border-slate-200 dark:border-navy-700 text-xs px-2.5 py-1 rounded-md text-slate-600 dark:text-slate-400">${k}</span>`).join("")}</div>` : ""}
        </div>
        
        <div class="p-6">
            <!-- Executive Summary & Final Verdict -->
            <div class="grid md:grid-cols-2 gap-8 mb-8">
                <div>
                    <h4 class="font-bold text-slate-900 dark:text-white mb-3 text-lg flex items-center gap-2"><i class="ph ph-file-text text-accent"></i> Executive Summary</h4>
                    <div class="text-slate-600 dark:text-slate-400 text-sm leading-relaxed">${data.executive_summary || ""}</div>
                </div>
                <div>
                    <h4 class="font-bold text-slate-900 dark:text-white mb-3 text-lg flex items-center gap-2"><i class="ph ph-gavel text-accent"></i> Final Verdict</h4>
                    <div class="text-slate-600 dark:text-slate-400 text-sm leading-relaxed p-4 bg-slate-50 dark:bg-navy-800/50 rounded-xl border border-slate-200 dark:border-navy-700">${data.final_verdict || ""}</div>
                </div>
            </div>

            <hr class="border-slate-100 dark:border-navy-800 my-8">

            <!-- Core Analysis -->
            <div class="grid md:grid-cols-3 gap-8 mb-8">
                <div>
                    <h4 class="font-bold text-slate-900 dark:text-white mb-3 text-lg flex items-center gap-2"><i class="ph ph-target text-slate-400"></i> Problem Statement</h4>
                    <div class="text-slate-600 dark:text-slate-400 text-sm leading-relaxed">${data.problem_statement || ""}</div>
                </div>
                <div>
                    <h4 class="font-bold text-slate-900 dark:text-white mb-3 text-lg flex items-center gap-2"><i class="ph ph-gear text-slate-400"></i> Methodology</h4>
                    <div class="text-slate-600 dark:text-slate-400 text-sm leading-relaxed">${data.methodology || ""}</div>
                </div>
                <div>
                    <h4 class="font-bold text-slate-900 dark:text-white mb-3 text-lg flex items-center gap-2"><i class="ph ph-chart-line-up text-slate-400"></i> Key Results</h4>
                    <div class="text-slate-600 dark:text-slate-400 text-sm leading-relaxed">${data.key_results || ""}</div>
                </div>
            </div>

            <hr class="border-slate-100 dark:border-navy-800 my-8">
            
            <div class="grid md:grid-cols-2 gap-8 mb-8">
                <div>
                    <h4 class="font-bold text-slate-900 dark:text-white mb-4 text-lg flex items-center gap-2"><i class="ph ph-thumbs-up text-emerald-500"></i> Strengths</h4>
                    ${renderList(data.strengths, "ph-check-circle", "text-emerald-500")}
                </div>
                <div>
                    <h4 class="font-bold text-slate-900 dark:text-white mb-4 text-lg flex items-center gap-2"><i class="ph ph-warning-circle text-amber-500"></i> Limitations</h4>
                    ${renderList(data.limitations, "ph-warning-circle", "text-amber-500")}
                </div>
            </div>

            <!-- Gaps, Future, Applications -->
            <div class="grid md:grid-cols-3 gap-8 mt-8 bg-slate-50/50 dark:bg-navy-950/30 p-6 rounded-xl border border-slate-100 dark:border-navy-800">
                <div>
                    <h4 class="font-bold text-slate-900 dark:text-white mb-3 text-md flex items-center gap-2"><i class="ph ph-magnifying-glass text-blue-500"></i> Research Gaps</h4>
                    <ul class="list-disc pl-5 text-sm text-slate-600 dark:text-slate-400 space-y-2">
                        ${(data.research_gaps || []).map(g => `<li>${g}</li>`).join("")}
                    </ul>
                </div>
                <div>
                    <h4 class="font-bold text-slate-900 dark:text-white mb-3 text-md flex items-center gap-2"><i class="ph ph-rocket text-purple-500"></i> Future Directions</h4>
                    <ul class="list-disc pl-5 text-sm text-slate-600 dark:text-slate-400 space-y-2">
                        ${(data.future_directions || []).map(f => `<li>${f}</li>`).join("")}
                    </ul>
                </div>
                <div>
                    <h4 class="font-bold text-slate-900 dark:text-white mb-3 text-md flex items-center gap-2"><i class="ph ph-buildings text-orange-500"></i> Applications</h4>
                    <div class="text-slate-600 dark:text-slate-400 text-sm leading-relaxed">${data.real_world_applications || ""}</div>
                </div>
            </div>
        </div>
    </div>
    `;
}

const scrollBtn = document.getElementById("scroll-bottom-btn");

function handleScroll(e) {
    const container = e.target;
    const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 150;
    
    if (isAtBottom) {
        scrollBtn.classList.add("opacity-0", "translate-y-4", "pointer-events-none");
    } else {
        scrollBtn.classList.remove("opacity-0", "translate-y-4", "pointer-events-none");
    }
}

if (searchView) searchView.addEventListener("scroll", handleScroll);
if (uploadView) uploadView.addEventListener("scroll", handleScroll);

if (scrollBtn) {
    scrollBtn.addEventListener("click", () => {
        scrollToBottom();
    });
}

function scrollToBottom() {
    const activeContainer = activeMode === "search" ? searchView : uploadView;
    if (activeContainer) {
        activeContainer.scrollTo({ top: activeContainer.scrollHeight, behavior: 'smooth' });
    }
}

// --- Change 1: Compact selected papers strip ---
function renderSelectedPapersStrip(selectedKeys, targetFeed = chatFeed) {
    const selected = currentPapers.filter(p => selectedKeys.has(p.doi || p.title));
    if (selected.length === 0) return;

    const stripDiv = document.createElement("div");
    stripDiv.className = "flex items-start gap-4 mb-4 animate-fade-in w-full";

    const iconDiv = document.createElement("div");
    iconDiv.className = "w-8 h-8 rounded-full bg-slate-200 dark:bg-navy-800 flex items-center justify-center flex-shrink-0 mt-1";
    iconDiv.innerHTML = `<i class="ph ph-cards text-accent"></i>`;

    const contentDiv = document.createElement("div");
    contentDiv.className = "flex-1 min-w-0";

    const label = document.createElement("p");
    label.className = "text-xs text-slate-400 dark:text-slate-500 font-medium uppercase tracking-wider mb-2";
    label.textContent = `Analyzing ${selected.length} paper${selected.length > 1 ? 's' : ''}`;
    contentDiv.appendChild(label);

    const list = document.createElement("div");
    list.className = "flex flex-col gap-2";

    selected.forEach(p => {
        const row = document.createElement("div");
        row.className = "flex items-center gap-3 bg-white dark:bg-navy-900 border border-slate-200 dark:border-navy-700 rounded-lg px-4 py-2.5";

        let badgesHTML = `<span class="source-badge text-[10px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded-sm flex-shrink-0">${p.source}</span>`;
        if (p.year) badgesHTML += `<span class="text-xs text-slate-400 font-mono flex-shrink-0">${p.year}</span>`;
        if (p.citationCount && p.citationCount > 0) badgesHTML += `<span class="text-[10px] text-amber-600 dark:text-amber-400 font-mono flex-shrink-0"><i class="ph-fill ph-quotes"></i> ${p.citationCount}</span>`;

        row.innerHTML = `
            <div class="flex items-center gap-2 flex-shrink-0">${badgesHTML}</div>
            <p class="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">${p.title}</p>
        `;
        list.appendChild(row);
    });

    contentDiv.appendChild(list);
    stripDiv.appendChild(iconDiv);
    stripDiv.appendChild(contentDiv);
    targetFeed.appendChild(stripDiv);
    scrollToBottom();
}

// --- Change 2: Clear selection state ---
function clearSelectionState() {
    selectedDois.clear();
    // Remove 'selected' class from all paper cards in the DOM
    document.querySelectorAll(".paper-card.selected").forEach(card => {
        card.classList.remove("selected");
    });
    updateActionBar();
    promptInput.placeholder = "Describe your research goal...";
}

// --- Change 3: Scroll-to-bottom button ---
(function initScrollButton() {
    const btn = document.createElement("button");
    btn.id = "scroll-to-bottom-btn";
    btn.className = "fixed right-6 z-50 w-10 h-10 rounded-full bg-accent text-white shadow-lg flex items-center justify-center opacity-0 pointer-events-none transition-all duration-300 hover:bg-blue-600 active:scale-90";
    btn.style.bottom = "120px";
    btn.innerHTML = `<i class="ph-bold ph-arrow-down text-lg"></i>`;
    btn.addEventListener("click", () => scrollToBottom());
    document.body.appendChild(btn);

    window.addEventListener("scroll", () => {
        const distFromBottom = document.body.scrollHeight - window.innerHeight - window.scrollY;
        if (distFromBottom > 300) {
            btn.classList.remove("opacity-0", "pointer-events-none");
            btn.classList.add("opacity-100", "pointer-events-auto");
        } else {
            btn.classList.add("opacity-0", "pointer-events-none");
            btn.classList.remove("opacity-100", "pointer-events-auto");
        }
    });
})();
