document.addEventListener("DOMContentLoaded", () => {
  const overviewRoot = document.querySelector("[data-overview-root]");
  if (!overviewRoot) {
    return;
  }

  const imageId = overviewRoot.dataset.imageId;
  if (!imageId) {
    return;
  }

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

  const stageOrder = [
    { key: "upload", title: "Image uploaded" },
    { key: "json", title: "JSON processed" },
    { key: "sort", title: "Sorting algorithm", pendingSubtitle: "Waiting for confirmation in Sorting View" },
    { key: "ngrams", title: "N-Grams" },
    { key: "suffix", title: "Suffix tree" },
  ];

  const statusMapping = {
    UPLOAD: { upload: "done", json: "running", sort: "waiting", ngrams: "waiting", suffix: "waiting" },
    JSON: { upload: "done", json: "done", sort: "running", ngrams: "waiting", suffix: "waiting" },
    SORT_VALIDATE: { upload: "done", json: "done", sort: "pending", ngrams: "waiting", suffix: "waiting" },
    SORT: { upload: "done", json: "done", sort: "done", ngrams: "running", suffix: "waiting" },
    NGRAMS: { upload: "done", json: "done", sort: "done", ngrams: "done", suffix: "running" },
    SUFFIX: { upload: "done", json: "done", sort: "done", ngrams: "done", suffix: "done" },
  };

  const renderPipeline = (statusCode) => {
    if (!pipelineContainer) {
      return;
    }
    const normalized = (statusCode || "").toUpperCase();
    const states = statusMapping[normalized] || statusMapping.UPLOAD;
    const html = stageOrder
      .map((stage) => renderStage(stage, states[stage.key] || "waiting"))
      .join("");
    pipelineContainer.innerHTML = html;
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

  applyBreadcrumb();

  const apiUrl = `/api/images/${imageId}?_=${Date.now()}`;

  fetch(apiUrl, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to load papyrus data");
      }
      return response.json();
    })
    .then((data) => {
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
});
