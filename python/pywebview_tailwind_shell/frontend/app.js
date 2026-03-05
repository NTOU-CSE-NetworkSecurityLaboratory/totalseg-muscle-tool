const ui = {
  tabSegBtn: document.getElementById("tab-seg-btn"),
  tabCompareBtn: document.getElementById("tab-compare-btn"),
  segPage: document.getElementById("seg-page"),
  comparePage: document.getElementById("compare-page"),
  sourceLabel: document.getElementById("source-label"),
  rangeHint: document.getElementById("range-hint"),
  modality: document.getElementById("modality"),
  task: document.getElementById("task"),
  chkSpine: document.getElementById("chk-spine"),
  chkFast: document.getElementById("chk-fast"),
  chkDraw: document.getElementById("chk-draw"),
  erosionIters: document.getElementById("erosion-iters"),
  chkRange: document.getElementById("chk-range"),
  sliceStart: document.getElementById("slice-start"),
  sliceEnd: document.getElementById("slice-end"),
  taskTableBody: document.getElementById("task-table-body"),
  progressLabel: document.getElementById("progress-label"),
  progressCase: document.getElementById("progress-case"),
  sessionLogPath: document.getElementById("session-log-path"),
  progressBar: document.getElementById("progress-bar"),
  btnSelectSource: document.getElementById("btn-select-source"),
  btnSelectAll: document.getElementById("btn-select-all"),
  btnUnselectAll: document.getElementById("btn-unselect-all"),
  btnStart: document.getElementById("btn-start"),
  btnStop: document.getElementById("btn-stop"),
  btnRetryFailed: document.getElementById("btn-retry-failed"),
  compareAiLabel: document.getElementById("compare-ai-label"),
  compareManualLabel: document.getElementById("compare-manual-label"),
  btnSelectCompareAi: document.getElementById("btn-select-compare-ai"),
  btnSelectCompareManual: document.getElementById("btn-select-compare-manual"),
  btnRunCompare: document.getElementById("btn-run-compare"),
  compareResult: document.getElementById("compare-result"),
  compareEmpty: document.getElementById("compare-empty"),
  logOutput: document.getElementById("log-output"),
  btnClearLogView: document.getElementById("btn-clear-log-view"),
  btnToggleAutoscroll: document.getElementById("btn-toggle-autoscroll"),
  btnCopyLog: document.getElementById("btn-copy-log"),
  btnCopyError: document.getElementById("btn-copy-error"),
  notice: document.getElementById("ui-notice"),
  diagnosticsList: document.getElementById("diagnostics-list"),
  licenseModal: document.getElementById("license-modal"),
  licenseInput: document.getElementById("license-input"),
  btnLicenseCancel: document.getElementById("btn-license-cancel"),
  btnLicenseApply: document.getElementById("btn-license-apply"),
};

const state = {
  taskOptionsCT: [],
  taskOptionsMRI: [],
  pollingTimer: null,
  logCursor: 0,
  logLines: [],
  ephemeralActive: false,
  autoScrollLog: true,
  running: false,
  lastErrorExcerpt: "",
};

async function copyText(text) {
  const value = String(text || "");
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const ta = document.createElement("textarea");
  ta.value = value;
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  document.body.removeChild(ta);
}

function setTab(tab) {
  const isSeg = tab === "seg";
  ui.segPage.classList.toggle("hidden", !isSeg);
  ui.comparePage.classList.toggle("hidden", isSeg);

  ui.tabSegBtn.classList.toggle("bg-brand", isSeg);
  ui.tabSegBtn.classList.toggle("text-white", isSeg);
  ui.tabSegBtn.classList.toggle("text-muted", !isSeg);
  ui.tabSegBtn.classList.toggle("hover:bg-brandSoft", !isSeg);

  ui.tabCompareBtn.classList.toggle("bg-brand", !isSeg);
  ui.tabCompareBtn.classList.toggle("text-white", !isSeg);
  ui.tabCompareBtn.classList.toggle("text-muted", isSeg);
  ui.tabCompareBtn.classList.toggle("hover:bg-brandSoft", isSeg);
}

function showNotice(kind, text) {
  if (!text) {
    ui.notice.classList.add("hidden");
    ui.notice.textContent = "";
    return;
  }

  ui.notice.className = "mb-4 rounded-xl border px-4 py-2 text-sm";
  if (kind === "error") {
    ui.notice.classList.add("border-[#ead8df]", "bg-[#faf2f5]", "text-[#8f5f70]");
  } else if (kind === "success") {
    ui.notice.classList.add("border-[#cfe2d8]", "bg-[#eff8f3]", "text-[#4d8069]");
  } else {
    ui.notice.classList.add("border-[#d3deef]", "bg-[#edf3fb]", "text-[#436da9]");
  }
  ui.notice.textContent = text;
  ui.notice.classList.remove("hidden");
}

function setTaskOptions(modality) {
  const options = modality === "MRI" ? state.taskOptionsMRI : state.taskOptionsCT;
  const current = ui.task.value;
  ui.task.innerHTML = options.map((x) => `<option value="${x}">${x}</option>`).join("");
  if (options.includes(current)) {
    ui.task.value = current;
  }
}

function statusBadge(status) {
  const safe = String(status || "Unknown");
  let cls = "bg-[#ecf2fa] text-[#5c6f88] border-[#d7e2f2]";
  if (safe === "Success") cls = "bg-[#eff8f3] text-[#4d8069] border-[#cfe2d8]";
  if (safe === "Running") cls = "bg-[#edf3fb] text-[#436da9] border-[#d3deef]";
  if (safe === "Queued") cls = "bg-[#f8f1e7] text-[#9a774e] border-[#e9dcc8]";
  if (safe.startsWith("Failed") || safe.startsWith("RangeError")) cls = "bg-[#faf2f5] text-[#8f5f70] border-[#ead8df]";
  if (safe === "Stopped") cls = "bg-[#ecf1f8] text-[#6b7b90] border-[#d7e2f2]";
  return `<span class="inline-flex rounded-full border px-2 py-1 text-xs font-semibold ${cls}">${safe}</span>`;
}

function renderTaskTable(tasks) {
  if (!tasks || tasks.length === 0) {
    ui.taskTableBody.innerHTML = `
      <tr>
        <td colspan="3" class="px-4 py-10 text-center text-slate-500">No DICOM case found</td>
      </tr>`;
    return;
  }

  ui.taskTableBody.innerHTML = tasks
    .map((t) => `
      <tr class="odd:bg-white even:bg-slate-50">
        <td class="px-3 py-3 align-top">
          <input
            type="checkbox"
            class="task-check h-4 w-4 rounded border-slate-300 text-brand"
            data-task-id="${t.id}"
            ${t.selected ? "checked" : ""}
            ${state.running ? "disabled" : ""}
          />
        </td>
        <td class="px-3 py-3 align-top text-slate-700">${t.label}</td>
        <td class="px-3 py-3 align-top">${statusBadge(t.status)}</td>
      </tr>`)
    .join("");

  document.querySelectorAll(".task-check").forEach((el) => {
    el.addEventListener("change", async (e) => {
      const taskId = Number(e.target.dataset.taskId);
      await window.pywebview.api.set_task_selected(taskId, e.target.checked);
    });
  });
}

function applyLogEvents(events) {
  if (!events || events.length === 0) return;

  for (const ev of events) {
    const type = ev.type || "line";
    const text = ev.text || "";

    if (type === "ephemeral") {
      if (state.ephemeralActive && state.logLines.length > 0) {
        state.logLines[state.logLines.length - 1] = text;
      } else {
        state.logLines.push(text);
        state.ephemeralActive = true;
      }
      continue;
    }

    if (state.ephemeralActive && state.logLines.length > 0) {
      if (text) state.logLines[state.logLines.length - 1] = text;
      state.ephemeralActive = false;
      continue;
    }

    state.logLines.push(text);
  }

  if (state.logLines.length > 5000) {
    state.logLines = state.logLines.slice(-5000);
  }

  ui.logOutput.textContent = state.logLines.join("\n");
  if (state.autoScrollLog) {
    ui.logOutput.scrollTop = ui.logOutput.scrollHeight;
  }
}

function setControlsDisabled(disabled) {
  const controls = [
    ui.btnSelectSource,
    ui.btnSelectAll,
    ui.btnUnselectAll,
    ui.modality,
    ui.task,
    ui.chkSpine,
    ui.chkFast,
    ui.chkDraw,
    ui.erosionIters,
    ui.chkRange,
    ui.sliceStart,
    ui.sliceEnd,
  ];
  for (const el of controls) {
    el.disabled = disabled;
    el.classList.toggle("opacity-60", disabled);
  }
}

function renderCompareResult(res) {
  ui.compareEmpty.classList.add("hidden");
  ui.compareResult.classList.remove("hidden");

  let qualityCls = "text-[#9a774e]";
  if (res.quality === "Excellent") qualityCls = "text-[#4d8069]";
  if (res.quality === "Good") qualityCls = "text-[#436da9]";
  if (res.quality === "Needs Review") qualityCls = "text-[#8f5f70]";

  ui.compareResult.innerHTML = `
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div class="rounded-lg border border-slate-200 bg-white px-3 py-2">
        <div class="text-[11px] uppercase tracking-wide text-slate-500">Slice</div>
        <div class="text-lg font-semibold text-slate-800">${res.slice_index_1based}</div>
      </div>
      <div class="rounded-lg border border-slate-200 bg-white px-3 py-2">
        <div class="text-[11px] uppercase tracking-wide text-slate-500">Dice</div>
        <div class="text-lg font-semibold text-slate-800">${res.dice.toFixed(4)}</div>
      </div>
      <div class="rounded-lg border border-slate-200 bg-white px-3 py-2">
        <div class="text-[11px] uppercase tracking-wide text-slate-500">AI Area</div>
        <div class="text-base font-semibold text-slate-800">${res.ai_area_cm2.toFixed(2)} cm2</div>
      </div>
      <div class="rounded-lg border border-slate-200 bg-white px-3 py-2">
        <div class="text-[11px] uppercase tracking-wide text-slate-500">Manual Area</div>
        <div class="text-base font-semibold text-slate-800">${res.manual_area_cm2.toFixed(2)} cm2</div>
      </div>
    </div>
    <div class="mt-3 text-sm font-semibold ${qualityCls}">Quality: ${res.quality}</div>`;
}

function renderDiagnostics(diag) {
  if (!diag || diag.length === 0) {
    ui.diagnosticsList.innerHTML = '<p class="text-xs text-slate-500">No diagnostics.</p>';
    return;
  }

  ui.diagnosticsList.innerHTML = diag
    .map((x) => `
      <div class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
        <div class="text-xs text-slate-700">${x}</div>
        <button class="diag-copy mt-2 cursor-pointer rounded border border-slate-300 px-2 py-1 text-[11px] text-slate-600 hover:bg-white" data-text="${x.replace(/"/g, "&quot;")}">Copy</button>
      </div>`)
    .join("");

  document.querySelectorAll(".diag-copy").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const text = e.target.dataset.text || "";
      await copyText(text);
      showNotice("success", "Diagnostic copied");
    });
  });
}

function applyRangeHint(rangeHint, tasks) {
  if (rangeHint === "single_auto_fill" && tasks?.length === 1) {
    const n = Number(tasks[0]?.slice_count || 0);
    if (n > 0) {
      ui.sliceStart.value = "1";
      ui.sliceEnd.value = String(n);
      ui.rangeHint.textContent = `Single case detected. Slice range auto-filled: 1 to ${n}.`;
      return;
    }
  }
  if (rangeHint === "multi_auto_clamp") {
    ui.rangeHint.textContent = "Multiple cases detected. Slice end will be clamped per case.";
    ui.sliceEnd.placeholder = "auto clamp";
    return;
  }
  ui.rangeHint.textContent = "";
}

function renderState(s) {
  if (!s) return;

  state.running = !!s.running;
  state.lastErrorExcerpt = s.last_failed_excerpt || "";

  ui.sourceLabel.textContent = s.source_root || "No folder selected";
  ui.compareAiLabel.textContent = s.compare_ai_mask || "No file selected";
  ui.compareManualLabel.textContent = s.compare_manual_mask || "No file selected";

  renderTaskTable(s.tasks || []);
  renderDiagnostics(s.diagnostics || []);
  applyRangeHint(s.range_hint, s.tasks || []);

  const done = s.progress?.done || 0;
  const total = s.progress?.total || 0;
  const percent = s.progress?.percent || 0;
  ui.progressLabel.textContent = `Progress: ${done} / ${total}`;
  ui.progressCase.textContent = s.running ? (s.progress.current_case || "Running") : "Idle";
  ui.progressBar.style.width = `${percent}%`;

  ui.sessionLogPath.textContent = s.session_log_path ? `Session Log: ${s.session_log_path}` : "";

  ui.btnStart.disabled = s.running;
  ui.btnStop.disabled = !s.running;
  ui.btnRetryFailed.disabled = !s.last_failed_task_id && s.last_failed_task_id !== 0;

  ui.btnStart.classList.toggle("opacity-60", s.running);
  ui.btnStop.classList.toggle("opacity-60", !s.running);
  ui.btnRetryFailed.classList.toggle("opacity-60", ui.btnRetryFailed.disabled);

  setControlsDisabled(s.running);

}

async function pollState() {
  try {
    const res = await window.pywebview.api.get_state(state.logCursor);
    state.logCursor = res.next_log_cursor || state.logCursor;
    applyLogEvents(res.log_events || []);
    renderState(res);

    if (res.pending_action === "needs_license" && ui.licenseModal.classList.contains("hidden")) {
      openLicenseModal();
      showNotice("error", "License required. Please apply key to continue.");
    }
  } catch (err) {
    console.error(err);
    showNotice("error", `Failed to poll state: ${err}`);
  }
}

async function startRun() {
  const payload = {
    modality: ui.modality.value,
    task: ui.task.value,
    spine: ui.chkSpine.checked,
    fast: ui.chkFast.checked,
    auto_draw: ui.chkDraw.checked,
    erosion_iters: Number(ui.erosionIters.value || 2),
    range_enabled: ui.chkRange.checked,
    slice_start: ui.sliceStart.value || "1",
    slice_end: ui.sliceEnd.value || "",
  };
  const res = await window.pywebview.api.start_segmentation(payload);
  if (!res.ok) {
    showNotice("error", res.message || "Failed to start segmentation");
    return;
  }
  showNotice("success", "Batch started");
}

async function runCompare() {
  ui.btnRunCompare.disabled = true;
  ui.btnRunCompare.classList.add("opacity-60");
  try {
    const res = await window.pywebview.api.run_compare_analysis();
    if (!res.ok) {
      showNotice("error", res.message || "Compare failed");
      return;
    }
    renderCompareResult(res);
    showNotice("success", "Compare finished");
  } catch (err) {
    showNotice("error", `Compare failed: ${err}`);
  } finally {
    ui.btnRunCompare.disabled = false;
    ui.btnRunCompare.classList.remove("opacity-60");
  }
}

function toggleAutoscroll() {
  state.autoScrollLog = !state.autoScrollLog;
  ui.btnToggleAutoscroll.textContent = `Autoscroll: ${state.autoScrollLog ? "On" : "Off"}`;
}

function openLicenseModal() {
  ui.licenseModal.classList.remove("hidden");
  ui.licenseModal.classList.add("flex");
}

function closeLicenseModal() {
  ui.licenseModal.classList.remove("flex");
  ui.licenseModal.classList.add("hidden");
}

async function applyLicense() {
  const raw = ui.licenseInput.value || "";
  const res = await window.pywebview.api.submit_license(raw);
  if (!res.ok) {
    showNotice("error", res.message || "Failed to apply license");
    return;
  }
  showNotice("success", `License applied: ${res.masked_key}`);
  closeLicenseModal();
  ui.licenseInput.value = "";
  await pollState();
}

async function retryFailedCase() {
  const res = await window.pywebview.api.retry_last_failed_case();
  if (!res.ok) {
    showNotice("error", res.message || "No failed case to retry");
    return;
  }
  showNotice("success", "Retry started");
}

async function copyAllLog() {
  await copyText(state.logLines.join("\n"));
  showNotice("success", "All logs copied");
}

async function copyErrorLog() {
  const text = state.lastErrorExcerpt || "";
  if (!text) {
    showNotice("info", "No error excerpt yet");
    return;
  }
  await copyText(text);
  showNotice("success", "Error excerpt copied");
}

async function bootstrap() {
  const data = await window.pywebview.api.get_bootstrap();
  state.taskOptionsCT = data.task_options_ct || [];
  state.taskOptionsMRI = data.task_options_mri || [];
  setTaskOptions(ui.modality.value);
  renderState(data.state);

  ui.tabSegBtn.addEventListener("click", () => setTab("seg"));
  ui.tabCompareBtn.addEventListener("click", () => setTab("compare"));

  ui.modality.addEventListener("change", (e) => setTaskOptions(e.target.value));

  ui.btnSelectSource.addEventListener("click", async () => {
    const res = await window.pywebview.api.choose_source_folder();
    if (res && res.ok === false && res.message !== "Cancelled") {
      showNotice("error", res.message || "Scan failed");
    } else if (res && res.ok) {
      showNotice("success", `Scan completed: ${res.count} case(s)`);
    }
    await pollState();
  });

  ui.btnSelectAll.addEventListener("click", async () => {
    await window.pywebview.api.set_all_selected(true);
    await pollState();
  });

  ui.btnUnselectAll.addEventListener("click", async () => {
    await window.pywebview.api.set_all_selected(false);
    await pollState();
  });

  ui.btnStart.addEventListener("click", startRun);

  ui.btnStop.addEventListener("click", async () => {
    await window.pywebview.api.stop_segmentation();
    showNotice("info", "Stop requested");
  });

  ui.btnRetryFailed.addEventListener("click", retryFailedCase);

  ui.btnSelectCompareAi.addEventListener("click", async () => {
    await window.pywebview.api.choose_compare_ai_file();
    await pollState();
  });

  ui.btnSelectCompareManual.addEventListener("click", async () => {
    await window.pywebview.api.choose_compare_manual_file();
    await pollState();
  });

  ui.btnRunCompare.addEventListener("click", runCompare);

  ui.btnClearLogView.addEventListener("click", () => {
    state.logLines = [];
    state.ephemeralActive = false;
    ui.logOutput.textContent = "";
  });

  ui.btnToggleAutoscroll.addEventListener("click", toggleAutoscroll);
  ui.btnCopyLog.addEventListener("click", copyAllLog);
  ui.btnCopyError.addEventListener("click", copyErrorLog);

  ui.btnLicenseCancel.addEventListener("click", closeLicenseModal);
  ui.btnLicenseApply.addEventListener("click", applyLicense);
  ui.licenseModal.addEventListener("click", (e) => {
    if (e.target === ui.licenseModal) closeLicenseModal();
  });

  if (state.pollingTimer) clearInterval(state.pollingTimer);
  state.pollingTimer = setInterval(pollState, 700);
  await pollState();
}

window.addEventListener("pywebviewready", () => {
  bootstrap().catch((err) => {
    console.error(err);
    showNotice("error", `UI bootstrap failed: ${err}`);
  });
});
