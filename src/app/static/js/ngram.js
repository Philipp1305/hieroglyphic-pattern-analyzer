document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-ngram-root]");
  if (!root) {
    return;
  }

  const imageId = root.dataset.imageId;
  const imageArea = root.querySelector("[data-ngram-image]");
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
  const selectedMoreBtn = root.querySelector("[data-ngram-selected-more]");
  if (selectedGlyphs) {
    selectedGlyphs.style.fontFamily =
      "'Noto Sans Egyptian Hieroglyphs','Segoe UI Historic','Segoe UI Symbol','Noto Sans',sans-serif";
  }

  const state = {
    items: [],
    lengths: [],
    activeLength: "all",
    search: "",
    selectedId: null,
  };

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

  if (!imageId || !imageArea) {
    showOverlay("No image selected", { showSpinner: false });
    setEmptyMessage("No image selected.");
    return;
  }

  showOverlay("Loading manuscript…");
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
      imageArea.style.backgroundImage = `url(${src})`;
      imageArea.classList.remove("opacity-0");
      hideOverlay();
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

    return {
      id: Number(item?.id) || 0,
      length: Number(item?.length) || 0,
      count: Number(item?.count) || 0,
      unicodeValues,
      unicodeLabel,
      symbol,
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
      if (selectedMoreBtn) {
        selectedMoreBtn.setAttribute("aria-disabled", "true");
        selectedMoreBtn.classList.add("pointer-events-none", "opacity-60");
      }
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

    if (selectedMoreBtn) {
      selectedMoreBtn.removeAttribute("aria-disabled");
      selectedMoreBtn.classList.remove("pointer-events-none", "opacity-60");
    }
  }

  if (selectedMoreBtn) {
    selectedMoreBtn.addEventListener("click", () => {
      const selection = getSelectedItem();
      if (!selection) {
        return;
      }
      showPatternInfo(selection);
    });
  }

  function showPatternInfo(item) {
    window.alert(
      `Pattern (n=${item.length}, occurrences=${item.count})\n${item.unicodeLabel || "No unicode data"}`,
    );
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
});
