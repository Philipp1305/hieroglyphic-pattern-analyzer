document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-glyph-root]");
  if (!root) return;

  const imageId = root.dataset.imageId;
  const loadingOverlay = root.querySelector("[data-glyph-loading]");
  const loadingText = root.querySelector("[data-glyph-loading-text]");
  const loadingSpinner = root.querySelector("[data-glyph-loading-spinner]");
  const listContainer = root.querySelector("[data-glyph-list]");
  const emptyState = root.querySelector("[data-glyph-empty]");
  const searchInput = root.querySelector("[data-glyph-search]");
  const totalBadge = root.querySelector("[data-glyph-total]");
  const minimapCount = root.querySelector("[data-glyph-minimap-count]");
  const canvas = root.querySelector("[data-glyph-canvas]");
  const contextListPrev = root.querySelector("[data-glyph-prev-list]");
  const contextListNext = root.querySelector("[data-glyph-next-list]");
  const posStartVal = root.querySelector("[data-glyph-pos-start-val]");
  const posMidVal = root.querySelector("[data-glyph-pos-mid-val]");
  const posEndVal = root.querySelector("[data-glyph-pos-end-val]");
  const posStartBar = root.querySelector("[data-glyph-pos-start-bar]");
  const posMidBar = root.querySelector("[data-glyph-pos-mid-bar]");
  const posEndBar = root.querySelector("[data-glyph-pos-end-bar]");
  const posMedian = root.querySelector("[data-glyph-pos-median]");
  const posStd = root.querySelector("[data-glyph-pos-std]");
  const posHistogram = root.querySelector("[data-glyph-pos-histogram]");
  const posBinLabel = root.querySelector("[data-glyph-pos-binlabel]");
  const contextList = root.querySelector("[data-glyph-context-list]");

  const state = {
    glyphs: {},
    groups: [],
    search: "",
    activeKey: null,
    baseImage: null,
    imageMeta: null,
    zoom: 1,
    pan: { x: 0, y: 0 },
    isPanning: false,
    panStart: null,
  };

  const unicodeToSymbol = (value = "") => {
    const cleaned = value.toString().trim().replace(/^U\+/i, "");
    if (!cleaned) return "";
    try {
      const codepoint = parseInt(cleaned, 16);
      if (Number.isNaN(codepoint)) return "";
      return String.fromCodePoint(codepoint);
    } catch (err) {
      return "";
    }
  };

  const unicodeArrayToSymbols = (arr = []) =>
    arr
      .map((u) => unicodeToSymbol(u || ""))
      .filter(Boolean)
      .join("");

  const showOverlay = (message, { spinner = true } = {}) => {
    if (!loadingOverlay) return;
    loadingOverlay.classList.remove("hidden");
    if (loadingText && message) loadingText.textContent = message;
    if (loadingSpinner) loadingSpinner.classList.toggle("hidden", !spinner);
  };
  const hideOverlay = () => {
    if (!loadingOverlay) return;
    loadingOverlay.classList.add("hidden");
    if (loadingSpinner) loadingSpinner.classList.add("hidden");
  };

  if (!imageId) {
    showOverlay("No image selected", { spinner: false });
    return;
  }

  showOverlay("Loading glyphs…");
  Promise.all([loadImage(imageId), loadStats(imageId)])
    .then(() => {
      renderList();
      pickDefault();
      hideOverlay();
    })
    .catch((error) => {
      console.error("[glyphes] failed to load", error);
      showOverlay("Data could not be loaded", { spinner: false });
    });

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      state.search = (e.target.value || "").toString().trim().toLowerCase();
      renderList();
    });
  }

  function loadStats(id) {
    return fetch(
      `/api/glyphes/${encodeURIComponent(id)}/stats?_=${Date.now()}`,
      {
        cache: "no-store",
      },
    )
      .then((r) => {
        if (!r.ok) throw new Error("glyph stats fetch failed");
        return r.json();
      })
      .then((payload) => {
        state.glyphs =
          typeof payload?.glyphs === "object" && payload.glyphs !== null
            ? payload.glyphs
            : {};
        state.groups = Array.isArray(payload?.groups) ? payload.groups : [];
        state.totalTypes = payload?.types || state.groups.length;
        if (!state.activeKey && state.groups.length) {
          state.activeKey = state.groups[0].key;
        }
        if (totalBadge) totalBadge.textContent = `${state.totalTypes} Glyphes`;
      });
  }

  function loadImage(id) {
    return fetch(`/api/images/${encodeURIComponent(id)}/full?_=${Date.now()}`, {
      cache: "no-store",
    })
      .then((r) => {
        if (!r.ok) throw new Error("image fetch failed");
        return r.json();
      })
      .then((payload) => {
        const src = payload?.image;
        return new Promise((resolve, reject) => {
          const img = new Image();
          img.onload = () => {
            state.baseImage = img;
            state.imageMeta = {
              width: img.naturalWidth || img.width || 0,
              height: img.naturalHeight || img.height || 0,
            };
            resolve();
          };
          img.onerror = reject;
          img.src = src;
        });
      });
  }

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  function renderList() {
    if (!listContainer) return;
    listContainer.innerHTML = "";
    const search = state.search;
    const filtered = state.groups.filter((g) => {
      if (!search) return true;
      return (
        g.key.toLowerCase().includes(search) ||
        (g.symbol || "").toLowerCase().includes(search)
      );
    });

    if (emptyState) emptyState.classList.toggle("hidden", filtered.length > 0);

    filtered.forEach((group) => {
      const isActive = group.key === state.activeKey;
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.glyphKey = group.key;
      button.className =
        "w-full rounded-xl border border-border-light dark:border-border-dark bg-white/70 dark:bg-gray-900/60 px-3 py-2 text-left transition shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary";
      if (isActive) {
        button.classList.add(
          "border-primary",
          "bg-primary/5",
          "shadow-md",
          "ring-2",
          "ring-primary/30",
          "dark:border-primary",
          "dark:bg-primary/10",
        );
      } else {
        button.classList.add(
          "hover:border-primary",
          "hover:ring-1",
          "hover:ring-primary/20",
        );
      }

      const badgeContent =
        group.symbol && group.symbol.trim().length
          ? group.symbol
          : group.code || group.key || "?";

      const badgeIsCode = !group.symbol || !group.symbol.trim().length;

      button.innerHTML = `
        <div class="flex items-center justify-between gap-3">
          <div class="flex items-center gap-3 min-w-0">
            <div class="h-10 w-10 rounded-lg bg-card-light dark:bg-card-dark border border-border-light dark:border-border-dark flex items-center justify-center text-2xl"
              style="font-family: 'Noto Sans Egyptian Hieroglyphs','Segoe UI Historic','Segoe UI Symbol','Noto Sans',sans-serif">
              ${
                badgeIsCode
                  ? `<span class="inline-flex items-center justify-center text-red-600 dark:text-red-300 text-[11px] px-1.5 py-0.5 rounded border border-red-200 dark:border-red-500/60 bg-red-50 dark:bg-red-900/30 leading-none font-semibold">${badgeContent}</span>`
                  : badgeContent
              }
            </div>
            <div class="min-w-0">
              <p class="text-sm font-semibold text-text-light dark:text-text-dark truncate">${group.key}</p>
              <p class="text-xs text-text-secondary-light dark:text-text-secondary-dark truncate">${group.unicode || group.code || ""}</p>
            </div>
          </div>
          <span class="text-xs font-semibold rounded-full px-2 py-1 bg-primary/10 text-primary" title="Anzahl der Vorkommen">${group.count}</span>
        </div>
      `;

      button.addEventListener("click", () => {
        state.activeKey = group.key;
        renderList();
        renderMinimap();
        renderTransitions();
        renderPositions();
        renderContexts();
      });

      listContainer.appendChild(button);
    });
  }

  function pickDefault() {
    if (!state.activeKey && state.groups.length) {
      state.activeKey = state.groups[0].key;
    }
    renderMinimap();
    renderTransitions();
    renderPositions();
    renderContexts();
  }

  // Canvas interactions
  if (canvas) {
    canvas.addEventListener("mousedown", startPan);
    canvas.addEventListener("mousemove", movePan);
    window.addEventListener("mouseup", endPan);
    canvas.addEventListener("wheel", onWheel, { passive: false });
  }

  function startPan(event) {
    event.preventDefault();
    state.isPanning = true;
    state.panStart = { x: event.clientX, y: event.clientY };
  }
  function movePan(event) {
    if (!state.isPanning || !state.panStart) return;
    const dx = event.clientX - state.panStart.x;
    const dy = event.clientY - state.panStart.y;
    state.pan.x += dx;
    state.pan.y += dy;
    state.panStart = { x: event.clientX, y: event.clientY };
    renderMinimap();
  }
  function endPan() {
    state.isPanning = false;
    state.panStart = null;
  }
  function onWheel(event) {
    if (!canvas) return;
    event.preventDefault();
    const delta = -event.deltaY;
    const factor = delta > 0 ? 1.05 : 0.95;
    state.zoom = clamp(state.zoom * factor, 0.6, 8);
    renderMinimap();
  }

  function renderMinimap() {
    if (!canvas || !state.baseImage || !state.imageMeta) return;
    const ctx = canvas.getContext("2d");
    const { clientWidth, clientHeight } = canvas.parentElement;
    canvas.width = clientWidth;
    canvas.height = clientHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const imgW = state.imageMeta.width;
    const imgH = state.imageMeta.height;
    if (!imgW || !imgH) return;

    const fitScale = Math.min(canvas.width / imgW, canvas.height / imgH);
    const scale = fitScale * state.zoom;
    const drawW = imgW * scale;
    const drawH = imgH * scale;
    const offsetX = (canvas.width - drawW) / 2 + state.pan.x;
    const offsetY = (canvas.height - drawH) / 2 + state.pan.y;

    ctx.save();
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(state.baseImage, offsetX, offsetY, drawW, drawH);

    const group = state.groups.find((g) => g.key === state.activeKey);
    const ids = group ? group.ids : [];
    if (minimapCount) minimapCount.textContent = `${ids.length} occurences`;

    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(59, 130, 246, 0.9)";
    ctx.fillStyle = "rgba(59, 130, 246, 0.18)";

    ids.forEach((gid) => {
      const meta = state.glyphs[String(gid)] || {};
      const x = Number(meta.x);
      const y = Number(meta.y);
      const w = Number(meta.width);
      const h = Number(meta.height);
      if ([x, y, w, h].some((v) => Number.isNaN(v))) return;
      const rx = offsetX + x * scale;
      const ry = offsetY + y * scale;
      const rw = w * scale;
      const rh = h * scale;
      ctx.beginPath();
      ctx.rect(rx, ry, rw, rh);
      ctx.fill();
      ctx.stroke();
    });
    ctx.restore();
  }

  function renderTransitions() {
    if (!contextListPrev || !contextListNext) return;
    contextListPrev.innerHTML = "";
    contextListNext.innerHTML = "";

    const group = state.groups.find((g) => g.key === state.activeKey);
    if (!group) return;
    const prevCounts = group.transitions?.prev || [];
    const nextCounts = group.transitions?.next || [];

    const renderListInner = (target, list) => {
      target.innerHTML = "";
      const top = list;
      const max = top.length ? top[0].count : 0;
      top.forEach(({ key, count }) => {
        const metaEntry = state.groups.find((g) => g.key === key);
        const symbol = metaEntry?.symbol || key;
        const row = document.createElement("div");
        row.className =
          "flex items-center gap-2 rounded-lg border border-border-light dark:border-border-dark px-2 py-1 bg-white/60 dark:bg-gray-900/60";
        const barWidth = max ? Math.round((count / max) * 100) : 0;
        row.innerHTML = `
          <div class="flex items-center gap-2 min-w-0">
            <span class="h-8 w-8 rounded-md bg-card-light dark:bg-card-dark border border-border-light dark:border-border-dark flex items-center justify-center text-lg"
              style="font-family: 'Noto Sans Egyptian Hieroglyphs','Segoe UI Historic','Segoe UI Symbol','Noto Sans',sans-serif">
              ${symbol}
            </span>
            <div class="min-w-0">
              <p class="text-sm font-semibold truncate">${key}</p>
              <div class="h-1.5 rounded-full bg-border-light dark:bg-border-dark mt-1">
                <div class="h-full rounded-full bg-primary" style="width:${barWidth}%"></div>
              </div>
            </div>
          </div>
          <span class="text-xs font-semibold text-text-secondary-light dark:text-text-secondary-dark">${count}</span>
        `;
        target.appendChild(row);
      });
      if (!top.length) {
        const empty = document.createElement("p");
        empty.className =
          "text-xs text-text-secondary-light dark:text-text-secondary-dark";
        empty.textContent = "No data.";
        target.appendChild(empty);
      }
    };

    renderListInner(contextListPrev, prevCounts);
    renderListInner(contextListNext, nextCounts);
  }

  function renderPositions() {
    const group = state.groups.find((g) => g.key === state.activeKey);
    if (!group) return;
    const positions = group.positions || { start: 0, mid: 0, end: 0, bins: [] };
    const start = positions.start || 0;
    const mid = positions.mid || 0;
    const end = positions.end || 0;
    const total = start + mid + end || 1;
    const pct = (n) => Math.round((n / total) * 100);
    const setVal = (el, value) => {
      if (el) el.textContent = `${value}%`;
    };
    const setBar = (el, value) => {
      if (el) el.style.width = `${value}%`;
    };

    setVal(posStartVal, pct(start));
    setVal(posMidVal, pct(mid));
    setVal(posEndVal, pct(end));
    setBar(posStartBar, pct(start));
    setBar(posMidBar, pct(mid));
    setBar(posEndBar, pct(end));

    const bins = Array.isArray(positions.bins) ? positions.bins : [];
    const binCount = bins.length || 0;
    const effectiveBinCount = binCount || 12;
    const totalBins = bins.reduce((sum, v) => sum + v, 0);

    const binCenters = binCount ? bins.map((_, i) => (i + 0.5) / binCount) : [];

    const medianVal = (() => {
      if (!totalBins || !binCount) return null;
      const target = totalBins / 2;
      let acc = 0;
      for (let i = 0; i < binCount; i++) {
        acc += bins[i];
        if (acc >= target) return binCenters[i];
      }
      return binCenters[binCount - 1] || null;
    })();

    if (posMedian)
      posMedian.textContent =
        medianVal === null ? "—" : `${Math.round(medianVal * 100)}%`;

    const stdVal = (() => {
      if (!totalBins || !binCount) return null;
      const mean =
        bins.reduce((s, v, i) => s + v * binCenters[i], 0) / totalBins;
      const variance =
        bins.reduce((s, v, i) => s + v * Math.pow(binCenters[i] - mean, 2), 0) /
        totalBins;
      return Math.sqrt(variance);
    })();

    if (posStd)
      posStd.textContent =
        stdVal === null ? "—" : `±${Math.round(stdVal * 100)}%`;

    if (posBinLabel) posBinLabel.textContent = `${effectiveBinCount} bins`;

    if (posHistogram) {
      posHistogram.innerHTML = "";
      const dataBins = binCount ? bins : new Array(effectiveBinCount).fill(0);
      const maxBin = Math.max(...dataBins, 1);
      dataBins.forEach((val, idx) => {
        const bar = document.createElement("div");
        const heightPct = Math.round((val / maxBin) * 100);
        bar.className =
          "relative flex h-full flex-col items-center justify-end text-[10px] text-text-secondary-light dark:text-text-secondary-dark";
        bar.innerHTML = `
          <div class="w-full rounded-t bg-primary/70 dark:bg-primary" style="height: ${
            heightPct > 0 ? heightPct : 6
          }%"></div>
          <span class="mt-1 font-semibold">${val}</span>
          <span class="opacity-70">${idx + 1}</span>
        `;
        posHistogram.appendChild(bar);
      });
    }
  }

  function renderContexts() {
    if (!contextList) return;
    contextList.innerHTML = "";
    const group = state.groups.find((g) => g.key === state.activeKey);
    if (!group) return;
    const top = Array.isArray(group.patterns) ? group.patterns : [];

    top.forEach(({ id, label, count, length, codes, unicode }) => {
      const symbols = unicodeArrayToSymbols(unicode || []);
      const chipContent =
        symbols || codes?.join(" ") || label || `Pattern ${id}`;
      const chipIsCode = !symbols;
      const row = document.createElement("div");
      row.className =
        "flex items-center justify-between gap-3 rounded-lg border border-border-light dark:border-border-dark bg-white/70 dark:bg-gray-900/60 px-3 py-2";
      row.innerHTML = `
        <div class="min-w-0">
          <p class="text-sm font-semibold truncate" style="font-family: 'Noto Sans Egyptian Hieroglyphs','Segoe UI Historic','Segoe UI Symbol','Noto Sans',sans-serif">
            ${
              chipIsCode
                ? `<span class="inline-flex items-center justify-center text-red-600 dark:text-red-300 text-[11px] px-1.5 py-0.5 rounded border border-red-200 dark:border-red-500/60 bg-red-50 dark:bg-red-900/30 leading-none font-semibold">${chipContent}</span>`
                : chipContent
            }
          </p>
          <p class="text-xs text-text-secondary-light dark:text-text-secondary-dark truncate">n = ${length || "—"} · ${codes?.join(" ") || ""}</p>
        </div>
        <span class="text-xs font-bold text-primary">×${count}</span>
      `;
      contextList.appendChild(row);
    });

    if (!top.length) {
      const empty = document.createElement("p");
      empty.className =
        "text-xs text-text-secondary-light dark:text-text-secondary-dark";
      empty.textContent = "No patterns found.";
      contextList.appendChild(empty);
    }
  }
});
