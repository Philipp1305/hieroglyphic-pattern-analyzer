document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-suffix-root]");
  if (!root) return;

  const imageId = root.dataset.imageId;
  const loadingOverlay = root.querySelector("[data-suffix-loading]");
  const loadingText = root.querySelector("[data-suffix-loading-text]");
  const loadingSpinner = root.querySelector("[data-suffix-loading-spinner]");

  const stableBody = root.querySelector("[data-suffix-stable-body]");
  const stemBody = root.querySelector("[data-suffix-stem-body]");
  const prefixBody = root.querySelector("[data-suffix-prefix-body]");
  const suffixBody = root.querySelector("[data-suffix-suffix-body]");

  const glyphFont =
    "'Noto Sans Egyptian Hieroglyphs','Segoe UI Historic','Segoe UI Symbol','Noto Sans',sans-serif";

  initTooltips();

  const state = {
    stable: [],
    stems: [],
    prefixes: [],
    suffixes: [],
  };

  const showOverlay = (message = "", { spinner = true } = {}) => {
    if (!loadingOverlay) return;
    loadingOverlay.classList.remove("hidden");
    if (loadingText) loadingText.textContent = message;
    if (loadingSpinner) loadingSpinner.classList.toggle("hidden", !spinner);
  };

  const hideOverlay = () => {
    if (!loadingOverlay) return;
    loadingOverlay.classList.add("hidden");
  };

  if (!imageId) {
    showOverlay("No image selected", { spinner: false });
    return;
  }

  showOverlay("Loading structure…");
  Promise.all([
    fetchJson(`/api/images/${encodeURIComponent(imageId)}/structure/stable_sequences`),
    fetchJson(`/api/images/${encodeURIComponent(imageId)}/structure/stable_stems`),
    fetchJson(`/api/images/${encodeURIComponent(imageId)}/structure/prefixes`),
    fetchJson(`/api/images/${encodeURIComponent(imageId)}/structure/suffixes`),
  ])
    .then(([stable, stems, prefixes, suffixes]) => {
      state.stable = stable?.items ?? [];
      state.stems = stems?.items ?? [];
      state.prefixes = prefixes?.items ?? [];
      state.suffixes = suffixes?.items ?? [];
      renderAll();
      hideOverlay();
    })
    .catch((err) => {
      console.error("[structure] load failed", err);
      showOverlay("Failed to load data", { spinner: false });
    });

  function fetchJson(url) {
    return fetch(`${url}?_=${Date.now()}`, { cache: "no-store" }).then((res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    });
  }

  function renderAll() {
    renderStable();
    renderStems();
    renderPrefixSuffix(prefixBody, state.prefixes);
    renderPrefixSuffix(suffixBody, state.suffixes);
  }

  function renderStable() {
    if (!stableBody) return;
    stableBody.innerHTML = "";
    const rows = (state.stable || []).slice(0, 10);

    if (!rows.length) {
      const empty = document.createElement("tr");
      empty.innerHTML = `
        <td class="px-4 py-4 text-sm text-slate-500 dark:text-slate-300" colspan="3">
          No pattern found.
        </td>`;
      stableBody.appendChild(empty);
      return;
    }

    rows.forEach((row) => {
      const tr = document.createElement("tr");
      tr.className =
        "hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors";
      const seqCell = buildSequenceCell(row);
      const count = formatInt(row.count);

      tr.innerHTML = `
        <td class="px-4 py-3 align-top">${seqCell}</td>
        <td class="px-4 py-3 text-center text-sm font-semibold">${count}</td>
        <td class="px-4 py-3 text-center text-xs text-slate-400">—</td>
      `;
      stableBody.appendChild(tr);
    });
  }

  function renderStems() {
    if (!stemBody) return;
    stemBody.innerHTML = "";
    const stems = state.stems || [];
    const maxStability = getMax(stems, "stability_score");
    const maxProductivity = getMax(stems, "productivity");
    const maxBoundary = getMax(stems, "boundary_strength");

    stems.forEach((row) => {
      const tr = document.createElement("tr");
      tr.className =
        "hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors";
      const seqCell = buildSequenceCell(row);
      tr.innerHTML = `
        <td class="px-4 py-3 align-top">${seqCell}</td>
        <td class="px-4 py-3 text-center text-sm font-semibold">${formatInt(
          row.count
        )}</td>
        <td class="px-4 py-3 text-sm">${renderMetricCell(
          row.stability_score,
          maxStability,
          {
            formatter: formatFloat,
            gradient: "from-amber-400 to-orange-500",
            label: "Stability relative to the strongest stem in this image",
          }
        )}</td>
        <td class="px-4 py-3 text-sm">${renderMetricCell(
          row.productivity,
          maxProductivity,
          {
            formatter: formatInt,
            gradient: "from-emerald-400 to-emerald-600",
            label: "Distinct left/right contexts compared with the most productive stem",
            detail: `
              <span class="inline-flex items-center gap-1 rounded-full bg-emerald-50 dark:bg-emerald-900/30 px-2 py-0.5 text-emerald-700 dark:text-emerald-100 font-semibold">
                L ${formatInt(row.left_types)}
              </span>
              <span class="inline-flex items-center gap-1 rounded-full bg-emerald-50 dark:bg-emerald-900/30 px-2 py-0.5 text-emerald-700 dark:text-emerald-100 font-semibold">
                R ${formatInt(row.right_types)}
              </span>
            `,
          }
        )}</td>
        <td class="px-4 py-3 text-sm">${renderMetricCell(
          row.boundary_strength,
          maxBoundary,
          {
            formatter: formatFloat,
            gradient: "from-indigo-400 to-indigo-600",
            label: "Boundary entropy compared with the tightest stem",
          }
        )}</td>
        <td class="px-4 py-3 text-center text-xs text-slate-400">—</td>
      `;
      stemBody.appendChild(tr);
    });
  }

  function renderPrefixSuffix(target, items) {
    if (!target) return;
    target.innerHTML = "";
    items.forEach((row) => {
      const tr = document.createElement("tr");
      tr.className =
        "hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors";
      const seqCell = buildSequenceCell(row);
      tr.innerHTML = `
        <td class="px-4 py-3 align-top">${seqCell}</td>
        <td class="px-4 py-3 text-center text-sm font-semibold">${formatInt(
          row.count
        )}</td>
        <td class="px-4 py-3 text-center text-sm">${formatFloat(
          row.share_percent ?? 0
        )}%</td>
        <td class="px-4 py-3 text-center text-xs text-slate-400">—</td>
      `;
      target.appendChild(tr);
    });
  }

  function buildSequenceCell(row) {
    const symbols = Array.isArray(row.symbol_values) ? row.symbol_values.join("") : row.symbol || "";
    const codes = Array.isArray(row.gardiner_codes)
      ? row.gardiner_codes.filter(Boolean).join(" ")
      : Array.isArray(row.seq)
      ? row.seq.join("·")
      : "";

    const length = row.length ?? (row.seq ? row.seq.length : 0);

    return `
      <div class="space-y-1">
        <div class="text-xl font-semibold tracking-widest leading-tight" style="font-family:${glyphFont}">
          ${symbols || "—"}
        </div>
        <div class="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400 flex items-center gap-2">
          <span class="inline-flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-slate-600 dark:text-slate-200">${length || "?"} glyphs</span>
          <span class="font-mono text-slate-600 dark:text-slate-300">${codes || "n/a"}</span>
        </div>
      </div>
    `;
  }

  function formatInt(val) {
    const num = Number(val);
    return Number.isFinite(num)
      ? num.toLocaleString("de-DE", { maximumFractionDigits: 0 })
      : "—";
  }

  function formatFloat(val) {
    const num = Number(val);
    return Number.isFinite(num)
      ? num.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : "—";
  }

  function initTooltips() {
    const triggers = document.querySelectorAll(".tooltip-trigger[data-tooltip]");
    let active = null;

    const remove = () => {
      if (active) {
        active.remove();
        active = null;
      }
    };

    const position = (trigger) => {
      if (!active) return;
      const rect = trigger.getBoundingClientRect();
      const margin = 8;
      let left = rect.right + margin;
      let top = rect.top + rect.height / 2;

      active.style.left = `${left}px`;
      active.style.top = `${top}px`;
      active.style.transform = "translateY(-50%)";

      const tipRect = active.getBoundingClientRect();

      if (left + tipRect.width > window.innerWidth - margin) {
        left = rect.left - margin - tipRect.width;
      }

      top = Math.max(margin, Math.min(top - tipRect.height / 2, window.innerHeight - tipRect.height - margin));

      active.style.left = `${left}px`;
      active.style.top = `${top}px`;
      active.style.transform = "none";
    };

    const show = (trigger) => {
      const text = trigger.getAttribute("data-tooltip");
      if (!text) return;
      remove();
      active = document.createElement("div");
      active.className =
        "pointer-events-none fixed z-50 max-w-xs rounded-lg border border-slate-200 bg-slate-900 text-white text-[11px] font-semibold leading-snug px-3 py-2 shadow-lg dark:border-slate-700";
      active.textContent = text;
      document.body.appendChild(active);
      position(trigger);
    };

    triggers.forEach((el) => {
      el.addEventListener("mouseenter", () => show(el));
      el.addEventListener("mouseleave", remove);
      el.addEventListener("focus", () => show(el));
      el.addEventListener("blur", remove);
    });

    window.addEventListener("scroll", remove, true);
    window.addEventListener("resize", remove);
  }

  function getMax(items, key) {
    return items.reduce((max, item) => {
      const value = Number(item?.[key]);
      if (!Number.isFinite(value)) return max;
      return value > max ? value : max;
    }, 0) || 1;
  }

  function renderMetricCell(value, max, { formatter, gradient, label, detail }) {
    const num = Number(value);
    const safeMax = max || 1;
    const ratio = Number.isFinite(num) && safeMax > 0 ? Math.max(0, Math.min(1, num / safeMax)) : 0;
    const width = (ratio * 100).toFixed(1);
    const display = formatter ? formatter(num) : formatFloat(num);

    return `
      <div class="space-y-2" title="${label || ""}">
        <div class="flex items-center gap-3">
          <div class="flex-1 h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
            <div class="h-full rounded-full bg-gradient-to-r ${gradient}" style="width:${width}%;"></div>
          </div>
        </div>
        <div class="flex items-start justify-between text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">
          <span class="font-semibold tabular-nums text-slate-700 dark:text-slate-100">${display}</span>
          ${
            detail
              ? `<div class="flex flex-wrap justify-end gap-1 text-[10px] uppercase tracking-wide text-slate-400 dark:text-slate-500">${detail}</div>`
              : ""
          }
        </div>
      </div>
    `;
  }
});
