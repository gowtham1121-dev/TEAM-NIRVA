/* =========================================================
   TEAM NIRVA — Visual Quality Intelligence
   Frontend logic: upload, validation, scanning, results, history.
   ========================================================= */

/* ---------- CONFIGURATION (easy to edit) ---------- */
const API_BASE_URL = "http://127.0.0.1:8000"; // Address of the FastAPI server
const DEMO_MODE = true;                       // true = simulated results, NO network requests
                                              // false = call the FastAPI backend

const MAX_FILE_SIZE = 10 * 1024 * 1024;       // 10 MB
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png", "webp"];
const REQUEST_TIMEOUT_MS = 30000;             // Backend request timeout

const HISTORY_STORAGE_KEY = "teamNirvaInspectionHistory"; // localStorage key
const HISTORY_MAX_ITEMS = 20;                             // Keep only the latest 20 records

(function () {
  "use strict";

  /* ---------- Element references ---------- */
  const byId = (id) => document.getElementById(id);
  const el = {
    imagePanel: byId("image-panel"),
    dropzone: byId("dropzone"),
    fileInput: byId("file-input"),
    browseButton: byId("browse-button"),
    preview: byId("preview"),
    previewImage: byId("preview-image"),
    fileName: byId("file-name"),
    fileDimensions: byId("file-dimensions"),
    removeButton: byId("remove-button"),
    scanLine: byId("scan-line"),
    defectMarker: byId("defect-marker"),
    analyzeButton: byId("analyze-button"),
    resetButton: byId("reset-button"),
    retryButton: byId("retry-button"),
    stateIdle: byId("state-idle"),
    stateRunning: byId("state-running"),
    stateResult: byId("state-result"),
    stateError: byId("state-error"),
    progress: byId("progress"),
    progressFill: byId("progress-fill"),
    stages: byId("stages"),
    resultClassification: byId("result-classification"),
    resultConfidence: byId("result-confidence"),
    confidenceFill: byId("confidence-fill"),
    resultSeverity: byId("result-severity"),
    resultId: byId("result-id"),
    resultMode: byId("result-mode"),
    resultExplanation: byId("result-explanation"),
    resultDisclaimer: byId("result-disclaimer"),
    errorMessage: byId("error-message"),
    statusImage: byId("status-image"),
    statusEngine: byId("status-engine"),
    statusApi: byId("status-api"),
    modeChip: byId("mode-chip"),
    historyList: byId("history-list"),
    historyEmpty: byId("history-empty"),
    historyCount: byId("history-count"),
    clearHistoryButton: byId("clear-history-button"),
    toastRegion: byId("toast-region")
  };

  /* ---------- App state ---------- */
  let selectedFile = null;   // The validated File object
  let previewUrl = null;     // Temporary URL used for the preview
  let isAnalyzing = false;   // True while an inspection is running
  let inspectionCounter = 0; // Used to build inspection IDs
  let history = [];          // Saved inspection records (newest first)

  // Maps a classification to the CSS tone used for colors.
  const TONES = { "GOOD": "good", "DEFECTIVE": "defective", "REQUIRES REVIEW": "review" };

  /* ---------- Small utilities ---------- */
  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function showToast(message, type) {
    if (!el.toastRegion) return;
    const toast = document.createElement("div");
    toast.className = "toast" + (type === "error" ? " error" : "");
    toast.textContent = message;
    el.toastRegion.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }

  // Shows exactly one of the right-panel states: idle | running | result | error
  function showState(name) {
    if (el.stateIdle) el.stateIdle.hidden = name !== "idle";
    if (el.stateRunning) el.stateRunning.hidden = name !== "running";
    if (el.stateResult) el.stateResult.hidden = name !== "result";
    if (el.stateError) el.stateError.hidden = name !== "error";
  }

  function formatSize(bytes) {
    if (bytes < 1024 * 1024) return Math.max(1, Math.round(bytes / 1024)) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function setApiStatus(label, isConnected) {
    if (!el.statusApi) return;
    el.statusApi.textContent = label;
    el.statusApi.dataset.status = isConnected ? "ok" : "error";
  }

  /* =========================================================
     FILE VALIDATION
     Returns an error message string, or null when the file is OK.
     ========================================================= */
  function validateFile(file) {
    const parts = file.name.split(".");
    const extension = parts.length > 1 ? parts.pop().toLowerCase() : "";
    const typeIsKnown = file.type !== "";
    const badType = typeIsKnown && !ALLOWED_TYPES.includes(file.type);

    if (!ALLOWED_EXTENSIONS.includes(extension) || badType) {
      return "Unsupported file type. Please upload a JPG, JPEG, PNG or WEBP image.";
    }
    if (file.size === 0) {
      return "This file is empty.";
    }
    if (file.size > MAX_FILE_SIZE) {
      return "File is too large (" + formatSize(file.size) + "). Maximum size is 10 MB.";
    }
    return null;
  }

  /* =========================================================
     UPLOAD + PREVIEW
     ========================================================= */
  function handleFile(file) {
    if (isAnalyzing) {
      showToast("Please wait for the current inspection to finish.", "error");
      return;
    }

    const problem = validateFile(file);
    if (problem) {
      showToast(problem, "error");
      return;
    }

    clearImage(false); // Remove any previous image first
    selectedFile = file;
    previewUrl = URL.createObjectURL(file);

    el.previewImage.onload = function () {
      el.fileName.textContent = file.name;
      el.fileDimensions.textContent =
        el.previewImage.naturalWidth + " × " + el.previewImage.naturalHeight +
        " px · " + formatSize(file.size);
      el.dropzone.hidden = true;
      el.preview.hidden = false;
      el.analyzeButton.disabled = false;
      if (el.statusImage) el.statusImage.textContent = "READY";
      showToast("Image loaded.");
    };

    el.previewImage.onerror = function () {
      showToast("This image could not be loaded. The file may be corrupted.", "error");
      clearImage(false);
    };

    el.previewImage.src = previewUrl;
  }

  // Returns the left panel and the right panel to their empty states.
  function clearImage(announce) {
    el.previewImage.onload = null;
    el.previewImage.onerror = null;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    selectedFile = null;

    el.previewImage.removeAttribute("src");
    el.preview.hidden = true;
    el.dropzone.hidden = false;
    el.fileInput.value = "";
    el.scanLine.hidden = true;
    el.defectMarker.hidden = true;
    el.analyzeButton.disabled = true;
    if (el.statusImage) el.statusImage.textContent = "NO IMAGE";
    showState("idle");

    if (announce) showToast("Image removed.");
  }

  /* ---------- Drag and drop (the whole left panel is a drop target) ---------- */
  let dragDepth = 0; // Counts nested dragenter/dragleave events to avoid flicker

  function dragHasFiles(event) {
    return event.dataTransfer && Array.from(event.dataTransfer.types || []).includes("Files");
  }

  if (el.imagePanel) {
    el.imagePanel.addEventListener("dragenter", (event) => {
      if (!dragHasFiles(event)) return;
      event.preventDefault();
      dragDepth += 1;
      el.imagePanel.classList.add("is-dragover");
    });

    el.imagePanel.addEventListener("dragover", (event) => {
      if (!dragHasFiles(event)) return;
      event.preventDefault(); // Required, otherwise the drop event never fires
    });

    el.imagePanel.addEventListener("dragleave", (event) => {
      if (!dragHasFiles(event)) return;
      dragDepth = Math.max(0, dragDepth - 1);
      if (dragDepth === 0) el.imagePanel.classList.remove("is-dragover");
    });

    el.imagePanel.addEventListener("drop", (event) => {
      event.preventDefault();
      dragDepth = 0;
      el.imagePanel.classList.remove("is-dragover");

      const files = event.dataTransfer ? event.dataTransfer.files : null;
      if (!files || files.length === 0) return;
      if (files.length > 1) showToast("Only one image can be inspected at a time. Using the first file.");
      handleFile(files[0]);
    });
  }

  // Stop the browser from opening a file that is dropped outside the panel.
  window.addEventListener("dragover", (event) => event.preventDefault());
  window.addEventListener("drop", (event) => event.preventDefault());

  /* ---------- Browse + remove buttons ---------- */
  if (el.browseButton) el.browseButton.addEventListener("click", () => el.fileInput.click());

  if (el.fileInput) {
    el.fileInput.addEventListener("change", () => {
      if (el.fileInput.files.length > 0) handleFile(el.fileInput.files[0]);
    });
  }

  if (el.removeButton) {
    el.removeButton.addEventListener("click", () => {
      if (!isAnalyzing) clearImage(true);
    });
  }

  /* =========================================================
     ANALYSIS
     analyzeImage(file) is the single entry point.
     - DEMO_MODE = true  -> simulated result, no network request.
     - DEMO_MODE = false -> POST to the FastAPI backend.
     ========================================================= */
  async function analyzeImage(file) {
    if (DEMO_MODE) {
      return analyzeSimulated(file);
    }
    return analyzeWithBackend(file);
  }

  /* ---------------------------------------------------------
     SIMULATED ANALYSIS (demo mode only)
     --------------------------------------------------------- */
  async function analyzeSimulated(file) {
    await sleep(600); // Pretend the engine is working

    const outcomes = [
      {
        classification: "GOOD", severity: "NONE", min: 0.90, max: 0.99,
        explanation: "Simulated outcome: no surface anomalies were flagged in this demonstration."
      },
      {
        classification: "DEFECTIVE", severity: Math.random() < 0.5 ? "MEDIUM" : "HIGH", min: 0.82, max: 0.97,
        explanation: "Simulated outcome: a potential surface defect is shown for demonstration purposes only."
      },
      {
        classification: "REQUIRES REVIEW", severity: "LOW", min: 0.55, max: 0.74,
        explanation: "Simulated outcome: confidence is low, so manual review would be recommended."
      }
    ];

    const pick = outcomes[Math.floor(Math.random() * outcomes.length)];
    return {
      classification: pick.classification,
      confidence: pick.min + Math.random() * (pick.max - pick.min),
      severity: pick.severity,
      explanation: pick.explanation,
      inspectionId: generateInspectionId(),
      mode: "SIMULATED"
    };
  }

  /* ---------------------------------------------------------
     BACKEND INTEGRATION (FastAPI)
     --------------------------------------------------------- */
  async function analyzeWithBackend(file) {
    const formData = new FormData();
    formData.append("file", file);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    let response;
    try {
      response = await fetch(API_BASE_URL + "/predict", {
        method: "POST",
        body: formData,
        signal: controller.signal
      });
    } catch (networkError) {
      setApiStatus("UNREACHABLE", false);
      if (networkError.name === "AbortError") {
        throw new Error("The inspection server took too long to respond. Please try again.");
      }
      throw new Error("Cannot reach the inspection server at " + API_BASE_URL + ". Is the backend running?");
    } finally {
      clearTimeout(timer);
    }

    if (!response.ok) {
      setApiStatus("ERROR " + response.status, false);
      throw new Error("The inspection server returned an error (" + response.status + ").");
    }

    let data;
    try {
      data = await response.json();
    } catch (parseError) {
      setApiStatus("INVALID RESPONSE", false);
      throw new Error("The inspection server sent a response that is not valid JSON.");
    }

    const result = normalizeBackendResponse(data);
    setApiStatus("CONNECTED", true);
    return result;
  }

  function normalizeBackendResponse(data) {
    const invalid = new Error("The server response was missing or contained invalid prediction data.");
    if (!data || typeof data !== "object") throw invalid;

    const labels = {
      good: "GOOD",
      defective: "DEFECTIVE",
      requires_review: "REQUIRES REVIEW",
      review: "REQUIRES REVIEW"
    };
    const key = typeof data.prediction === "string"
      ? data.prediction.trim().toLowerCase().replace(/\s+/g, "_")
      : "";
    const classification = labels[key];

    let confidence = data.confidence;
    if (!classification || typeof confidence !== "number" || !isFinite(confidence) || confidence < 0 || confidence > 100) {
      throw invalid;
    }
    if (confidence > 1) confidence = confidence / 100;

    const validSeverities = ["NONE", "LOW", "MEDIUM", "HIGH"];
    let severity = "NONE";
    if (classification === "DEFECTIVE") severity = confidence > 0.9 ? "HIGH" : confidence > 0.75 ? "MEDIUM" : "LOW";
    if (classification === "REQUIRES REVIEW") severity = "LOW";
    if (typeof data.severity === "string" && validSeverities.includes(data.severity.toUpperCase())) {
      severity = data.severity.toUpperCase();
    }

    const defects = Array.isArray(data.defects) ? data.defects : [];
    const explanation = defects.length > 0
      ? "Detected: " + defects.map((d) => (typeof d === "string" ? d : (d && d.type) || "defect")).join(", ") + "."
      : "Result returned by the inspection backend.";

    return {
      classification: classification,
      confidence: confidence,
      severity: severity,
      explanation: explanation,
      inspectionId: typeof data.inspection_id === "string" && data.inspection_id ? data.inspection_id : generateInspectionId(),
      mode: "BACKEND"
    };
  }

  /* ---------- Inspection ID generator ---------- */
  function generateInspectionId() {
    inspectionCounter += 1;
    const suffix = Math.floor(Math.random() * 1296).toString(36).toUpperCase().padStart(2, "0");
    return "NV-" + String(inspectionCounter).padStart(4, "0") + "-" + suffix;
  }

  /* =========================================================
     INSPECTION FLOW
     ========================================================= */
  const STAGE_DURATION_MS = 900;

  function setProgress(percent) {
    if (!el.progressFill || !el.progress) return;
    el.progressFill.style.width = percent + "%";
    el.progress.setAttribute("aria-valuenow", String(Math.round(percent)));
  }

  function setActiveStage(index) {
    if (!el.stages) return;
    Array.from(el.stages.children).forEach((item, i) => {
      item.classList.toggle("done", i < index);
      item.classList.toggle("active", i === index);
    });
  }

  async function runInspection() {
    if (!selectedFile || isAnalyzing) return;

    isAnalyzing = true;
    el.analyzeButton.disabled = true;
    el.removeButton.disabled = true;
    el.defectMarker.hidden = true;
    if (el.statusImage) el.statusImage.textContent = "PROCESSING";

    showState("running");
    setProgress(0);
    setActiveStage(-1);
    el.scanLine.hidden = false;

    const analysis = analyzeImage(selectedFile).then(
      (result) => ({ ok: true, result: result }),
      (error) => ({ ok: false, error: error })
    );

    const stageCount = el.stages ? el.stages.children.length : 0;
    for (let i = 0; i < stageCount; i++) {
      setActiveStage(i);
      await sleep(40);
      setProgress(((i + 1) / stageCount) * 90);
      await sleep(STAGE_DURATION_MS);
    }

    const outcome = await analysis;

    el.scanLine.hidden = true;
    isAnalyzing = false;
    el.removeButton.disabled = false;
    if (el.statusImage) el.statusImage.textContent = "READY";

    if (outcome.ok) {
      setActiveStage(stageCount);
      setProgress(100);
      addHistoryEntry(selectedFile, outcome.result);
      await sleep(300);
      showResult(outcome.result);
    } else {
      showError(outcome.error && outcome.error.message ? outcome.error.message : "Inspection failed.");
    }
  }

  /* =========================================================
     RESULT DISPLAY
     ========================================================= */
  function showResult(result) {
    const tone = TONES[result.classification];
    const isSimulated = result.mode === "SIMULATED";

    el.stateResult.dataset.tone = tone;
    el.resultClassification.textContent = result.classification;
    el.resultSeverity.textContent = result.severity;
    el.resultId.textContent = result.inspectionId;
    el.resultMode.textContent = result.mode;
    el.resultExplanation.textContent = result.explanation;

    el.resultDisclaimer.textContent = isSimulated
      ? "Demo prediction only. Not generated by a trained AI model."
      : "Result provided by the connected inspection backend.";

    el.defectMarker.style.setProperty("--marker-color", tone === "review" ? "var(--orange)" : "var(--red)");
    el.defectMarker.hidden = !(isSimulated && tone !== "good");

    const percent = Math.round(result.confidence * 1000) / 10;
    el.resultConfidence.textContent = "0.0%";
    el.confidenceFill.style.width = "0%";
    showState("result");

    requestAnimationFrame(() => requestAnimationFrame(() => {
      el.confidenceFill.style.width = percent + "%";
    }));
    animateNumber(percent);

    if (typeof el.resultClassification.focus === "function") {
      el.resultClassification.focus({ preventScroll: true });
    }
  }

  function animateNumber(target) {
    const duration = 1000;
    const start = performance.now();
    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      el.resultConfidence.textContent = (target * progress).toFixed(1) + "%";
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  function showError(message) {
    el.errorMessage.textContent = message;
    el.analyzeButton.disabled = !selectedFile;
    showState("error");
    showToast(message, "error");
  }

  function retryInspection() {
    el.defectMarker.hidden = true;
    el.analyzeButton.disabled = !selectedFile;
    showState("idle");
  }

  function inspectAnotherImage() {
    clearImage(false);
  }

  /* =========================================================
     INSPECTION HISTORY
     ========================================================= */
  function createThumbnail(image) {
    try {
      const size = 96;
      const canvas = document.createElement("canvas");
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext("2d");
      const side = Math.min(image.naturalWidth, image.naturalHeight);
      const sx = (image.naturalWidth - side) / 2;
      const sy = (image.naturalHeight - side) / 2;
      ctx.drawImage(image, sx, sy, side, side, 0, 0, size, size);
      return canvas.toDataURL("image/jpeg", 0.6);
    } catch (error) {
      return "";
    }
  }

  function loadHistory() {
    try {
      const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed
        .filter((item) =>
          item && typeof item === "object" &&
          typeof item.fileName === "string" &&
          typeof item.id === "string" &&
          typeof item.confidence === "number" &&
          Object.prototype.hasOwnProperty.call(TONES, item.classification)
        )
        .slice(0, HISTORY_MAX_ITEMS);
    } catch (error) {
      return [];
    }
  }

  function saveHistory() {
    try {
      localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
    } catch (error) {
      try {
        const withoutThumbnails = history.map((item) => Object.assign({}, item, { thumbnail: "" }));
        localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(withoutThumbnails));
      } catch (secondError) {
        showToast("History could not be saved in this browser.", "error");
      }
    }
  }

  function addHistoryEntry(file, result) {
    const entry = {
      id: result.inspectionId,
      fileName: file.name,
      dimensions: el.previewImage.naturalWidth + " × " + el.previewImage.naturalHeight,
      timestamp: new Date().toISOString(),
      classification: result.classification,
      confidence: result.confidence,
      severity: result.severity,
      mode: result.mode,
      thumbnail: createThumbnail(el.previewImage)
    };
    history.unshift(entry);
    history = history.slice(0, HISTORY_MAX_ITEMS);
    saveHistory();
    renderHistory();
  }

  function removeHistoryEntry(index) {
    history.splice(index, 1);
    saveHistory();
    renderHistory();
    showToast("Record removed.");
  }

  function clearHistory() {
    if (history.length === 0) return;
    if (!window.confirm("Clear all inspection history?")) return;
    history = [];
    saveHistory();
    renderHistory();
    showToast("History cleared.");
  }

  function formatTimestamp(isoString) {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return "Unknown time";
    return date.toLocaleString([], { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  }

  function buildHistoryItem(entry, index, onRemove) {
    const item = document.createElement("li");
    item.className = "history-item";
    if (TONES[entry.classification]) {
      item.dataset.tone = TONES[entry.classification];
    }

    // Thumbnail (or placeholder)
    let thumb;
    if (typeof entry.thumbnail === "string" && entry.thumbnail.startsWith("data:image/")) {
      thumb = document.createElement("img");
      thumb.src = entry.thumbnail;
      thumb.alt = "Thumbnail of " + entry.fileName;
      thumb.className = "history-thumb";
    } else {
      thumb = document.createElement("div");
      thumb.className = "history-thumb history-thumb-empty";
      thumb.textContent = "NO IMG";
    }

    // File name + metadata
    const main = document.createElement("div");
    main.className = "history-main";

    const name = document.createElement("div");
    name.className = "history-name";
    name.textContent = entry.fileName;
    name.title = entry.fileName;

    const meta = document.createElement("div");
    meta.className = "history-meta";
    meta.textContent = formatTimestamp(entry.timestamp) + " · " + entry.id;

    main.appendChild(name);
    main.appendChild(meta);

    // Classification + details
    const resultBox = document.createElement("div");
    resultBox.className = "history-result";

    const badge = document.createElement("span");
    badge.className = "history-badge";
    badge.textContent = entry.classification;

    const detail = document.createElement("span");
    detail.className = "history-detail";
    const confidencePercent = (Math.round((entry.confidence || 0) * 1000) / 10).toFixed(1);
    detail.textContent =
      confidencePercent + "% · " +
      (entry.severity || "—") + " · " +
      (entry.mode || "—");

    resultBox.appendChild(badge);
    resultBox.appendChild(detail);

    // Remove button
    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "history-remove";
    removeButton.setAttribute("aria-label", "Remove " + entry.fileName);
    removeButton.title = "Remove item";
    removeButton.textContent = "✕";

    removeButton.addEventListener("click", (e) => {
      e.stopPropagation();
      if (typeof onRemove === "function") {
        onRemove(entry, index);
      }
    });

    // Assemble and return element
    item.appendChild(thumb);
    item.appendChild(main);
    item.appendChild(resultBox);
    item.appendChild(removeButton);

    return item;
  }

  function renderHistory() {
    if (!el.historyList) return;
    el.historyList.innerHTML = "";

    const count = history.length;
    if (el.historyCount) {
      el.historyCount.textContent = count > 0 ? `(${count})` : "";
    }
    if (el.clearHistoryButton) {
      el.clearHistoryButton.disabled = count === 0;
    }

    if (count === 0) {
      if (el.historyEmpty) el.historyEmpty.hidden = false;
      return;
    }

    if (el.historyEmpty) el.historyEmpty.hidden = true;

    history.forEach((entry, index) => {
      const itemNode = buildHistoryItem(entry, index, (_entry, idx) => {
        removeHistoryEntry(idx);
      });
      el.historyList.appendChild(itemNode);
    });
  }

  /* =========================================================
     INITIALIZATION & EVENT BINDINGS
     ========================================================= */
  if (el.analyzeButton) el.analyzeButton.addEventListener("click", runInspection);
  if (el.retryButton) el.retryButton.addEventListener("click", retryInspection);
  if (el.resetButton) el.resetButton.addEventListener("click", inspectAnotherImage);
  if (el.clearHistoryButton) el.clearHistoryButton.addEventListener("click", clearHistory);

  // Status indicators & mode setup
  if (el.modeChip) {
    el.modeChip.textContent = DEMO_MODE ? "DEMO (SIMULATED)" : "LIVE (FASTAPI)";
    el.modeChip.classList.toggle("is-demo", DEMO_MODE);
  }
  if (el.statusEngine) {
    el.statusEngine.textContent = DEMO_MODE ? "SIMULATOR" : "AI MODEL";
  }
  if (el.statusImage) {
    el.statusImage.textContent = "NO IMAGE";
  }
  if (el.statusApi) {
    if (DEMO_MODE) {
      setApiStatus("OFFLINE (DEMO)", false);
    } else {
      setApiStatus("STANDBY", true);
    }
  }

  // Load and render history from localStorage
  history = loadHistory();
  renderHistory();
})();