/**
 * SYS_CORE // PROTOCOL_DISPATCHER &bull; CLIENT CONTROLLER
 * Terminal Command Interface for Geo-Spatial Vector Dispatch & Endpoint Probe
 */

document.addEventListener("DOMContentLoaded", () => {
  // ── Mode Switcher Elements ────────────────────────────────────────────────
  const tabBtnGmb = document.getElementById("tab-btn-gmb");
  const tabBtnWebsites = document.getElementById("tab-btn-websites");
  const panelGmb = document.getElementById("panel-gmb-mode");
  const panelWebsites = document.getElementById("panel-websites-mode");

  // ── GMB Form Elements ─────────────────────────────────────────────────────
  const gmbForm = document.getElementById("gmb-form");
  const gmbNicheInput = document.getElementById("gmb-niche-input");
  const gmbLocationInput = document.getElementById("gmb-location-input");
  const gmbMaxResults = document.getElementById("gmb-max-results");
  const gmbExhaustive = document.getElementById("gmb-exhaustive");
  const gmbEnrich = document.getElementById("gmb-enrich");
  const btnGmbStart = document.getElementById("btn-gmb-start");
  const btnGmbCancel = document.getElementById("btn-gmb-cancel");

  // ── Website Form Elements ─────────────────────────────────────────────────
  const websiteForm = document.getElementById("extraction-form");
  const urlsInput = document.getElementById("urls-input");
  const fileInput = document.getElementById("file-input");
  const urlColumnInput = document.getElementById("url-column-input");
  const dropZone = document.getElementById("drop-zone");
  const dropZoneLabel = document.getElementById("drop-zone-label");
  const btnStart = document.getElementById("btn-start");
  const btnCancel = document.getElementById("btn-cancel");
  const btnLoadSample = document.getElementById("btn-load-sample");
  const colSelectedIndicator = document.getElementById("col-selected-indicator");
  const colSelectedName = document.getElementById("col-selected-name");
  const btnReselectCol = document.getElementById("btn-reselect-col");

  // ── Metrics & Progress ────────────────────────────────────────────────────
  const metricTitle1 = document.getElementById("metric-title-1");
  const metricSub1 = document.getElementById("metric-sub-1");
  const metricTitle3 = document.getElementById("metric-title-3");
  const metricSub3 = document.getElementById("metric-sub-3");
  const statMainCounter = document.getElementById("stat-main-counter");
  const statEmails = document.getElementById("stat-emails");
  const statThirdCounter = document.getElementById("stat-third-counter");
  const progressBarFill = document.getElementById("progress-bar-fill");
  const progressStatusText = document.getElementById("progress-status-text");

  // ── Console & Table ───────────────────────────────────────────────────────
  const logFeed = document.getElementById("log-feed");
  const btnClearLog = document.getElementById("btn-clear-log");
  const resultsTable = document.getElementById("results-table");
  const resultsThead = document.getElementById("results-thead");
  const resultsTbody = document.getElementById("results-tbody");
  const resultsTitle = document.getElementById("results-title");
  const resultsCountBadge = document.getElementById("results-count-badge");
  const searchInput = document.getElementById("search-results-input");
  const btnExportExcel = document.getElementById("btn-export-excel");
  const btnExportXls = document.getElementById("btn-export-xls");
  const btnExportCsv = document.getElementById("btn-export-csv");

  // ── History ───────────────────────────────────────────────────────────────
  const btnToggleHistory = document.getElementById("btn-toggle-history");
  const btnCloseHistory = document.getElementById("btn-close-history");
  const historyPanel = document.getElementById("history-panel");
  const historyList = document.getElementById("history-list");
  const historyCountBadge = document.getElementById("history-count-badge");

  // ── Search History & Pipeline ─────────────────────────────────────────────
  const btnFeedUrls = document.getElementById("btn-feed-urls");
  const pipeUrlCount = document.getElementById("pipe-url-count");
  const btnToggleSearchHistory = document.getElementById("btn-toggle-search-history");
  const btnCloseSearchHistory = document.getElementById("btn-close-search-history");
  const btnClearSearchHistory = document.getElementById("btn-clear-search-history");
  const searchHistoryPanel = document.getElementById("search-history-panel");
  const searchHistoryList = document.getElementById("search-history-list");
  const searchHistoryCountBadge = document.getElementById("search-history-count-badge");

  // ── Column Picker Modal ───────────────────────────────────────────────────
  const colPickerOverlay = document.getElementById("col-picker-overlay");
  const colList = document.getElementById("col-list");
  const modalFileInfo = document.getElementById("modal-file-info");
  const modalHintText = document.getElementById("modal-hint-text");
  const modalConfirmBtn = document.getElementById("modal-confirm-btn");
  const modalCancelBtn = document.getElementById("modal-cancel-btn");

  // ── State ─────────────────────────────────────────────────────────────────
  let currentMode = "gmb"; // "gmb" or "websites"
  let activeTaskId = null;
  let activeEventSource = null;
  let allResults = [];
  let selectedColumn = null;
  let lastInspectData = null;

  // ── 1. Tab Switching ──────────────────────────────────────────────────────
  function switchMode(mode) {
    currentMode = mode;
    if (mode === "gmb") {
      tabBtnGmb.classList.add("active");
      tabBtnWebsites.classList.remove("active");
      panelGmb.style.display = "block";
      panelWebsites.style.display = "none";

      metricTitle1.textContent = "RESOLVED_NODES";
      metricSub1.textContent = "GEO_ENTITIES_PARSED";
      metricTitle3.textContent = "ACTIVE_DOMAINS";
      metricSub3.textContent = "HOST_URLS_DETECTED";
      resultsTitle.textContent = "PERSISTENT_DATA_CACHE // GEO_NODES";
    } else {
      tabBtnWebsites.classList.add("active");
      tabBtnGmb.classList.remove("active");
      panelGmb.style.display = "none";
      panelWebsites.style.display = "block";

      metricTitle1.textContent = "HOSTS_SCANNED";
      metricSub1.textContent = "TARGET_BATCH_QUEUE";
      metricTitle3.textContent = "PAGE_PACKETS";
      metricSub3.textContent = "INTERNAL_DOM_NODES";
      resultsTitle.textContent = "PERSISTENT_DATA_CACHE // ENDPOINT_IDENTIFIERS";
    }
    renderTableHeader();
    renderTable();
  }

  tabBtnGmb.addEventListener("click", () => switchMode("gmb"));
  tabBtnWebsites.addEventListener("click", () => switchMode("websites"));

  // ── 2. Tag Suggestions Click Handler ──────────────────────────────────────
  document.querySelectorAll(".tag-pill").forEach(pill => {
    pill.addEventListener("click", () => {
      const targetId = pill.dataset.target;
      const val = pill.dataset.val;
      if (targetId && val) {
        const input = document.getElementById(targetId);
        if (input) {
          input.value = val;
          input.focus();
        }
      }
    });
  });

  // ── 3. Sample URLs for Website Mode ───────────────────────────────────────
  const sampleUrls = [
    "https://httpbin.org",
    "https://example.com",
    "https://news.ycombinator.com"
  ];

  btnLoadSample.addEventListener("click", () => {
    urlsInput.value = sampleUrls.join("\n");
    appendLog("Test target nodes buffered into URI stream.", "info");
  });

  // ── 4. Drop Zone & File Handling (Website Mode) ────────────────────────────
  dropZone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      handleFileSelected(fileInput.files[0]);
    }
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    if (!fileInput.files.length) dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
      handleFileSelected(file);
    }
  });

  async function handleFileSelected(file) {
    const fname = file.name.toLowerCase();
    dropZoneLabel.innerHTML = `PAYLOAD_LOADED: <span class="term-accent-cyan">${escapeHtml(file.name)}</span>`;
    dropZone.classList.add("has-file");

    if (fname.endsWith(".txt")) {
      colSelectedIndicator.style.display = "none";
      urlColumnInput.value = "";
      appendLog(`Raw text stream bound: ${file.name}`, "info");
      return;
    }

    if (fname.endsWith(".csv") || fname.endsWith(".xlsx") || fname.endsWith(".xls")) {
      await inspectAndShowColumnPicker(file);
    }
  }

  async function inspectAndShowColumnPicker(file) {
    const formData = new FormData();
    formData.append("file", file);

    try {
      dropZoneLabel.innerHTML = `<span class="term-accent-amber">INSPECTING_DATAFRAME_CHUNKS: ${escapeHtml(file.name)}...</span>`;
      const resp = await fetch("/api/inspect-file", { method: "POST", body: formData });
      if (!resp.ok) throw new Error("Could not parse spreadsheet payload.");
      const data = await resp.json();
      lastInspectData = data;
      showColumnPickerModal(data, file.name);
    } catch (err) {
      appendLog(`Payload inspection fault: ${err.message}`, "warning");
      dropZoneLabel.innerHTML = `PAYLOAD_LOADED: <span class="term-accent-cyan">${escapeHtml(file.name)}</span>`;
    }
  }

  function showColumnPickerModal(data, filename) {
    modalFileInfo.textContent = `[TARGET_FILE: ${filename} // ${data.total_rows} RECORDS_INDEXED]`;
    modalHintText.textContent = `> Select data column vector containing host endpoints:`;
    colList.innerHTML = "";

    selectedColumn = data.suggested_column || (data.columns.length > 0 ? data.columns[0] : null);

    data.columns.forEach(colName => {
      const samples = data.column_samples[colName] || [];
      const isAuto = colName === data.suggested_column;
      const isSelected = colName === selectedColumn;

      const item = document.createElement("div");
      item.className = `col-item${isSelected ? " selected" : ""}${isAuto ? " auto-detected" : ""}`;
      item.dataset.col = colName;

      item.innerHTML = `
        <div class="col-item-header">
          <span class="col-name">${escapeHtml(colName)}</span>
          ${isAuto ? '<span class="col-auto-badge">AUTO_MATCH</span>' : ''}
          <span class="col-count-tag">${data.total_rows} rows</span>
        </div>
        <div class="col-samples">
          ${samples.slice(0, 3).map(s => `<span class="col-sample">${escapeHtml(s)}</span>`).join("")}
        </div>
      `;

      item.addEventListener("click", () => {
        colList.querySelectorAll(".col-item").forEach(el => el.classList.remove("selected"));
        item.classList.add("selected");
        selectedColumn = colName;
        modalConfirmBtn.disabled = false;
      });

      colList.appendChild(item);
    });

    modalConfirmBtn.disabled = !selectedColumn;
    colPickerOverlay.classList.add("open");
  }

  modalConfirmBtn.addEventListener("click", () => {
    if (!selectedColumn) return;
    urlColumnInput.value = selectedColumn;
    colSelectedName.textContent = selectedColumn;
    colSelectedIndicator.style.display = "flex";
    colPickerOverlay.classList.remove("open");
    appendLog(`Bound vector column: "${selectedColumn}"`, "info");
  });

  modalCancelBtn.addEventListener("click", () => colPickerOverlay.classList.remove("open"));

  // ── 5. GMB Form Submission ────────────────────────────────────────────────
  gmbForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const niche = gmbNicheInput.value.trim();
    const location = gmbLocationInput.value.trim();
    const maxResults = parseInt(gmbMaxResults.value, 10) || 100;
    const exhaustiveMode = gmbExhaustive.checked;
    const enrichEmails = gmbEnrich.checked;

    if (!niche || !location) {
      alert("Missing parameter: Target Vector and Spatial Sector are mandatory.");
      return;
    }

    allResults = [];
    resetMetrics();
    renderTableHeader();
    renderTable();
    setRunningState(true, "gmb");
    appendLog(`[INIT] Dispatching geo-spatial sequence: '${niche}' in sector '${location}'...`, "info");

    const formData = new FormData();
    formData.append("niche", niche);
    formData.append("location", location);
    formData.append("max_results", maxResults);
    formData.append("exhaustive_mode", exhaustiveMode);
    formData.append("enrich_emails", enrichEmails);

    try {
      const resp = await fetch("/api/gmb/tasks", { method: "POST", body: formData });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Dispatch request rejected.");
      }
      const data = await resp.json();
      activeTaskId = data.task_id;
      statMainCounter.textContent = "0";
      appendLog(`[DISPATCH] Task registered [PID: ${activeTaskId}]. Target vector staged (Cap: ${maxResults}).`, "info");

      connectEventStream(activeTaskId, "gmb");

    } catch (err) {
      appendLog(`[FAULT] ${err.message}`, "error");
      setRunningState(false, "gmb");
    }
  });

  btnGmbCancel.addEventListener("click", async () => {
    if (!activeTaskId) return;
    appendLog("[INTERRUPT] Sending SIGTERM to thread...", "warning");
    try {
      await fetch(`/api/tasks/${activeTaskId}/cancel`, { method: "POST" });
      if (activeEventSource) activeEventSource.close();
      setRunningState(false, "gmb");
      appendLog("[ABORT] Process terminated by user.", "warning");
      progressStatusText.textContent = "SIGNAL_ABORT // THREAD_TERMINATED";
    } catch (e) {
      console.error(e);
    }
  });

  // ── 6. Website Form Submission ────────────────────────────────────────────
  websiteForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const textUrls = urlsInput.value.trim();
    const hasFile = fileInput.files.length > 0;

    if (!textUrls && !hasFile) {
      alert("Missing input: Buffer target endpoints or provide dataframe payload.");
      return;
    }

    allResults = [];
    resetMetrics();
    renderTableHeader();
    renderTable();
    setRunningState(true, "websites");

    const formData = new FormData(websiteForm);

    try {
      const response = await fetch("/api/tasks", { method: "POST", body: formData });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Stream initiation failure.");
      }

      const data = await response.json();
      activeTaskId = data.task_id;
      statMainCounter.textContent = `0 / ${data.total_urls}`;
      appendLog(`[DISPATCH] Stream staged [PID: ${activeTaskId}]. Buffer size: ${data.total_urls} host(s).`, "info");

      connectEventStream(activeTaskId, "websites");

    } catch (err) {
      appendLog(`[FAULT] ${err.message}`, "error");
      setRunningState(false, "websites");
    }
  });

  btnCancel.addEventListener("click", async () => {
    if (!activeTaskId) return;
    appendLog("[INTERRUPT] Aborting crawler stream...", "warning");
    try {
      await fetch(`/api/tasks/${activeTaskId}/cancel`, { method: "POST" });
      if (activeEventSource) activeEventSource.close();
      setRunningState(false, "websites");
      appendLog("[ABORT] Stream interrupted by user signal.", "warning");
      progressStatusText.textContent = "SIGNAL_ABORT // STREAM_CLOSED";
    } catch (e) {
      console.error(e);
    }
  });

  // ── 7. Unified SSE Stream Connection ──────────────────────────────────────
  function connectEventStream(taskId, mode) {
    if (activeEventSource) activeEventSource.close();
    activeEventSource = new EventSource(`/api/tasks/${taskId}/stream`);

    activeEventSource.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleStreamEvent(msg, mode);
      } catch (e) { /* heartbeat */ }
    };

    activeEventSource.onerror = () => {
      if (activeEventSource) activeEventSource.close();
      setRunningState(false, mode);
    };
  }

  function handleStreamEvent(msg, mode) {
    switch (msg.type) {
      case "init":
        if (msg.task_type === "gmb" || mode === "gmb") {
          currentMode = "gmb";
          renderTableHeader();
          statMainCounter.textContent = msg.completed_sites || 0;
          statEmails.textContent = msg.total_emails || 0;
          statThirdCounter.textContent = (msg.existing_results || []).filter(r => r.website).length;
        } else {
          currentMode = "websites";
          renderTableHeader();
          statMainCounter.textContent = `${msg.completed_sites} / ${msg.total_sites}`;
          statEmails.textContent = msg.total_emails || 0;
          statThirdCounter.textContent = msg.total_pages || 0;
        }
        if (msg.existing_results && msg.existing_results.length > 0) {
          allResults = msg.existing_results;
          renderTable();
        }
        break;

      case "gmb_start":
        appendLog(`[ACTIVE] ${msg.message}`, "info");
        progressStatusText.textContent = `EXEC_SWEEP // ${msg.niche} @ ${msg.location}`;
        progressBarFill.style.width = "10%";
        break;

      case "log":
        appendLog(msg.message, msg.level || "info");
        break;

      case "gmb_profile_found":
        const profile = msg.profile;
        const existingIdx = allResults.findIndex(p => p.place_id === profile.place_id);
        if (existingIdx >= 0) {
          allResults[existingIdx] = profile;
        } else {
          allResults.push(profile);
        }
        renderTable();
        statMainCounter.textContent = msg.total_profiles;
        statEmails.textContent = msg.total_emails;
        statThirdCounter.textContent = allResults.filter(r => r.website).length;
        progressStatusText.textContent = `RESOLVED: ${profile.business_name} // 0x${Math.floor(Math.random()*65535).toString(16).toUpperCase()}`;
        break;

      case "task_start":
        appendLog(`[RUNNING] ${msg.message}`, "info");
        progressStatusText.textContent = msg.message;
        break;

      case "progress":
        const pData = msg.data;
        if (pData.event === "page_start") {
          progressStatusText.textContent = `STREAM_PACKET: ${pData.current_page}`;
          statThirdCounter.textContent = msg.total_pages + pData.pages_scanned;
        } else if (pData.event === "email_found") {
          appendLog(`[IDENT_MATCH] Discovered payload on ${pData.source_page}: ${pData.email}`, "success");
          statEmails.textContent = msg.total_emails + 1;
        }
        break;

      case "site_done":
        const site = msg.site;
        allResults.push(site);
        renderTable();
        statMainCounter.textContent = `${msg.completed_sites} / ${msg.total_sites}`;
        statEmails.textContent = msg.total_emails;
        statThirdCounter.textContent = msg.total_pages;

        const percent = Math.round((msg.completed_sites / msg.total_sites) * 100);
        progressBarFill.style.width = `${percent}%`;

        if (site.status === "Success") {
          appendLog(`[COMMITTED] ${site.target_url} -> ${site.all_emails_list ? site.all_emails_list.length : 0} payload(s). Primary: ${site.primary_email}`, "success");
        } else {
          appendLog(`[STATUS_FLAG] ${site.target_url} -> ${site.status}`, "warning");
        }
        break;

      case "task_completed":
        appendLog(`[SYS_OK] ${msg.message}`, "success");
        progressStatusText.textContent = "SEQUENCE_COMPLETE // RECORDS_COMMITTED_TO_CACHE";
        progressBarFill.style.width = "100%";
        setRunningState(false, mode);
        if (activeEventSource) activeEventSource.close();
        setTimeout(() => {
          loadHistory();
          loadSearchHistory();
        }, 800);
        break;

      case "task_error":
        appendLog(`[SYS_FAULT] ${msg.message}`, "error");
        progressStatusText.textContent = "FAULT // PROCESS_HALTED";
        setRunningState(false, mode);
        if (activeEventSource) activeEventSource.close();
        break;
    }
  }

  function resetMetrics() {
    statMainCounter.textContent = "0";
    statEmails.textContent = "0";
    statThirdCounter.textContent = "0";
    progressBarFill.style.width = "0%";
    progressStatusText.textContent = "THREAD_ACTIVE // BUFFERING_STREAM...";
  }

  function setRunningState(isRunning, mode) {
    if (isRunning) {
      if (mode === "gmb") {
        btnGmbStart.style.display = "none";
        btnGmbCancel.style.display = "inline-flex";
      } else {
        btnStart.style.display = "none";
        btnCancel.style.display = "inline-flex";
      }
      btnExportExcel.disabled = true;
      btnExportXls.disabled = true;
      btnExportCsv.disabled = true;
    } else {
      btnGmbStart.style.display = "inline-flex";
      btnGmbCancel.style.display = "none";
      btnStart.style.display = "inline-flex";
      btnCancel.style.display = "none";
      if (allResults.length > 0) {
        btnExportExcel.disabled = false;
        btnExportXls.disabled = false;
        btnExportCsv.disabled = false;
      }
    }
  }

  // ── 8. Table Header & Body Rendering ──────────────────────────────────────
  function renderTableHeader() {
    const isGmb = currentMode === "gmb" || (allResults.length > 0 && allResults[0].business_name);
    if (isGmb) {
      resultsThead.innerHTML = `
        <tr>
          <th>ENTITY_IDENTIFIER</th>
          <th>SECTOR_CLASS</th>
          <th>COMM_LINE</th>
          <th>IDENTITY_PAYLOAD</th>
          <th>HOST_ENDPOINT</th>
          <th>GEO_COORDINATES</th>
          <th>CONF_SCORE</th>
          <th>SYS_REF</th>
        </tr>
      `;
    } else {
      resultsThead.innerHTML = `
        <tr>
          <th>HOST_ENDPOINT</th>
          <th>PRIMARY_IDENTITY</th>
          <th>DISCOVERED_PAYLOADS</th>
          <th>PACKETS_SCANNED</th>
          <th>STATUS_CODE</th>
          <th>COMMANDS</th>
        </tr>
      `;
    }
  }

  function renderTable() {
    const isGmb = currentMode === "gmb" || (allResults.length > 0 && allResults[0].business_name);
    const query = searchInput.value.trim().toLowerCase();

    const filtered = allResults.filter(r => {
      if (!query) return true;
      if (isGmb) {
        const name = (r.business_name || "").toLowerCase();
        const cat = (r.category || "").toLowerCase();
        const phone = (r.phone || "").toLowerCase();
        const email = (r.primary_email || "").toLowerCase();
        const addr = (r.address || "").toLowerCase();
        const web = (r.website || "").toLowerCase();
        return name.includes(query) || cat.includes(query) || phone.includes(query) || email.includes(query) || addr.includes(query) || web.includes(query);
      } else {
        const target = (r.target_url || "").toLowerCase();
        const primary = (r.primary_email || "").toLowerCase();
        const all = (r.all_emails || "").toLowerCase();
        return target.includes(query) || primary.includes(query) || all.includes(query);
      }
    });

    resultsCountBadge.textContent = `[BUFFER: ${allResults.length} RECORD${allResults.length === 1 ? '' : 'S'}]`;

    // ── Update [PIPE_URLS_TO_EMAIL_TAB] Button Visibility ──
    if (btnFeedUrls && pipeUrlCount) {
      const websiteUrls = allResults
        .map(r => r.website)
        .filter(w => w && typeof w === "string" && w.trim().length > 3 && w !== "-");
      const uniqueWebsites = [...new Set(websiteUrls.map(w => w.trim()))];

      if (uniqueWebsites.length > 0 && (currentMode === "gmb" || (allResults.length > 0 && allResults[0].business_name))) {
        btnFeedUrls.style.display = "inline-flex";
        pipeUrlCount.textContent = uniqueWebsites.length;
      } else {
        btnFeedUrls.style.display = "none";
      }
    }

    if (filtered.length === 0) {
      const colSpan = isGmb ? 8 : 6;
      resultsTbody.innerHTML = `
        <tr class="empty-row">
          <td colspan="${colSpan}">${allResults.length === 0 ? '[BUFFER_EMPTY] No records staged. Execute a query above to populate data cache.' : '[GREP_EMPTY] No matching records found for current query.'}</td>
        </tr>
      `;
      return;
    }

    if (isGmb) {
      resultsTbody.innerHTML = filtered.map(r => {
        const ratingStr = r.rating ? `<span class="rating-pill">⭐ ${escapeHtml(r.rating)}<span class="reviews-cnt">(${escapeHtml(r.reviews_count || '0')})</span></span>` : '<span class="term-dim">-</span>';

        const phoneBadge = r.phone 
          ? `<span class="phone-tag">${escapeHtml(r.phone)}</span>`
          : '<span class="term-dim">-</span>';

        const emailBadge = r.primary_email 
          ? `<div class="primary-email-badge">
               <span>⚡</span>
               ${escapeHtml(r.primary_email)}
             </div>`
          : '<span class="term-dim">-</span>';

        const webLink = r.website
          ? `<a href="${escapeHtml(r.website)}" target="_blank" rel="noopener noreferrer" class="link-pill">[HOST ↗]</a>`
          : '<span class="term-dim">-</span>';

        const mapsLink = r.maps_url
          ? `<a href="${escapeHtml(r.maps_url)}" target="_blank" rel="noopener noreferrer" class="link-pill link-maps">[GEO_REF ↗]</a>`
          : '<span class="term-dim">-</span>';

        return `
          <tr>
            <td><strong>${escapeHtml(r.business_name || 'N/A')}</strong></td>
            <td><span class="term-badge-sub">${escapeHtml(r.category || 'NODE')}</span></td>
            <td>${phoneBadge}</td>
            <td>${emailBadge}</td>
            <td>${webLink}</td>
            <td style="max-width: 220px; font-size: 11px; color: var(--term-text-muted);">${escapeHtml(r.address || '-')}</td>
            <td>${ratingStr}</td>
            <td>${mapsLink}</td>
          </tr>
        `;
      }).join("");

    } else {
      resultsTbody.innerHTML = filtered.map(r => {
        let statusClass = "danger";
        if (r.status === "Success") statusClass = "success";
        else if (r.status === "No Email Found") statusClass = "warning";

        const emailList = r.all_emails_list || [];
        const emailChips = emailList.length > 0
          ? emailList.map(em => `<span class="email-tag">${escapeHtml(em)}</span>`).join("")
          : '<span class="term-dim">None</span>';

        const primaryBadge = r.primary_email
          ? `<div class="primary-email-badge">
               <span>⚡</span>
               ${escapeHtml(r.primary_email)}
             </div>`
          : '<span class="term-dim">-</span>';

        return `
          <tr>
            <td>
              <a href="${escapeHtml(r.target_url)}" target="_blank" rel="noopener noreferrer" class="site-url-link">
                ${escapeHtml(r.target_url)}
                <span style="font-size:10px;">↗</span>
              </a>
            </td>
            <td>${primaryBadge}</td>
            <td><div style="max-width: 320px; display: flex; flex-wrap: wrap;">${emailChips}</div></td>
            <td><strong>${r.pages_scanned || 0}</strong></td>
            <td><span class="status-chip ${statusClass}">[${escapeHtml(r.status)}]</span></td>
            <td>
              ${r.primary_email ? `<button type="button" class="copy-btn" onclick="navigator.clipboard.writeText('${escapeHtml(r.primary_email)}'); this.textContent = '[COPIED]'; setTimeout(() => this.textContent = '[CPY]', 1500);">[CPY]</button>` : '-'}
            </td>
          </tr>
        `;
      }).join("");
    }
  }

  searchInput.addEventListener("input", renderTable);

  // ── 9. Live Downloads ─────────────────────────────────────────────────────
  btnExportExcel.addEventListener("click", () => {
    if (!activeTaskId) return;
    window.location.href = `/api/tasks/${activeTaskId}/export/excel`;
  });

  btnExportXls.addEventListener("click", () => {
    if (!activeTaskId) return;
    window.location.href = `/api/tasks/${activeTaskId}/export/xls`;
  });

  btnExportCsv.addEventListener("click", () => {
    if (!activeTaskId) return;
    window.location.href = `/api/tasks/${activeTaskId}/export/csv`;
  });

  // ── Pipe Discovered URLs into Email Extraction Tab ─────────────────────────
  if (btnFeedUrls) {
    btnFeedUrls.addEventListener("click", () => {
      const websiteUrls = allResults
        .map(r => r.website)
        .filter(w => w && typeof w === "string" && w.trim().length > 3 && w !== "-");
      const uniqueWebsites = [...new Set(websiteUrls.map(w => w.trim()))];

      if (uniqueWebsites.length === 0) {
        alert("No valid website URLs discovered in currently staged profiles.");
        return;
      }

      urlsInput.value = uniqueWebsites.join("\n");
      switchMode("websites");

      const originalHtml = btnFeedUrls.innerHTML;
      btnFeedUrls.innerHTML = `<span class="btn-glyph">✓</span> [PIPED ${uniqueWebsites.length} HOSTS!]`;
      setTimeout(() => {
        btnFeedUrls.innerHTML = originalHtml;
      }, 2000);

      panelWebsites.scrollIntoView({ behavior: "smooth", block: "start" });
      urlsInput.focus();

      appendLog(`[PIPE_OK] Piped ${uniqueWebsites.length} unique domain host(s) into TTY-02 URI stream buffer. Ready for email extraction sequence.`, "success");
    });
  }

  // ── 10. History Panel ─────────────────────────────────────────────────────
  btnToggleHistory.addEventListener("click", () => {
    const isOpen = historyPanel.style.display !== "none";
    if (isOpen) {
      historyPanel.style.display = "none";
    } else {
      historyPanel.style.display = "block";
      loadHistory();
    }
  });

  btnCloseHistory.addEventListener("click", () => {
    historyPanel.style.display = "none";
  });

  async function loadHistory() {
    try {
      const resp = await fetch("/api/history");
      const data = await resp.json();
      const sessions = data.sessions || [];

      if (sessions.length > 0) {
        historyCountBadge.textContent = sessions.length;
        historyCountBadge.style.display = "inline-flex";
      } else {
        historyCountBadge.style.display = "none";
      }

      if (sessions.length === 0) {
        historyList.innerHTML = `<div class="history-empty">[ARCHIVE_EMPTY] No persistent sessions found. Complete a query sequence to commit records.</div>`;
        return;
      }

      historyList.innerHTML = sessions.map(s => {
        const isGmb = s.task_type === "gmb" || s.niche;
        const typeBadge = isGmb 
          ? `<span class="term-badge-tag" style="border-color:var(--neon-green); color:var(--neon-green)">[GEO_VECTOR]</span>` 
          : `<span class="term-badge-tag">[URI_PROBE]</span>`;

        const titleText = isGmb 
          ? `<strong>${escapeHtml(s.niche)}</strong> @ ${escapeHtml(s.location)}`
          : `${s.completed_sites}/${s.total_sites} target hosts`;

        const statsText = isGmb
          ? `<span>⬢ ${s.total_profiles || 0} nodes</span> <span>⚡ ${s.total_emails || 0} payloads</span>`
          : `<span>🌐 ${s.completed_sites}/${s.total_sites} hosts</span> <span>⚡ ${s.total_emails} payloads</span>`;

        return `
          <div class="history-item" data-id="${escapeHtml(s.task_id)}">
            <div class="history-item-left">
              <div class="history-item-meta">
                ${typeBadge}
                <span class="history-timestamp">[${escapeHtml(s.timestamp_display)}]</span>
                <span class="history-badge ${s.status === 'Completed' ? 'success' : 'warning'}">[${escapeHtml(s.status)}]</span>
              </div>
              <div style="font-size: 12px; color: var(--term-text-bright); margin-top: 2px;">
                ${titleText}
              </div>
              <div class="history-item-stats">
                ${statsText}
              </div>
            </div>
            <div class="history-item-actions">
              <button class="term-btn btn-hist-load hist-load" data-id="${escapeHtml(s.task_id)}" data-type="${isGmb ? 'gmb' : 'websites'}" title="Mount session into active cache">
                [LOAD_CACHE]
              </button>
              <button class="term-btn hist-dl-xlsx" data-id="${escapeHtml(s.task_id)}" title="Dump XLSX">
                .XLSX
              </button>
              <button class="term-btn hist-dl-xls" data-id="${escapeHtml(s.task_id)}" title="Dump XLS">
                .XLS
              </button>
              <button class="term-btn hist-dl-csv" data-id="${escapeHtml(s.task_id)}" title="Dump CSV">
                .CSV
              </button>
              <button class="term-btn hist-delete" data-id="${escapeHtml(s.task_id)}" title="Purge Record">
                [DEL]
              </button>
            </div>
          </div>
        `;
      }).join("");

      // Bind view/load buttons
      historyList.querySelectorAll(".hist-load").forEach(btn => {
        btn.addEventListener("click", async () => {
          try {
            const r = await fetch(`/api/history/${btn.dataset.id}/results`);
            if (!r.ok) {
              appendLog("[FAULT] Could not load archived session records.", "error");
              return;
            }
            const data = await r.json();
            allResults = data.results || [];
            activeTaskId = btn.dataset.id;
            currentMode = btn.dataset.type || "gmb";
            switchMode(currentMode);

            if (data.entry) {
              statEmails.textContent = data.entry.total_emails ?? allResults.length;
              statMainCounter.textContent = data.entry.total_profiles ?? data.entry.completed_sites ?? allResults.length;
              progressBarFill.style.width = "100%";
              progressStatusText.textContent = `MOUNTED_CACHE // SESSION [${data.entry.timestamp_display}]`;
            }

            btnExportExcel.disabled = false;
            btnExportXls.disabled = false;
            btnExportCsv.disabled = false;

            historyPanel.style.display = "none";
            document.getElementById("results-section").scrollIntoView({ behavior: "smooth" });
            appendLog(`[MOUNT_OK] Historical session ${btn.dataset.id} staged into cache (${allResults.length} records).`, "success");
          } catch (err) {
            appendLog(`[FAULT] Error mounting archive: ${err.message}`, "error");
          }
        });
      });

      // Bind download buttons
      historyList.querySelectorAll(".hist-dl-xlsx").forEach(btn => {
        btn.addEventListener("click", () => {
          window.location.href = `/api/history/${btn.dataset.id}/download/xlsx`;
        });
      });

      historyList.querySelectorAll(".hist-dl-xls").forEach(btn => {
        btn.addEventListener("click", () => {
          window.location.href = `/api/history/${btn.dataset.id}/download/xls`;
        });
      });

      historyList.querySelectorAll(".hist-dl-csv").forEach(btn => {
        btn.addEventListener("click", () => {
          window.location.href = `/api/history/${btn.dataset.id}/download/csv`;
        });
      });

      // Bind delete button
      historyList.querySelectorAll(".hist-delete").forEach(btn => {
        btn.addEventListener("click", async () => {
          if (!confirm("Purge this archived session and its committed files from disk?")) return;
          try {
            const r = await fetch(`/api/history/${btn.dataset.id}`, { method: "DELETE" });
            if (r.ok) {
              loadHistory();
            }
          } catch (err) {
            console.error(err);
          }
        });
      });

    } catch (err) {
      historyList.innerHTML = `<div class="history-empty" style="color:var(--neon-red)">[FAULT] Failed to retrieve session database.</div>`;
    }
  }

  // ── 11. Search History Panel & Audit Trail ─────────────────────────────────
  if (btnToggleSearchHistory) {
    btnToggleSearchHistory.addEventListener("click", () => {
      const isOpen = searchHistoryPanel.style.display !== "none";
      if (isOpen) {
        searchHistoryPanel.style.display = "none";
      } else {
        searchHistoryPanel.style.display = "block";
        historyPanel.style.display = "none";
        loadSearchHistory();
      }
    });
  }

  if (btnCloseSearchHistory) {
    btnCloseSearchHistory.addEventListener("click", () => {
      searchHistoryPanel.style.display = "none";
    });
  }

  if (btnClearSearchHistory) {
    btnClearSearchHistory.addEventListener("click", async () => {
      if (!confirm("Purge all persistent search history records?")) return;
      try {
        const resp = await fetch("/api/search-history", { method: "DELETE" });
        if (resp.ok) {
          loadSearchHistory();
          appendLog("[PURGE] Search history audit logs cleared.", "info");
        }
      } catch (e) {
        console.error(e);
      }
    });
  }

  async function loadSearchHistory() {
    try {
      const resp = await fetch("/api/search-history");
      const data = await resp.json();
      const searches = data.searches || [];

      if (searches.length > 0) {
        searchHistoryCountBadge.textContent = searches.length;
        searchHistoryCountBadge.style.display = "inline-flex";
      } else {
        searchHistoryCountBadge.style.display = "none";
      }

      if (searches.length === 0) {
        searchHistoryList.innerHTML = `<div class="history-empty">[EMPTY_LOG] No search queries recorded yet. Execute a search to record query telemetry.</div>`;
        return;
      }

      searchHistoryList.innerHTML = searches.map(s => {
        const isGmb = s.search_type === "gmb";
        const typeBadge = isGmb 
          ? `<span class="term-badge-tag" style="border-color:var(--neon-green); color:var(--neon-green)">[GEO_VECTOR]</span>` 
          : `<span class="term-badge-tag">[URI_PROBE]</span>`;

        let statusClass = "warning";
        if (s.status === "Completed") statusClass = "success";
        else if (s.status === "Failed" || s.status === "Cancelled") statusClass = "danger";

        const countLabel = isGmb
          ? `<span class="term-accent-green" style="font-weight:700;">⬢ ${s.results_count || 0} PROFILES EXTRACTED</span>`
          : `<span class="term-accent-cyan" style="font-weight:700;">🌐 ${s.results_count || 0} HOSTS SCANNED</span>`;

        const emailLabel = `<span class="term-accent-cyan">⚡ ${s.emails_count || 0} EMAILS</span>`;

        return `
          <div class="history-item" data-id="${escapeHtml(s.task_id)}">
            <div class="history-item-left">
              <div class="history-item-meta">
                ${typeBadge}
                <span class="history-timestamp">[${escapeHtml(s.timestamp_display)}]</span>
                <span class="status-chip ${statusClass}">[${escapeHtml(s.status)}]</span>
              </div>
              <div style="font-size: 13px; font-weight: 700; color: var(--term-text-bright); margin-top: 3px;">
                ${escapeHtml(s.query)}
              </div>
              <div class="history-item-stats">
                ${countLabel} &bull; ${emailLabel}
              </div>
            </div>
            <div class="history-item-actions">
              <button class="term-btn btn-search-load" data-id="${escapeHtml(s.task_id)}" data-type="${isGmb ? 'gmb' : 'websites'}" title="Mount extracted results into active table">
                [LOAD_RESULTS]
              </button>
              ${isGmb && s.niche ? `
              <button class="term-btn btn-search-rerun" data-niche="${escapeHtml(s.niche)}" data-location="${escapeHtml(s.location)}" title="Populate form and re-run search">
                [RE-SEARCH]
              </button>` : ''}
              <button class="term-btn btn-search-del" data-id="${escapeHtml(s.task_id)}" title="Delete Search Record">
                [DEL]
              </button>
            </div>
          </div>
        `;
      }).join("");

      // Bind Search Load buttons
      searchHistoryList.querySelectorAll(".btn-search-load").forEach(btn => {
        btn.addEventListener("click", async () => {
          try {
            const r = await fetch(`/api/history/${btn.dataset.id}/results`);
            if (!r.ok) {
              appendLog("[FAULT] Could not load search result data.", "error");
              return;
            }
            const data = await r.json();
            allResults = data.results || [];
            activeTaskId = btn.dataset.id;
            currentMode = btn.dataset.type || "gmb";
            switchMode(currentMode);

            if (data.entry) {
              statEmails.textContent = data.entry.total_emails ?? allResults.length;
              statMainCounter.textContent = data.entry.total_profiles ?? data.entry.completed_sites ?? allResults.length;
              progressBarFill.style.width = "100%";
              progressStatusText.textContent = `MOUNTED_CACHE // SEARCH [${data.entry.timestamp_display}]`;
            }

            btnExportExcel.disabled = false;
            btnExportXls.disabled = false;
            btnExportCsv.disabled = false;

            searchHistoryPanel.style.display = "none";
            document.getElementById("results-section").scrollIntoView({ behavior: "smooth" });
            appendLog(`[MOUNT_OK] Historical search ${btn.dataset.id} loaded (${allResults.length} records).`, "success");
          } catch (err) {
            appendLog(`[FAULT] Error loading search results: ${err.message}`, "error");
          }
        });
      });

      // Bind Re-Search buttons
      searchHistoryList.querySelectorAll(".btn-search-rerun").forEach(btn => {
        btn.addEventListener("click", () => {
          const niche = btn.dataset.niche;
          const loc = btn.dataset.location;
          if (niche && loc) {
            switchMode("gmb");
            gmbNicheInput.value = niche;
            gmbLocationInput.value = loc;
            searchHistoryPanel.style.display = "none";
            panelGmb.scrollIntoView({ behavior: "smooth" });
            btnGmbStart.focus();
            appendLog(`[RE-QUERY] Staged search vector: '${niche}' in '${loc}'. Ready to initialize dispatch.`, "info");
          }
        });
      });

      // Bind Search Delete buttons
      searchHistoryList.querySelectorAll(".btn-search-del").forEach(btn => {
        btn.addEventListener("click", async () => {
          try {
            const r = await fetch(`/api/search-history/${btn.dataset.id}`, { method: "DELETE" });
            if (r.ok) {
              loadSearchHistory();
            }
          } catch (err) {
            console.error(err);
          }
        });
      });

    } catch (err) {
      searchHistoryList.innerHTML = `<div class="history-empty" style="color:var(--neon-red)">[FAULT] Failed to retrieve search history.</div>`;
    }
  }

  // ── Logging & Utilities ───────────────────────────────────────────────────
  function appendLog(message, level = "info") {
    const entry = document.createElement("div");
    entry.className = `log-entry ${level}`;
    const timestamp = new Date().toLocaleTimeString();
    entry.textContent = `[${timestamp}] ${message}`;
    logFeed.appendChild(entry);
    logFeed.scrollTop = logFeed.scrollHeight;
  }

  btnClearLog.addEventListener("click", () => {
    logFeed.innerHTML = '<div class="log-entry info">[SYS_RESET] Console stream cleared.</div>';
  });

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Initial startup
  switchMode("gmb");
  loadHistory();
  loadSearchHistory();
});
