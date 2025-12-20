document.addEventListener("DOMContentLoaded", () => {
  const gridRoot = document.querySelector("[data-collection-grid]");
  if (!gridRoot) {
    return;
  }

  const searchInput = document.querySelector("[data-collection-search]");
  const sortSelect = document.querySelector("[data-collection-sort]");
  let collectionItems = [];

  const renderEmpty = (message) => {
    gridRoot.innerHTML = `
      <div class="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-border-light dark:border-border-dark bg-card-light dark:bg-card-dark/70 py-16">
        <span class="relative flex h-8 w-8">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span class="relative inline-flex h-8 w-8 rounded-full bg-primary/70"></span>
        </span>
        <p class="text-sm text-text-secondary-light dark:text-text-secondary-dark">${message}</p>
      </div>
    `;
  };

  const statusClass = (variant) => {
    if (variant === "action") {
      return "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200";
    }
    return "bg-primary/10 text-primary border border-primary/20";
  };

  const renderCards = (items, emptyMessage = "No collection entries found yet.") => {
    if (!items.length) {
      renderEmpty(emptyMessage);
      return;
    }

    const cards = document.createElement("div");
    cards.className = "grid grid-cols-1 md:grid-cols-2 gap-6";
    cards.innerHTML = items
      .map(
        (item) => {
          const statusCode = (item.status_code || "").toString().trim().toUpperCase();
          const isActionRequired = statusCode === "SORT_VALIDATE";
          const variant = item.status_variant || "info";
          const mainBadgeClass = statusClass(variant);
          const statusLabel = item.status_label || "Unknown";
          return `
        <a class="group flex flex-col overflow-hidden rounded-2xl border border-border-light dark:border-border-dark bg-card-light dark:bg-card-dark shadow-lg transition-all hover:shadow-xl hover:-translate-y-1"
            href="/overview?id=${encodeURIComponent(item.id)}">
            <div class="aspect-[4/3] overflow-hidden">
                ${
                  item.image_src
                    ? `<img class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
                        alt="${item.title || "Collection preview"}"
                        src="${item.image_src}" />`
                    : `<div class="flex h-full w-full items-center justify-center bg-stone-200 dark:bg-stone-800 text-sm text-text-secondary-light dark:text-text-secondary-dark">
                        No preview
                      </div>`
                }
            </div>
            <div class="p-5 flex flex-col gap-2">
                <div class="flex items-center justify-between gap-2">
                    <p class="text-base font-semibold truncate">${item.title || "Untitled item"}</p>
                    <div class="flex flex-wrap items-center gap-2 justify-end">
                        ${
                          isActionRequired
                            ? `<span class="text-[11px] rounded-full px-2 py-0.5 ${statusClass("action")}">Action required</span>`
                            : ""
                        }
                        <span class="text-xs rounded-full px-2 py-0.5 ${mainBadgeClass}">
                            ${statusLabel}
                        </span>
                    </div>
                </div>
                <p class="text-xs text-text-secondary-light dark:text-text-secondary-dark">ID #${item.id}</p>
            </div>
        </a>
    `;
        }
      )
      .join("");

    gridRoot.innerHTML = "";
    gridRoot.appendChild(cards);
  };

  const filterAndSortItems = () => {
    const query = (searchInput?.value || "").trim().toLowerCase();
    const sortDirection = (sortSelect?.value || "desc").toLowerCase() === "asc" ? "asc" : "desc";

    const filtered = collectionItems.filter((item) => {
      if (!query) {
        return true;
      }
      return (item.title || "").toLowerCase().includes(query);
    });

    const sorted = [...filtered].sort((a, b) => {
      if (sortDirection === "asc") {
        return a.id - b.id;
      }
      return b.id - a.id;
    });

    const emptyMessage = query ? "No collection entries match your search." : "No collection entries found yet.";
    renderCards(sorted, emptyMessage);
  };

  if (searchInput) {
    searchInput.addEventListener("input", () => filterAndSortItems());
  }
  if (sortSelect) {
    sortSelect.addEventListener("change", () => filterAndSortItems());
  }

  const url = `/api/collection?_=${Date.now()}`;
  fetch(url, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to load collection");
      }
      return response.json();
    })
    .then((data) => {
      collectionItems = data.items || [];
      filterAndSortItems();
    })
    .catch((error) => {
      console.error(error);
      renderEmpty("Failed to load collection.");
    });
});
