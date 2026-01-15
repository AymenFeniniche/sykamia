const API_BASE = "http://127.0.0.1:8000";

const isSeriesPage = window.location.pathname.endsWith("series.html");
const isFilmsPage  = window.location.pathname.endsWith("films.html");

// ---------- Genres (split + unique + contains) ----------
const GENRE_SPLIT_REGEX = /&|,|\//;

function splitGenres(value) {
  if (!value) return [];
  return String(value)
    .split(GENRE_SPLIT_REGEX)
    .map(s => s.trim())
    .filter(Boolean);
}

function extractUniqueGenresFromItems(items) {
  const set = new Set();
  items.forEach(it => {
    const raw = it.genre ?? it.genres ?? "";
    splitGenres(raw).forEach(g => set.add(g));
  });
  return Array.from(set).sort((a, b) => a.localeCompare(b, "fr"));
}

function movieHasGenre(movie, selectedGenre) {
  if (!selectedGenre) return true; // "" = tous
  const raw = movie.genre ?? movie.genres ?? "";
  return splitGenres(raw).includes(selectedGenre);
}

// ---------- Pagination ----------
let currentPage = 1;
const itemsPerPage = 50;
let allItems = [];

function qs(id) {
  return document.getElementById(id);
}

async function fetchJSON(url) {
  const res = await fetch(url);
  console.log('Fetch URL:', url, 'Status:', res.status);
  if (!res.ok) throw new Error(`HTTP ${res.status} - ${url}`);
  return await res.json();
}

// ---------- Render ----------
function renderCards(containerEl, items, typeLabel, type) {
  containerEl.innerHTML = "";

  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const itemsToShow = items.slice(startIndex, endIndex);

  itemsToShow.forEach((item) => {
    const card = document.createElement("div");
    card.className = "card-movies";
    card.style.cursor = "pointer";

    const poster = item.poster_url || "images/placeholder.jpg"; // fallback
    const title  = item.title || "Sans titre";
    const genreText = item.genre ? ` | ${item.genre}` : "";

    card.innerHTML = `
      <div class="card-movies-img">
        <img src="${poster}" alt="${title}">
      </div>
      <h3>${title}</h3>
      <span>${typeLabel}${genreText}</span>
    `;

    card.addEventListener("click", () => {
      const detailsUrl = `details.html?type=${type}&id=${encodeURIComponent(item.id)}`;
      window.location.href = detailsUrl;
    });

    containerEl.appendChild(card);
  });

  updatePaginationControls(items.length);
}

function fillSelect(selectEl, values, placeholder) {
  selectEl.innerHTML = `<option value="">${placeholder}</option>`;
  values.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    selectEl.appendChild(opt);
  });
}

// ---------- URL builder ----------
function buildTitlesUrl(type) {
  const q     = qs("searchInput")?.value?.trim() || "";
  const genre = qs("filterGenre")?.value || "";
  const year  = qs("filterYear")?.value || "";
  const sort  = qs("sortOrder")?.value || "az";

  // backend attend asc/desc
  const order = sort === "za" ? "desc" : "asc";

  const params = new URLSearchParams();
  params.set("type", type);         // "movie" ou "series"
  params.set("order", order);
  if (q)     params.set("q", q);
  if (genre) params.set("genre", genre);
  if (year)  params.set("year", year);

  return `${API_BASE}/api/titles?${params.toString()}`;
}

// ---------- Main init ----------
async function initCatalogPage(type) {
  const containerSelector = type === "series" ? ".series-container" : ".movies-container";
  const container = document.querySelector(containerSelector);
  if (!container) return;

  // Pays non dispo
  const countrySelect = qs("filterCountry");
  if (countrySelect) {
    countrySelect.disabled = true;
    countrySelect.innerHTML = `<option value="">Pays (non disponible)</option>`;
  }

  // 1) Charger filtres
  const filters = await fetchJSON(`${API_BASE}/api/filters?type=${type}`);

  // ✅ GENRES : au lieu d’afficher des combos, on split + unique
  if (qs("filterGenre")) {
    const rawGenres = filters.genres || [];
    const unique = Array.from(
      new Set(rawGenres.flatMap(g => splitGenres(g)))
    ).sort((a, b) => a.localeCompare(b, "fr"));

    fillSelect(qs("filterGenre"), unique, "Genre (tous)");
  }

  if (qs("filterYear")) {
    fillSelect(qs("filterYear"), filters.years || [], "Année (toutes)");
  }

  // 2) Recharge la liste
  async function refresh() {
    const url = buildTitlesUrl(type);
    const data = await fetchJSON(url);
    allItems = data.items || [];
    currentPage = 1;

    // ✅ BONUS : filtre “contient” côté front (même si backend renvoie combos)
    const selectedGenre = qs("filterGenre")?.value || "";
    const filtered = selectedGenre
      ? allItems.filter(m => movieHasGenre(m, selectedGenre))
      : allItems;

    renderCards(container, filtered, type === "series" ? "Série" : "Film", type);
  }

  // 3) Events
  ["filterGenre", "filterYear", "sortOrder"].forEach((id) => {
    const el = qs(id);
    if (el) el.addEventListener("change", refresh);
  });

  const searchEl = qs("searchInput");
  if (searchEl) {
    let timer = null;
    searchEl.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(refresh, 250);
    });
  }

  const resetBtn = qs("resetBtn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      if (qs("filterGenre")) qs("filterGenre").value = "";
      if (qs("filterYear"))  qs("filterYear").value = "";
      if (qs("sortOrder"))   qs("sortOrder").value = "az";
      if (qs("searchInput")) qs("searchInput").value = "";
      refresh();
    });
  }

  // 4) Premier chargement + pagination
  await refresh();
  setupPaginationEvents(type, container);
}

// ---------- Pagination controls ----------
function updatePaginationControls(totalItems) {
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const pageInfo = qs("pageInfo");
  const prevBtn = qs("prevPage");
  const nextBtn = qs("nextPage");

  if (pageInfo) pageInfo.textContent = `Page ${currentPage} / ${totalPages} (${totalItems} items)`;
  if (prevBtn) prevBtn.disabled = currentPage === 1;
  if (nextBtn) nextBtn.disabled = currentPage >= totalPages;
}

function setupPaginationEvents(type, container) {
  const prevBtn = qs("prevPage");
  const nextBtn = qs("nextPage");

  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage--;
        // ⚠️ IMPORTANT : on rerender la page à partir de allItems filtrés par genre
        const selectedGenre = qs("filterGenre")?.value || "";
        const filtered = selectedGenre ? allItems.filter(m => movieHasGenre(m, selectedGenre)) : allItems;
        renderCards(container, filtered, type === "series" ? "Série" : "Film", type);
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      const selectedGenre = qs("filterGenre")?.value || "";
      const filtered = selectedGenre ? allItems.filter(m => movieHasGenre(m, selectedGenre)) : allItems;

      const totalPages = Math.ceil(filtered.length / itemsPerPage);
      if (currentPage < totalPages) {
        currentPage++;
        renderCards(container, filtered, type === "series" ? "Série" : "Film", type);
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    });
  }
}

// ---------- Boot ----------
document.addEventListener("DOMContentLoaded", async () => {
  try {
    if (isSeriesPage) await initCatalogPage("series");
    if (isFilmsPage)  await initCatalogPage("movie");
  } catch (e) {
    console.error("Erreur chargement catalogue:", e);
  }
});
