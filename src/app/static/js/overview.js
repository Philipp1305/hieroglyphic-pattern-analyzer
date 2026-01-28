document.addEventListener("DOMContentLoaded", () => {
  const overviewRoot = document.querySelector("[data-overview-root]");
  if (!overviewRoot) {
    return;
  }

  const imageId = overviewRoot.dataset.imageId;
  if (!imageId) {
    return;
  }

  const socket = typeof io === "function" ? io() : null;
  console.log("[overview] socket ready:", Boolean(socket));
  const titleEl = overviewRoot.querySelector("[data-overview-title]");
  const imageWrapper = overviewRoot.querySelector("[data-overview-image]");
  const imageEl = overviewRoot.querySelector("[data-overview-image-content]");
  const loadingEl = overviewRoot.querySelector("[data-overview-loading]");
  const breadcrumbEl = overviewRoot.querySelector("[data-overview-breadcrumb]");
  const pipelineContainer = overviewRoot.querySelector(
    "[data-pipeline-container]",
  );

  const applyTitle = (value) => {
    if (titleEl && value) {
      titleEl.textContent = value;
    }
  };

  const applyImage = (src) => {
    if (imageEl && src) {
      imageEl.style.backgroundImage = `url(${src})`;
      imageEl.classList.remove("opacity-0");
    }
  };

  const hideLoading = () => {
    if (loadingEl) {
      loadingEl.style.display = "none";
    }
  };

  const applyBreadcrumb = () => {
    if (breadcrumbEl) {
      breadcrumbEl.textContent = `ID #${imageId}`;
    }
  };

  let stageOrder = [
    { key: "upload", title: "Upload Image" },
    { key: "json", title: "Process JSON" },
    {
      key: "sort",
      title: "Sort Glyphs",
      pendingSubtitle: "Waiting for Validation",
    },
    { key: "suffix", title: "Pattern Analysis" },
  ];
  let statusesLoaded = false;
  let pendingStatusCode = null;

  const jsonDoneCodes = new Set([
    "JSON_DONE",
    "SORT_START",
    "SORT_VALIDATE",
    "SORT_DONE",
    "ANALYZE_START",
    "ANALYZE_DONE",
    "DONE",
  ]);
  const sortPendingCodes = new Set(["SORT_VALIDATE"]);
  const sortRunningCodes = new Set(["SORT_START"]);
  const sortDoneCodes = new Set([
    "SORT_DONE",
    "ANALYZE_START",
    "ANALYZE_DONE",
    "DONE",
  ]);
  const analyzeRunningCodes = new Set(["ANALYZE_START"]);
  const analyzeDoneCodes = new Set(["ANALYZE_DONE", "DONE"]);

  const resolveStates = (statusCode) => {
    const code = (statusCode || "").toString().trim().toUpperCase();
    console.log("[overview] resolveStates", code);
    const upload = "done"; // upload is always checked
    const json = jsonDoneCodes.has(code)
      ? "done"
      : code === "JSON_START"
        ? "running"
        : "running";
    const sort = sortPendingCodes.has(code)
      ? "pending"
      : sortRunningCodes.has(code)
        ? "running"
        : sortDoneCodes.has(code)
          ? "done"
          : "waiting";
    const suffix = analyzeDoneCodes.has(code)
      ? "done"
      : analyzeRunningCodes.has(code)
        ? "running"
        : sortDoneCodes.has(code)
          ? "pending"
          : "waiting";
    return { upload, json, sort, suffix };
  };

  const renderPipelineLoading = () => {
    if (!pipelineContainer) {
      return;
    }
    pipelineContainer.innerHTML = `
      <div class="flex items-center justify-center py-16 text-sm text-text-secondary-light dark:text-text-secondary-dark">
        Loading pipeline…
      </div>
    `;
  };

  const renderPipeline = (statusCode, options = {}) => {
    if (!pipelineContainer) {
      return;
    }
    const forceRender = Boolean(options.force);
    const normalized = (statusCode || "").toString().trim().toUpperCase();
    const states = resolveStates(normalized);
    const html = stageOrder
      .map((stage) => renderStage(stage, states[stage.key] || "waiting"))
      .join("");
    pipelineContainer.innerHTML = html;

    updateActionCards(normalized);
  };

  const renderStage = (stage, state) => {
    const subtitle =
      state === "pending"
        ? stage.pendingSubtitle || "Pending user action"
        : stage.subtitle || "";

    switch (state) {
      case "done":
        return stageDone(stage.title, subtitle);
      case "running":
        return stageRunning(stage.title, subtitle || "Processing…");
      case "pending":
        return stagePending(stage.title, subtitle);
      default:
        return stageWaiting(stage.title, subtitle || "Waiting");
    }
  };

  const stageDone = (title, subtitle) => `
    <div class="flex flex-1 items-center justify-between px-5 py-4">
        <div class="flex items-center gap-4">
            <div class="flex size-9 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300">
                <span class="material-symbols-outlined text-base">check_circle</span>
            </div>
            <div class="flex flex-col">
                <span class="text-sm font-semibold text-text-light dark:text-text-dark">${title}</span>
                ${subtitle ? `<span class="text-xs text-text-secondary-light dark:text-text-secondary-dark">${subtitle}</span>` : ""}
            </div>
        </div>
        <span class="text-xs font-semibold uppercase text-text-secondary-light dark:text-text-secondary-dark">Done</span>
    </div>
  `;

  const stageRunning = (title, subtitle) => `
    <div class="flex flex-1 items-center justify-between px-5 py-4 bg-primary/5 dark:bg-primary/15">
        <div class="flex items-center gap-4">
            <div class="flex size-9 items-center justify-center rounded-full text-primary">
                <span class="material-symbols-outlined animate-spin text-xl">progress_activity</span>
            </div>
            <div class="flex flex-col">
                <span class="text-sm font-semibold text-text-light dark:text-text-dark">${title}</span>
                ${subtitle ? `<span class="text-xs text-primary">${subtitle}</span>` : ""}
            </div>
        </div>
        <span class="rounded-full bg-primary/10 px-3 py-1 text-[10px] font-semibold uppercase text-primary">Running</span>
    </div>
  `;

  const stagePending = (title, subtitle) => `
    <div class="flex flex-1 items-center justify-between px-5 py-4 bg-amber-50 dark:bg-amber-500/10">
        <div class="flex items-center gap-4">
            <div class="flex size-9 items-center justify-center rounded-full text-amber-600 dark:text-amber-300">
                <span class="material-symbols-outlined text-xl">hourglass_bottom</span>
            </div>
            <div class="flex flex-col">
                <span class="text-sm font-semibold text-text-light dark:text-text-dark">${title}</span>
                ${subtitle ? `<span class="text-xs text-amber-600 dark:text-amber-200">${subtitle}</span>` : ""}
            </div>
        </div>
        <span class="rounded-full bg-amber-200/70 dark:bg-amber-500/30 px-3 py-1 text-[10px] font-semibold uppercase text-amber-700 dark:text-amber-100">Pending</span>
    </div>
  `;

  const stageWaiting = (title, subtitle) => `
    <div class="flex flex-1 items-center justify-between px-5 py-4 opacity-80">
        <div class="flex items-center gap-4">
            <div class="flex size-9 items-center justify-center rounded-full bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300">
                <span class="material-symbols-outlined text-base">schedule</span>
            </div>
            <div class="flex flex-col">
                <span class="text-sm font-semibold text-text-light dark:text-text-dark">${title}</span>
                ${subtitle ? `<span class="text-xs text-text-secondary-light dark:text-text-secondary-dark">${subtitle}</span>` : ""}
            </div>
        </div>
        <span class="text-xs font-semibold uppercase text-text-secondary-light dark:text-text-secondary-dark">Waiting</span>
    </div>
  `;

  const lockedButtonClasses = [
    "bg-transparent",
    "text-text-secondary-light",
    "dark:text-text-secondary-dark",
    "border",
    "border-border-light",
    "dark:border-border-dark",
    "hover:border-primary",
    "hover:text-primary",
  ];
  const unlockedButtonClasses = [
    "bg-primary",
    "text-white",
    "border-transparent",
    "shadow-md",
    "hover:bg-primary/90",
    "hover:text-white",
  ];
  const lockedStateClasses = [
    "pointer-events-none",
    "opacity-60",
    "cursor-not-allowed",
    "border-dashed",
  ];

  const actionRules = [
    {
      key: "sort",
      unlockedStatuses: [
        "SORT_VALIDATE",
        "ANALYZE_START",
        "ANALYZE_DONE",
        "SORT_DONE",
        "DONE",
      ],
    },
    {
      key: "patterns",
      unlockedStatuses: ["DONE"],
    },
    {
      key: "structure",
      unlockedStatuses: ["DONE"],
    },
    {
      key: "glyphs",
      unlockedStatuses: ["DONE"],
    },
  ];

  const updateActionCards = (statusCode = "") => {
    const normalizedStatus = (statusCode || "").toString().trim().toUpperCase();
    actionRules.forEach((rule) => {
      const card = overviewRoot.querySelector(
        `[data-action-card="${rule.key}"]`,
      );
      if (!card) {
        return;
      }
      const button = card.querySelector("[data-action-button]");
      const badge = card.querySelector("[data-action-badge]");

      const unlocked = (rule.unlockedStatuses || []).includes(normalizedStatus);
      const isLocked = !unlocked;

      card.classList.toggle("cursor-not-allowed", isLocked);
      if (button) {
        if (isLocked) {
          button.classList.add(...lockedStateClasses);
          button.classList.remove(...unlockedButtonClasses);
          button.classList.add(...lockedButtonClasses);
          button.setAttribute("aria-disabled", "true");
        } else {
          button.classList.remove(...lockedStateClasses);
          button.classList.remove(...lockedButtonClasses);
          button.classList.add(...unlockedButtonClasses);
          button.removeAttribute("aria-disabled");
        }
      }
      if (badge) {
        const showBadge = (text, addClasses = [], removeClasses = []) => {
          badge.style.display = text ? "inline-flex" : "none";
          badge.textContent = text || "";
          if (removeClasses.length) {
            badge.classList.remove(...removeClasses);
          }
          if (addClasses.length) {
            badge.classList.add(...addClasses);
          }
        };

        if (rule.key === "sort") {
          if (normalizedStatus === "SORT_VALIDATE") {
            showBadge(
              "Action required",
              ["bg-primary/10", "text-primary"],
              [
                "bg-border-light",
                "text-text-secondary-light",
                "dark:bg-border-dark",
              ],
            );
          } else if (isLocked) {
            showBadge(
              "Locked",
              [
                "bg-border-light",
                "text-text-secondary-light",
                "dark:bg-border-dark",
              ],
              ["bg-primary/10", "text-primary"],
            );
          } else {
            showBadge(
              "",
              [],
              [
                "bg-primary/10",
                "text-primary",
                "bg-border-light",
                "text-text-secondary-light",
                "dark:bg-border-dark",
              ],
            );
          }
        } else {
          if (isLocked) {
            showBadge(
              "Locked",
              [
                "bg-border-light",
                "text-text-secondary-light",
                "dark:bg-border-dark",
              ],
              ["bg-primary/10", "text-primary"],
            );
          } else {
            showBadge(
              "",
              [],
              [
                "bg-primary/10",
                "text-primary",
                "bg-border-light",
                "text-text-secondary-light",
                "dark:bg-border-dark",
              ],
            );
          }
        }
      }
    });
  };

  applyBreadcrumb();

  const apiUrl = `/api/images/${imageId}?_=${Date.now()}`;
  const metaUrl = `/api/images/${imageId}/meta?_=${Date.now()}`;
  let metaPayload = null;
  let pageLoaded = false;
  let labelsLoaded = true; // static labels; no DB fetch needed

  const getNormalizedStatus = (value) =>
    (value || "").toString().trim().toUpperCase();

  const getStatusLabel = (_code, fallback) => fallback;

  const applyStatusLabels = () => {};

  if (socket) {
    socket.on("s2c:pipeline_status", (data) => {
      console.log("[overview] s2c:pipeline_status received", data);
      if (!data || String(data.image_id) !== String(imageId)) {
        console.log("[overview] pipeline_status ignored (different id)");
        return;
      }
      if (data.status_code) {
        renderPipeline(data.status_code, { force: true });
        maybeStopPolling(data.status_code);
      }
    });
  }

  // Delay first render until labels and an initial status are present
  renderPipelineLoading();
  let initialStatus = null;

  const tryInitialRender = () => {
    if (!labelsLoaded || initialStatus === null) return;
    renderPipeline(initialStatus);
  };

  window.addEventListener("load", () => {
    console.log("[overview] window load");
    pageLoaded = true;
  });

  fetch(apiUrl, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to load papyrus data");
      }
      return response.json();
    })
    .then((data) => {
      console.log("[overview] image data loaded", data);
      applyTitle(data.title || `Papyrus #${imageId}`);
      applyImage(data.image);
      initialStatus = data.status_code;
      tryInitialRender();
      hideLoading();
    })
    .catch((error) => {
      console.error(error);
      applyTitle("Papyrus konnte nicht geladen werden");
      hideLoading();
      tryInitialRender();
    });

  fetch(metaUrl, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to load papyrus metadata");
      }
      return response.json();
    })
    .then((meta) => {
      console.log("[overview] meta loaded", meta);
      metaPayload = meta || {};
      if (meta && meta.status_code) {
        initialStatus = meta.status_code;
        tryInitialRender();
      }
    })
    .catch((error) => {
      console.error(error);
    });

  // Static labels now; mark as loaded immediately.
  statusesLoaded = true;
  applyStatusLabels();
  labelsLoaded = true;
  tryInitialRender();

  // Fallback polling to keep pipeline fresh even if sockets fail.
  const pollIntervalMs = 3000;
  const stopPollingCodes = new Set(["DONE"]);

  let pollTimer = null;

  const maybeStopPolling = (statusCode) => {
    const code = (statusCode || "").toString().trim().toUpperCase();
    if (stopPollingCodes.has(code) && pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
      console.log("[overview] polling stopped at", code);
    }
  };

  const startPolling = () => {
    if (pollTimer) return;
    pollTimer = setInterval(pollStatus, pollIntervalMs);
    console.log("[overview] polling started");
  };

  const pollStatus = () => {
    fetch(metaUrl, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load papyrus metadata");
        }
        return response.json();
      })
      .then((meta) => {
        if (meta && meta.status_code) {
          renderPipeline(meta.status_code);
          console.log("[overview] poll status_code", meta.status_code);
          maybeStopPolling(meta.status_code);
        }
      })
      .catch((error) => console.error("[overview] poll meta error", error));
  };
  startPolling();
});
