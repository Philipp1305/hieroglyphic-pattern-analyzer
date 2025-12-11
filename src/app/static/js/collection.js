document.addEventListener("DOMContentLoaded", () => {
  const gridRoot = document.querySelector("[data-collection-grid]");
  if (!gridRoot) {
    return;
  }

  const emptyState = gridRoot.querySelector("[data-collection-empty]");

  const renderEmpty = (message) => {
    if (emptyState) {
      emptyState.textContent = message;
    }
  };

  const renderCards = (items) => {
    if (!items.length) {
      renderEmpty("No collection entries found yet.");
      return;
    }

    const cards = document.createElement("div");
    cards.className = "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6";
    cards.innerHTML = items
      .map(
        (item) => `
        <a class="group flex flex-col overflow-hidden rounded-xl border border-border-light dark:border-border-dark bg-card-light dark:bg-card-dark shadow-sm transition-all hover:shadow-lg hover:-translate-y-1"
            href="/overview?id=${encodeURIComponent(item.id)}">
            <div class="aspect-h-3 aspect-w-4 overflow-hidden">
                ${
                  item.image_src
                    ? `<img class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                        alt="${item.title || "Collection preview"}"
                        src="${item.image_src}" />`
                    : `<div class="flex h-full w-full items-center justify-center bg-stone-200 dark:bg-stone-800 text-sm text-text-secondary-light dark:text-text-secondary-dark">
                        No preview
                      </div>`
                }
            </div>
            <div class="p-4">
                <div class="flex items-center justify-between gap-2">
                    <p class="text-sm font-semibold truncate">${item.title || "Untitled item"}</p>
                    <span class="text-xs rounded-full px-2 py-0.5 ${statusClass(item.status_variant)}">
                        ${item.status_label || "Unknown"}
                    </span>
                </div>
            </div>
        </a>
    `
      )
      .join("");

    gridRoot.innerHTML = "";
    gridRoot.appendChild(cards);
  };

  const statusClass = (variant) => {
    switch (variant) {
      case "success":
        return "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200";
      case "warning":
        return "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200";
      case "error":
        return "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-200";
      default:
        return "bg-slate-200 text-slate-700 dark:bg-slate-600/30 dark:text-slate-200";
    }
  };

  const url = `/api/collection?_=${Date.now()}`;
  fetch(url, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to load collection");
      }
      return response.json();
    })
    .then((data) => renderCards(data.items || []))
    .catch((error) => {
      console.error(error);
      renderEmpty("Failed to load collection.");
    });
});
