document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-ngram-root]");
  if (!root) {
    return;
  }

  const imageId = root.dataset.imageId;
  const imageWrapper = root.querySelector("[data-ngram-image-wrapper]");
  const imageCanvas = root.querySelector("[data-ngram-canvas]");
  const loadingOverlay = root.querySelector("[data-ngram-loading]");
  const loadingText = root.querySelector("[data-ngram-loading-text]");
  const loadingSpinner = root.querySelector("[data-ngram-loading-spinner]");

  const filterContainer = root.querySelector("[data-ngram-filters]");
  const listContainer = root.querySelector("[data-ngram-list]");
  const listLoading = root.querySelector("[data-ngram-list-loading]");
  const emptyState = root.querySelector("[data-ngram-empty]");
  const searchInput = root.querySelector("[data-ngram-search]");
  const selectedGlyphs = root.querySelector("[data-ngram-selected-glyphs]");
  const selectedUnicodes = root.querySelector("[data-ngram-selected-unicodes]");
  const selectedCount = root.querySelector("[data-ngram-selected-count]");
  const selectedLength = root.querySelector("[data-ngram-selected-length]");
  if (selectedGlyphs) {
    selectedGlyphs.style.fontFamily =
      "'Noto Sans Egyptian Hieroglyphs','Segoe UI Historic','Segoe UI Symbol','Noto Sans',sans-serif";
  }

  const OCCURRENCE_COLORS = [
    {
      fill: "rgba(134, 239, 172, 0.25)",
      stroke: "rgba(22, 163, 74, 0.9)",
    },
    {
      fill: "rgba(96, 165, 250, 0.25)",
      stroke: "rgba(59, 130, 246, 0.9)",
    },
    {
      fill: "rgba(248, 180, 180, 0.25)",
      stroke: "rgba(239, 68, 68, 0.85)",
    },
  ];

  // Match zoom sensitivity from the sort view (view size scales by 0.93 per tick).
  const ZOOM_STEP = 1 / 0.93;
  // Do not allow zooming out beyond the initial fit (100%).
  const MIN_ZOOM = 1;
  const MAX_ZOOM = 10;

  const state = {
    items: [],
    lengths: [],
    activeLength: "all",
    search: "",
    selectedId: null,
    imageMeta: null,
    baseImage: null,
    zoom: 1,
    pan: { x: 0, y: 0 },
    isPanning: false,
    panStart: null,
  };

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  const showOverlay = (message, { showSpinner = true } = {}) => {
    if (loadingOverlay) {
      loadingOverlay.classList.remove("hidden");
    }
    if (loadingText && message) {
      loadingText.textContent = message;
    }
    if (loadingSpinner) {
      loadingSpinner.classList.toggle("hidden", !showSpinner);
    }
  };

  const hideOverlay = () => {
    if (loadingOverlay) {
      loadingOverlay.classList.add("hidden");
    }
    if (loadingSpinner) {
      loadingSpinner.classList.add("hidden");
    }
  };

  const setListLoading = (loading) => {
    if (!listLoading) {
      return;
    }
    listLoading.classList.toggle("hidden", !loading);
  };

  const setEmptyMessage = (message) => {
    if (!emptyState) {
      return;
    }
    const textEl = emptyState.querySelector("p");
    if (textEl && message) {
      textEl.textContent = message;
    }
    emptyState.classList.toggle("hidden", !message);
  };

  if (!imageId || !imageCanvas) {
    showOverlay("No image selected", { showSpinner: false });
    setEmptyMessage("No image selected.");
    return;
  }

  showOverlay(" Loading workspace…");
  setListLoading(true);

  loadImage(imageId);
  loadNgrams(imageId);

  if (searchInput) {
    searchInput.addEventListener("input", (event) => {
      state.search = (event.target.value || "").toString().trim();
      renderList();
    });
  }

  function loadImage(id) {
    const apiUrl = `/api/images/${encodeURIComponent(id)}/full?_=${Date.now()}`;
    fetch(apiUrl, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load image");
        }
        return response.json();
      })
      .then((data) => {
        if (data && data.image) {
          state.zoom = 1;
          state.pan = { x: 0, y: 0 };
          applyImage(data.image);
        } else {
          throw new Error("Missing image payload");
        }
      })
      .catch((error) => {
        console.error("[ngram] load image error", error);
        showOverlay("Image could not be loaded", { showSpinner: false });
      });
  }

  function applyImage(src) {
    const img = new Image();
    img.onload = () => {
      state.imageMeta = {
        src,
        width: img.naturalWidth || img.width || 0,
        height: img.naturalHeight || img.height || 0,
      };
      state.baseImage = img;
      hideOverlay();
      renderBoundingBoxes();
    };
    img.onerror = () => {
      console.error("[ngram] failed to load image");
      showOverlay("Image could not be loaded", { showSpinner: false });
    };
    img.src = src;
  }

  function loadNgrams(id) {
    const apiUrl = `/api/images/${encodeURIComponent(id)}/ngrams?_=${Date.now()}`;
    setEmptyMessage("");

    fetch(apiUrl, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load N-grams");
        }
        return response.json();
      })
      .then((data) => {
        state.items = Array.isArray(data?.items)
          ? data.items.map(normalizePattern)
          : [];
        state.lengths = Array.isArray(data?.lengths) ? data.lengths : [];
        if (
          state.activeLength !== "all" &&
          !state.lengths.includes(Number(state.activeLength))
        ) {
          state.activeLength = "all";
        }
        if (state.items.length && !state.selectedId) {
          state.selectedId = state.items[0].id;
        }
        renderFilters();
        renderList();
      })
      .catch((error) => {
        console.error("[ngram] load ngrams error", error);
        state.items = [];
        state.lengths = [];
        renderFilters();
        renderList();
        setEmptyMessage("Failed to load N-grams.");
      })
      .finally(() => {
        setListLoading(false);
      });
  }

  function normalizePattern(item) {
    const unicodeValues = Array.isArray(item?.unicode_values)
      ? item.unicode_values
      : [];
    const unicodeLabel =
      item?.unicode_label || unicodeValues.join(" ").trim() || "";
    const symbol = item?.symbol || formatUnicodeSymbol(unicodeLabel);
    const occurrences = Array.isArray(item?.occurrences)
      ? item.occurrences
          .map(normalizeOccurrence)
          .filter(Boolean)
      : [];

    return {
      id: Number(item?.id) || 0,
      length: Number(item?.length) || 0,
      count: Number(item?.count) || 0,
      unicodeValues,
      unicodeLabel,
      symbol,
      occurrences,
    };
  }

  function normalizeOccurrence(occ) {
    if (!occ) return null;
    const bboxes = Array.isArray(occ?.bboxes)
      ? occ.bboxes
          .map((bbox) => ({
            bbox_x: Number(bbox?.bbox_x),
            bbox_y: Number(bbox?.bbox_y),
            bbox_width: Number(bbox?.bbox_width),
            bbox_height: Number(bbox?.bbox_height),
          }))
          .filter(
            (bbox) =>
              Number.isFinite(bbox.bbox_x) &&
              Number.isFinite(bbox.bbox_y) &&
              Number.isFinite(bbox.bbox_width) &&
              Number.isFinite(bbox.bbox_height),
          )
      : [];
    return {
      id: Number(occ?.id) || 0,
      glyphIds: Array.isArray(occ?.glyph_ids)
        ? occ.glyph_ids.map((gid) => Number(gid)).filter(Number.isFinite)
        : [],
      bboxes,
    };
  }

  function renderFilters() {
    if (!filterContainer) {
      return;
    }
    filterContainer.innerHTML = "";
    const options = ["all", ...state.lengths];
    options.forEach((option) => {
      const isAll = option === "all";
      const label = isAll ? "All" : `n = ${option}`;
      const isActive =
        state.activeLength === option ||
        (!isAll && Number(state.activeLength) === Number(option));
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.ngramFilter = String(option);
      button.setAttribute("aria-pressed", isActive ? "true" : "false");
      button.className = [
        "flex h-7 cursor-pointer shrink-0 items-center justify-center gap-x-2 rounded-lg px-3 text-sm font-semibold leading-normal transition",
        isActive
          ? "bg-primary/20 text-primary border border-primary/30"
          : "bg-gray-200 dark:bg-gray-700 text-text-secondary-light dark:text-text-secondary-dark hover:bg-gray-300 dark:hover:bg-gray-600",
      ].join(" ");
      button.textContent = label;
      button.addEventListener("click", () => {
        state.activeLength = isAll ? "all" : Number(option);
        renderFilters();
        renderList();
      });
      filterContainer.appendChild(button);
    });
    updateFilterCount(getFilteredItems().length);
  }

  function renderList() {
    if (!listContainer) {
      return;
    }
    listContainer.innerHTML = "";

    const filtered = getFilteredItems();
    updateFilterCount(filtered.length);
    if (!filtered.length) {
      const hasData = state.items.length > 0;
      setEmptyMessage(
        hasData
          ? "No patterns match the current filters."
          : "No N-grams available yet.",
      );
      state.selectedId = null;
      renderSelection();
      return;
    }
    setEmptyMessage("");

    if (!filtered.some((item) => item.id === state.selectedId)) {
      state.selectedId = filtered[0].id;
    }

    filtered.forEach((item) => {
      const card = createPatternCard(item);
      const isSelected = item.id === state.selectedId;
      if (isSelected) {
        card.classList.add(
          "border-primary",
          "bg-primary/5",
          "shadow-md",
          "dark:border-primary",
          "dark:bg-primary/10",
        );
      }
      card.addEventListener("click", () => {
        state.selectedId = item.id;
        renderList();
        renderSelection();
      });
      listContainer.appendChild(card);
    });
    renderSelection();
  }

  function getFilteredItems() {
    const active = state.activeLength;
    const term = state.search.toLowerCase();
    return state.items.filter((item) => {
      const matchesLength =
        active === "all" || Number(item.length) === Number(active);
      const matchesSearch =
        !term ||
        item.unicodeLabel.toLowerCase().includes(term) ||
        (item.symbol || "").toLowerCase().includes(term);
      return matchesLength && matchesSearch;
    });
  }

  function updateFilterCount(count) {
    const counter = root.querySelector("[data-ngram-filter-count]");
    if (counter) {
      counter.textContent = Number(count) || 0;
    }
  }

  function createPatternCard(item) {
    const card = document.createElement("div");
    card.className =
      "p-3 rounded-lg border border-border-light dark:border-border-dark bg-white/80 dark:bg-gray-900/60 hover:border-primary/60 transition shadow-sm cursor-pointer";
    card.dataset.ngramPattern = String(item.id);

    const glyphText = document.createElement("div");
    glyphText.className =
      "text-xl font-semibold tracking-widest text-text-light dark:text-text-dark leading-tight whitespace-nowrap overflow-x-auto overflow-y-hidden custom-scrollbar cursor-pointer";
    glyphText.style.fontFamily =
      "'Noto Sans Egyptian Hieroglyphs','Segoe UI Historic','Segoe UI Symbol','Noto Sans',sans-serif";
    setGlyphContent(
      glyphText,
      item.unicodeValues,
      item.symbol,
      item.unicodeLabel,
    );

    const divider = document.createElement("div");
    divider.className =
      "border-t border-border-light dark:border-border-dark my-2";

    const statsRow = document.createElement("div");
    statsRow.className =
      "flex items-center gap-2 text-xs text-text-secondary-light dark:text-text-secondary-dark";

    const lengthLabel = document.createElement("span");
    lengthLabel.className =
      "rounded-full bg-primary/10 text-primary px-2 py-0.5 font-semibold";
    lengthLabel.textContent = `n = ${item.length}`;

    const occLabel = document.createElement("span");
    occLabel.className =
      "rounded-full bg-border-light dark:bg-border-dark px-2 py-0.5 font-semibold text-text-secondary-light dark:text-text-secondary-dark";
    occLabel.textContent = `Occurrences: ${
      Number.isFinite(item.count)
        ? item.count.toLocaleString()
        : item.count || "—"
    }`;

    statsRow.appendChild(lengthLabel);
    statsRow.appendChild(occLabel);

    card.appendChild(glyphText);
    card.appendChild(divider);
    card.appendChild(statsRow);

    return card;
  }

  function getSelectedItem() {
    return state.items.find((item) => item.id === state.selectedId);
  }

  function renderSelection() {
    const selection = getSelectedItem();
    if (
      !selectedGlyphs ||
      !selectedUnicodes ||
      !selectedCount ||
      !selectedLength
    ) {
      return;
    }
    if (!selection) {
      selectedGlyphs.textContent = "Select a pattern from the sidebar";
      selectedUnicodes.textContent = "—";
      selectedCount.textContent = "Occurrences: —";
      selectedLength.textContent = "n = —";
      renderBoundingBoxes();
      return;
    }

    selectedGlyphs.textContent = "";
    setGlyphContent(
      selectedGlyphs,
      selection.unicodeValues,
      selection.symbol,
      selection.unicodeLabel,
    );
    selectedUnicodes.innerHTML = "";
    const items =
      Array.isArray(selection.unicodeValues) && selection.unicodeValues.length
        ? selection.unicodeValues
        : [selection.unicodeLabel || "—"];
    items.forEach((val) => {
      const row = document.createElement("p");
      row.className =
        "text-xs font-mono text-text-secondary-light dark:text-text-secondary-dark whitespace-nowrap";
      row.textContent = val || "—";
      selectedUnicodes.appendChild(row);
    });
    selectedCount.textContent = Number.isFinite(selection.count)
      ? `Occurrences: ${selection.count.toLocaleString()}`
      : `Occurrences: ${selection.count || "—"}`;
    selectedLength.textContent = `n = ${selection.length || "—"}`;

    renderBoundingBoxes();
  }

  function setGlyphContent(
    element,
    unicodeValues,
    fallbackSymbol,
    fallbackLabel,
  ) {
    if (!element) return;
    element.innerHTML = "";
    const values =
      Array.isArray(unicodeValues) && unicodeValues.length ? unicodeValues : [];
    if (!values.length) {
      const fallback = fallbackSymbol || fallbackLabel || "";
      if (fallback) {
        element.textContent = fallback;
        return;
      }
      const unknown = document.createElement("span");
      unknown.textContent = "?";
      unknown.className = "text-red-500 font-semibold";
      element.appendChild(unknown);
      return;
    }
    const frag = document.createDocumentFragment();
    values.forEach((val) => {
      const span = document.createElement("span");
      span.className = "inline-block";
      const code = (val || "").toString().trim().replace(/^U\+/i, "");
      if (!code) {
        span.textContent = "?";
        span.classList.add("text-red-500", "font-semibold");
      } else {
        const cp = parseInt(code, 16);
        if (Number.isNaN(cp)) {
          span.textContent = "?";
          span.classList.add("text-red-500", "font-semibold");
        } else {
          try {
            span.textContent = String.fromCodePoint(cp);
          } catch (err) {
            span.textContent = "?";
            span.classList.add("text-red-500", "font-semibold");
          }
        }
      }
      frag.appendChild(span);
    });
    element.appendChild(frag);
  }

  function formatUnicodeSymbol(unicodeString) {
    if (!unicodeString || typeof unicodeString !== "string") {
      return "";
    }
    const parts = unicodeString
      .trim()
      .split(/\s+/)
      .map((part) => part.replace(/^U\+/i, ""))
      .filter(Boolean);
    if (!parts.length) {
      return "";
    }
    try {
      return parts
        .map((hex) => String.fromCodePoint(parseInt(hex, 16)))
        .join("");
    } catch (err) {
      return "";
    }
  }

  function renderBoundingBoxes() {
    if (!imageCanvas) {
      return;
    }
    const ctx = imageCanvas.getContext("2d");
    if (!ctx) {
      return;
    }

    const rect = imageCanvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    if (!width || !height) {
      return;
    }
    const dpr = window.devicePixelRatio || 1;
    const pixelWidth = Math.max(1, Math.round(width * dpr));
    const pixelHeight = Math.max(1, Math.round(height * dpr));
    if (
      imageCanvas.width !== pixelWidth ||
      imageCanvas.height !== pixelHeight
    ) {
      imageCanvas.width = pixelWidth;
      imageCanvas.height = pixelHeight;
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, imageCanvas.width, imageCanvas.height);
    ctx.save();
    ctx.scale(dpr, dpr);

    const selection = getSelectedItem();
    const occurrences = Array.isArray(selection?.occurrences)
      ? selection.occurrences
      : [];
    const imgWidth = Number(state.imageMeta?.width) || 0;
    const imgHeight = Number(state.imageMeta?.height) || 0;
    const baseImage = state.baseImage;

    if (baseImage && imgWidth && imgHeight) {
      const baseScale = Math.max(width / imgWidth, height / imgHeight) || 1;
      const scale = baseScale * (state.zoom || 1);
      const drawWidth = imgWidth * scale;
      const drawHeight = imgHeight * scale;
      const maxPanX = Math.max(0, (drawWidth - width) / 2);
      const maxPanY = Math.max(0, (drawHeight - height) / 2);
      const panX = clamp(state.pan?.x || 0, -maxPanX, maxPanX);
      const panY = clamp(state.pan?.y || 0, -maxPanY, maxPanY);
      state.pan = { x: panX, y: panY };
      const offsetX = (width - drawWidth) / 2 + panX;
      const offsetY = (height - drawHeight) / 2 + panY;

      ctx.drawImage(baseImage, offsetX, offsetY, drawWidth, drawHeight);

      if (occurrences.length) {
        occurrences.forEach((occ, idx) => {
          const color =
            OCCURRENCE_COLORS[
              ((idx % OCCURRENCE_COLORS.length) + OCCURRENCE_COLORS.length) %
                OCCURRENCE_COLORS.length
            ] || OCCURRENCE_COLORS[0];
          const fill = color.fill;
          const stroke = color.stroke;
          (occ.bboxes || []).forEach((bbox) => {
            const left = offsetX + bbox.bbox_x * scale;
            const top = offsetY + bbox.bbox_y * scale;
            const boxWidth = bbox.bbox_width * scale;
            const boxHeight = bbox.bbox_height * scale;
            ctx.fillStyle = fill;
            ctx.strokeStyle = stroke;
            ctx.lineWidth = 2;
            ctx.fillRect(left, top, boxWidth, boxHeight);
            ctx.strokeRect(left, top, boxWidth, boxHeight);
          });
        });
      }
    }

    ctx.restore();
  }

  function handleCanvasZoom(event) {
    if (!imageCanvas || !state.imageMeta) {
      return;
    }
    const rect = imageCanvas.getBoundingClientRect();
    const imgWidth = Number(state.imageMeta?.width) || 0;
    const imgHeight = Number(state.imageMeta?.height) || 0;
    if (!imgWidth || !imgHeight) {
      return;
    }

    const baseScale = Math.max(rect.width / imgWidth, rect.height / imgHeight) || 1;
    const currentScale = baseScale * (state.zoom || 1);
    const drawWidth = imgWidth * currentScale;
    const drawHeight = imgHeight * currentScale;
    const panX = state.pan?.x || 0;
    const panY = state.pan?.y || 0;
    const offsetX = (rect.width - drawWidth) / 2 + panX;
    const offsetY = (rect.height - drawHeight) / 2 + panY;

    const step = ZOOM_STEP || 1.07;
    const factor = event.deltaY < 0 ? step : 1 / step;
    const newZoom = clamp((state.zoom || 1) * factor, MIN_ZOOM, MAX_ZOOM);
    const newScale = baseScale * newZoom;

    const pointerX = event.clientX - rect.left;
    const pointerY = event.clientY - rect.top;
    const imgX = (pointerX - offsetX) / currentScale;
    const imgY = (pointerY - offsetY) / currentScale;

    const newDrawWidth = imgWidth * newScale;
    const newDrawHeight = imgHeight * newScale;
    const newBaseOffsetX = (rect.width - newDrawWidth) / 2;
    const newBaseOffsetY = (rect.height - newDrawHeight) / 2;
    const newOffsetX = pointerX - imgX * newScale;
    const newOffsetY = pointerY - imgY * newScale;

    const nextPanX = newOffsetX - newBaseOffsetX;
    const nextPanY = newOffsetY - newBaseOffsetY;

    state.zoom = newZoom;
    state.pan = { x: nextPanX, y: nextPanY };
    renderBoundingBoxes();
  }

  function handlePanStart(event) {
    if (event.button !== 0 || !imageCanvas || !state.imageMeta) {
      return;
    }
    event.preventDefault();
    state.isPanning = true;
    state.panStart = {
      x: event.clientX,
      y: event.clientY,
      pan: { ...(state.pan || { x: 0, y: 0 }) },
    };
  }

  function handlePanMove(event) {
    if (!state.isPanning || !state.panStart) {
      return;
    }
    event.preventDefault();
    const dx = event.clientX - state.panStart.x;
    const dy = event.clientY - state.panStart.y;
    state.pan = {
      x: (state.panStart.pan.x || 0) + dx,
      y: (state.panStart.pan.y || 0) + dy,
    };
    renderBoundingBoxes();
  }

  function handlePanEnd() {
    state.isPanning = false;
    state.panStart = null;
  }

  if (imageCanvas) {
    imageCanvas.addEventListener("mousedown", handlePanStart);
    imageCanvas.addEventListener("mousemove", handlePanMove);
    imageCanvas.addEventListener("mouseup", handlePanEnd);
    imageCanvas.addEventListener("mouseleave", handlePanEnd);

    imageCanvas.addEventListener(
      "wheel",
      (event) => {
        if (!state.baseImage || !state.imageMeta) {
          return;
        }
        event.preventDefault();
        handleCanvasZoom(event);
      },
      { passive: false },
    );
  }

  window.addEventListener("resize", () => renderBoundingBoxes());
});
