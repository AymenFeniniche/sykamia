const API_BASE = "http://127.0.0.1:8000";

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} - ${url}`);
  return await res.json();
}

async function loadDetails() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get('id');
  const type = params.get('type');

  console.log('ID:', id, 'Type:', type);

  if (!id || !type) {
    document.getElementById('detailsTitle').textContent = 'Erreur : ID ou type manquant';
    console.error('Paramètres manquants dans l\'URL');
    return;
  }

  try {
    const url = `${API_BASE}/api/details?type=${type}&id=${encodeURIComponent(id)}`;
    console.log('Fetching:', url);
    
    const data = await fetchJSON(url);
    console.log('Données reçues:', data);
    
    // Changer le label selon le type
    const directorsLabel = document.getElementById('detailsDirectorsLabel');
    if (directorsLabel) {
      directorsLabel.textContent = type === 'series' ? 'Créateur(s)' : 'Réalisateur(s)';
    }
    
    // Remplir les informations
    document.getElementById('detailsTitle').textContent = data.title || 'Titre non disponible';
    document.getElementById('detailsPoster').src = data.poster_url || '';
    document.getElementById('detailsPoster').alt = data.title || '';
    
    // Meta informations
    document.getElementById('detailsGenre').textContent = data.genre || 'Genre non disponible';
    document.getElementById('detailsYear').textContent = data.year || '';
    document.getElementById('detailsDuration').textContent = data.duration || '';
    
    // Synopsis
    document.getElementById('detailsSynopsis').textContent = data.synopsis || 'Synopsis non disponible';
    
    // Réalisateurs
    document.getElementById('detailsDirectors').textContent = data.directors || 'Non disponible';
    
    // Acteurs
    document.getElementById('detailsActors').textContent = data.actors || 'Non disponible';
    
    // Charger les recommandations
    await loadRecommendations(type, id);
    
  } catch (error) {
    console.error('Erreur chargement des détails:', error);
    document.getElementById('detailsTitle').textContent = 'Erreur de chargement';
    document.getElementById('detailsSynopsis').textContent = 'Impossible de charger les détails. Vérifiez que le serveur backend est en cours d\'exécution.';
  }
}

async function loadRecommendations(type, currentId) {
  try {
    const url = `${API_BASE}/api/recommendations?type=${type}&id=${encodeURIComponent(currentId)}&limit=6`;
    console.log('Chargement des recommandations:', url);
    
    const data = await fetchJSON(url);
    const items = data.items || [];
    
    const container = document.getElementById('recommendationsContainer');
    
    if (items.length === 0) {
      container.innerHTML = '<p style="text-align:center; color: rgba(255,255,255,.7);">Aucune recommandation disponible</p>';
      return;
    }
    
    container.innerHTML = '';
    
    items.forEach(item => {
      const card = document.createElement('div');
      card.className = 'recommendation-card';
      card.style.cursor = 'pointer';
      
      card.innerHTML = `
        <div class="recommendation-poster">
          <img src="${item.poster_url}" alt="${item.title}">
        </div>
        <h4>${item.title}</h4>
        <span>${item.year || ''}</span>
      `;
      
      card.addEventListener('click', () => {
        window.location.href = `details.html?type=${type}&id=${encodeURIComponent(item.id)}`;
      });
      
      container.appendChild(card);
    });
    
  } catch (error) {
    console.error('Erreur chargement recommandations:', error);
  }
}

document.addEventListener('DOMContentLoaded', loadDetails);
