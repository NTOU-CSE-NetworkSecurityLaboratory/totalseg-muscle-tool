const ui = {
  tabSegBtn: document.getElementById("tab-seg-btn"),
  tabExportBtn: document.getElementById("tab-export-btn"),
  tabCompareBtn: document.getElementById("tab-compare-btn"),
  btnOpenSettings: document.getElementById("btn-open-settings"),
  settingsModal: document.getElementById("settings-modal"),
  btnCloseSettings: document.getElementById("btn-close-settings"),
  settingsCurrentVersion: document.getElementById("settings-current-version"),
  settingsUpdateStatus: document.getElementById("settings-update-status"),
  settingsUpdateHint: document.getElementById("settings-update-hint"),
  btnCheckUpdate: document.getElementById("btn-check-update"),
  btnOpenReleases: document.getElementById("btn-open-releases"),
  btnInstallUpdate: document.getElementById("btn-install-update"),
  settingsLicenseInput: document.getElementById("settings-license-input"),
  settingsLicenseStatus: document.getElementById("settings-license-status"),
  btnSettingsLicenseApply: document.getElementById("btn-settings-license-apply"),
  segPage: document.getElementById("seg-page"),
  comparePage: document.getElementById("compare-page"),
  modalitySection: document.getElementById("modality-section"),
  sourceLabel: document.getElementById("source-label"),
  rangeHint: document.getElementById("range-hint"),
  modality: document.getElementById("modality"),
  task: document.getElementById("task"),
  erosionIters: document.getElementById("erosion-iters"),
  chkRange: document.getElementById("chk-range"),
  sliceStart: document.getElementById("slice-start"),
  sliceEnd: document.getElementById("slice-end"),
  huMin: document.getElementById("hu-min"),
  huMax: document.getElementById("hu-max"),
  taskTableBody: document.getElementById("task-table-body"),
  progressLabel: document.getElementById("progress-label"),
  progressCase: document.getElementById("progress-case"),
  sessionLogPath: document.getElementById("session-log-path"),
  progressLabelCard: document.getElementById("progress-label-card"),
  progressCaseCard: document.getElementById("progress-case-card"),
  sessionLogPathCard: document.getElementById("session-log-path-card"),
  progressBar: document.getElementById("progress-bar"),
  btnSelectSource: document.getElementById("btn-select-source"),
  btnOpenFolder: document.getElementById("btn-open-folder"),
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
  btnCopyLog: document.getElementById("btn-copy-log"),
  notice: document.getElementById("ui-notice"),
  diagnosticsList: document.getElementById("diagnostics-list"),
  licenseModal: document.getElementById("license-modal"),
  btnLicenseOpenUrl: document.getElementById("btn-license-open-url"),
  licenseInput: document.getElementById("license-input"),
  btnLicenseCancel: document.getElementById("btn-license-cancel"),
  btnLicenseApply: document.getElementById("btn-license-apply"),
  btnSettingsLicenseOpenUrl: document.getElementById("btn-settings-license-open-url"),
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
  updateStatus: null,
  dismissedPendingAction: "",
  activeMode: "full",
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
  // page visibility
  ui.segPage.classList.toggle("hidden", tab === "compare");
  ui.comparePage.classList.toggle("hidden", tab !== "compare");

  // modality hidden only on compare tab
  if (ui.modalitySection) ui.modalitySection.classList.toggle("hidden", tab === "compare");

  // export-settings (erosion, slice range, HU) only visible for export tab
  const exportSettings = document.getElementById("export-settings-section");
  if (exportSettings) exportSettings.classList.toggle("hidden", tab !== "export");

  // active mode
  state.activeMode = tab === "export" ? "export_only" : "full";

  // tab button active styles
  const ACTIVE = ["bg-brand", "text-white", "border-[#335fc1]"];
  const INACTIVE = ["text-muted", "bg-white", "border-[#d7e0eb]", "hover:bg-brandSoft"];

  for (const [btn, name] of [
    [ui.tabSegBtn, "seg"],
    [ui.tabExportBtn, "export"],
    [ui.tabCompareBtn, "compare"],
  ]) {
    const active = tab === name;
    ACTIVE.forEach((c) => btn.classList.toggle(c, active));
    INACTIVE.forEach((c) => btn.classList.toggle(c, !active));
  }
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

function renderUpdateStatus(status) {
  state.updateStatus = status || null;
  if (!ui.settingsCurrentVersion) return;

  const current = status?.current_version || "unknown";
  ui.settingsCurrentVersion.textContent = current;

  if (!status) {
    ui.settingsUpdateStatus.textContent = "尚未檢查更新";
    ui.settingsUpdateHint.textContent = "";
    ui.btnInstallUpdate.disabled = true;
    return;
  }

  if (!status.ok) {
    ui.settingsUpdateStatus.textContent = `目前版本：v${current}`;
    ui.settingsUpdateHint.textContent = status.install_block_reason || "目前無法取得更新資訊。";
    ui.btnInstallUpdate.disabled = true;
    return;
  }

  const latest = status.latest_version ? `｜最新：v${status.latest_version}` : "";
  ui.settingsUpdateStatus.textContent = `目前版本：v${current}${latest}`;

  if (!status.install_supported) {
    ui.settingsUpdateHint.textContent = status.install_block_reason || "目前環境不支援 GUI 更新。";
    ui.btnInstallUpdate.disabled = true;
    return;
  }

  if (status.update_available) {
    ui.settingsUpdateHint.textContent = "偵測到較新正式版，可更新到最新 release。";
    ui.btnInstallUpdate.disabled = false;
  } else {
    ui.settingsUpdateHint.textContent = "目前已是最新正式版。";
    ui.btnInstallUpdate.disabled = true;
  }
}

function localizeStatus(status) {
  const raw = String(status || "");
  if (raw === "Ready") return "就緒";
  if (raw === "Success") return "完成";
  if (raw === "Running") return "執行中";
  if (raw === "Queued") return "排隊中";
  if (raw === "Stopped") return "已停止";
  if (raw === "Idle") return "待命中";
  if (raw === "Unknown") return "未知";
  if (raw.startsWith("Failed")) return raw.replace("Failed", "失敗");
  if (raw.startsWith("RangeError")) return raw.replace("RangeError", "範圍錯誤");
  return raw;
}

function renderTaskTable(tasks) {
  if (!tasks || tasks.length === 0) {
    ui.taskTableBody.innerHTML = `
      <tr>
        <td colspan="3" class="px-4 py-10 text-center text-slate-500">找不到 DICOM 病例</td>
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
        <td class="px-3 py-3 align-top">${statusBadge(localizeStatus(t.status))}</td>
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

function syncSliceRangeInputs() {
  const enabled = ui.chkRange.checked;
  for (const el of [ui.sliceStart, ui.sliceEnd]) {
    el.disabled = !enabled;
    el.classList.toggle("opacity-40", !enabled);
  }
}

function setControlsDisabled(disabled) {
  const controls = [
    ui.btnSelectSource,
    ui.btnSelectAll,
    ui.btnUnselectAll,
    ui.modality,
    ui.task,
    ui.erosionIters,
    ui.chkRange,
    ui.sliceStart,
    ui.sliceEnd,
    ui.huMin,
    ui.huMax,
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
        <div class="text-[11px] uppercase tracking-wide text-slate-500">切片</div>
        <div class="text-lg font-semibold text-slate-800">${res.slice_index_1based}</div>
      </div>
      <div class="rounded-lg border border-slate-200 bg-white px-3 py-2">
        <div class="text-[11px] uppercase tracking-wide text-slate-500">Dice</div>
        <div class="text-lg font-semibold text-slate-800">${res.dice.toFixed(4)}</div>
      </div>
      <div class="rounded-lg border border-slate-200 bg-white px-3 py-2">
        <div class="text-[11px] uppercase tracking-wide text-slate-500">AI 面積</div>
        <div class="text-base font-semibold text-slate-800">${res.ai_area_cm2.toFixed(2)} cm2</div>
      </div>
      <div class="rounded-lg border border-slate-200 bg-white px-3 py-2">
        <div class="text-[11px] uppercase tracking-wide text-slate-500">人工面積</div>
        <div class="text-base font-semibold text-slate-800">${res.manual_area_cm2.toFixed(2)} cm2</div>
      </div>
    </div>
    <div class="mt-3 text-sm font-semibold ${qualityCls}">品質：${res.quality}</div>`;
}

function renderDiagnostics(diag) {
  if (!diag || diag.length === 0) {
    ui.diagnosticsList.innerHTML = '<p class="text-xs text-slate-500">目前沒有診斷資訊。</p>';
    return;
  }

  ui.diagnosticsList.innerHTML = diag
    .map((x) => `
      <div class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
        <div class="text-xs text-slate-700">${x}</div>
        <button class="diag-copy mt-2 cursor-pointer rounded border border-slate-300 px-2 py-1 text-[11px] text-slate-600 hover:bg-white" data-text="${x.replace(/"/g, "&quot;")}">複製</button>
      </div>`)
    .join("");

  document.querySelectorAll(".diag-copy").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const text = e.target.dataset.text || "";
      await copyText(text);
      showNotice("success", "已複製診斷資訊");
    });
  });
}

function applyRangeHint(rangeHint, tasks) {
  if (rangeHint === "single_auto_fill" && tasks?.length === 1) {
    const n = Number(tasks[0]?.slice_count || 0);
    if (n > 0) {
      ui.sliceStart.value = "1";
      ui.sliceEnd.value = String(n);
      ui.rangeHint.textContent = `偵測到單一病例，已自動填入切片範圍：1 到 ${n}。`;
      return;
    }
  }
  if (rangeHint === "multi_auto_clamp") {
    ui.rangeHint.textContent = "偵測到多個病例，結束切片會依各病例自動截斷。";
    ui.sliceEnd.placeholder = "自動截斷";
    return;
  }
  ui.rangeHint.textContent = "";
}

function renderState(s) {
  if (!s) return;

  state.running = !!s.running;
  state.lastErrorExcerpt = s.last_failed_excerpt || "";
  if (!s.pending_action || s.pending_action !== state.dismissedPendingAction) {
    state.dismissedPendingAction = "";
  }

  ui.sourceLabel.textContent = s.source_root || "尚未選擇資料夾";
  ui.compareAiLabel.textContent = s.compare_ai_mask || "尚未選擇檔案";
  ui.compareManualLabel.textContent = s.compare_manual_mask || "尚未選擇檔案";

  renderTaskTable(s.tasks || []);
  renderDiagnostics(s.diagnostics || []);
  applyRangeHint(s.range_hint, s.tasks || []);

  const done = s.progress?.done || 0;
  const total = s.progress?.total || 0;
  const percent = s.progress?.percent || 0;
  ui.progressLabel.textContent = `進度：${done} / ${total}`;
  ui.progressCase.textContent = s.running ? (s.progress.current_case || "執行中") : "待命中";
  if (ui.progressLabelCard) ui.progressLabelCard.textContent = `${done} / ${total}`;
  if (ui.progressCaseCard) ui.progressCaseCard.textContent = s.running
    ? (s.progress.current_case || "執行中")
    : "待命中";
  ui.progressBar.style.width = `${percent}%`;

  ui.sessionLogPath.textContent = s.session_log_path ? `批次記錄：${s.session_log_path}` : "";
  if (ui.sessionLogPathCard) {
    ui.sessionLogPathCard.textContent = s.session_log_path || "尚未開始";
  }

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

    if (
      res.pending_action === "needs_license" &&
      state.dismissedPendingAction !== "needs_license" &&
      ui.licenseModal.classList.contains("hidden")
    ) {
      openLicenseModal();
      showNotice("error", "需要授權，請先套用 key 後再繼續。");
    }
  } catch (err) {
    console.error(err);
    showNotice("error", `狀態更新失敗：${err}`);
  }
}

async function startRun() {
  const payload = {
    mode: state.activeMode,
    modality: ui.modality.value,
    task: ui.task.value,
    erosion_iters: Number(ui.erosionIters.value || 2),
    range_enabled: ui.chkRange.checked,
    slice_start: ui.sliceStart.value || "1",
    slice_end: ui.sliceEnd.value || "",
    hu_min: ui.huMin.value !== "" ? Number(ui.huMin.value) : null,
    hu_max: ui.huMax.value !== "" ? Number(ui.huMax.value) : null,
  };
  const res = await window.pywebview.api.start_segmentation(payload);
  if (!res.ok) {
    showNotice("error", res.message || "啟動分割失敗");
    return;
  }
  showNotice("success", "已開始批次執行");
}

async function runCompare() {
  ui.btnRunCompare.disabled = true;
  ui.btnRunCompare.classList.add("opacity-60");
  try {
    const res = await window.pywebview.api.run_compare_analysis();
    if (!res.ok) {
      showNotice("error", res.message || "比對失敗");
      return;
    }
    renderCompareResult(res);
    showNotice("success", "比對完成");
  } catch (err) {
    showNotice("error", `比對失敗：${err}`);
  } finally {
    ui.btnRunCompare.disabled = false;
    ui.btnRunCompare.classList.remove("opacity-60");
  }
}

function openLicenseModal() {
  ui.licenseModal.classList.remove("hidden");
  ui.licenseModal.classList.add("flex");
}

function closeLicenseModal() {
  ui.licenseModal.classList.remove("flex");
  ui.licenseModal.classList.add("hidden");
}

function dismissLicenseModal() {
  state.dismissedPendingAction = "needs_license";
  closeLicenseModal();
}

async function refreshLicenseStatus() {
  if (!ui.settingsLicenseStatus) return;
  try {
    const res = await window.pywebview.api.get_current_license();
    if (res.has_license) {
      ui.settingsLicenseStatus.textContent = `目前授權：${res.masked_key}`;
      ui.settingsLicenseStatus.className = "mt-1.5 text-xs text-[#4d8069]";
    } else {
      ui.settingsLicenseStatus.textContent = "尚未設定授權";
      ui.settingsLicenseStatus.className = "mt-1.5 text-xs text-[#8f5f70]";
    }
  } catch {
    ui.settingsLicenseStatus.textContent = "無法讀取授權狀態";
    ui.settingsLicenseStatus.className = "mt-1.5 text-xs text-muted";
  }
}

function openSettingsModal() {
  ui.settingsModal.classList.remove("hidden");
  ui.settingsModal.classList.add("flex");
  refreshLicenseStatus();
}

function closeSettingsModal() {
  ui.settingsModal.classList.remove("flex");
  ui.settingsModal.classList.add("hidden");
}

async function refreshUpdateStatus() {
  ui.btnCheckUpdate.disabled = true;
  try {
    const status = await window.pywebview.api.get_update_status();
    renderUpdateStatus(status);
  } catch (err) {
    renderUpdateStatus({
      ok: false,
      current_version: ui.settingsCurrentVersion?.textContent || "unknown",
      install_supported: false,
      install_block_reason: `檢查更新失敗：${err}`,
    });
  } finally {
    ui.btnCheckUpdate.disabled = false;
  }
}

async function installLatestReleaseUpdate() {
  try {
    const res = await window.pywebview.api.install_latest_release_update();
    if (!res.ok) {
      showNotice("info", res.message || "目前無法更新。");
      return;
    }
    showNotice("success", res.message || "已啟動更新程序。");
    if (res.close_window) {
      window.setTimeout(async () => {
        try {
          await window.pywebview.api.close_for_update();
        } catch (err) {
          console.error(err);
          showNotice("error", `自動關閉視窗失敗：${err}`);
        }
      }, 900);
    }
  } catch (err) {
    showNotice("error", `更新失敗：${err}`);
  }
}

async function openReleasesPage() {
  try {
    await window.pywebview.api.open_releases_page();
  } catch (err) {
    showNotice("error", `無法開啟 Releases：${err}`);
  }
}

async function openLicenseApplyUrl() {
  try {
    await window.pywebview.api.open_license_apply_url();
  } catch (err) {
    showNotice("error", `無法開啟授權頁面：${err}`);
  }
}

async function applyLicense() {
  const raw = ui.licenseInput.value || "";
  const res = await window.pywebview.api.submit_license(raw);
  if (!res.ok) {
    showNotice("error", res.message || "套用授權失敗");
    return;
  }
  showNotice("success", `授權已套用：${res.masked_key}`);
  state.dismissedPendingAction = "";
  closeLicenseModal();
  ui.licenseInput.value = "";
  await pollState();
}

async function applyLicenseFromSettings() {
  const raw = ui.settingsLicenseInput.value || "";
  const res = await window.pywebview.api.submit_license(raw);
  if (!res.ok) {
    showNotice("error", res.message || "套用授權失敗");
    return;
  }
  showNotice("success", `授權已套用：${res.masked_key}`);
  state.dismissedPendingAction = "";
  ui.settingsLicenseInput.value = "";
  await Promise.all([pollState(), refreshLicenseStatus()]);
}

async function retryFailedCase() {
  const res = await window.pywebview.api.retry_last_failed_case();
  if (!res.ok) {
    showNotice("error", res.message || "沒有可重試的失敗病例");
    return;
  }
  showNotice("success", "已開始重試");
}

async function copyAllLog() {
  await copyText(state.logLines.join("\n"));
  showNotice("success", "已複製全部記錄");
}

async function bootstrap() {
  const data = await window.pywebview.api.get_bootstrap();
  state.taskOptionsCT = data.task_options_ct || [];
  state.taskOptionsMRI = data.task_options_mri || [];
  renderUpdateStatus(data.update_status || {
    ok: true,
    current_version: data.current_version || "unknown",
    latest_version: null,
    update_available: false,
    install_supported: false,
    install_block_reason: "",
  });
  setTaskOptions(ui.modality.value);
  renderState(data.state);

  ui.tabSegBtn.addEventListener("click", () => setTab("seg"));
  ui.tabExportBtn.addEventListener("click", () => setTab("export"));
  ui.tabCompareBtn.addEventListener("click", () => setTab("compare"));
  ui.btnOpenSettings.addEventListener("click", openSettingsModal);
  ui.btnCloseSettings.addEventListener("click", closeSettingsModal);
  ui.btnCheckUpdate.addEventListener("click", refreshUpdateStatus);
  ui.btnOpenReleases.addEventListener("click", openReleasesPage);
  ui.btnInstallUpdate.addEventListener("click", installLatestReleaseUpdate);
  ui.btnSettingsLicenseApply.addEventListener("click", applyLicenseFromSettings);

  ui.modality.addEventListener("change", (e) => setTaskOptions(e.target.value));

  ui.chkRange.addEventListener("change", syncSliceRangeInputs);
  syncSliceRangeInputs();

  ui.btnOpenFolder.addEventListener("click", async () => {
    const res = await window.pywebview.api.open_source_folder();
    if (res && !res.ok) showNotice("error", res.message || "無法開啟資料夾");
  });

  ui.btnSelectSource.addEventListener("click", async () => {
    const res = await window.pywebview.api.choose_source_folder();
    if (res && res.ok === false && res.message !== "Cancelled") {
      showNotice("error", res.message || "掃描失敗");
    } else if (res && res.ok) {
      showNotice("success", `掃描完成：${res.count} 個病例`);
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
    showNotice("info", "已送出停止要求");
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

  ui.btnCopyLog.addEventListener("click", copyAllLog);

  ui.btnLicenseOpenUrl.addEventListener("click", openLicenseApplyUrl);
  ui.btnLicenseCancel.addEventListener("click", dismissLicenseModal);
  ui.btnLicenseApply.addEventListener("click", applyLicense);
  ui.btnSettingsLicenseOpenUrl.addEventListener("click", openLicenseApplyUrl);
  ui.licenseModal.addEventListener("click", (e) => {
    if (e.target === ui.licenseModal) dismissLicenseModal();
  });
  ui.settingsModal.addEventListener("click", (e) => {
    if (e.target === ui.settingsModal) closeSettingsModal();
  });

  setTab("seg");

  if (state.pollingTimer) clearInterval(state.pollingTimer);
  state.pollingTimer = setInterval(pollState, 700);
  await pollState();
}

window.addEventListener("pywebviewready", () => {
  bootstrap().catch((err) => {
    console.error(err);
    showNotice("error", `介面初始化失敗：${err}`);
  });
});
