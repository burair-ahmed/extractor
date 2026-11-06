/**
 * Email Extractor Pro - Client-side Controller v2
 * Real-time SSE streaming, XLS column picker, live DOM updates,
 * table search, export triggers, and history panel.
 */

document.addEventListener("DOMContentLoaded", () => {
  // ── Core elements ─────────────────────────────────────────────────────────
  const form = document.getElementById("extraction-form");
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

  // ── Metrics & Progress ─────────────────────────────────────────────────────
  const statEmails = document.getElementById("stat-emails");
  const statSites = document.getElementById("stat-sites");
  const statSitesPercent = document.getElementById("stat-sites-percent");
  const statPages = document.getElementById("stat-pages");
  const progressBarFill = document.getElementById("progress-bar-fill");
  const progressStatusText = document.getElementById("progress-status-text");

  // ── Console & Table ────────────────────────────────────────────────────────
  const logFeed = document.getElementById("log-feed");
  const btnClearLog = document.getElementById("btn-clear-log");
  const resultsTbody = document.getElementById("results-tbody");
  const resultsCountBadge = document.getElementById("results-count-badge");
  const searchInput = document.getElementById("search-results-input");
  const btnExportExcel = document.getElementById("btn-export-excel");
  const btnExportXls = document.getElementById("btn-export-xls");
  const btnExportCsv = document.getElementById("btn-export-csv");

  // ── History ────────────────────────────────────────────────────────────────
  const btnToggleHistory = document.getElementById("btn-toggle-history");
  const btnCloseHistory = document.getElementById("btn-close-history");
  const historyPanel = document.getElementById("history-panel");
  const historyList = document.getElementById("history-list");
  const historyCountBadge = document.getElementById("history-count-badge");

  // ── Column Picker Modal ────────────────────────────────────────────────────
  const colPickerOverlay = document.getElementById("col-picker-overlay");
  const colList = document.getElementById("col-list");
  const modalFileInfo = document.getElementById("modal-file-info");
  const modalHintText = document.getElementById("modal-hint-text");
  const modalConfirmBtn = document.getElementById("modal-confirm-btn");
  const modalCancelBtn = document.getElementById("modal-cancel-btn");

  // ── State ──────────────────────────────────────────────────────────────────
  let activeTaskId = null;
  let activeEventSource = null;
  let allResults = [];
  let pendingFileData = null;     // {bytes, filename} while modal is open
  let selectedColumn = null;      // column chosen by user
  let lastInspectData = null;     // last /api/inspect-file response

  // ── 1. Sample URLs ─────────────────────────────────────────────────────────
  const sampleUrls = [
    "https://httpbin.org",
    "https://example.com",
    "https://news.ycombinator.com"
  ];

  btnLoadSample.addEventListener("click", () => {
    urlsInput.value = sampleUrls.join("\n");
    appendLog("Loaded demo URLs into target input.", "info");
  });

  // ── 2. Drop Zone & File Handling ───────────────────────────────────────────
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
      // Assign to file input via DataTransfer
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
      handleFileSelected(file);
    }
  });

  /**
   * Called whenever a file is selected. If it is an xls/xlsx/csv,
   * call the /api/inspect-file endpoint and show the column picker.
   * For .txt, just update the drop zone label directly.
   */
  async function handleFileSelected(file) {
    const fname = file.name.toLowerCase();
    dropZone.classList.add("dragover");
    dropZoneLabel.innerHTML = `<span class="highlight">${escapeHtml(file.name)}</span> (${(file.size / 1024).toFixed(1)} KB)`;

    // Reset previously selected column
    selectedColumn = null;
    urlColumnInput.value = "";
    colSelectedIndicator.style.display = "none";

    if (fname.endsWith(".xls") || fname.endsWith(".xlsx") || fname.endsWith(".csv")) {
      dropZoneLabel.innerHTML += ` <span class="file-analyzing">Analyzing columns…</span>`;
      try {
        const formData = new FormData();
        formData.append("file", file);
        const resp = await fetch("/api/inspect-file", { method: "POST", body: formData });
        if (!resp.ok) {
          const err = await resp.json();
          appendLog(`File analysis error: ${err.detail}`, "error");
          return;
        }
        const data = await resp.json();
        lastInspectData = data;
        openColumnPicker(data);
      } catch (err) {
        appendLog(`Could not inspect file: ${err.message}`, "error");
      }
    }
  }

  // ── 3. Column Picker Modal ─────────────────────────────────────────────────
  function openColumnPicker(data) {
    const { columns, total_rows, column_samples, column_rows, suggested_column, filename } = data;

    modalFileInfo.textContent = `${escapeHtml(filename)} — ${total_rows.toLocaleString()} total rows, ${columns.length} columns`;
    modalHintText.textContent = suggested_column
      ? `✨ Auto-detected "${suggested_column}" as your URL column. Click to confirm or select any other column below.`
      : "Select the column that contains website addresses to automatically load them into the search input.";

    colList.innerHTML = "";
    let preSelected = null;

    columns.forEach((col) => {
      const samples = (column_samples[col] || []).slice(0, 3);
      const isSuggested = col === suggested_column;
      const count = (column_rows && column_rows[col]) ? column_rows[col].length : 0;

      const item = document.createElement("div");
      item.className = "col-item" + (isSuggested ? " suggested" : "");
      item.dataset.col = col;
      item.innerHTML = `
        <div class="col-item-radio">
          <span class="col-radio-dot"></span>
        </div>
        <div class="col-item-info">
          <div class="col-item-name">
            <span>${escapeHtml(col)}</span>
            ${isSuggested ? '<span class="col-suggested-tag">Suggested</span>' : ""}
            <span class="col-count-tag">${count.toLocaleString()} URL${count === 1 ? '' : 's'}</span>
          </div>
          <div class="col-item-samples">
            ${samples.map(s => `<span class="col-sample">${escapeHtml(s)}</span>`).join("")}
            ${samples.length === 0 ? '<span class="col-sample empty">No data</span>' : ""}
          </div>
        </div>
      `;

      item.addEventListener("click", () => {
        colList.querySelectorAll(".col-item").forEach(el => el.classList.remove("active"));
        item.classList.add("active");
        selectedColumn = col;
        modalConfirmBtn.disabled = false;
      });

      colList.appendChild(item);

      if (isSuggested) preSelected = item;
    });

    // Pre-select suggested column
    if (preSelected) {
      preSelected.classList.add("active");
      selectedColumn = suggested_column;
      modalConfirmBtn.disabled = false;
    } else {
      modalConfirmBtn.disabled = true;
    }

    colPickerOverlay.classList.add("visible");
    colPickerOverlay.setAttribute("aria-hidden", "false");
  }

  function closeColumnPicker() {
    colPickerOverlay.classList.remove("visible");
    colPickerOverlay.setAttribute("aria-hidden", "true");
  }

  modalConfirmBtn.addEventListener("click", () => {
    if (!selectedColumn) return;
    urlColumnInput.value = selectedColumn;
    colSelectedName.textContent = selectedColumn;
    colSelectedIndicator.style.display = "flex";

    // Automatically fill that column's rows into the search/target input!
    if (lastInspectData && lastInspectData.column_rows && lastInspectData.column_rows[selectedColumn]) {
      const rows = lastInspectData.column_rows[selectedColumn];
      urlsInput.value = rows.join("\n");
      appendLog(`✨ Automatically filled ${rows.length} website URLs from column "${selectedColumn}" into search!`, "success");
    } else {
      appendLog(`Column "${selectedColumn}" selected as the URL source.`, "info");
    }

    closeColumnPicker();
  });


  modalCancelBtn.addEventListener("click", () => {
    closeColumnPicker();
    // Clear the file selection to avoid confusion
    fileInput.value = "";
    dropZone.classList.remove("dragover");
    dropZoneLabel.innerHTML = `<span class="highlight">Click to browse</span> or drag &amp; drop list file`;
    selectedColumn = null;
    urlColumnInput.value = "";
    colSelectedIndicator.style.display = "none";
  });

  btnReselectCol.addEventListener("click", () => {
    if (lastInspectData) openColumnPicker(lastInspectData);
  });

  // Close modal on overlay click
  colPickerOverlay.addEventListener("click", (e) => {
    if (e.target === colPickerOverlay) modalCancelBtn.click();
  });

  // ── 4. Console ─────────────────────────────────────────────────────────────
  btnClearLog.addEventListener("click", () => { logFeed.innerHTML = ""; });

  function appendLog(message, type = "normal") {
    const timeStr = new Date().toLocaleTimeString();
    const entry = document.createElement("div");
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${timeStr}] ${message}`;
    logFeed.appendChild(entry);
    logFeed.scrollTop = logFeed.scrollHeight;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // ── 5. Form Submit & Task Launch ───────────────────────────────────────────
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const urlsVal = urlsInput.value.trim();
    const fileVal = fileInput.files.length > 0;

    if (!urlsVal && !fileVal) {
      alert("Please provide at least one website URL or upload a file.");
      return;
    }

    // If a spreadsheet file is loaded but no column picked yet, prompt
    if (fileVal) {
      const fname = fileInput.files[0].name.toLowerCase();
      if ((fname.endsWith(".xls") || fname.endsWith(".xlsx") || fname.endsWith(".csv")) && !urlColumnInput.value) {
        if (lastInspectData) {
          openColumnPicker(lastInspectData);
        } else {
          appendLog("Please wait for file analysis or re-select the file.", "warning");
        }
        return;
      }
    }

    const formData = new FormData(form);

    setRunningState(true);
    resetMetrics();
    allResults = [];
    renderTable();
    appendLog("Initiating extraction task...", "info");

    try {
      const response = await fetch("/api/tasks", {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to start extraction task.");
      }

      const data = await response.json();
      activeTaskId = data.task_id;
      statSites.textContent = `0 / ${data.total_urls}`;
      appendLog(`Task registered [${activeTaskId}]. Crawling ${data.total_urls} domain(s).`, "info");

      connectEventStream(activeTaskId);

    } catch (err) {
      appendLog(`Error: ${err.message}`, "error");
      setRunningState(false);
    }
  });

  // ── 6. Cancel Task ─────────────────────────────────────────────────────────
  btnCancel.addEventListener("click", async () => {
    if (!activeTaskId) return;
    appendLog("Stopping crawler task...", "warning");
    try {
      await fetch(`/api/tasks/${activeTaskId}/cancel`, { method: "POST" });
      if (activeEventSource) activeEventSource.close();
      setRunningState(false);
      appendLog("Extraction halted by user.", "warning");
      progressStatusText.textContent = "Halted by user.";
    } catch (e) {
      console.error(e);
    }
  });

  // ── 7. SSE Stream ──────────────────────────────────────────────────────────
  function connectEventStream(taskId) {
    if (activeEventSource) activeEventSource.close();
    activeEventSource = new EventSource(`/api/tasks/${taskId}/stream`);

    activeEventSource.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleStreamEvent(msg);
      } catch (e) { /* heartbeat */ }
    };

    activeEventSource.onerror = () => {
      if (activeEventSource) activeEventSource.close();
      setRunningState(false);
    };
  }

  function handleStreamEvent(msg) {
    switch (msg.type) {
      case "init":
        statSites.textContent = `${msg.completed_sites} / ${msg.total_sites}`;
        statEmails.textContent = msg.total_emails;
        statPages.textContent = msg.total_pages;
        if (msg.existing_results && msg.existing_results.length > 0) {
          allResults = msg.existing_results;
          renderTable();
        }
        break;

      case "task_start":
        appendLog(msg.message, "info");
        progressStatusText.textContent = msg.message;
        break;

      case "progress":
        const pData = msg.data;
        if (pData.event === "page_start") {
          progressStatusText.textContent = `Scanning: ${pData.current_page}`;
          statPages.textContent = msg.total_pages + pData.pages_scanned;
        } else if (pData.event === "email_found") {
          appendLog(`Found EMAIL on ${pData.source_page}: ${pData.email}`, "success");
          statEmails.textContent = msg.total_emails + 1;
        }
        break;

      case "site_done":
        const site = msg.site;
        allResults.push(site);
        renderTable();
        statSites.textContent = `${msg.completed_sites} / ${msg.total_sites}`;
        statEmails.textContent = msg.total_emails;
        statPages.textContent = msg.total_pages;

        const percent = Math.round((msg.completed_sites / msg.total_sites) * 100);
        progressBarFill.style.width = `${percent}%`;
        statSitesPercent.textContent = `${percent}% Completed`;

        if (site.status === "Success") {
          appendLog(`[DONE] ${site.target_url} → Found ${site.all_emails_list ? site.all_emails_list.length : 0} email(s). Primary: ${site.primary_email}`, "success");
        } else {
          appendLog(`[DONE] ${site.target_url} → Status: ${site.status}`, "warning");
        }
        break;

      case "task_completed":
        appendLog(msg.message, "success");
        progressStatusText.textContent = "Extraction completed & auto-saved to history!";
        progressBarFill.style.width = "100%";
        statSitesPercent.textContent = "100% Completed";
        setRunningState(false);
        if (activeEventSource) activeEventSource.close();
        // Refresh history so new entry shows up
        setTimeout(loadHistory, 800);
        break;

      case "task_error":
        appendLog(msg.message, "error");
        progressStatusText.textContent = "Extraction encountered an error.";
        setRunningState(false);
        if (activeEventSource) activeEventSource.close();
        break;
    }
  }

  function resetMetrics() {
    statEmails.textContent = "0";
    statSites.textContent = "0 / 0";
    statSitesPercent.textContent = "0% Completed";
    statPages.textContent = "0";
    progressBarFill.style.width = "0%";
    progressStatusText.textContent = "Crawling in progress...";
  }

  function setRunningState(isRunning) {
    if (isRunning) {
      btnStart.style.display = "none";
      btnCancel.style.display = "inline-flex";
      btnExportExcel.disabled = true;
      btnExportXls.disabled = true;
      btnExportCsv.disabled = true;
    } else {
      btnStart.style.display = "inline-flex";
      btnCancel.style.display = "none";
      if (allResults.length > 0) {
        btnExportExcel.disabled = false;
        btnExportXls.disabled = false;
        btnExportCsv.disabled = false;
      }
    }
  }


  // ── 8. Render Results Table ────────────────────────────────────────────────
  function renderTable() {
    const query = searchInput.value.trim().toLowerCase();
    const filtered = allResults.filter(r => {
      if (!query) return true;
      const target = (r.target_url || "").toLowerCase();
      const primary = (r.primary_email || "").toLowerCase();
      const all = (r.all_emails || "").toLowerCase();
      return target.includes(query) || primary.includes(query) || all.includes(query);
    });

    resultsCountBadge.textContent = `${allResults.length} Result${allResults.length === 1 ? '' : 's'}`;

    if (filtered.length === 0) {
      resultsTbody.innerHTML = `
        <tr class="empty-row">
          <td colspan="6">${allResults.length === 0 ? 'No websites crawled yet.' : 'No matching results found.'}</td>
        </tr>
      `;
      return;
    }

    resultsTbody.innerHTML = filtered.map(r => {
      let statusClass = "danger";
      if (r.status === "Success") statusClass = "success";
      else if (r.status === "No Email Found") statusClass = "warning";

      const emailList = r.all_emails_list || [];
      const emailChips = emailList.length > 0
        ? emailList.map(em => `<span class="email-tag">${escapeHtml(em)}</span>`).join("")
        : '<span class="text-dim">None</span>';

      const primaryBadge = r.primary_email
        ? `<div class="primary-email-badge">
             <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
             ${escapeHtml(r.primary_email)}
           </div>`
        : '<span class="text-dim">-</span>';

      return `
        <tr>
          <td>
            <a href="${escapeHtml(r.target_url)}" target="_blank" rel="noopener noreferrer" class="site-url-link">
              ${escapeHtml(r.target_url)}
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
            </a>
          </td>
          <td>${primaryBadge}</td>
          <td><div style="max-width: 320px; display: flex; flex-wrap: wrap;">${emailChips}</div></td>
          <td><strong>${r.pages_scanned || 0}</strong></td>
          <td><span class="status-chip ${statusClass}">${escapeHtml(r.status)}</span></td>
          <td>
            ${r.primary_email ? `<button type="button" class="copy-btn" onclick="navigator.clipboard.writeText('${escapeHtml(r.primary_email)}'); this.textContent = 'Copied!'; setTimeout(() => this.textContent = 'Copy', 1500);">Copy</button>` : '-'}
          </td>
        </tr>
      `;
    }).join("");
  }

  searchInput.addEventListener("input", renderTable);

  // ── 9. Live Downloads ──────────────────────────────────────────────────────
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

  // ── 10. History Panel ──────────────────────────────────────────────────────
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

      // Update badge
      if (sessions.length > 0) {
        historyCountBadge.textContent = sessions.length;
        historyCountBadge.style.display = "inline-flex";
      } else {
        historyCountBadge.style.display = "none";
      }

      if (sessions.length === 0) {
        historyList.innerHTML = `<div class="history-empty">No saved sessions yet. Complete an extraction to see it here.</div>`;
        return;
      }

      historyList.innerHTML = sessions.map(s => `
        <div class="history-item" data-id="${escapeHtml(s.task_id)}">
          <div class="history-item-left">
            <div class="history-item-meta">
              <span class="history-timestamp">${escapeHtml(s.timestamp_display)}</span>
              <span class="history-badge ${s.status === 'Completed' ? 'success' : 'warning'}">${escapeHtml(s.status)}</span>
            </div>
            <div class="history-item-stats">
              <span>🌐 ${s.completed_sites}/${s.total_sites} sites</span>
              <span>📧 ${s.total_emails} emails</span>
              <span>📄 ${s.total_pages} pages</span>
            </div>
            <div class="history-sample-urls">
              ${(s.urls_sample || []).slice(0, 3).map(u => `<span class="history-url-chip">${escapeHtml(u)}</span>`).join("")}
              ${(s.urls_sample || []).length > 3 ? `<span class="history-url-chip more">+${s.total_sites - 3} more</span>` : ""}
            </div>
          </div>
          <div class="history-item-actions">
            <button class="btn btn-hist-load hist-load" data-id="${escapeHtml(s.task_id)}" title="Load extracted data into results table">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
              View
            </button>
            <button class="btn btn-export hist-dl-xlsx" data-id="${escapeHtml(s.task_id)}" title="Download XLSX">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
              .xlsx
            </button>
            <button class="btn btn-secondary hist-dl-xls" data-id="${escapeHtml(s.task_id)}" title="Download legacy XLS">
              .xls
            </button>
            <button class="btn btn-secondary hist-dl-csv" data-id="${escapeHtml(s.task_id)}" title="Download CSV">
              .csv
            </button>
            <button class="btn btn-danger hist-delete" data-id="${escapeHtml(s.task_id)}" title="Delete entry" style="padding:8px 12px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path></svg>
            </button>
          </div>
        </div>
      `).join("");

      // Bind view/load buttons
      historyList.querySelectorAll(".hist-load").forEach(btn => {
        btn.addEventListener("click", async () => {
          try {
            const r = await fetch(`/api/history/${btn.dataset.id}/results`);
            if (!r.ok) {
              appendLog("Could not load history results.", "error");
              return;
            }
            const data = await r.json();
            allResults = data.results || [];
            activeTaskId = btn.dataset.id;
            renderTable();

            if (data.entry) {
              statEmails.textContent = data.entry.total_emails ?? allResults.length;
              statSites.textContent = `${data.entry.completed_sites ?? allResults.length} / ${data.entry.total_sites ?? allResults.length}`;
              statSitesPercent.textContent = "100% Completed";
              statPages.textContent = data.entry.total_pages ?? "-";
              progressBarFill.style.width = "100%";
              progressStatusText.textContent = `Viewing historical session (${data.entry.timestamp_display})`;
            }

            btnExportExcel.disabled = false;
            btnExportXls.disabled = false;
            btnExportCsv.disabled = false;

            historyPanel.style.display = "none";
            document.getElementById("results-section").scrollIntoView({ behavior: "smooth" });
            appendLog(`Loaded history session ${btn.dataset.id} into results (${allResults.length} records).`, "success");
          } catch (err) {
            appendLog(`Error loading history: ${err.message}`, "error");
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
          if (!confirm("Delete this history entry and its saved files?")) return;
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
      historyList.innerHTML = `<div class="history-empty" style="color:var(--accent-rose)">Failed to load history.</div>`;
    }
  }

  // Load history count on startup (update badge)
  loadHistory();
});

