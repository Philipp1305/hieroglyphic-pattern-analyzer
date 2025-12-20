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
  const pipelineContainer = overviewRoot.querySelector("[data-pipeline-container]");

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
    { key: "upload", title: "Image uploaded" },
    { key: "json", title: "JSON processed" },
    { key: "sort", title: "Sorting algorithm", pendingSubtitle: "Waiting for confirmation in Sorting View" },
    { key: "ngrams", title: "N-Grams" },
    { key: "suffix", title: "Suffix tree" },
  ];
  let statusesLoaded = false;
  let pendingStatusCode = null;

  const statusMapping = {
    UPLOAD: { upload: "done", json: "running", sort: "waiting", ngrams: "waiting", suffix: "waiting" },
    JSON: { upload: "done", json: "done", sort: "running", ngrams: "waiting", suffix: "waiting" },
    SORT_VALIDATE: { upload: "done", json: "done", sort: "pending", ngrams: "waiting", suffix: "waiting" },
    SORT: { upload: "done", json: "done", sort: "done", ngrams: "running", suffix: "waiting" },
    NGRAMS: { upload: "done", json: "done", sort: "done", ngrams: "done", suffix: "running" },
    SUFFIX: { upload: "done", json: "done", sort: "done", ngrams: "done", suffix: "done" },
    DONE: { upload: "done", json: "done", sort: "done", ngrams: "done", suffix: "done" },
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

  const renderPipeline = (statusCode) => {
    if (!pipelineContainer) {
      return;
    }
    if (!statusesLoaded) {
      pendingStatusCode = statusCode;
      renderPipelineLoading();
      return;
    }
    const normalized = (statusCode || "").toString().trim().toUpperCase();
    const states = statusMapping[normalized] || statusMapping.UPLOAD;
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
  const lockedStateClasses = ["pointer-events-none", "opacity-60", "cursor-not-allowed", "border-dashed"];

  const actionRules = [
    {
      key: "sort",
      lockedStatuses: ["UPLOAD", "JSON"],
    },
    {
      key: "ngrams",
      lockedStatuses: ["UPLOAD", "JSON", "SORT_VALIDATE", "SORT"],
    },
    {
      key: "suffix",
      lockedStatuses: ["UPLOAD", "JSON", "SORT_VALIDATE", "SORT", "NGRAMS"],
    },
  ];

  const updateActionCards = (statusCode = "") => {
    const normalizedStatus = (statusCode || "").toString().trim().toUpperCase();
    actionRules.forEach((rule) => {
      const card = overviewRoot.querySelector(`[data-action-card="${rule.key}"]`);
      if (!card) {
        return;
      }
      const button = card.querySelector("[data-action-button]");
      const badge = card.querySelector("[data-action-badge]");

      const isLocked = rule.lockedStatuses.includes(normalizedStatus);

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
            showBadge("Action required", ["bg-primary/10", "text-primary"], ["bg-border-light", "text-text-secondary-light", "dark:bg-border-dark"]);
          } else if (isLocked) {
            showBadge("Locked", ["bg-border-light", "text-text-secondary-light", "dark:bg-border-dark"], ["bg-primary/10", "text-primary"]);
          } else {
            showBadge("", [], ["bg-primary/10", "text-primary", "bg-border-light", "text-text-secondary-light", "dark:bg-border-dark"]);
          }
        } else {
          if (isLocked) {
            showBadge("Locked", ["bg-border-light", "text-text-secondary-light", "dark:bg-border-dark"], ["bg-primary/10", "text-primary"]);
          } else {
            showBadge("", [], ["bg-primary/10", "text-primary", "bg-border-light", "text-text-secondary-light", "dark:bg-border-dark"]);
          }
        }
      }
    });
  };

  applyBreadcrumb();

  const apiUrl = `/api/images/${imageId}?_=${Date.now()}`;
  const metaUrl = `/api/images/${imageId}/meta?_=${Date.now()}`;
  const statusUrl = `/api/statuses?_=${Date.now()}`;
  const autoActionMap = {
    UPLOAD: { event: "c2s:process_image", needsTolerance: false },
    JSON: { event: "c2s:start_sorting", needsTolerance: true },
  };
  let metaPayload = null;
  let statusLabels = {};
  let pageLoaded = false;
  const triggeredActions = new Set();

  const getNormalizedStatus = (value) =>
    (value || "").toString().trim().toUpperCase();

  const getStatusLabel = (code, fallback) => {
    const normalized = getNormalizedStatus(code);
    return statusLabels[normalized] || fallback;
  };

  const applyStatusLabels = () => {
    stageOrder = [
      { key: "upload", title: getStatusLabel("UPLOAD", "Image uploaded") },
      { key: "json", title: getStatusLabel("JSON", "JSON processed") },
      {
        key: "sort",
        title: getStatusLabel("SORT_VALIDATE", getStatusLabel("SORT", "Sorting algorithm")),
        pendingSubtitle: "Waiting for confirmation in Sorting View",
      },
      { key: "ngrams", title: getStatusLabel("NGRAMS", "N-Grams") },
      { key: "suffix", title: getStatusLabel("SUFFIX", "Suffix tree") },
    ];
  };

  const maybeStartAutoPipeline = (statusOverride) => {
    if (!pageLoaded || !metaPayload || !socket) {
      console.log("[overview] auto pipeline blocked", {
        pageLoaded,
        hasMeta: Boolean(metaPayload),
        hasSocket: Boolean(socket),
      });
      return;
    }
    const statusCode = getNormalizedStatus(
      statusOverride ?? metaPayload.status_code
    );
    console.log("[overview] auto pipeline status", statusCode);
    const action = autoActionMap[statusCode];
    if (!action || triggeredActions.has(action.event)) {
      console.log("[overview] auto pipeline no action", action);
      return;
    }
    const payload = { image_id: Number(imageId) };
    if (action.needsTolerance) {
      const tolerance = Number(metaPayload.tolerance);
      if (!Number.isFinite(tolerance) || tolerance <= 0) {
        console.log("[overview] auto pipeline invalid tolerance", metaPayload.tolerance);
        return;
      }
      payload.tolerance = tolerance;
    }
    triggeredActions.add(action.event);
    console.log("[overview] auto pipeline emit", action.event, payload);
    socket.emit(action.event, payload);
  };

  if (socket) {
    socket.on("s2c:start_sorting:response", (data) => {
      console.log("[overview] s2c:start_sorting:response", data);
      if (!data || String(data.image_id) !== String(imageId)) {
        return;
      }
      if (data.status === "success") {
        renderPipeline(data.status_code || "SORT_VALIDATE");
      }
    });

    socket.on("s2c:process_image:response", (data) => {
      console.log("[overview] s2c:process_image:response", data);
      if (!data || String(data.image_id) !== String(imageId)) {
        return;
      }
      if (data.status === "success") {
        renderPipeline(data.status_code || "JSON");
        maybeStartAutoPipeline("JSON");
      }
    });
  }

  window.addEventListener("load", () => {
    console.log("[overview] window load");
    pageLoaded = true;
    maybeStartAutoPipeline();
  });

  renderPipelineLoading();

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
      renderPipeline(data.status_code);
      hideLoading();
    })
    .catch((error) => {
      console.error(error);
      applyTitle("Papyrus konnte nicht geladen werden");
      renderPipeline();
      hideLoading();
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
        renderPipeline(meta.status_code);
      }
      maybeStartAutoPipeline();
    })
    .catch((error) => {
      console.error(error);
    });

  fetch(statusUrl, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to load status labels");
      }
      return response.json();
    })
    .then((data) => {
      const items = data.items || [];
      statusLabels = items.reduce((acc, item) => {
        const code = getNormalizedStatus(item.status_code);
        if (code && !acc[code]) {
          acc[code] = item.status || "";
        }
        return acc;
      }, {});
      statusesLoaded = true;
      applyStatusLabels();
      const nextStatus =
        pendingStatusCode ??
        (metaPayload ? metaPayload.status_code : null);
      renderPipeline(nextStatus);
    })
    .catch((error) => {
      console.error(error);
    });
});
