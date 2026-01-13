const API_BASE = "http://127.0.0.1:8000";

const isSeriesPage = window.location.pathname.endsWith("series.html");
const isFilmsPage = window.location.pathname.endsWith("films.html");

function qs(id) {
  return document.getElementById(id);
}

const TMDB_KEY = "TA_CLE_API";
const URL = `https://api.themoviedb.org/3/movie/now_playing?api_key=${TMDB_KEY}&language=fr-FR&page=1`;

async function loadNowPlaying() {
  const res = await fetch(URL);
  const data = await res.json();
  return data.results; // liste de films
}
async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} - ${url}`);
  return await res.json();
}

function renderCards(containerEl, items, typeLabel) {
  containerEl.innerHTML = "";

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "card-movies";

    card.innerHTML = `
      <div class="card-movies-img">
        <img src="${item.poster_url}" alt="${item.title}">
      </div>
      <h3>${item.title}</h3>
      <span>${typeLabel}${item.genre ? " | " + item.genre : ""}</span>
    `;

    containerEl.appendChild(card);
  });
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

function buildTitlesUrl(type) {
  const q = qs("searchInput")?.value?.trim() || "";
  const genre = qs("filterGenre")?.value || "";
  const year = qs("filterYear")?.value || "";
  const sort = qs("sortOrder")?.value || "az";

  const order = sort === "za" ? "desc" : "asc";

  const params = new URLSearchParams();
  params.set("type", type);
  if (q) params.set("q", q);
  if (genre) params.set("genre", genre);
  if (year) params.set("year", year);
  params.set("order", order);

  return `${API_BASE}/api/titles?${params.toString()}`;
}

async function initCatalogPage(type) {
  const containerSelector = type === "series" ? ".series-container" : ".movies-container";
  const container = document.querySelector(containerSelector);
  if (!container) return;

  // ✅ Pays : TMDb scraping -> non dispo. On désactive le filtre.
  const countrySelect = qs("filterCountry");
  if (countrySelect) {
    countrySelect.disabled = true;
    countrySelect.innerHTML = `<option value="">Pays (non disponible)</option>`;
  }

  // 1) Charger filtres
  const filters = await fetchJSON(`${API_BASE}/api/filters?type=${type}`);
  if (qs("filterGenre")) fillSelect(qs("filterGenre"), filters.genres || [], "Genre (tous)");
  if (qs("filterYear")) fillSelect(qs("filterYear"), filters.years || [], "Année (toutes)");

  // 2) Recharge la liste
  async function refresh() {
    const url = buildTitlesUrl(type);
    const data = await fetchJSON(url);
    renderCards(container, data.items || [], type === "series" ? "Série" : "Film");
  }

  // 3) Events
  ["filterGenre", "filterYear", "sortOrder"].forEach((id) => {
    const el = qs(id);
    if (el) el.addEventListener("change", refresh);
  });

  const searchEl = qs("searchInput");
  if (searchEl) {
    clearTimeout(window.__searchTimer);
    searchEl.addEventListener("input", () => {
      clearTimeout(window.__searchTimer);
      window.__searchTimer = setTimeout(refresh, 250);
    });
  }

  const resetBtn = qs("resetBtn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      if (qs("filterGenre")) qs("filterGenre").value = "";
      if (qs("filterYear")) qs("filterYear").value = "";
      if (qs("sortOrder")) qs("sortOrder").value = "az";
      if (qs("searchInput")) qs("searchInput").value = "";
      refresh();
    });
  }

  // 4) Premier chargement
  await refresh();
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    if (isSeriesPage) await initCatalogPage("series");
    if (isFilmsPage) await initCatalogPage("movie");
  } catch (e) {
    console.error("Erreur chargement catalogue:", e);
  }
});
