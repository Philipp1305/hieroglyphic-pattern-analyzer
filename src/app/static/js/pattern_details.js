document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-pattern-root]");
  if (!root) return;

  const patternId = Number(root.dataset.patternId);
  if (!patternId) {
    console.warn("[pattern-details] missing pattern id");
    return;
  }

  const glyphsEl = root.querySelector("[data-pattern-glyphs]");
  const occurrencesEl = root.querySelector("[data-pattern-occurrences]");
  const lengthEl = root.querySelector("[data-pattern-length]");

  const sentencesList = root.querySelector("[data-pattern-sentences-list]");
  const sentencesEmpty = root.querySelector("[data-pattern-sentences-empty]");
  const loadingOverlay = root.querySelector("[data-pattern-loading]");

  const tokensContainer = root.querySelector("[data-pattern-tokens]");
  const tokensEmpty = root.querySelector("[data-pattern-tokens-empty]");
  const transcriptionEl = root.querySelector("[data-pattern-transcription]");
  const translationEl = root.querySelector("[data-pattern-translation]");
  const linksContainer = root.querySelector("[data-pattern-links]");

  const state = {
    pattern: null,
    sentences: [],
    selectedSentenceId: null,
  };

  fetchDetails();

  function fetchDetails() {
    setLoading(true);
    fetch(
      `/api/patterns/${encodeURIComponent(patternId)}/details?_=${Date.now()}`,
      {
        cache: "no-store",
      },
    )
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        state.pattern = data?.pattern || null;
        state.sentences = Array.isArray(data?.sentences) ? data.sentences : [];
        state.selectedSentenceId =
          state.sentences.length > 0 ? String(state.sentences[0].id) : null;

        renderPatternHeader(data);
        renderSentences();
        renderSelection();
        highlightPatternForSelection();
      })
      .catch((err) => {
        console.error("[pattern-details] load error", err);
        state.pattern = null;
        state.sentences = [];
        state.selectedSentenceId = null;
        renderPatternHeader(null);
        renderSentences();
        renderSelection();
      })
      .finally(() => setLoading(false));
  }

  function renderPatternHeader(data) {
    const pattern = data?.pattern || {};
    const length =
      typeof pattern.length === "number" && pattern.length > 0
        ? pattern.length
        : pattern.gardiner_ids?.length || "—";

    const occurrenceTotal =
      (typeof data?.occurrence_count === "number" && data.occurrence_count) ||
      (typeof pattern.count === "number" && pattern.count) ||
      0;

    if (glyphsEl) {
      setGlyphContent(glyphsEl, {
        symbolValues: pattern.symbol_values,
        symbolText: pattern.symbol,
        codes: pattern.gardiner_codes,
        fallbackLabel: pattern.gardiner_label,
      });
      glyphsEl.style.fontFamily =
        "'Noto Sans Egyptian Hieroglyphs','Segoe UI Historic','Segoe UI Symbol','Noto Sans',sans-serif";
    }

    if (occurrencesEl) {
      occurrencesEl.textContent = occurrenceTotal.toString();
    }
    if (lengthEl) {
      lengthEl.textContent = `n = ${length}`;
    }
  }

  function renderSentences() {
    const list = sentencesList;
    if (!list) return;
    list.replaceChildren();

    const sentences = state.sentences;
    if (sentencesEmpty)
      sentencesEmpty.classList.toggle("hidden", sentences.length !== 0);
    if (sentences.length === 0) return;

    sentences.forEach((s) => {
      const item = document.createElement("button");
      item.type = "button";
      item.dataset.sentenceId = String(s.id);
      item.className =
        "w-full text-left px-4 py-3 flex flex-col gap-1 hover:bg-primary/5 transition-colors";

      const line1 = document.createElement("div");
      line1.className = "flex items-center gap-2";
      const title = document.createElement("p");
      title.className = "text-sm font-semibold";
      title.textContent =
        s.transcription || s.translation || `Sentence ${s.id}`;
      line1.append(title);

      const line2 = document.createElement("p");
      line2.className =
        "text-xs text-text-secondary-light dark:text-text-secondary-dark line-clamp-2";
      line2.textContent = s.translation || "—";

      item.append(line1, line2);

      item.addEventListener("click", () => {
        state.selectedSentenceId = String(s.id);
        highlightSelection();
        renderSelection();
      });

      list.appendChild(item);
    });

    highlightSelection();
  }

  function highlightSelection() {
    if (!sentencesList) return;
    const selected = state.selectedSentenceId;
    sentencesList.querySelectorAll("[data-sentence-id]").forEach((el) => {
      const isSelected = String(el.dataset.sentenceId) === String(selected);

      el.classList.toggle("bg-primary/10", isSelected);

      if (isSelected) {
        el.classList.add("border-l-4", "border-solid");
        el.style.borderLeftColor = "#E97451";
      } else {
        el.classList.remove("border-l-4", "border-solid");
        el.style.borderLeftColor = "";
      }
    });
  }

  function renderSelection() {
    const sentence =
      state.sentences.find(
        (s) => String(s.id) === String(state.selectedSentenceId),
      ) || null;

    const tokens = sentence?.matching_tokens || [];
    if (tokensContainer) {
      tokensContainer.replaceChildren();
      if (!tokens.length) {
        if (tokensEmpty) tokensEmpty.classList.remove("hidden");
      } else {
        if (tokensEmpty) tokensEmpty.classList.add("hidden");
        tokens.forEach((t) => tokensContainer.appendChild(renderToken(t)));
      }
    }

    if (transcriptionEl) {
      transcriptionEl.textContent = sentence?.transcription || "—";
    }
    if (translationEl) {
      // prefer translation/meaning, fall back to transcription if missing
      translationEl.textContent =
        sentence?.translation || sentence?.transcription || "—";
    }

    renderLinks(sentence);
    highlightPatternForSelection();
  }

  function setLoading(show) {
    if (loadingOverlay) loadingOverlay.classList.toggle("hidden", !show);
  }

  function renderToken(token) {
    const card = document.createElement("div");
    card.className =
      "rounded-lg border border-border-light dark:border-border-dark bg-white/80 dark:bg-gray-900/60 px-4 py-3";

    const header = document.createElement("div");
    header.className = "flex items-center justify-between gap-2";
    const lemma = document.createElement("p");
    lemma.className = "text-sm font-semibold";
    lemma.textContent = token.lemma_id || "—";
    const pos = document.createElement("span");
    pos.className =
      "text-[11px] uppercase tracking-wide rounded-full bg-primary/10 text-primary px-2 py-0.5 font-bold";
    pos.textContent = token.pos || "pos";
    header.append(lemma, pos);

    const freq = document.createElement("p");
    freq.className =
      "text-xs text-text-secondary-light dark:text-text-secondary-dark";
    const freqVal =
      typeof token.corpus_frequency === "number"
        ? token.corpus_frequency
        : token.corpus_frequency || 0;
    freq.textContent = `Corpus freq: ${freqVal}`;

    const mdc = document.createElement("p");
    mdc.className = "text-xs font-mono text-text-secondary-light";
    mdc.textContent = token.mdc || "";

    const translit = document.createElement("p");
    translit.className = "text-sm italic";
    translit.textContent = token.transcription || "—";

    const transl = document.createElement("p");
    transl.className =
      "text-sm text-text-secondary-light dark:text-text-secondary-dark";
    transl.textContent = token.translation || "—";

    card.append(header, freq, mdc, translit, transl);
    return card;
  }

  function renderLinks(sentence) {
    if (!linksContainer) return;
    linksContainer.replaceChildren();
    const ids = (
      Array.isArray(sentence?.tla_ids) && sentence.tla_ids.length
        ? sentence.tla_ids
        : sentence?.id
          ? [sentence.id]
          : []
    ).filter(Boolean);

    if (!ids.length) {
      const empty = document.createElement("p");
      empty.className =
        "text-xs text-text-secondary-light dark:text-text-secondary-dark";
      empty.textContent = "No external references.";
      linksContainer.appendChild(empty);
      return;
    }

    ids.forEach((id) => {
      const a = document.createElement("a");
      a.className =
        "flex items-center justify-between gap-3 rounded-xl border border-primary/30 bg-primary/10 px-4 py-3 text-sm font-semibold text-text-light dark:text-text-dark transition-colors hover:bg-primary/15";
      a.href = `https://thesaurus-linguae-aegyptiae.de/sentence/${encodeURIComponent(
        id,
      )}`;
      a.target = "_blank";
      const left = document.createElement("div");
      left.className = "flex items-center gap-3";
      const icon = document.createElement("span");
      icon.className = "material-symbols-outlined text-primary";
      icon.textContent = "open_in_new";
      const label = document.createElement("span");
      label.textContent = id;
      left.append(icon, label);
      a.append(left);
      linksContainer.appendChild(a);
    });
  }

  function setGlyphContent(element, options = {}) {
    const {
      symbolValues = [],
      symbolText = "",
      codes = [],
      fallbackLabel = "",
    } = options;
    if (!element) return;
    element.innerHTML = "";
    const normalizedCodes = Array.isArray(codes)
      ? codes
          .map((code) => (code ?? "").toString().trim())
          .filter((code) => code.length)
      : [];
    const normalizedSymbols = Array.isArray(symbolValues)
      ? symbolValues.map((val) => (val ?? "").toString())
      : [];

    const maxLen = Math.max(normalizedSymbols.length, normalizedCodes.length);
    if (maxLen > 0) {
      const frag = document.createDocumentFragment();
      for (let i = 0; i < maxLen; i += 1) {
        const sym = (normalizedSymbols[i] || "").trim();
        const code = normalizedCodes[i] || "";
        const span = document.createElement("span");
        span.className = "inline-block";
        span.style.marginRight = "0.35rem";
        span.dataset.glyphIdx = String(i);
        if (sym) {
          span.textContent = sym;
        } else if (code) {
          span.textContent = code;
          span.className = [
            "inline-flex",
            "items-center",
            "justify-center",
            "text-red-600",
            "dark:text-red-300",
            "text-[11px]",
            "px-1.5",
            "py-0.5",
            "rounded",
            "border",
            "border-red-200",
            "dark:border-red-500/60",
            "bg-red-50",
            "dark:bg-red-900/30",
            "leading-none",
            "font-semibold",
          ].join(" ");
        } else {
          span.textContent = "?";
          span.className = [
            "inline-flex",
            "items-center",
            "justify-center",
            "text-red-500",
            "font-semibold",
          ].join(" ");
        }
        frag.appendChild(span);
      }
      element.appendChild(frag);
      return;
    }

    const symbol = (symbolText || "").toString().trim();
    if (symbol) {
      element.textContent = symbol;
      return;
    }

    const fallback =
      (typeof fallbackLabel === "string" && fallbackLabel.trim()) || "";
    if (fallback) {
      element.textContent = fallback;
      return;
    }

    const unknown = document.createElement("span");
    unknown.textContent = "?";
    unknown.className = "text-red-500 font-semibold";
    element.appendChild(unknown);
  }

  function highlightPatternForSelection() {
    if (!glyphsEl) return;
    glyphsEl.style.position = "relative";

    const existing = glyphsEl.querySelector("[data-glyph-highlight]");
    if (existing) existing.remove();

    const spans = Array.from(glyphsEl.querySelectorAll("[data-glyph-idx]"));
    if (!spans.length) return;

    const sentence =
      state.sentences.find(
        (s) => String(s.id) === String(state.selectedSentenceId),
      ) || null;
    if (!sentence || !Array.isArray(sentence.matched_patterns)) return;

    // Use the first matched pattern to highlight its span.
    const mp = sentence.matched_patterns.find(
      (p) =>
        Number.isFinite(Number(p?.pattern_start)) &&
        Number.isFinite(Number(p?.pattern_end)),
    );
    if (!mp) return;

    const start = Number(mp.pattern_start);
    const end = Number(mp.pattern_end);
    const inRange = spans.filter((span) => {
      const idx = Number(span.dataset.glyphIdx);
      return Number.isFinite(idx) && idx >= start && idx < end;
    });
    if (!inRange.length) return;

    let left = Infinity;
    let top = Infinity;
    let right = -Infinity;
    let bottom = -Infinity;
    inRange.forEach((span) => {
      const rect = span.getBoundingClientRect();
      const parentRect = glyphsEl.getBoundingClientRect();
      const relLeft = rect.left - parentRect.left + glyphsEl.scrollLeft;
      const relTop = rect.top - parentRect.top + glyphsEl.scrollTop;
      const relRight = relLeft + rect.width;
      const relBottom = relTop + rect.height;
      left = Math.min(left, relLeft);
      top = Math.min(top, relTop);
      right = Math.max(right, relRight);
      bottom = Math.max(bottom, relBottom);
    });

    const overlay = document.createElement("div");
    overlay.dataset.glyphHighlight = "true";
    overlay.style.position = "absolute";
    overlay.style.pointerEvents = "none";
    overlay.style.left = `${left - 4}px`;
    overlay.style.top = `${top - 4}px`;
    overlay.style.width = `${right - left + 8}px`;
    overlay.style.height = `${bottom - top + 8}px`;
    overlay.style.border = "2px solid #E97451";
    overlay.style.borderRadius = "8px";
    overlay.style.boxSizing = "border-box";

    glyphsEl.appendChild(overlay);

    // Scroll to bring the highlighted area into view.
    const firstSpan = inRange[0];
    if (firstSpan && typeof firstSpan.scrollIntoView === "function") {
      firstSpan.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
        inline: "center",
      });
    }
  }
});
