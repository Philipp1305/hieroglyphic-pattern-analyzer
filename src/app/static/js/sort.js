(function () {
    const COLUMN_COLOR_PALETTE = [
        {
            fill: "rgba(134, 239, 172, 0.25)",
            stroke: "rgba(22, 163, 74, 0.9)",
            focusFill: "rgba(74, 222, 128, 0.35)",
            focusStroke: "rgba(21, 128, 61, 1)",
            chartBg: "rgba(134, 239, 172, 0.45)",
            chartActive: "rgba(34, 197, 94, 0.85)",
        },
        {
            fill: "rgba(96, 165, 250, 0.25)",
            stroke: "rgba(59, 130, 246, 0.9)",
            focusFill: "rgba(59, 130, 246, 0.35)",
            focusStroke: "rgba(29, 78, 216, 1)",
            chartBg: "rgba(96, 165, 250, 0.45)",
            chartActive: "rgba(59, 130, 246, 0.85)",
        },
        {
            fill: "rgba(248, 180, 180, 0.25)",
            stroke: "rgba(239, 68, 68, 0.85)",
            focusFill: "rgba(248, 113, 113, 0.35)",
            focusStroke: "rgba(220, 38, 38, 1)",
            chartBg: "rgba(248, 180, 180, 0.45)",
            chartActive: "rgba(248, 113, 113, 0.85)",
        },
    ];

    const MANUAL_FOCUS_FILL = "rgba(74, 222, 128, 0.35)";
    const MANUAL_FOCUS_STROKE = "rgba(21, 128, 61, 1)";
    const MANUAL_NEIGHBOR_FILL = "rgba(134, 239, 172, 0.2)";
    const MANUAL_NEIGHBOR_STROKE = "rgba(34, 197, 94, 0.85)";
    const MEASUREMENT_LINE_COLOR = MANUAL_FOCUS_STROKE;
    const MEASUREMENT_TEXT_BG = "rgba(255, 255, 255, 0.9)";
    const MEASUREMENT_TEXT_COLOR = "rgba(15, 23, 42, 0.95)";
    const MIN_VIEW_SIZE = 50;
    const ZOOM_IN_FACTOR = 0.93;
    const ZOOM_OUT_FACTOR = 1.07;
    const PAN_SENSITIVITY = 0.75;

    const sortState = {
        root: null,
        columns: [],
        glyphs: {},
        focusIndex: 0,
        baseImage: null,
        imageReady: false,
        activeGlyphId: null,
        activeColumnIndex: null,
        canvasHotspots: [],
        viewWindow: null,
        canvasTransform: null,
        canvasAspectRatio: 1,
        isPanning: false,
        panStart: null,
        panMoved: false,
        skipNextCanvasClick: false,
        measurementButton: null,
        measurement: {
            active: false,
            startPoint: null,
            lastSegment: null,
            cleanupTimer: null,
        },
        preserveViewOnFocus: false,
        mode: "auto",
        activateTab: null,
        loading: {
            image: true,
            snapshot: true,
        },
        lastAutomaticTolerance: null,
        hasUnsavedChanges: false,
    };

    document.addEventListener("DOMContentLoaded", () => {
        const root = document.querySelector("[data-sort-root]");
        if (!root) {
            return;
        }

        sortState.root = root;

        setupTabs(sortState);
        setupToleranceSlider(root, sortState);
        setupAutomaticSortingPreview(sortState);
        setupColumnNavigation(sortState);
        setupCanvasInteractions(sortState);
        setupMeasurementTools(sortState);
        setupSelectionClearButton(sortState);
        setupApplySorting(sortState);
        setupLeaveWarning(sortState);
        updateLoadingOverlay(sortState);

        const imageId = root.dataset.imageId;
        if (!imageId) {
            return;
        }

        loadMetadata(imageId, root, sortState);
        loadFullImage(imageId, sortState);
        loadSortingSnapshot(imageId, sortState);

        window.addEventListener("resize", () => renderColumnCanvas(sortState));
    });

    function setupTabs(state) {
        const root = state.root;
        if (!root) {
            return;
        }
        const tabButtons = root.querySelectorAll("[data-sort-tab]");
        const panels = root.querySelectorAll("[data-sort-panel]");
        if (!tabButtons.length || !panels.length) {
            return;
        }

        const activateTab = (mode) => {
            tabButtons.forEach((btn) => {
                const isActive = btn.dataset.sortTab === mode;
                btn.setAttribute("aria-selected", String(isActive));
                btn.classList.toggle("border-primary", isActive);
                btn.classList.toggle("bg-primary/10", isActive);
                btn.classList.toggle("text-primary", isActive);
                btn.classList.toggle("border-border-light", !isActive);
                btn.classList.toggle("dark:border-border-dark", !isActive);
                btn.classList.toggle("text-text-secondary-light", !isActive);
                btn.classList.toggle("dark:text-text-secondary-dark", !isActive);
            });

            panels.forEach((panel) => {
                panel.classList.toggle("hidden", panel.dataset.sortPanel !== mode);
            });

            state.mode = mode;
            state.viewWindow = null;
            if (mode === "manual") {
                renderManualColumns(state);
            }
            renderColumnCanvas(state);
        };

        state.activateTab = (mode) => activateTab(mode);

        tabButtons.forEach((btn) => {
            btn.addEventListener("click", () => activateTab(btn.dataset.sortTab));
        });

        activateTab("auto");
    }

    function setupToleranceSlider(root, state) {
        const slider = root.querySelector("[data-sort-tolerance-input]");
        if (!slider) {
            return;
        }
        const numericInput = root.querySelector("[data-sort-tolerance-input-field]");

        setToleranceValue(root, slider.value);

        slider.addEventListener("input", () => {
            setToleranceValue(root, slider.value);
        });

        if (numericInput) {
            numericInput.addEventListener("input", () => {
                setToleranceValue(root, numericInput.value);
            });
        }
    }

    function setupAutomaticSortingPreview(state) {
        const root = state.root;
        if (!root) {
            return;
        }
        const button = root.querySelector("[data-sort-preview-run]");
        if (!button) {
            return;
        }
        button.addEventListener("click", () => runAutomaticSortingPreview(state, button));
    }

    async function runAutomaticSortingPreview(state, button) {
        const root = state?.root;
        if (!root) {
            return;
        }
        const imageId = root.dataset.imageId;
        const tolerance = getToleranceValue(root);
        if (!imageId || !Number.isFinite(tolerance) || tolerance <= 0) {
            return;
        }
        button.disabled = true;
        button.classList.add("opacity-60", "pointer-events-none");
        setLoadingState(state, "snapshot", true);
        try {
            const response = await fetch(`/api/sorting/${imageId}/preview`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ tolerance }),
            });
            if (!response.ok) {
                throw new Error(`Request failed (${response.status})`);
            }
            const snapshot = await response.json();
            state.lastAutomaticTolerance = tolerance;
            applySortingSnapshot(snapshot, state, { markUnsaved: true });
        } catch (error) {
            console.error("Failed to run automatic sorting preview", error);
        } finally {
            button.disabled = false;
            button.classList.remove("opacity-60", "pointer-events-none");
            setLoadingState(state, "snapshot", false);
        }
    }

    async function submitSortingSnapshot(state, triggerButton, action = "stay") {
        const root = state?.root;
        if (!root) {
            return;
        }
        const imageId = root.dataset.imageId;
        if (!imageId) {
            return;
        }
        const columnsPayload = normalizeColumnsForRequest(state?.columns);
        const toleranceValue = state?.lastAutomaticTolerance ?? getToleranceValue(root);
        const payload = { columns: columnsPayload };
        if (Number.isFinite(toleranceValue) && toleranceValue > 0) {
            payload.tolerance = Math.round(toleranceValue);
        }
        if ((action || "").toLowerCase() === "leave") {
            payload.advance_status = true;
        }

        toggleApplyButtonsLoading(root, true, triggerButton);
        if (triggerButton) {
            triggerButton.blur();
        }

        try {
            const response = await fetch(`/api/sorting/${imageId}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });
            if (!response.ok) {
                throw new Error(`Request failed (${response.status})`);
            }
            const result = await response.json();
            console.log("[sort] apply sorting success", result);
            setUnsavedChanges(state, false);
            if ((action || "").toLowerCase() === "leave") {
                window.location.href = `/overview?id=${imageId}`;
                return;
            }
            loadSortingSnapshot(imageId, state);
        } catch (error) {
            console.error("Failed to apply sorting", error);
        } finally {
            toggleApplyButtonsLoading(root, false, null);
        }
    }

    function normalizeColumnsForRequest(columns) {
        if (!Array.isArray(columns)) {
            return [];
        }
        return columns.map((column, index) => {
            const glyphs = Array.isArray(column?.glyph_ids) ? column.glyph_ids : [];
            const normalizedGlyphs = glyphs
                .map((glyphId) => {
                    const numeric = Number.parseInt(glyphId, 10);
                    return Number.isInteger(numeric) ? numeric : null;
                })
                .filter((value) => Number.isInteger(value));
            const parsedCol = Number.parseInt(column?.col, 10);
            const colIdx = Number.isInteger(parsedCol) ? parsedCol : index;
            return {
                col: colIdx,
                glyph_ids: normalizedGlyphs,
            };
        });
    }

    function toggleApplyButtonsLoading(root, isLoading, activeButton) {
        if (!root) {
            return;
        }
        const buttons = root.querySelectorAll("[data-sort-apply]");
        if (!buttons.length) {
            return;
        }
        buttons.forEach((btn) => {
            btn.disabled = Boolean(isLoading);
            btn.classList.toggle("opacity-60", Boolean(isLoading));
            btn.classList.toggle("pointer-events-none", Boolean(isLoading));
            const spinner = btn.querySelector("[data-sort-apply-spinner]");
            const icon = btn.querySelector("[data-sort-apply-icon]");
            const text = btn.querySelector("[data-sort-apply-text]");
            const defaultText =
                btn.dataset.sortApplyDefaultText ||
                (text && text.textContent ? text.textContent.trim() : "Apply sorting");
            btn.dataset.sortApplyDefaultText = defaultText;
            const isActive = Boolean(activeButton && btn === activeButton);
            if (spinner) {
                spinner.classList.toggle("hidden", !(isLoading && isActive));
            }
            if (icon) {
                icon.classList.toggle("hidden", Boolean(isLoading && isActive));
            }
            if (text) {
                text.textContent = isLoading && isActive ? "Applying..." : defaultText;
            }
        });
    }

    function setupMeasurementTools(state) {
        const root = state.root;
        if (!root) {
            return;
        }
        const button = root.querySelector("[data-sort-measure-btn]");
        if (!button) {
            return;
        }
        state.measurementButton = button;
        button.addEventListener("click", () => {
            if (!state.imageReady) {
                return;
            }
            if (state.measurement?.active) {
                cancelMeasurementMode(state);
            } else {
                startMeasurementMode(state);
            }
        });
        updateMeasurementButtonState(state);
    }

    function setupSelectionClearButton(state) {
        const root = state.root;
        if (!root) {
            return;
        }
        const clearButton = root.querySelector("[data-sort-clear-selection]");
        if (!clearButton) {
            return;
        }
        clearButton.addEventListener("click", () => {
            state.activeGlyphId = null;
            state.activeColumnIndex = null;
            renderManualColumns(state);
            renderColumnCanvas(state);
        });
    }

    function setupApplySorting(state) {
        const root = state.root;
        if (!root) {
            return;
        }
        const applyButtons = root.querySelectorAll("[data-sort-apply]");
        if (!applyButtons.length) {
            return;
        }
        applyButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const action = button.dataset.sortApplyAction || "stay";
                submitSortingSnapshot(state, button, action);
            });
        });
    }

    function startMeasurementMode(state) {
        if (!state) {
            return;
        }
        if (!state.measurement) {
            state.measurement = {
                active: false,
                startPoint: null,
                lastSegment: null,
                cleanupTimer: null,
            };
        }
        clearMeasurementCleanup(state);
        state.measurement.active = true;
        state.measurement.startPoint = null;
        state.measurement.lastSegment = null;
        updateMeasurementButtonState(state);
        renderColumnCanvas(state);
    }

    function cancelMeasurementMode(state) {
        if (!state?.measurement) {
            return;
        }
        clearMeasurementCleanup(state);
        state.measurement.active = false;
        state.measurement.startPoint = null;
        updateMeasurementButtonState(state);
        renderColumnCanvas(state);
    }

    function updateMeasurementButtonState(state) {
        const button = state?.measurementButton;
        if (!button) {
            return;
        }
        const measurement = state.measurement || {};
        const disabled = !state.imageReady;
        button.disabled = disabled;
        button.classList.toggle("opacity-40", disabled);
        button.classList.toggle("pointer-events-none", disabled);
        const isActive = Boolean(measurement.active);
        button.classList.toggle("border-primary", isActive);
        button.classList.toggle("text-primary", isActive);
        button.classList.toggle("bg-primary/5", isActive);
        const label = button.querySelector("[data-sort-measure-label]");
        if (label) {
            if (disabled) {
                label.textContent = "Measure tolerance on image";
            } else if (measurement.active && measurement.startPoint) {
                label.textContent = "Select end point";
            } else if (measurement.active) {
                label.textContent = "Select start point";
            } else {
                label.textContent = "Measure tolerance on image";
            }
        }
    }

    function setupCanvasInteractions(state) {
        const root = state.root;
        if (!root) {
            return;
        }
        const canvas = root.querySelector("[data-sort-canvas]");
        if (!canvas) {
            return;
        }
        canvas.addEventListener("click", (event) => handleCanvasClick(event, state));
        canvas.addEventListener("wheel", (event) => handleCanvasWheel(event, state), {
            passive: false,
        });
        canvas.addEventListener("mousedown", (event) => handleCanvasPanStart(event, state));
        window.addEventListener("keydown", (event) => handleCanvasKeyPan(event, state));
    }

    function handleCanvasClick(event, state) {
        if (state?.skipNextCanvasClick) {
            state.skipNextCanvasClick = false;
            return;
        }
        if (handleMeasurementClick(event, state)) {
            return;
        }
        const hit = findCanvasHotspot(state, event);
        if (!hit) {
            return;
        }

        const safeIndex = Math.max(0, Math.min(state.columns.length - 1, hit.columnIndex));
        state.focusIndex = safeIndex;
        state.activeColumnIndex = safeIndex;
        state.activeGlyphId = hit.glyphId;
        if (state.mode === "manual") {
            state.preserveViewOnFocus = true;
        }
        if (state.mode !== "manual" && typeof state.activateTab === "function") {
            state.activateTab("manual");
        } else {
            onColumnFocusChange(state);
        }
        highlightManualGlyph(state, safeIndex, hit.glyphId);
    }

    function handleMeasurementClick(event, state) {
        if (!state?.measurement?.active) {
            return false;
        }
        const imagePoint = getImagePointFromEvent(event, state);
        if (!imagePoint) {
            return true;
        }
        const measurement = state.measurement;
        if (!measurement.startPoint) {
            measurement.startPoint = imagePoint;
            measurement.lastSegment = null;
            updateMeasurementButtonState(state);
            renderColumnCanvas(state);
            return true;
        }
        const horizontalEnd = {
            x: imagePoint.x,
            y: measurement.startPoint.y,
        };
        const measuredLength = Math.abs(horizontalEnd.x - measurement.startPoint.x);
        measurement.lastSegment = {
            start: measurement.startPoint,
            end: horizontalEnd,
        };
        measurement.startPoint = null;
        measurement.active = false;
        scheduleMeasurementCleanup(state, measurement.lastSegment);
        updateMeasurementButtonState(state);
        applyMeasuredTolerance(state, measuredLength);
        renderColumnCanvas(state);
        return true;
    }

    function handleCanvasWheel(event, state) {
        if (!state.viewWindow || !state.baseImage) {
            return;
        }
        event.preventDefault();
        const canvas = event.currentTarget;
        const rect = canvas.getBoundingClientRect();
        if (!rect.width || !rect.height) {
            return;
        }
        const imageWidth = state.baseImage.naturalWidth || state.baseImage.width || 1;
        const imageHeight = state.baseImage.naturalHeight || state.baseImage.height || 1;

        const view = state.viewWindow;
        const targetRatio =
            state.canvasAspectRatio || (rect.width && rect.height ? rect.width / Math.max(rect.height, 1) : 1) || 1;
        const pointerX = event.clientX - rect.left;
        const pointerY = event.clientY - rect.top;
        const relX = pointerX / rect.width;
        const relY = pointerY / rect.height;

        const zoomFactor = event.deltaY < 0 ? ZOOM_IN_FACTOR : ZOOM_OUT_FACTOR;
        let proposedWidth = view.width * zoomFactor;
        proposedWidth = clamp(proposedWidth, MIN_VIEW_SIZE, imageWidth);
        let scaleApplied = proposedWidth / view.width;
        let proposedHeight = view.height * scaleApplied;
        if (proposedHeight < MIN_VIEW_SIZE) {
            scaleApplied = MIN_VIEW_SIZE / view.height;
            proposedHeight = view.height * scaleApplied;
            proposedWidth = view.width * scaleApplied;
        }
        if (proposedHeight > imageHeight) {
            scaleApplied = imageHeight / view.height;
            proposedHeight = view.height * scaleApplied;
            proposedWidth = view.width * scaleApplied;
        }
        const newWidth = clamp(proposedWidth, MIN_VIEW_SIZE, imageWidth);
        const newHeight = clamp(proposedHeight, MIN_VIEW_SIZE, imageHeight);

        let newX = view.x + (view.width - newWidth) * relX;
        let newY = view.y + (view.height - newHeight) * relY;
        newX = clamp(newX, 0, imageWidth - newWidth);
        newY = clamp(newY, 0, imageHeight - newHeight);

        const normalizedView = normalizeViewWindow(
            {
                x: newX,
                y: newY,
                width: newWidth,
                height: newHeight,
            },
            view?.aspectRatio || targetRatio,
            imageWidth,
            imageHeight
        );
        state.viewWindow = {
            ...normalizedView,
            locked: true,
            mode: state.mode,
        };
        renderColumnCanvas(state);
    }

    function handleCanvasPanStart(event, state) {
        if (event.button !== 0 || !state.viewWindow || !state.baseImage) {
            return;
        }
        const canvas = event.currentTarget;
        const rect = canvas.getBoundingClientRect();
        if (!rect.width || !rect.height) {
            return;
        }
        event.preventDefault();
        state.isPanning = true;
        state.panMoved = false;
        state.panStart = {
            x: event.clientX,
            y: event.clientY,
            view: { ...state.viewWindow },
            rect,
        };
        const handleMove = (evt) => handleCanvasPanMove(evt, state);
        const handleUp = (evt) => handleCanvasPanEnd(evt, state, handleMove);
        state.panMoveHandler = handleMove;
        window.addEventListener("mousemove", handleMove);
        window.addEventListener("mouseup", handleUp, { once: true });
    }

    function handleCanvasPanMove(event, state) {
        if (!state.isPanning || !state.panStart || !state.baseImage) {
            return;
        }
        const { rect, view } = state.panStart;
        const imageWidth = state.baseImage.naturalWidth || state.baseImage.width || 1;
        const imageHeight = state.baseImage.naturalHeight || state.baseImage.height || 1;
        if (!rect.width || !rect.height) {
            return;
        }
        const deltaX = (event.clientX - state.panStart.x) * PAN_SENSITIVITY;
        const deltaY = (event.clientY - state.panStart.y) * PAN_SENSITIVITY;
        if (!state.panMoved && (Math.abs(deltaX) > 2 || Math.abs(deltaY) > 2)) {
            state.panMoved = true;
        }
        const scaleX = view.width / rect.width;
        const scaleY = view.height / rect.height;
        let newX = view.x - deltaX * scaleX;
        let newY = view.y - deltaY * scaleY;
        newX = clamp(newX, 0, imageWidth - view.width);
        newY = clamp(newY, 0, imageHeight - view.height);

        const normalizedView = normalizeViewWindow(
            {
                x: newX,
                y: newY,
                width: view.width,
                height: view.height,
            },
            view.aspectRatio || state.canvasAspectRatio || view.width / Math.max(view.height, 1),
            imageWidth,
            imageHeight
        );
        state.viewWindow = {
            ...normalizedView,
            locked: true,
            mode: state.mode,
        };
        renderColumnCanvas(state);
    }

    function handleCanvasPanEnd(event, state, moveHandler) {
        window.removeEventListener("mousemove", moveHandler);
        if (state?.panMoved) {
            state.skipNextCanvasClick = true;
        }
        state.isPanning = false;
        state.panStart = null;
        state.panMoved = false;
        state.panMoveHandler = null;
    }

    function handleCanvasKeyPan(event, state) {
        if (!state?.root) {
            return;
        }
        const target = event.target;
        if (
            target &&
            (target.tagName === "INPUT" ||
                target.tagName === "TEXTAREA" ||
                target.isContentEditable)
        ) {
            return;
        }
        let handled = false;
        switch (event.key) {
            case "ArrowLeft":
                if (state.focusIndex > 0) {
                    state.focusIndex -= 1;
                    onColumnFocusChange(state);
                    handled = true;
                }
                break;
            case "ArrowRight":
                if (state.columns && state.focusIndex < state.columns.length - 1) {
                    state.focusIndex += 1;
                    onColumnFocusChange(state);
                    handled = true;
                }
                break;
            default:
                return;
        }
        if (handled) {
            event.preventDefault();
        }
    }

    function findCanvasHotspot(state, event) {
        const hotspots = Array.isArray(state.canvasHotspots) ? state.canvasHotspots : [];
        if (!hotspots.length) {
            return null;
        }
        const canvas = event.currentTarget;
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        return hotspots.find(
            (spot) =>
                x >= spot.x &&
                x <= spot.x + spot.width &&
                y >= spot.y &&
                y <= spot.y + spot.height
        );
    }

    function setupColumnNavigation(state) {
        const root = state.root;
        if (!root) {
            return;
        }

        const prevButton = root.querySelector('[data-sort-nav="prev"]');
        const nextButton = root.querySelector('[data-sort-nav="next"]');
        state.navButtons = { prev: prevButton, next: nextButton };

        if (prevButton) {
            prevButton.addEventListener("click", () => {
                if (state.focusIndex <= 0) {
                    return;
                }
                state.focusIndex -= 1;
                onColumnFocusChange(state);
            });
        }

        if (nextButton) {
            nextButton.addEventListener("click", () => {
                if (state.focusIndex >= state.columns.length - 1) {
                    return;
                }
                state.focusIndex += 1;
                onColumnFocusChange(state);
            });
        }
    }


    function onColumnFocusChange(state) {
        const preserveView = Boolean(state?.preserveViewOnFocus);
        state.preserveViewOnFocus = false;
        if (state.viewWindow && !preserveView) {
            state.viewWindow.locked = false;
        }
        updateColumnNavigation(state);
        highlightActiveColumn(state);
        renderColumnCanvas(state);
    }

    function updateColumnNavigation(state) {
        const root = state.root;
        if (!root) {
            return;
        }

        const visible = getVisibleColumns(state);
        const label = root.querySelector("[data-sort-range-label]");
        if (label) {
            const focused = state.columns?.[state.focusIndex];
            const colNumber = Number(focused?.col);
            if (Number.isFinite(colNumber)) {
                label.textContent = `Selected Column: ${colNumber}`;
            } else {
                label.textContent = "Selected Column: —";
            }
        }

        const navButtons = state.navButtons || {};
        setNavDisabled(navButtons.prev, state.focusIndex <= 0);
        setNavDisabled(
            navButtons.next,
            !state.columns.length || state.focusIndex >= state.columns.length - 1
        );
    }

    function setNavDisabled(button, disabled) {
        if (!button) {
            return;
        }
        if (disabled) {
            button.setAttribute("disabled", "true");
        } else {
            button.removeAttribute("disabled");
        }
    }

    function getVisibleColumns(state) {
        const { columns, focusIndex } = state;
        if (!columns.length) {
            return [];
        }
        const visible = [];
        for (let offset = -1; offset <= 1; offset += 1) {
            const idx = focusIndex + offset;
            if (idx < 0 || idx >= columns.length) {
                continue;
            }
            visible.push({ column: columns[idx], index: idx });
        }
        return visible;
    }

    function setCanvasMessage(state, text) {
        const root = state.root;
        if (!root) {
            return;
        }
        const messageEl = root.querySelector("[data-sort-canvas-message]");
        if (!messageEl) {
            return;
        }
        if (text) {
            messageEl.textContent = text;
            messageEl.classList.remove("hidden");
        } else {
            messageEl.classList.add("hidden");
        }
    }

    function updateLoadingOverlay(state) {
        const root = state?.root;
        if (!root) {
            return;
        }
        const overlay = root.querySelector("[data-sort-loading]");
        if (!overlay) {
            return;
        }
        const loaders = state.loading || {};
        const isLoading = Boolean(loaders.image) || Boolean(loaders.snapshot);
        overlay.classList.toggle("hidden", !isLoading);
    }

    function setLoadingState(state, key, value) {
        if (!state) {
            return;
        }
        if (!state.loading) {
            state.loading = { image: false, snapshot: false };
        }
        if (state.loading[key] === value) {
            return;
        }
        state.loading[key] = value;
        updateLoadingOverlay(state);
    }

    async function fetchJson(url) {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Request failed (${response.status})`);
        }
        return response.json();
    }

    function loadMetadata(imageId, root, state) {
        fetchJson(`/api/images/${imageId}/meta`)
            .then((meta) => updateMetadata(meta, root, imageId, state))
            .catch((error) => console.error("Failed to load metadata", error));
    }

    function updateMetadata(meta, root, fallbackId, state) {
        const displayName = meta.title || meta.file_name || `Image #${meta.id ?? fallbackId}`;
        const imageNameEl = root.querySelector("[data-sort-image-name]");
        if (imageNameEl) {
            imageNameEl.textContent = displayName;
        }

        const imageIdEl = root.querySelector("[data-sort-image-id]");
        if (imageIdEl) {
            imageIdEl.textContent = `ID #${meta.id ?? fallbackId}`;
        }

        const readingLabel = (meta.reading_direction || "").toUpperCase();
        const readingEls = root.querySelectorAll("[data-sort-reading]");
        readingEls.forEach((el) => {
            el.textContent = readingLabel || "—";
        });
        const readingBadge = root.querySelector("[data-sort-reading-label]");
        if (readingBadge) {
            readingBadge.textContent = readingLabel ? `${readingLabel} detected` : "—";
        }

        const toleranceText =
            typeof meta.tolerance === "number" ? `${meta.tolerance} px` : "—";
        const toleranceEl = root.querySelector("[data-sort-tolerance]");
        if (toleranceEl) {
            toleranceEl.textContent = toleranceText;
        }

        if (typeof meta.tolerance === "number") {
            setToleranceValue(root, meta.tolerance);
        } else {
            setToleranceValue(root, "");
        }
        const toleranceValue = getToleranceValue(root);
        if (state && Number.isFinite(toleranceValue)) {
            state.lastAutomaticTolerance = toleranceValue;
        }
        setUnsavedChanges(state, false);
    }

    function loadFullImage(imageId, state) {
        if (state) {
            state.imageReady = false;
            resetMeasurementState(state);
            updateMeasurementButtonState(state);
        }
        setLoadingState(state, "image", true);
        fetchJson(`/api/images/${imageId}/full`)
            .then((payload) => {
                if (!payload.image) {
                    setCanvasMessage(state, "Image data unavailable.");
                    setLoadingState(state, "image", false);
                    return;
                }

                const img = new Image();
                img.onload = () => {
                    state.baseImage = img;
                    state.imageReady = true;
                    state.viewWindow = null;
                    renderColumnCanvas(state);
                    setLoadingState(state, "image", false);
                    updateMeasurementButtonState(state);
                };
                img.onerror = () => {
                    console.error("Failed to decode image");
                    setCanvasMessage(state, "Unable to load image.");
                    setLoadingState(state, "image", false);
                    updateMeasurementButtonState(state);
                };
                img.src = payload.image;
            })
            .catch((error) => {
                console.error("Failed to load full image", error);
                setCanvasMessage(state, "Unable to load image.");
                setLoadingState(state, "image", false);
                updateMeasurementButtonState(state);
            });
    }

    function loadSortingSnapshot(imageId, state) {
        const { root } = state;
        setLoadingState(state, "snapshot", true);
        fetchJson(`/api/sorting/${imageId}`)
            .then((snapshot) => {
                applySortingSnapshot(snapshot, state, { markUnsaved: false });
                setLoadingState(state, "snapshot", false);
            })
            .catch((error) => {
                console.error("Failed to load sorting snapshot", error);
                setLoadingState(state, "snapshot", false);
            });
    }

    function applySortingSnapshot(snapshot, state, options = {}) {
        if (!state?.root) {
            return;
        }
        const markUnsaved = Boolean(options?.markUnsaved);
        state.columns = Array.isArray(snapshot?.columns) ? snapshot.columns : [];
        state.glyphs = snapshot?.glyphs || {};
        resetMeasurementState(state);
        if (!state.columns.length) {
            state.focusIndex = 0;
            state.activeColumnIndex = null;
            state.activeGlyphId = null;
        } else if (state.focusIndex >= state.columns.length) {
            state.focusIndex = state.columns.length - 1;
        } else if (state.focusIndex < 0) {
            state.focusIndex = 0;
        }

        state.viewWindow = null;
        renderColumnChart(state.root, snapshot, state);
        renderManualColumns(state);
        onColumnFocusChange(state);
        setUnsavedChanges(state, markUnsaved ? true : false);
    }

    function updateToleranceLabel(root, value) {
        return;
    }

    function setToleranceValue(root, value) {
        const slider = root.querySelector("[data-sort-tolerance-input]");
        if (!slider) {
            return;
        }
        const numericInput = root.querySelector("[data-sort-tolerance-input-field]");

        const numeric = Number(value);
        if (value === "" || Number.isNaN(numeric)) {
            if (numericInput) {
                numericInput.value = "";
            }
            return;
        }

        const rawMin = Number(slider.min);
        const rawMax = Number(slider.max);
        const safeMin = Number.isNaN(rawMin) ? numeric : rawMin;
        const safeMax = Number.isNaN(rawMax) ? numeric : rawMax;
        const clamped = Math.min(safeMax, Math.max(safeMin, numeric));
        slider.value = clamped;
        if (numericInput) {
            numericInput.value = clamped;
        }
    }

    function getToleranceValue(root) {
        const slider = root.querySelector("[data-sort-tolerance-input]");
        if (!slider) {
            return null;
        }
        const numeric = Number(slider.value);
        if (Number.isNaN(numeric) || numeric <= 0) {
            return null;
        }
        return numeric;
    }

    function renderColumnChart(root, snapshot, state) {
        const container = root.querySelector("[data-sort-column-bars]");
        if (!container) {
            return;
        }

        container.innerHTML = "";
        const columns = Array.isArray(snapshot?.columns) ? snapshot.columns : [];
        if (!columns.length) {
            const empty = document.createElement("div");
            empty.className =
                "flex w-full items-center justify-center text-[11px] text-text-secondary-light dark:text-text-secondary-dark";
            empty.textContent = "No sorting data available.";
            container.append(empty);
            return;
        }

        const maxGlyphs = columns.reduce((max, column) => {
            const glyphs = Array.isArray(column?.glyph_ids) ? column.glyph_ids.length : 0;
            return Math.max(max, glyphs);
        }, 0);
        const safeMax = maxGlyphs || 1;

        columns.forEach((column, index) => {
            const glyphCount = Array.isArray(column?.glyph_ids) ? column.glyph_ids.length : 0;
            const heightPercent = (glyphCount / safeMax) * 100;

            const bar = document.createElement("div");
            bar.className =
                "flex-1 rounded-sm bg-slate-300/60 dark:bg-slate-700/80 transition-[height] duration-300 ease-out cursor-pointer";
            if (!glyphCount) {
                bar.classList.add("bg-primary/20", "dark:bg-primary/25");
            }

            bar.style.height = `${heightPercent}%`;
            bar.dataset.column = String(column?.col ?? "");
            bar.dataset.count = String(glyphCount);
            bar.dataset.index = String(index);
            bar.title = `Column ${column?.col ?? "?"}: ${glyphCount} glyph${
                glyphCount === 1 ? "" : "s"
            }`;

            if (state) {
                bar.addEventListener("click", () => {
                    if (state.focusIndex === index) {
                        return;
                    }
                    state.focusIndex = index;
                    onColumnFocusChange(state);
                });
            }

            container.append(bar);
        });

        if (state) {
            highlightActiveColumn(state);
        }
    }

    function highlightActiveColumn(state) {
        const root = state.root;
        if (!root) {
            return;
        }
        const bars = root.querySelectorAll("[data-sort-column-bars] > div[data-index]");
        const activeIndex = state.focusIndex;
        bars.forEach((bar) => {
            const isActive = Number(bar.dataset.index) === activeIndex;
            bar.classList.toggle("ring-1", isActive);
            bar.classList.toggle("ring-primary/70", isActive);
            bar.classList.toggle("bg-amber-400/60", isActive);
            bar.classList.toggle("dark:bg-amber-400/40", isActive);
            bar.classList.toggle("bg-slate-300/60", !isActive);
            bar.classList.toggle("dark:bg-slate-700/80", !isActive);
        });
    }

    function renderColumnCanvas(state) {
        if (!state || !state.root) {
            return;
        }
        const root = state.root;

        const canvas = root.querySelector("[data-sort-canvas]");
        if (!canvas) {
            return;
        }

        const rect = canvas.getBoundingClientRect();
        if (!rect.width || !rect.height) {
            return;
        }

        const canvasRatio = rect.width / Math.max(rect.height, 1);
        state.canvasAspectRatio = canvasRatio;

        const ctx = canvas.getContext("2d");
        const dpr = window.devicePixelRatio || 1;
        const pixelWidth = Math.max(1, Math.round(rect.width * dpr));
        const pixelHeight = Math.max(1, Math.round(rect.height * dpr));
        if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
            canvas.width = pixelWidth;
            canvas.height = pixelHeight;
        }

        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.save();
        ctx.scale(dpr, dpr);
        ctx.fillStyle = "rgba(15,23,42,0.05)";
        ctx.fillRect(0, 0, rect.width, rect.height);

        state.canvasHotspots = [];
        state.canvasTransform = null;

        const allColumns = Array.isArray(state.columns)
            ? state.columns.map((column, index) => ({ column, index }))
            : [];
        const isManualMode = state.mode === "manual";
        const visibleColumns = isManualMode ? getVisibleColumns(state) : allColumns;
        if (!visibleColumns.length) {
            ctx.restore();
            setCanvasMessage(state, "Sorting data not available.");
            return;
        }
        if (!state.imageReady || !state.baseImage) {
            ctx.restore();
            setCanvasMessage(state, "Image loading…");
            return;
        }

        const imageWidth = state.baseImage.naturalWidth || state.baseImage.width;
        const imageHeight = state.baseImage.naturalHeight || state.baseImage.height;

        let cropX = 0;
        let cropY = 0;
        let cropWidth = imageWidth;
        let cropHeight = imageHeight;

        if (isManualMode) {
            const bounds = computeColumnsBoundingBox(visibleColumns, state.glyphs);
            if (!bounds) {
                ctx.restore();
                setCanvasMessage(state, "Glyph geometry missing.");
                return;
            }
            setCanvasMessage(state, null);
            const padding = Math.max(30, Math.min(120, Math.max(bounds.width, bounds.height) * 0.1));
            const desiredWidth = Math.min(imageWidth, bounds.width + padding * 2);
            const desiredHeight = Math.min(imageHeight, bounds.height + padding * 2);
            cropX = Math.max(0, bounds.minX - padding);
            cropY = Math.max(0, bounds.minY - padding);
            if (cropX + desiredWidth > imageWidth) {
                cropX = Math.max(0, imageWidth - desiredWidth);
            }
            if (cropY + desiredHeight > imageHeight) {
                cropY = Math.max(0, imageHeight - desiredHeight);
            }
            cropWidth = Math.max(1, Math.min(desiredWidth, imageWidth));
            cropHeight = Math.max(1, Math.min(desiredHeight, imageHeight));
        } else {
            setCanvasMessage(state, null);
        }

        const baseViewRect = {
            x: cropX,
            y: cropY,
            width: cropWidth,
            height: cropHeight,
        };
        const useStoredView =
            state.viewWindow &&
            state.viewWindow.locked &&
            state.viewWindow.mode === state.mode;
        const normalizedBaseView = normalizeViewWindow(baseViewRect, canvasRatio, imageWidth, imageHeight);
        const viewRect = useStoredView
            ? normalizeViewWindow(state.viewWindow, canvasRatio, imageWidth, imageHeight)
            : normalizedBaseView;
        state.viewWindow = {
            ...viewRect,
            locked: Boolean(useStoredView),
            mode: state.mode,
        };

        cropX = state.viewWindow.x;
        cropY = state.viewWindow.y;
        cropWidth = state.viewWindow.width;
        cropHeight = state.viewWindow.height;

        const scale = Math.min(rect.width / cropWidth, rect.height / cropHeight) || 1;
        const drawWidth = cropWidth * scale;
        const drawHeight = cropHeight * scale;
        const offsetX = (rect.width - drawWidth) / 2;
        const offsetY = (rect.height - drawHeight) / 2;

        state.canvasTransform = {
            offsetX,
            offsetY,
            scale,
            cropX,
            cropY,
            drawWidth,
            drawHeight,
        };

        ctx.drawImage(
            state.baseImage,
            cropX,
            cropY,
            cropWidth,
            cropHeight,
            offsetX,
            offsetY,
            drawWidth,
            drawHeight
        );

        const focusEntry = visibleColumns.find((entry) => entry.index === state.focusIndex);
        const renderColumns = isManualMode && focusEntry ? [focusEntry] : visibleColumns;
        const selectedGlyphId =
            state.activeGlyphId !== null && state.activeGlyphId !== undefined
                ? String(state.activeGlyphId)
                : null;

        const measurement = state.measurement || {};
        const hideGlyphs = Boolean(measurement.active || measurement.lastSegment);
        if (!hideGlyphs) {
            renderColumns.forEach((entry) => {
                const ids = Array.isArray(entry.column?.glyph_ids) ? entry.column.glyph_ids : [];
                ids.forEach((glyphId) => {
                    const glyph = state.glyphs[String(glyphId)];
                    if (!glyph) {
                        return;
                    }
                    const glyphX = Number(glyph.x);
                    const glyphY = Number(glyph.y);
                    const glyphWidth = Number(glyph.width);
                    const glyphHeight = Number(glyph.height);
                    if (
                        [glyphX, glyphY, glyphWidth, glyphHeight].some(
                            (value) => !Number.isFinite(value)
                        )
                    ) {
                        return;
                    }
                    const relX = offsetX + (glyphX - cropX) * scale;
                    const relY = offsetY + (glyphY - cropY) * scale;
                    const relW = glyphWidth * scale;
                    const relH = glyphHeight * scale;
                    const isActiveColumn = entry.index === state.focusIndex;
                    const colors = getColumnColorConfig(entry.index);
                    if (state.mode === "auto") {
                        ctx.fillStyle = isActiveColumn ? colors.focusFill : colors.fill;
                        ctx.strokeStyle = isActiveColumn ? colors.focusStroke : colors.stroke;
                        ctx.lineWidth = isActiveColumn ? 2 : 1;
                    } else {
                        ctx.fillStyle = isActiveColumn ? MANUAL_FOCUS_FILL : MANUAL_NEIGHBOR_FILL;
                        ctx.strokeStyle = isActiveColumn ? MANUAL_FOCUS_STROKE : MANUAL_NEIGHBOR_STROKE;
                        ctx.lineWidth = isActiveColumn ? 2 : 1;
                    }
                    ctx.fillRect(relX, relY, relW, relH);
                    ctx.strokeRect(relX, relY, relW, relH);

                    const isSelectedGlyph = selectedGlyphId !== null && String(glyphId) === selectedGlyphId;
                    if (isSelectedGlyph) {
                        ctx.save();
                        ctx.lineWidth = ctx.lineWidth + 2;
                        ctx.strokeStyle = "rgba(248, 113, 113, 0.95)";
                        ctx.shadowColor = "rgba(248, 113, 113, 0.6)";
                        ctx.shadowBlur = 12;
                        ctx.strokeRect(relX, relY, relW, relH);
                        ctx.restore();
                    }

                    state.canvasHotspots.push({
                        glyphId,
                        columnIndex: entry.index,
                        x: relX,
                        y: relY,
                        width: relW,
                        height: relH,
                    });
                });
            });
        }

        renderMeasurementOverlay(ctx, state, state.canvasTransform);

        ctx.restore();
    }

    function renderMeasurementOverlay(ctx, state, transform) {
        if (!ctx || !state?.measurement || !transform) {
            return;
        }
        const measurement = state.measurement;
        const hasStart = Boolean(measurement.startPoint);
        const hasSegment =
            Boolean(measurement.lastSegment?.start) && Boolean(measurement.lastSegment?.end);
        if (!hasStart && !hasSegment) {
            return;
        }
        ctx.save();
        const color = MEASUREMENT_LINE_COLOR;
        ctx.lineWidth = 2;
        ctx.strokeStyle = color;
        ctx.fillStyle = color;

        if (hasStart) {
            const projectedStart = projectImagePointToCanvas(measurement.startPoint, transform);
            if (projectedStart) {
                ctx.beginPath();
                ctx.arc(projectedStart.x, projectedStart.y, 6, 0, Math.PI * 2);
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(projectedStart.x, projectedStart.y, 3, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        if (hasSegment) {
            const segment = measurement.lastSegment;
            const startPoint = projectImagePointToCanvas(segment.start, transform);
            const endPoint = projectImagePointToCanvas(segment.end, transform);
            if (startPoint && endPoint) {
                ctx.strokeStyle = color;
                ctx.beginPath();
                ctx.moveTo(startPoint.x, startPoint.y);
                ctx.lineTo(endPoint.x, endPoint.y);
                ctx.stroke();

                const label = `${Math.round(Math.abs(segment.end.x - segment.start.x))} px`;
                const labelX = (startPoint.x + endPoint.x) / 2;
                const lineY = (startPoint.y + endPoint.y) / 2;
                const labelY = Math.max(14, lineY - 14);
                ctx.save();
                ctx.font = "12px 'Inter', 'Segoe UI', sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                const metrics = ctx.measureText(label);
                const paddingX = 6;
                const paddingY = 3;
                const boxWidth = metrics.width + paddingX * 2;
                const boxHeight = 18;
                ctx.fillStyle = MEASUREMENT_TEXT_BG;
                ctx.strokeStyle = "rgba(15, 23, 42, 0.2)";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.rect(labelX - boxWidth / 2, labelY - boxHeight / 2, boxWidth, boxHeight);
                ctx.fill();
                ctx.stroke();
                ctx.fillStyle = MEASUREMENT_TEXT_COLOR;
                ctx.fillText(label, labelX, labelY);
                ctx.restore();
                ctx.strokeStyle = color;
                ctx.fillStyle = color;
            }
        }

        ctx.restore();
    }

    function projectImagePointToCanvas(point, transform) {
        if (!point || !transform || !Number.isFinite(transform.scale) || transform.scale <= 0) {
            return null;
        }
        return {
            x: transform.offsetX + (point.x - transform.cropX) * transform.scale,
            y: transform.offsetY + (point.y - transform.cropY) * transform.scale,
        };
    }

    function getImagePointFromEvent(event, state) {
        if (!state?.canvasTransform) {
            return null;
        }
        const transform = state.canvasTransform;
        const canvas = event.currentTarget;
        if (!canvas) {
            return null;
        }
        const rect = canvas.getBoundingClientRect();
        if (!rect.width || !rect.height || !transform.scale) {
            return null;
        }
        const pointerX = event.clientX - rect.left;
        const pointerY = event.clientY - rect.top;
        const localX = pointerX - transform.offsetX;
        const localY = pointerY - transform.offsetY;
        if (localX < 0 || localY < 0 || localX > transform.drawWidth || localY > transform.drawHeight) {
            return null;
        }
        return {
            x: transform.cropX + localX / transform.scale,
            y: transform.cropY + localY / transform.scale,
        };
    }

    function scheduleMeasurementCleanup(state, segment) {
        if (!state?.measurement) {
            return;
        }
        clearMeasurementCleanup(state);
        if (!segment) {
            return;
        }
        state.measurement.cleanupTimer = window.setTimeout(() => {
            if (state.measurement.lastSegment === segment) {
                state.measurement.lastSegment = null;
                state.measurement.cleanupTimer = null;
                renderColumnCanvas(state);
            }
        }, 2400);
    }

    function clearMeasurementCleanup(state) {
        if (state?.measurement?.cleanupTimer) {
            clearTimeout(state.measurement.cleanupTimer);
            state.measurement.cleanupTimer = null;
        }
    }

    function applyMeasuredTolerance(state, length) {
        if (!state?.root || !Number.isFinite(length)) {
            return;
        }
        const rounded = Math.max(1, Math.round(length));
        setToleranceValue(state.root, rounded);
    }

    function resetMeasurementState(state) {
        if (!state) {
            return;
        }
        if (!state.measurement) {
            state.measurement = {
                active: false,
                startPoint: null,
                lastSegment: null,
                cleanupTimer: null,
            };
        }
        clearMeasurementCleanup(state);
        state.measurement.active = false;
        state.measurement.startPoint = null;
        state.measurement.lastSegment = null;
        updateMeasurementButtonState(state);
    }

    function computeColumnsBoundingBox(visibleColumns, glyphs) {
        let minX = Number.POSITIVE_INFINITY;
        let minY = Number.POSITIVE_INFINITY;
        let maxX = Number.NEGATIVE_INFINITY;
        let maxY = Number.NEGATIVE_INFINITY;
        let hasGlyph = false;

        visibleColumns.forEach((entry) => {
            const glyphIds = Array.isArray(entry.column?.glyph_ids) ? entry.column.glyph_ids : [];
            glyphIds.forEach((glyphId) => {
                const glyph = glyphs[String(glyphId)];
                if (!glyph) {
                    return;
                }
                const glyphX = Number(glyph.x);
                const glyphY = Number(glyph.y);
                const glyphWidth = Number(glyph.width);
                const glyphHeight = Number(glyph.height);
                if (
                    [glyphX, glyphY, glyphWidth, glyphHeight].some(
                        (value) => !Number.isFinite(value)
                    )
                ) {
                    return;
                }
                hasGlyph = true;
                minX = Math.min(minX, glyphX);
                minY = Math.min(minY, glyphY);
                maxX = Math.max(maxX, glyphX + glyphWidth);
                maxY = Math.max(maxY, glyphY + glyphHeight);
            });
        });

        if (!hasGlyph) {
            return null;
        }

        return {
            minX,
            minY,
            maxX,
            maxY,
            width: Math.max(1, maxX - minX),
            height: Math.max(1, maxY - minY),
        };
    }

    function renderManualColumns(state) {
        const root = state.root;
        if (!root) {
            return;
        }
        const container = root.querySelector("[data-sort-columns]");
        if (!container) {
            return;
        }
        container.innerHTML = "";

        const columns = Array.isArray(state.columns) ? state.columns : [];
        const glyphs = state.glyphs || {};

        if (!columns.length) {
            container.innerHTML =
                '<p class="text-xs text-text-secondary-light dark:text-text-secondary-dark">No sorting data available.</p>';
        } else {
            columns.forEach((column, index) => {
                container.appendChild(createColumnElement(column, glyphs, false, index, state));
            });
        }

        const collapseBtn = root.querySelector("[data-sort-collapse-all]");
        if (collapseBtn && !collapseBtn.dataset.bound) {
            collapseBtn.addEventListener("click", () => {
                container.querySelectorAll("[data-sort-column-body]").forEach((body) => {
                    body.classList.add("hidden");
                });
                container.querySelectorAll("[data-sort-column-icon]").forEach((icon) => {
                    icon.textContent = "chevron_right";
                });
            });
            collapseBtn.dataset.bound = "true";
        }

        if (
            typeof state.activeColumnIndex === "number" &&
            state.activeGlyphId !== null &&
            !Number.isNaN(state.activeColumnIndex)
        ) {
            highlightManualGlyph(state, state.activeColumnIndex, state.activeGlyphId, {
                scroll: false,
            });
        }
    }

    function createColumnElement(column, glyphs, openDefault, columnIndex, state) {
        const glyphIds = Array.isArray(column?.glyph_ids) ? column.glyph_ids : [];
        const wrapper = document.createElement("div");
        wrapper.className =
            "rounded-lg border border-border-light dark:border-border-dark bg-white/80 dark:bg-gray-900/40 shadow-sm";
        wrapper.dataset.sortColumnIndex = String(columnIndex);

        const header = document.createElement("button");
        header.type = "button";
        header.className =
            "w-full flex items-center gap-2 px-3 py-2 text-sm font-semibold text-text-light dark:text-text-dark";

        const icon = document.createElement("span");
        icon.className = "material-symbols-outlined text-base";
        icon.dataset.sortColumnIcon = "true";
        icon.textContent = openDefault ? "expand_more" : "chevron_right";

        const label = document.createElement("span");
        label.textContent = `Column ${column?.col ?? "—"}`;

        const count = document.createElement("span");
        count.className =
            "ml-auto text-xs rounded-full bg-white/60 dark:bg-gray-900/60 px-2 py-0.5 border border-border-light dark:border-border-dark";
        count.textContent = `${glyphIds.length} glyph${glyphIds.length === 1 ? "" : "s"}`;

        header.append(icon, label, count);

        const body = document.createElement("div");
        body.className =
            "px-3 pb-3 space-y-2 text-sm text-text-secondary-light dark:text-text-secondary-dark" +
            (openDefault ? "" : " hidden");
        body.dataset.sortColumnBody = "true";

        header.addEventListener("click", () => {
            const hidden = body.classList.toggle("hidden");
            icon.textContent = hidden ? "chevron_right" : "expand_more";
        });

        if (!glyphIds.length) {
            const empty = document.createElement("p");
            empty.className = "text-xs text-text-secondary-light dark:text-text-secondary-dark";
            empty.textContent = "No glyphs in this column.";
            body.append(empty);
        } else {
            glyphIds.forEach((glyphId) => {
                body.append(
                    createGlyphRow(glyphId, glyphs[String(glyphId)] || {}, columnIndex, state)
                );
            });
        }

        wrapper.append(header, body);
        return wrapper;
    }

    function moveGlyphToNeighbor(state, columnIndex, glyphId, direction) {
        if (!state || !Array.isArray(state.columns)) {
            return;
        }
        const targetIndex = columnIndex + direction;
        if (targetIndex < 0 || targetIndex >= state.columns.length) {
            return;
        }
        const sourceColumn = state.columns[columnIndex];
        const targetColumn = state.columns[targetIndex];
        if (!sourceColumn || !targetColumn) {
            return;
        }
        const sourceGlyphs = Array.isArray(sourceColumn.glyph_ids) ? sourceColumn.glyph_ids : [];
        const glyphIdx = sourceGlyphs.indexOf(glyphId);
        if (glyphIdx === -1) {
            return;
        }
        sourceGlyphs.splice(glyphIdx, 1);
        sourceColumn.glyph_ids = sourceGlyphs;

        const targetGlyphs = Array.isArray(targetColumn.glyph_ids) ? targetColumn.glyph_ids : [];
        targetGlyphs.push(glyphId);
        targetGlyphs.sort(
            (a, b) => getGlyphSortKey(state.glyphs, a) - getGlyphSortKey(state.glyphs, b)
        );
        targetColumn.glyph_ids = targetGlyphs;

        state.activeColumnIndex = null;
        state.activeGlyphId = null;
        state.preserveViewOnFocus = true;
        renderManualColumns(state);
        renderColumnChart(state.root, { columns: state.columns }, state);
        onColumnFocusChange(state);
        setUnsavedChanges(state, true);
    }

    function getGlyphSortKey(glyphs, glyphId) {
        const meta = glyphs?.[String(glyphId)];
        if (!meta) {
            return Number.MAX_SAFE_INTEGER;
        }
        const y = Number(meta.y);
        if (Number.isFinite(y)) {
            return y;
        }
        const x = Number(meta.x);
        return Number.isFinite(x) ? x : Number.MAX_SAFE_INTEGER;
    }

    function createGlyphRow(glyphId, meta, columnIndex, state) {
        const row = document.createElement("div");
        row.className =
            "flex items-center gap-2 rounded-lg border border-border-light dark:border-border-dark bg-white/90 dark:bg-gray-900/60 px-2 py-2 cursor-pointer";
        row.dataset.sortGlyph = String(glyphId);
        row.dataset.sortGlyphColumn = String(columnIndex);

        const dragIcon = document.createElement("span");
        dragIcon.className = "material-symbols-outlined text-lg text-text-secondary-light dark:text-text-secondary-dark";
        dragIcon.textContent = "drag_indicator";

        const badge = document.createElement("div");
        badge.className =
            "size-8 rounded-md bg-amber-100 text-amber-700 font-semibold flex items-center justify-center border border-amber-300 text-base";
        badge.style.fontFamily =
            "'Noto Sans Egyptian Hieroglyphs','Segoe UI Historic','Segoe UI Symbol','Noto Sans',sans-serif";
        const unicodeSymbol = formatUnicodeSymbol(meta.unicode);
        badge.textContent = unicodeSymbol || meta.gardiner_code || String(glyphId);

        const info = document.createElement("div");
        info.className = "flex flex-col";
        const title = meta.gardiner_code || `Glyph ${glyphId}`;
        const unicodeLabel = unicodeSymbol
            ? `${unicodeSymbol} ${meta.unicode || ""}`.trim()
            : meta.unicode || "";
        const coords =
            typeof meta.x === "number" && typeof meta.y === "number"
                ? `(${Math.round(meta.x)}, ${Math.round(meta.y)})`
                : "";
        const size =
            typeof meta.width === "number" && typeof meta.height === "number"
                ? `${Math.round(meta.width)}×${Math.round(meta.height)}`
                : "";
        const metaLine = [unicodeLabel, coords, size].filter(Boolean).join(" • ") || `ID ${glyphId}`;
        info.innerHTML = `<span class="text-sm font-semibold text-text-light dark:text-text-dark">${title}</span><span class="text-xs text-text-secondary-light dark:text-text-secondary-dark">${metaLine}</span>`;

        const controls = document.createElement("div");
        controls.className = "ml-auto flex items-center gap-1";

        const hasLeft = columnIndex > 0;
        const hasRight = columnIndex < (state.columns?.length || 0) - 1;

        const leftBtn = document.createElement("button");
        leftBtn.type = "button";
        leftBtn.className =
            "size-7 rounded-full border border-border-light dark:border-border-dark flex items-center justify-center text-text-secondary-light dark:text-text-secondary-dark hover:bg-primary/10 disabled:opacity-40 disabled:pointer-events-none";
        leftBtn.innerHTML = '<span class="material-symbols-outlined text-sm leading-none">chevron_left</span>';
        leftBtn.disabled = !hasLeft;
        leftBtn.addEventListener("click", (event) => {
            event.stopPropagation();
            moveGlyphToNeighbor(state, columnIndex, glyphId, -1);
        });

        const rightBtn = document.createElement("button");
        rightBtn.type = "button";
        rightBtn.className =
            "size-7 rounded-full border border-border-light dark:border-border-dark flex items-center justify-center text-text-secondary-light dark:text-text-secondary-dark hover:bg-primary/10 disabled:opacity-40 disabled:pointer-events-none";
        rightBtn.innerHTML = '<span class="material-symbols-outlined text-sm leading-none">chevron_right</span>';
        rightBtn.disabled = !hasRight;
        rightBtn.addEventListener("click", (event) => {
            event.stopPropagation();
            moveGlyphToNeighbor(state, columnIndex, glyphId, 1);
        });

        controls.append(leftBtn, rightBtn);

        row.append(dragIcon, badge, info, controls);

        row.addEventListener("click", () => {
            state.focusIndex = columnIndex;
            state.activeColumnIndex = columnIndex;
            state.activeGlyphId = glyphId;
            onColumnFocusChange(state);
            highlightManualGlyph(state, columnIndex, glyphId);
        });
        return row;
    }

    function highlightManualGlyph(state, columnIndex, glyphId, options = {}) {
        const root = state.root;
        if (!root) {
            return;
        }
        const container = root.querySelector("[data-sort-columns]");
        if (!container) {
            return;
        }
        clearManualGlyphHighlight(container);
        const columnEl = container.querySelector(
            `[data-sort-column-index="${columnIndex}"]`
        );
        if (!columnEl) {
            return;
        }
        expandColumnElement(columnEl);
        const glyphRow = columnEl.querySelector(`[data-sort-glyph="${glyphId}"]`);
        if (!glyphRow) {
            return;
        }
        glyphRow.classList.add(
            "ring-2",
            "ring-primary/70",
            "ring-offset-1",
            "ring-offset-white",
            "dark:ring-offset-gray-900"
        );
        if (options.scroll !== false) {
            glyphRow.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }
    }

    function getColumnColorConfig(columnIndex) {
        if (!COLUMN_COLOR_PALETTE.length) {
            return {
                fill: "rgba(96, 165, 250, 0.25)",
                stroke: "rgba(59, 130, 246, 0.9)",
                focusFill: "rgba(96, 165, 250, 0.35)",
                focusStroke: "rgba(37, 99, 235, 1)",
                chartBg: "rgba(96, 165, 250, 0.45)",
                chartActive: "rgba(59, 130, 246, 0.85)",
            };
        }
        const index = Number.isFinite(columnIndex) ? columnIndex : 0;
        return COLUMN_COLOR_PALETTE[((index % COLUMN_COLOR_PALETTE.length) + COLUMN_COLOR_PALETTE.length) % COLUMN_COLOR_PALETTE.length];
    }

    function clearManualGlyphHighlight(container) {
        container
            .querySelectorAll("[data-sort-glyph].ring-2")
            .forEach((row) => {
                row.classList.remove(
                    "ring-2",
                    "ring-primary/70",
                    "ring-offset-1",
                    "ring-offset-white",
                    "dark:ring-offset-gray-900"
                );
            });
    }

    function expandColumnElement(columnEl) {
        const body = columnEl.querySelector("[data-sort-column-body]");
        if (!body) {
            return;
        }
        if (body.classList.contains("hidden")) {
            body.classList.remove("hidden");
            const icon = columnEl.querySelector("[data-sort-column-icon]");
            if (icon) {
                icon.textContent = "expand_more";
            }
        }
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
            return parts.map((hex) => String.fromCodePoint(parseInt(hex, 16))).join("");
        } catch (err) {
            return "";
        }
    }

    function setupLeaveWarning(state) {
        const root = state?.root;
        if (!root) {
            return;
        }
        const backLink = root.querySelector("[data-sort-back]");
        if (!backLink) {
            return;
        }
        backLink.addEventListener("click", (event) => {
            if (!state.hasUnsavedChanges) {
                return;
            }
            const confirmed = window.confirm(
                "You have unsaved changes. Leave the sorting view and discard them?"
            );
            if (!confirmed) {
                event.preventDefault();
            }
        });
    }

    function setUnsavedChanges(state, value) {
        if (!state) {
            return;
        }
        state.hasUnsavedChanges = Boolean(value);
    }

    function normalizeViewWindow(view, aspectRatio, imageWidth, imageHeight) {
        if (!imageWidth || !imageHeight) {
            return null;
        }
        const hasView = view && typeof view === "object";
        const baseView = hasView
            ? clampViewWindow(view, imageWidth, imageHeight)
            : { x: 0, y: 0, width: imageWidth, height: imageHeight };
        const safeAspect =
            Number.isFinite(aspectRatio) && aspectRatio > 0
                ? aspectRatio
                : baseView.width / Math.max(baseView.height, 1);
        const projected = alignWindowToAspect(baseView, safeAspect, imageWidth, imageHeight);
        return {
            ...projected,
            aspectRatio: safeAspect,
        };
    }

    function alignWindowToAspect(baseView, aspectRatio, imageWidth, imageHeight) {
        if (!Number.isFinite(aspectRatio) || aspectRatio <= 0) {
            return { ...baseView };
        }
        let width = clamp(baseView.width, MIN_VIEW_SIZE, imageWidth);
        let height = clamp(baseView.height, MIN_VIEW_SIZE, imageHeight);
        let x = clamp(baseView.x, 0, Math.max(0, imageWidth - width));
        let y = clamp(baseView.y, 0, Math.max(0, imageHeight - height));
        let centerX = x + width / 2;
        let centerY = y + height / 2;

        const currentRatio = width / Math.max(height, 1);
        if (Math.abs(currentRatio - aspectRatio) > 0.001) {
            if (currentRatio < aspectRatio) {
                const expandedWidth = height * aspectRatio;
                if (expandedWidth <= imageWidth) {
                    width = expandedWidth;
                } else {
                    width = imageWidth;
                    height = width / aspectRatio;
                }
            } else {
                const expandedHeight = width / aspectRatio;
                if (expandedHeight <= imageHeight) {
                    height = expandedHeight;
                } else {
                    height = imageHeight;
                    width = height * aspectRatio;
                }
            }
        }

        if (width < MIN_VIEW_SIZE) {
            width = MIN_VIEW_SIZE;
            height = width / aspectRatio;
        }
        if (height < MIN_VIEW_SIZE) {
            height = MIN_VIEW_SIZE;
            width = height * aspectRatio;
        }
        if (width > imageWidth) {
            width = imageWidth;
            height = width / aspectRatio;
        }
        if (height > imageHeight) {
            height = imageHeight;
            width = height * aspectRatio;
        }

        const halfWidth = width / 2;
        const halfHeight = height / 2;
        const maxCenterX = imageWidth - halfWidth;
        const maxCenterY = imageHeight - halfHeight;
        centerX = clamp(centerX, halfWidth, Math.max(halfWidth, maxCenterX));
        centerY = clamp(centerY, halfHeight, Math.max(halfHeight, maxCenterY));

        x = clamp(centerX - halfWidth, 0, Math.max(0, imageWidth - width));
        y = clamp(centerY - halfHeight, 0, Math.max(0, imageHeight - height));

        return { x, y, width, height };
    }

    function clampViewWindow(view, imageWidth, imageHeight) {
        const width = clamp(view.width || imageWidth, MIN_VIEW_SIZE, imageWidth);
        const height = clamp(view.height || imageHeight, MIN_VIEW_SIZE, imageHeight);
        const x = clamp(view.x || 0, 0, Math.max(0, imageWidth - width));
        const y = clamp(view.y || 0, 0, Math.max(0, imageHeight - height));
        return { x, y, width, height };
    }

    function clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }
})();
