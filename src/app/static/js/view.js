(function () {
    const init = () => {
        const area = document.querySelector("[data-highlight-area]");
        const buttons = document.querySelectorAll("[data-highlight-color]");
        if (!area || !buttons.length) {
            return;
        }

        const palette = {
            emerald: { bg: "rgba(34, 197, 94, 0.45)", border: "#22c55e" },
            amber: { bg: "rgba(245, 158, 11, 0.45)", border: "#f59e0b" },
            sky: { bg: "rgba(56, 189, 248, 0.45)", border: "#38bdf8" }
        };

        const applyColor = (key) => {
            const colors = palette[key] || palette.emerald;
            area.style.setProperty("--highlight-color-bg", colors.bg);
            area.style.setProperty("--highlight-color-border", colors.border);
            buttons.forEach((button) => {
                const isActive = button.dataset.highlightColor === key;
                button.setAttribute("aria-pressed", isActive ? "true" : "false");
            });
        };

        buttons.forEach((button) => {
            button.addEventListener("click", () => applyColor(button.dataset.highlightColor));
        });

        const active = document.querySelector("[data-highlight-color][aria-pressed='true']");
        applyColor(active ? active.dataset.highlightColor : "emerald");
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    } else {
        init();
    }
})();
