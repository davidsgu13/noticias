(function () {
  "use strict";

  const feedEl = document.getElementById("feed");
  const loadingMsg = document.getElementById("loadingMsg");
  const emptyState = document.getElementById("emptyState");
  const filtersEl = document.getElementById("filters");
  const lastUpdatedEl = document.getElementById("lastUpdated");
  const itemCountEl = document.getElementById("itemCount");

  let allItems = [];
  let activeFilter = "todas";

  // cache-bust para que GitHub Pages / el navegador no sirvan un JSON viejo
  const DATA_URL = "data/news.json?_=" + Date.now();

  function formatRelativeTime(isoString) {
    const date = new Date(isoString);
    const diffMs = Date.now() - date.getTime();
    const diffMin = Math.round(diffMs / 60000);

    if (diffMin < 1) return "justo ahora";
    if (diffMin < 60) return `hace ${diffMin} min`;
    const diffH = Math.round(diffMin / 60);
    if (diffH < 24) return `hace ${diffH} h`;
    const diffD = Math.round(diffH / 24);
    if (diffD === 1) return "ayer";
    return `hace ${diffD} días`;
  }

  function formatLastUpdated(isoString) {
    if (!isoString) return "sin datos todavía";
    const date = new Date(isoString);
    const bogota = new Intl.DateTimeFormat("es-CO", {
      timeZone: "America/Bogota",
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
    return `${bogota} (hora Bogotá)`;
  }

  function renderFilters(categories) {
    filtersEl.innerHTML = "";
    const all = document.createElement("button");
    all.className = "filters__chip is-active";
    all.dataset.filter = "todas";
    all.textContent = "Todas";
    filtersEl.appendChild(all);

    categories.forEach((cat) => {
      const chip = document.createElement("button");
      chip.className = "filters__chip";
      chip.dataset.filter = cat;
      chip.textContent = cat;
      filtersEl.appendChild(chip);
    });

    filtersEl.addEventListener("click", (e) => {
      const btn = e.target.closest(".filters__chip");
      if (!btn) return;
      activeFilter = btn.dataset.filter;
      [...filtersEl.children].forEach((c) =>
        c.classList.toggle("is-active", c === btn)
      );
      renderFeed();
    });
  }

  function renderFeed() {
    const items =
      activeFilter === "todas"
        ? allItems
        : allItems.filter((i) => i.category === activeFilter);

    feedEl.innerHTML = "";

    if (items.length === 0) {
      const p = document.createElement("p");
      p.className = "feed__loading";
      p.textContent = "No hay noticias en esta categoría todavía.";
      feedEl.appendChild(p);
      return;
    }

    items.forEach((item) => {
      const card = document.createElement("article");
      card.className = "card";
      card.dataset.sourceFlag = item.category === "fuente directa" ? "true" : "false";

      card.innerHTML = `
        <div class="card__meta">
          <span class="card__source">${escapeHtml(item.source)}</span>
          <span class="card__time" title="${escapeHtml(item.published)}">${formatRelativeTime(item.published)}</span>
        </div>
        <h2 class="card__title"><a href="${escapeAttr(item.link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a></h2>
        ${item.summary ? `<p class="card__summary">${escapeHtml(item.summary)}</p>` : ""}
        <span class="card__category">${escapeHtml(item.category)}</span>
      `;
      feedEl.appendChild(card);
    });
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));
  }

  function escapeAttr(str) {
    return escapeHtml(str);
  }

  async function init() {
    try {
      const res = await fetch(DATA_URL, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      allItems = Array.isArray(data.items) ? data.items : [];
      lastUpdatedEl.textContent = formatLastUpdated(data.last_updated_utc);
      itemCountEl.textContent = allItems.length
        ? `${allItems.length} noticias`
        : "";

      loadingMsg.remove();

      if (allItems.length === 0) {
        emptyState.hidden = false;
        return;
      }

      const categories = [...new Set(allItems.map((i) => i.category))].sort();
      renderFilters(categories);
      renderFeed();
    } catch (err) {
      console.error("No se pudo cargar data/news.json", err);
      loadingMsg.textContent =
        "No se pudo cargar el archivo de noticias. Si el sitio se acaba de publicar, espera al primer despliegue automático.";
    }
  }

  init();
})();
